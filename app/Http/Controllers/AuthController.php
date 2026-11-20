<?php

namespace App\Http\Controllers;

use App\Http\Requests\LoginRequest;
use App\Http\Requests\RegisterRequest;
use App\Models\AuditLog;
use App\Models\User;
use App\Services\GuestHistory;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

class AuthController extends Controller
{
    public function showLogin(): Response|RedirectResponse
    {
        if (Auth::check()) {
            return redirect()->route('dashboard');
        }

        return Inertia::render('Auth/Login');
    }

    public function showRegister(): Response|RedirectResponse
    {
        if (Auth::check()) {
            return redirect()->route('dashboard');
        }

        return Inertia::render('Auth/Register');
    }

    public function register(RegisterRequest $request, GuestHistory $guest): JsonResponse|RedirectResponse
    {
        $user = User::create($request->safe()->only(['name', 'email', 'password'])); // password hashed by the model cast
        $guest->clear();
        Auth::login($user);
        $request->session()->regenerate();
        AuditLog::record('register', $request, $user->id);

        return $this->done($request, $user);
    }

    public function login(LoginRequest $request, GuestHistory $guest): JsonResponse|RedirectResponse
    {
        $key = 'login:'.Str::transliterate(mb_strtolower($request->input('email'))).'|'.$request->ip();
        $max = (int) config('hulagwai.limits.login_attempts');

        if (RateLimiter::tooManyAttempts($key, $max)) {
            AuditLog::record('login_locked', $request);
            throw ValidationException::withMessages([
                'email' => ['Too many attempts. Try again in '.RateLimiter::availableIn($key).' seconds.'],
            ])->status(429);
        }

        if (! Auth::attempt($request->only('email', 'password'), false)) {
            RateLimiter::hit($key, 60 * 5);
            AuditLog::record('login_failed', $request);
            // Same message for "no such user" and "wrong password" (no account enumeration).
            throw ValidationException::withMessages(['email' => ['These credentials do not match our records.']]);
        }

        RateLimiter::clear($key);
        $guest->clear();
        $request->session()->regenerate(); // session-fixation defence
        AuditLog::record('login_success', $request);

        return $this->done($request, $request->user());
    }

    public function logout(Request $request): JsonResponse|RedirectResponse
    {
        AuditLog::record('logout', $request);
        Auth::guard('web')->logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return $request->expectsJson() ? response()->json(['ok' => true]) : redirect('/');
    }

    private function done(Request $request, User $user): JsonResponse|RedirectResponse
    {
        return $request->expectsJson()
            ? response()->json(['user' => $user->toAccountArray()])
            : redirect()->intended('/');
    }
}

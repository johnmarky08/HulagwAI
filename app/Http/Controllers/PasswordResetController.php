<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\ExtensionToken;
use App\Models\User;
use Illuminate\Auth\Events\PasswordReset;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Password;
use Illuminate\Support\Str;
use Illuminate\Validation\Rules\Password as PasswordRule;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

/** Forgot / reset password. Tokens are created, hashed and expired by Laravel's password broker. */
class PasswordResetController extends Controller
{
    /** Same answer whether or not the address has an account (no account enumeration). */
    private const SENT = 'If an account exists for that email, a password reset link is on its way. Check your inbox and spam folder.';

    public function showForgot(): Response|RedirectResponse
    {
        return Auth::check() ? redirect()->route('profile') : Inertia::render('Auth/ForgotPassword');
    }

    /** POST /forgot-password {email} */
    public function sendLink(Request $request): JsonResponse
    {
        $request->merge(['email' => mb_strtolower(trim((string) $request->input('email')))]);
        $request->validate(['email' => ['required', 'email:rfc', 'max:190']]);

        try {
            // Broker statuses (sent / unknown user / throttled) are deliberately not revealed.
            $status = Password::sendResetLink($request->only('email'));
            AuditLog::record('password_reset_requested', $request, null, ['status' => $status]);
        } catch (\Throwable $e) {
            report($e); // e.g. mail server down: logged for the admin, generic answer for the visitor
        }

        return response()->json(['ok' => true, 'message' => self::SENT]);
    }

    public function showReset(Request $request, string $token): Response|RedirectResponse
    {
        if (Auth::check()) {
            return redirect()->route('profile');
        }

        return Inertia::render('Auth/ResetPassword', [
            'token' => Str::limit($token, 128, ''),
            'email' => Str::limit((string) $request->query('email', ''), 190, ''),
        ]);
    }

    /** POST /reset-password {token, email, password, password_confirmation} */
    public function reset(Request $request): JsonResponse
    {
        $request->merge(['email' => mb_strtolower(trim((string) $request->input('email')))]);
        $request->validate([
            'token' => ['required', 'string', 'max:128'],
            'email' => ['required', 'email:rfc', 'max:190'],
            'password' => ['required', 'string', 'max:128', 'confirmed', PasswordRule::defaults()],
        ]);

        $status = Password::reset(
            $request->only('email', 'password', 'password_confirmation', 'token'),
            function (User $user, string $password) {
                $user->forceFill(['password' => $password])->setRememberToken(Str::random(60));
                $user->save();
                // A reset means the old credentials may be compromised: revoke paired browser extensions too.
                ExtensionToken::where('user_id', $user->id)->delete();
                event(new PasswordReset($user));
            },
        );

        if ($status !== Password::PASSWORD_RESET) {
            AuditLog::record('password_reset_failed', $request);
            throw ValidationException::withMessages(['email' => ['This reset link is invalid or has expired. Request a new one.']]);
        }
        AuditLog::record('password_reset', $request);

        return response()->json(['ok' => true, 'message' => 'Your password has been reset. You can now log in.']);
    }
}

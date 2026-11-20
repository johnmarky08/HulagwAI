<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\User;
use App\Services\GuestHistory;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

/**
 * "Continue with Google" — OAuth 2.0 authorization-code flow with PKCE and a CSRF state, using OpenID Connect
 * userinfo. No extra package: two HTTPS calls to Google. Signed-in users hitting /auth/google/redirect LINK Google
 * to their existing account instead of signing in.
 */
class GoogleAuthController extends Controller
{
    private const AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';

    private const TOKEN_URL = 'https://oauth2.googleapis.com/token';

    private const USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo';

    public static function enabled(): bool
    {
        return filled(config('services.google.client_id')) && filled(config('services.google.client_secret'));
    }

    /** GET /auth/google/redirect */
    public function redirect(Request $request): RedirectResponse
    {
        if (! self::enabled()) {
            return $this->fail($request, 'google_unavailable');
        }

        $state = Str::random(40);
        $verifier = Str::random(64);
        $request->session()->put('google_oauth', [
            'state' => $state,
            'verifier' => $verifier,
            'link' => (bool) $request->user(),
        ]);

        $query = http_build_query([
            'client_id' => config('services.google.client_id'),
            'redirect_uri' => config('services.google.redirect'),
            'response_type' => 'code',
            'scope' => 'openid email profile',
            'state' => $state,
            'code_challenge' => rtrim(strtr(base64_encode(hash('sha256', $verifier, true)), '+/', '-_'), '='),
            'code_challenge_method' => 'S256',
            'prompt' => 'select_account',
        ], '', '&', PHP_QUERY_RFC3986);

        return redirect()->away(self::AUTH_URL.'?'.$query);
    }

    /** GET /auth/google/callback?code=&state= */
    public function callback(Request $request, GuestHistory $guest): RedirectResponse
    {
        $flow = $request->session()->pull('google_oauth');
        $state = (string) $request->query('state', '');

        if (! is_array($flow) || $state === '' || ! hash_equals((string) $flow['state'], $state)) {
            return $this->fail($request, 'google_failed');
        }
        if ($request->filled('error') || ! $request->filled('code')) {
            return $this->fail($request, 'google_cancelled', $flow['link']);
        }

        $profile = $this->fetchProfile((string) $request->query('code'), (string) $flow['verifier']);
        if ($profile === null) {
            return $this->fail($request, 'google_failed', $flow['link']);
        }
        if (! filter_var($profile['email_verified'] ?? false, FILTER_VALIDATE_BOOLEAN)) {
            return $this->fail($request, 'google_email_unverified', $flow['link']);
        }

        $sub = (string) $profile['sub'];
        $email = mb_strtolower(trim((string) $profile['email']));

        // Linking from the profile page.
        if ($flow['link'] && ($current = $request->user())) {
            $owner = User::where('google_id', $sub)->first();
            if ($owner && $owner->id !== $current->id) {
                return $this->fail($request, 'google_in_use', true);
            }
            $current->forceFill(['google_id' => $sub])->save();
            AuditLog::record('google_linked', $request, $current->id);

            return redirect('/profile?google=linked');
        }

        $user = User::where('google_id', $sub)->first();
        if (! $user && ($user = User::where('email', $email)->first())) {
            // Google verified this address, so it is safe to attach Google to the existing account.
            $user->forceFill(['google_id' => $sub])->save();
        }
        $created = false;
        if (! $user) {
            $name = Str::limit(trim((string) ($profile['name'] ?? '')) ?: Str::before($email, '@'), 60, '');
            $user = new User(['name' => mb_strlen($name) >= 2 ? $name : 'HulagwAI user', 'email' => $email]);
            $user->forceFill(['google_id' => $sub, 'email_verified_at' => now()])->save();
            $created = true;
        }

        $guest->clear();
        Auth::login($user);
        $request->session()->regenerate(); // session-fixation defence
        AuditLog::record($created ? 'register_google' : 'login_google', $request, $user->id);

        return redirect()->intended('/dashboard');
    }

    /** DELETE /api/v1/account/google -> unlink (only when a password exists, so the account stays reachable) */
    public function unlink(Request $request): JsonResponse
    {
        $user = $request->user();
        if ($user->password === null) {
            return response()->json([
                'code' => 'password_required',
                'message' => 'Set a password first, otherwise you would no longer be able to log in.',
            ], 422);
        }
        $user->forceFill(['google_id' => null])->save();
        AuditLog::record('google_unlinked', $request, $user->id);

        return response()->json(['ok' => true]);
    }

    /** @return array<string,mixed>|null */
    private function fetchProfile(string $code, string $verifier): ?array
    {
        try {
            $token = Http::asForm()->acceptJson()->timeout(10)->post(self::TOKEN_URL, [
                'code' => $code,
                'client_id' => config('services.google.client_id'),
                'client_secret' => config('services.google.client_secret'),
                'redirect_uri' => config('services.google.redirect'),
                'grant_type' => 'authorization_code',
                'code_verifier' => $verifier,
            ]);
            $access = $token->successful() ? $token->json('access_token') : null;
            if (! is_string($access) || $access === '') {
                return null;
            }

            $info = Http::withToken($access)->acceptJson()->timeout(10)->get(self::USERINFO_URL);
            $data = $info->successful() ? $info->json() : null;

            return is_array($data) && filled($data['sub'] ?? null) && filter_var($data['email'] ?? null, FILTER_VALIDATE_EMAIL)
                ? $data : null;
        } catch (\Throwable) {
            return null;
        }
    }

    private function fail(Request $request, string $code, bool $toProfile = false): RedirectResponse
    {
        AuditLog::record('google_auth_failed', $request, $request->user()?->id, ['code' => $code]);

        return redirect(($toProfile && $request->user() ? '/profile' : '/login').'?error='.$code);
    }
}

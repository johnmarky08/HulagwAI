<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\ExtensionToken;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class ExtensionAuthController extends Controller
{
    private const PAIR_TTL_MINUTES = 3;

    private const TOKEN_TTL_DAYS = 30;

    /** Create a short-lived, single-use code from the signed-in HulagwAI site. */
    public function pair(Request $request): JsonResponse
    {
        /** @var User|null $user */
        $user = $request->user();
        if (! $user) {
            return response()->json(['code' => 'authentication_required', 'message' => 'Sign in to HulagwAI before pairing the extension.'], 401);
        }

        $code = bin2hex(random_bytes(16));
        Cache::put($this->pairKey($code), $user->getAuthIdentifier(), now()->addMinutes(self::PAIR_TTL_MINUTES));
        AuditLog::record('extension_pair_code_created', $request, (int) $user->getAuthIdentifier());

        return response()->json([
            'code' => $code,
            'expires_in' => self::PAIR_TTL_MINUTES * 60,
        ]);
    }

    /** Exchange the one-time site code for a revocable, expiring extension token. */
    public function exchange(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'code' => ['required', 'string', 'size:32', 'regex:/\A[a-f0-9]{32}\z/i'],
        ]);
        $userId = Cache::pull($this->pairKey($validated['code']));
        if (! $userId) {
            throw ValidationException::withMessages([
                'code' => ['That pairing code is invalid, already used, or expired. Generate a new code on HulagwAI.'],
            ]);
        }

        $user = User::find($userId);
        if (! $user) {
            return response()->json(['code' => 'user_not_found', 'message' => 'The HulagwAI account could not be found.'], 404);
        }

        $plainText = bin2hex(random_bytes(32));
        $expiresAt = now()->addDays(self::TOKEN_TTL_DAYS);
        ExtensionToken::create([
            'user_id' => $user->getAuthIdentifier(),
            'name' => 'HulagwAI image scanner',
            'token_hash' => hash('sha256', $plainText),
            'expires_at' => $expiresAt,
        ]);
        AuditLog::record('extension_token_created', $request, (int) $user->getAuthIdentifier());

        return response()->json([
            'token' => $plainText,
            'expires_at' => $expiresAt->toIso8601String(),
        ]);
    }

    public function revoke(Request $request): JsonResponse
    {
        /** @var ExtensionToken|null $token */
        $token = $request->attributes->get('extension_token');
        if ($token && ! $token->revoked_at) {
            $token->forceFill(['revoked_at' => now()])->save();
            AuditLog::record('extension_token_revoked', $request, (int) $token->user_id);
        }

        return response()->json(['ok' => true]);
    }

    private function pairKey(string $code): string
    {
        return 'hulagwai:extension-pair:'.hash('sha256', Str::lower($code));
    }
}

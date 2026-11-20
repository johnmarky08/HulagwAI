<?php

namespace App\Http\Middleware;

use App\Models\ExtensionToken;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class ResolveExtensionToken
{
    public function handle(Request $request, Closure $next, string $required = 'optional'): Response
    {
        $plainText = $request->bearerToken();
        if (! $plainText) {
            return $required === 'required'
                ? response()->json(['code' => 'extension_auth_required', 'message' => 'Pair the browser extension with your HulagwAI account.'], 401)
                : $next($request);
        }

        if (! preg_match('/\A[a-f0-9]{64}\z/i', $plainText)) {
            return response()->json(['code' => 'invalid_extension_token', 'message' => 'The extension token is invalid or expired.'], 401);
        }

        $token = ExtensionToken::query()
            ->with('user')
            ->where('token_hash', hash('sha256', $plainText))
            ->whereNull('revoked_at')
            ->where('expires_at', '>', now())
            ->first();

        if (! $token || ! $token->user) {
            return response()->json(['code' => 'invalid_extension_token', 'message' => 'The extension token is invalid or expired.'], 401);
        }

        $request->attributes->set('extension_token', $token);
        $request->setUserResolver(fn () => $token->user);
        if (! $token->last_used_at || $token->last_used_at->lt(now()->subMinutes(5))) {
            $token->forceFill(['last_used_at' => now()])->saveQuietly();
        }

        return $next($request);
    }
}

<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/** Baseline hardening headers (OWASP A05 Security Misconfiguration). */
class SecurityHeaders
{
    public function handle(Request $request, Closure $next): Response
    {
        $response = $next($request);

        // Anything that is not production may talk to the Vite dev server on ANY local port
        // (Vite may pick 5174, 5175 ... if 5173 is busy). IPv6 literals such as [::1] are not valid CSP sources, so
        // vite.config.js pins the dev server to 127.0.0.1.
        $dev = ! app()->isProduction();
        $vite = $dev ? ' http://localhost:* http://127.0.0.1:*' : '';
        $ws = $dev ? ' ws://localhost:* ws://127.0.0.1:*' : '';

        $csp = implode('; ', [
            "default-src 'self'",
            "script-src 'self'".$vite,
            "style-src 'self' 'unsafe-inline'".$vite,   // Svelte injects scoped styles
            "img-src 'self' data: blob:".$vite,
            "font-src 'self' data:".$vite,
            "connect-src 'self'".$vite.$ws,
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]);

        $h = $response->headers;
        if (! $h->has('Content-Security-Policy')) {
            $h->set('Content-Security-Policy', $csp);
        }
        $h->set('X-Content-Type-Options', 'nosniff');
        $h->set('X-Frame-Options', 'DENY');
        $h->set('Referrer-Policy', 'strict-origin-when-cross-origin');
        $h->set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()');
        $h->set('Cross-Origin-Opener-Policy', 'same-origin');
        $h->set('Cross-Origin-Resource-Policy', 'same-origin');
        if ($request->isSecure()) {
            $h->set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
        }
        if ($request->is('api/*')) {
            $h->set('Cache-Control', $h->get('Cache-Control') && str_contains($h->get('Cache-Control'), 'max-age') ? $h->get('Cache-Control') : 'no-store, private');
        }

        return $response;
    }
}

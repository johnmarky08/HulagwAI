<?php

use App\Http\Middleware\HandleInertiaRequests;
use App\Http\Middleware\SecurityHeaders;
use App\Http\Middleware\ResolveExtensionToken;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__ . '/../routes/web.php',
        commands: __DIR__ . '/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->alias([
            'extension.token' => ResolveExtensionToken::class,
        ]);
        // Pair-code creation stays CSRF-protected; these paths require one-time codes or scoped bearer tokens.
        $middleware->validateCsrfTokens(except: [
            'api/v1/extension/exchange',
            'api/v1/extension/token',
            'api/v1/extension/analyses',
            'api/v1/extension/analyses/*',
        ]);
        $middleware->web(append: [
            HandleInertiaRequests::class,
            SecurityHeaders::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        // The JSON API always answers with JSON (never an HTML error page / stack trace).
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $e) => $request->is('api/*') || $request->expectsJson());
    })->create();

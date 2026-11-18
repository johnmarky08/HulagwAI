<?php

/*
|--------------------------------------------------------------------------
| HulagwAI settings
|--------------------------------------------------------------------------
| Everything tunable about uploads, quotas, the ML service link and guest
| (not-signed-in) behaviour lives here so the frontend team never has to
| touch controller code.
*/

return [

    'ml' => [
        // Must stay on loopback. The ML service is never exposed to browsers.
        'url' => env('ML_SERVICE_URL', 'http://127.0.0.1:8001'),
        'token' => env('ML_SERVICE_TOKEN'),
        'timeout' => (int) env('ML_TIMEOUT', 90),
        'connect_timeout' => 3,
    ],

    'upload' => [
        'max_bytes' => 5 * 1024 * 1024,                     // 5 MB per image
        'extensions' => ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'],
        'min_side' => 16,
        'max_side' => 8192,
        'max_pixels' => 40_000_000,
    ],

    'quota' => [
        'user_bytes' => 50 * 1024 * 1024,                   // 50 MB of stored originals per account
    ],

    'guest' => [
        'history_limit' => 10,                              // newest N results kept in the session
        'pending_limit' => 2,                               // concurrent in-flight analyses per session
        'stale_minutes' => 15,                              // in-flight guest rows older than this are purged
    ],

    'queue' => [
        'max_backlog' => 50,                                // refuse new work above this many queued analyses
    ],

    'history' => [
        'per_page' => 6,
    ],

    'limits' => [
        // name => [attempts, decay minutes]
        'analyze_per_minute' => 6,
        'analyze_per_hour' => 60,
        'login_attempts' => 5,
        'register_per_hour' => 10,
        'api_per_minute' => 120,
    ],

    'password' => [
        'min' => 10,
        'check_breached' => (bool) env('PASSWORD_CHECK_BREACHED', false), // needs internet (HIBP k-anonymity)
    ],
];

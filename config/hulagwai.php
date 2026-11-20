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

    /*
    | Notices shown to users (CSST 102: intended use, limitations, responsible use).
    | Served by the API so every frontend shows the same wording.
    */
    'notice' => [
        'intended_use' => 'HulagwAI gives a second opinion on whether an image is likely AI-generated or real. It is an educational decision-support tool, not proof, and must not be the only basis for accusing, penalising or judging anyone.',
        'limitations' => [
            'Predictions are probabilities and can be wrong in either direction.',
            'Small, heavily compressed, screenshotted or edited images are unreliable; partly AI-edited photos may be judged as real.',
            'Generators released after the training data may not be recognised.',
            'Missing metadata proves nothing, and metadata can be forged.',
            'The confidence score is how strongly the model favours its prediction, not the probability that the image is authentic.',
        ],
        'attribution' => 'Generator attribution is a closed-set estimate over a few well-known AI families. It can be wrong, cannot name generators it was not trained on (it should then answer "unknown"), and is more reliable for the family than for the exact version.',
        'evidence' => 'The evidence list shows signals from the detector models and the file itself. It does not identify specific defects such as extra fingers or garbled text, and a highlighted region shows where the model looks, not a verified flaw.',
        'privacy' => 'Do not upload images of other people, minors, IDs or confidential material without permission. Guests: the image is deleted right after analysis and only the result stays in your session. Signed-in users: images are stored encrypted until you delete them.',
        'responsible_use' => [
            'Treat an AI-generated verdict as a lead to verify (source, context, other tools), never as a conclusion.',
            'Prefer Inconclusive over a forced answer; keep a human in the loop for any high-impact decision.',
            'Report suspected errors so the model can be re-evaluated.',
        ],
    ],

];

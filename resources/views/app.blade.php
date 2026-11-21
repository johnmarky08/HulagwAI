<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1">
        @php
            // Browsers cache favicons very aggressively. Versioning the URL with the file's modification time makes
            // them fetch the new logo as soon as the file is replaced (and keep caching it until the next change).
            $icon = fn (string $path) => '/'.$path.(is_file(public_path($path)) ? '?v='.filemtime(public_path($path)) : '');
        @endphp
        <link rel="icon" type="image/svg+xml" href="{{ $icon('favicon.svg') }}">
        <link rel="icon" type="image/png" sizes="32x32" href="{{ $icon('icons/hulagwai-32.png') }}">
        <link rel="icon" type="image/x-icon" href="{{ $icon('favicon.ico') }}">
        <link rel="apple-touch-icon" href="{{ $icon('icons/hulagwai-128.png') }}">
        <title inertia>HulagwAI</title>
        @vite(['resources/css/app.css', 'resources/js/app.js'])
        @inertiaHead
    </head>
    <body>
        @inertia
    </body>
</html>

<?php

namespace App\Http\Middleware;

use Illuminate\Http\Request;
use Inertia\Middleware;

class HandleInertiaRequests extends Middleware
{
    /**
     * The root template that's loaded on the first page visit.
     *
     * @see https://inertiajs.com/server-side-setup#root-template
     *
     * @var string
     */
    protected $rootView = 'app';

    /**
     * Determines the current asset version.
     *
     * @see https://inertiajs.com/asset-versioning
     */
    public function version(Request $request): ?string
    {
        return parent::version($request);
    }

    /**
     * Props shared with every page. Keep secrets out of here - everything is visible to the browser.
     *
     * @return array<string, mixed>
     */
    public function share(Request $request): array
    {
        return [
            ...parent::share($request),
            'auth' => fn () => [
                'user' => $request->user() ? ['id' => $request->user()->id, 'name' => $request->user()->name, 'email' => $request->user()->email] : null,
            ],
            'limits' => fn () => [
                'max_upload_mb' => (int) (config('hulagwai.upload.max_bytes') / 1048576),
                'quota_mb' => (int) (config('hulagwai.quota.user_bytes') / 1048576),
                'extensions' => array_keys(config('hulagwai.upload.extensions')),
            ],
        ];
    }
}

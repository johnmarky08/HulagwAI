<?php

namespace App\Providers;

use App\Services\FileVault;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;
use Illuminate\Validation\Rules\Password;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(FileVault::class);
    }

    public function boot(): void
    {
        $cfg = config('hulagwai.limits');
        $who = fn (Request $r) => $r->user()?->getAuthIdentifier() ?? $r->ip();

        RateLimiter::for('api', fn (Request $r) => Limit::perMinute($cfg['api_per_minute'])->by($who($r)));

        RateLimiter::for('analyze', fn (Request $r) => [
            Limit::perMinute($cfg['analyze_per_minute'])->by('a1:'.$who($r)),
            Limit::perHour($cfg['analyze_per_hour'])->by('a2:'.$who($r)),
            Limit::perHour($cfg['analyze_per_hour'] * 3)->by('a3:'.$r->ip()), // shared-IP ceiling
        ]);

        RateLimiter::for('auth', fn (Request $r) => Limit::perMinute(20)->by('auth:'.$r->ip()));
        RateLimiter::for('register', fn (Request $r) => Limit::perHour($cfg['register_per_hour'])->by('reg:'.$r->ip()));
        RateLimiter::for('password-reset', fn (Request $r) => [
            Limit::perHour(5)->by('pr-ip:'.$r->ip()),
            Limit::perHour(3)->by('pr-mail:'.sha1(mb_strtolower((string) $r->input('email')))),
        ]);
        RateLimiter::for('report', fn (Request $r) => Limit::perMinute(10)->by('rep:'.$who($r)));

        Password::defaults(function () {
            $rule = Password::min((int) config('hulagwai.password.min'))->mixedCase()->numbers();

            return config('hulagwai.password.check_breached') ? $rule->uncompromised() : $rule;
        });
    }
}

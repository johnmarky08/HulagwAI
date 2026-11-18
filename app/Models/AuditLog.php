<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;

class AuditLog extends Model
{
    public const UPDATED_AT = null;

    protected $fillable = ['event', 'user_id', 'ip_hash', 'user_agent', 'context'];

    protected function casts(): array
    {
        return ['context' => 'array'];
    }

    /** @param array<string, scalar|null> $context  Never put secrets, emails or filenames in here. */
    public static function record(string $event, ?Request $request = null, ?int $userId = null, array $context = []): void
    {
        try {
            $request ??= request();
            static::create([
                'event' => $event,
                'user_id' => $userId ?? $request?->user()?->getAuthIdentifier(),
                'ip_hash' => $request?->ip() ? hash_hmac('sha256', $request->ip(), (string) config('app.key')) : null,
                'user_agent' => $request ? mb_substr((string) $request->userAgent(), 0, 160) : null,
                'context' => $context ?: null,
            ]);
        } catch (\Throwable $e) {
            report($e); // auditing must never break the request
        }
    }
}

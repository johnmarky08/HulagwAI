<?php

namespace App\Services;

use App\Models\Analysis;
use Illuminate\Http\Request;

/**
 * The ONLY place that decides "may this visitor see analysis X?".
 * Signed-in users: rows they own. Guests: ids present in their own session.
 * Anything else -> null -> 404 (no existence leak, no IDOR).
 */
final class AnalysisAccess
{
    public function __construct(private readonly GuestHistory $guest) {}

    public static function validId(string $id): bool
    {
        return (bool) preg_match('/^[0-9A-HJKMNP-TV-Z]{26}$/i', $id);
    }

    /** @return array<string,mixed>|null */
    public function record(Request $request, string $id): ?array
    {
        if (! self::validId($id)) {
            return null;
        }
        $id = strtoupper($id);

        if ($user = $request->user()) {
            $row = Analysis::where('uuid', $id)->where('user_id', $user->getAuthIdentifier())->first();

            return $row ? Records::fromModel($row) : null;
        }

        if ($item = $this->guest->find($id)) {
            return $item;
        }
        if (! in_array($id, $this->guest->pending(), true)) {
            return null;
        }
        $row = Analysis::where('uuid', $id)->whereNull('user_id')->first();
        if (! $row) {
            $this->guest->removePending($id);

            return null;
        }

        return $row->status->value === 'done' ? $this->guest->claim($row) : Records::fromModel($row, false);
    }

    /** DB row owned by the current visitor (signed-in) or an in-flight guest row listed in their session. */
    public function row(Request $request, string $id): ?Analysis
    {
        if (! self::validId($id)) {
            return null;
        }
        $id = strtoupper($id);
        if ($user = $request->user()) {
            return Analysis::where('uuid', $id)->where('user_id', $user->getAuthIdentifier())->first();
        }

        return in_array($id, $this->guest->pending(), true) ? Analysis::where('uuid', $id)->whereNull('user_id')->first() : null;
    }
}

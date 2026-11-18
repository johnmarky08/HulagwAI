<?php

namespace App\Services;

use App\Models\Analysis;
use Illuminate\Http\Request;
use Illuminate\Support\Collection;

/** One code path for the History screen, whether the data comes from MySQL (signed in) or the session (guest). */
final class HistoryService
{
    public function __construct(private readonly GuestHistory $guest, private readonly Presenter $presenter) {}

    /** @return Collection<int, array<string,mixed>> */
    public function records(Request $request): Collection
    {
        if ($user = $request->user()) {
            return Analysis::query()
                ->where('user_id', $user->getAuthIdentifier())
                ->where('status', 'done')
                ->get()
                ->map(fn (Analysis $a) => Records::fromModel($a, false));
        }

        return collect($this->guest->all());
    }

    /**
     * @param array{search?:?string,result?:?string,range?:?string,sort?:?string,page?:int,per_page?:int} $f
     * @return array{data:list<array<string,mixed>>,meta:array<string,int>,stats:array<string,int>}
     */
    public function query(Request $request, array $f): array
    {
        $all = $this->records($request);

        $stats = [
            'total' => $all->count(),
            'likely_real' => $all->where('verdict', 'real')->count(),
            'ai_generated' => $all->where('verdict', 'ai_generated')->count(),
            'inconclusive' => $all->where('verdict', 'inconclusive')->count(),
        ];

        $rows = $all
            ->when(($f['result'] ?? 'all') !== 'all', fn ($c) => $c->where('verdict', $f['result']))
            ->when(($f['range'] ?? 'all') !== 'all', function ($c) use ($f) {
                $since = now()->subDays((int) rtrim((string) $f['range'], 'd'));

                return $c->filter(fn ($r) => $r['analyzed_at'] && strtotime($r['analyzed_at']) >= $since->timestamp);
            })
            ->when(filled($f['search'] ?? null), function ($c) use ($f) {
                $needle = mb_strtolower((string) $f['search']);

                return $c->filter(fn ($r) => str_contains(mb_strtolower((string) $r['filename']), $needle));
            });

        $rows = match ($f['sort'] ?? 'newest') {
            'oldest' => $rows->sortBy('analyzed_at'),
            'confidence_desc' => $rows->sortByDesc('confidence'),
            'confidence_asc' => $rows->sortBy('confidence'),
            default => $rows->sortByDesc('analyzed_at'),
        };

        $perPage = max(1, min(50, (int) ($f['per_page'] ?? config('hulagwai.history.per_page'))));
        $total = $rows->count();
        $last = max(1, (int) ceil($total / $perPage));
        $page = max(1, min($last, (int) ($f['page'] ?? 1)));

        return [
            'data' => $rows->forPage($page, $perPage)->map(fn ($r) => $this->presenter->listItem($r))->values()->all(),
            'meta' => [
                'page' => $page, 'per_page' => $perPage, 'total' => $total, 'last_page' => $last,
                'from' => $total ? ($page - 1) * $perPage + 1 : 0, 'to' => min($total, $page * $perPage),
            ],
            'stats' => $stats,
        ];
    }

    /** @return list<array<string,scalar|null>> flat rows for CSV/JSON export (no image data) */
    public function exportRows(Request $request): array
    {
        return $this->records($request)->sortByDesc('analyzed_at')->map(fn ($r) => [
            'id' => $r['id'],
            'filename' => $r['filename'],
            'format' => $r['format'],
            'width' => $r['width'],
            'height' => $r['height'],
            'size_bytes' => $r['size_bytes'],
            'verdict' => $r['verdict'],
            'ai_probability' => $r['ai_probability'],
            'confidence' => $r['confidence'],
            'sha256' => $r['sha256'],
            'analyzed_at' => $r['analyzed_at'],
        ])->values()->all();
    }
}

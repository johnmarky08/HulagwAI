<?php

namespace App\Http\Controllers;

use App\Exceptions\QuotaExceeded;
use App\Http\Requests\UploadImageRequest;
use App\Jobs\AnalyzeImageJob;
use App\Models\Analysis;
use App\Models\AuditLog;
use App\Models\ModelVersion;
use App\Models\User;
use App\Services\AnalysisAccess;
use App\Services\FileVault;
use App\Services\GuestHistory;
use App\Services\ImageGuard;
use App\Services\Presenter;
use App\Services\Records;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class AnalysisController extends Controller
{
    public function __construct(
        private readonly AnalysisAccess $access,
        private readonly Presenter $presenter,
        private readonly FileVault $vault,
        private readonly GuestHistory $guest,
    ) {}

    /** POST /api/v1/analyses  (multipart: image) */
    public function store(UploadImageRequest $request, ImageGuard $guard): JsonResponse
    {
        $img = $guard->inspect($request->file('image'));
        $user = $request->user();

        if (! $user && count($this->guest->pending()) >= (int) config('hulagwai.guest.pending_limit')) {
            return $this->error('too_many_pending', 'Please wait for your current analysis to finish.', 429);
        }
        if (Analysis::where('status', 'queued')->count() >= (int) config('hulagwai.queue.max_backlog')) {
            return $this->error('busy', 'The service is busy. Please try again in a moment.', 503);
        }

        if ($user && ($dup = $this->duplicate($user->getAuthIdentifier(), $img['sha256']))) {
            return response()->json([...$this->presenter->full(Records::fromModel($dup)), 'duplicate' => true]);
        }

        $uuid = (string) Str::ulid();
        $path = $this->vault->put($img['bytes'], $uuid.':original');

        try {
            DB::transaction(function () use ($user, $img, $uuid, $path) {
                if ($user) {
                    // Serialise this user's uploads so concurrent requests cannot overshoot the quota.
                    User::whereKey($user->getAuthIdentifier())->lockForUpdate()->first();
                    $used = (int) Analysis::where('user_id', $user->getAuthIdentifier())
                        ->whereNotIn('status', ['failed', 'cancelled'])->sum('size_bytes');
                    $limit = (int) config('hulagwai.quota.user_bytes');
                    if ($used + $img['size'] > $limit) {
                        throw new QuotaExceeded($used, $limit);
                    }
                }
                Analysis::create([
                    'uuid' => $uuid, 'user_id' => $user?->getAuthIdentifier(), 'status' => 'queued', 'stage' => 'queued', 'progress' => 5,
                    'sha256' => $img['sha256'], 'original_name' => $img['name'], 'mime_type' => $img['mime'], 'format' => $img['format'],
                    'width' => $img['width'], 'height' => $img['height'], 'size_bytes' => $img['size'], 'file_path' => $path,
                ]);
            });
        } catch (QuotaExceeded $e) {
            $this->vault->delete($path);

            return response()->json([
                'code' => 'quota_exceeded',
                'message' => 'Storage limit reached. Delete some analyses from History to free space.',
                'used_bytes' => $e->used, 'limit_bytes' => $e->limit,
            ], 413);
        } catch (\Throwable $e) {
            $this->vault->delete($path);
            throw $e;
        }

        if (! $user) {
            $this->guest->addPending($uuid);
        }
        AnalyzeImageJob::dispatch($uuid);
        AuditLog::record('analysis_created', $request, $user?->getAuthIdentifier(), ['bytes' => $img['size'], 'format' => $img['format']]);

        return response()->json($this->presenter->status(Records::fromModel(Analysis::where('uuid', $uuid)->firstOrFail(), false)), 202);
    }

    /** GET /api/v1/analyses/{id}  -> progress while running, full result when done */
    public function show(Request $request, string $id): JsonResponse
    {
        $rec = $this->access->record($request, $id);
        if (! $rec) {
            return $this->error('not_found', 'Analysis not found.', 404);
        }

        return response()->json($rec['status'] === 'done' ? $this->presenter->full($rec) : $this->presenter->status($rec));
    }

    /** GET /api/v1/analyses/{id}/image?variant=preview|thumb */
    public function image(Request $request, string $id): Response|JsonResponse
    {
        $variant = $request->query('variant') === 'thumb' ? 'thumb' : 'preview';
        $rec = $this->access->record($request, $id);
        if (! $rec || $rec['status'] !== 'done') {
            return $this->error('not_found', 'Image not found.', 404);
        }

        $bytes = $this->imageBytes($request, $rec, $variant);
        if ($bytes === null) {
            return $this->error('not_found', 'Image not found.', 404);
        }

        return response($bytes, 200, [
            'Content-Type' => 'image/jpeg',
            'X-Content-Type-Options' => 'nosniff',
            'Content-Security-Policy' => "default-src 'none'; sandbox",
            'Cache-Control' => 'private, max-age=300',
            'Content-Disposition' => 'inline; filename="image.jpg"',
        ]);
    }

    /** DELETE /api/v1/analyses/{id}  -> cancel (if running) or delete (if finished) */
    public function destroy(Request $request, string $id): JsonResponse
    {
        if (! AnalysisAccess::validId($id)) {
            return $this->error('not_found', 'Analysis not found.', 404);
        }
        $id = strtoupper($id);

        if (! $request->user() && $this->guest->find($id)) {
            $this->guest->remove($id);

            return response()->json(['ok' => true]);
        }

        $row = $this->access->row($request, $id);
        if (! $row) {
            return $this->error('not_found', 'Analysis not found.', 404);
        }

        $paths = DB::transaction(function () use ($row) {
            $locked = Analysis::whereKey($row->getKey())->lockForUpdate()->first();
            if (! $locked) {
                return [];
            }
            $paths = [$locked->file_path, $locked->preview_path, $locked->thumb_path];
            $locked->delete(); // a running job sees "no row" and stops; its late output is cleaned by the job

            return $paths;
        });
        foreach ($paths as $p) {
            $this->vault->delete($p);
        }
        if (! $request->user()) {
            $this->guest->removePending($id);
        }
        AuditLog::record('analysis_deleted', $request);

        return response()->json(['ok' => true]);
    }

    /** @param array<string,mixed> $rec */
    private function imageBytes(Request $request, array $rec, string $variant): ?string
    {
        if ($request->user()) {
            $row = Analysis::where('uuid', $rec['id'])->where('user_id', $request->user()->getAuthIdentifier())->first();
            $path = $variant === 'thumb' ? $row?->thumb_path : $row?->preview_path;

            return $path ? $this->vault->get($path, $rec['id'].':'.$variant) : null;
        }

        return isset($rec['thumb_b64']) ? (base64_decode($rec['thumb_b64'], true) ?: null) : null; // guests: thumbnail only
    }

    private function duplicate(int|string $userId, string $sha): ?Analysis
    {
        $latest = ModelVersion::query()->max('id');

        return Analysis::where('user_id', $userId)->where('sha256', $sha)->where('status', 'done')
            ->where('model_version_id', $latest)->latest('id')->first();
    }

    private function error(string $code, string $message, int $status): JsonResponse
    {
        return response()->json(['code' => $code, 'message' => $message], $status);
    }
}

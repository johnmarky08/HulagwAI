<?php

namespace App\Jobs;

use App\Enums\AnalysisStatus as S;
use App\Exceptions\MlException;
use App\Models\Analysis;
use App\Models\AuditLog;
use App\Services\FileVault;
use App\Services\MlClient;
use App\Services\ModelRegistry;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\DB;
use Throwable;

/**
 * Runs one analysis. Every status change happens inside a short transaction
 * with a row lock and an expected-previous-status check, so cancelling /
 * deleting from the UI can never be overwritten by a late worker.
 */
class AnalyzeImageJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 1;
    public int $timeout = 150;
    public bool $failOnTimeout = true;

    public function __construct(public string $uuid)
    {
        $this->afterCommit();
    }

    public function handle(FileVault $vault, MlClient $ml, ModelRegistry $registry): void
    {
        $a = Analysis::where('uuid', $this->uuid)->first();
        if (! $a || $a->status !== S::Queued) {
            return;
        }

        $newFiles = [];
        try {
            if (! $this->advance(S::Queued, S::Preprocessing, 15)) {
                return;
            }
            $bytes = $vault->get((string) $a->file_path, $a->uuid.':original');
            if (! hash_equals($a->sha256, hash('sha256', $bytes))) {
                throw new MlException('integrity_error');
            }

            if (! $this->advance(S::Preprocessing, S::Analyzing, 40)) {
                return;
            }
            $res = $ml->analyze($bytes);
            unset($bytes);

            if (! $this->advance(S::Analyzing, S::Finalizing, 85)) {
                return;
            }
            $mv = $registry->resolve($res['model']);
            $newFiles = [
                'preview' => $vault->put($res['preview'], $a->uuid.':preview'),
                'thumb' => $vault->put($res['thumb'], $a->uuid.':thumb'),
            ];

            $saved = DB::transaction(function () use ($res, $mv, $newFiles, $vault) {
                $row = Analysis::where('uuid', $this->uuid)->lockForUpdate()->first();
                if (! $row || $row->status !== S::Finalizing) {
                    return false;
                }
                $guest = $row->user_id === null;
                $originalPath = $row->file_path;
                $row->forceFill([
                    'status' => S::Done,
                    'stage' => 'done',
                    'progress' => 100,
                    'verdict' => $res['verdict'],
                    'ai_probability' => $res['ai_probability'],
                    'confidence' => $res['confidence'],
                    'model_version_id' => $mv->id,
                    'preview_path' => $newFiles['preview'],
                    'thumb_path' => $newFiles['thumb'],
                    'details' => $res['details'],
                    'analyzed_at' => now(),
                    'file_path' => $guest ? null : $originalPath, // guests: original is not kept
                ])->save();
                if ($guest) {
                    DB::afterCommit(fn () => $vault->delete($originalPath));
                }

                return true;
            });

            if (! $saved) { // cancelled/deleted while we were working
                foreach ($newFiles as $p) {
                    $vault->delete($p);
                }
                return;
            }
            AuditLog::record('analysis_done', null, $a->user_id, ['verdict' => $res['verdict']]);
        } catch (Throwable $e) {
            foreach ($newFiles as $p) {
                app(FileVault::class)->delete($p);
            }
            $this->markFailed($e);
        }
    }

    public function failed(Throwable $e): void
    {
        $this->markFailed($e);
    }

    private function advance(S $from, S $to, int $progress): bool
    {
        return DB::transaction(function () use ($from, $to, $progress) {
            $row = Analysis::where('uuid', $this->uuid)->lockForUpdate()->first();
            if (! $row || $row->status !== $from) {
                return false;
            }
            $row->forceFill(['status' => $to, 'stage' => $to->value, 'progress' => $progress])->save();

            return true;
        });
    }

    private function markFailed(Throwable $e): void
    {
        $code = $e instanceof MlException ? $e->errorCode : 'analysis_failed';
        if (! $e instanceof MlException) {
            report($e);
        }
        $vault = app(FileVault::class);

        $path = null;
        $uid = null;
        DB::transaction(function () use ($code, &$path, &$uid) {
            $row = Analysis::where('uuid', $this->uuid)->lockForUpdate()->first();
            if (! $row || $row->status->isFinal()) {
                return;
            }
            $path = $row->file_path;
            $uid = $row->user_id;
            $row->forceFill(['status' => S::Failed, 'stage' => 'failed', 'progress' => 0, 'error_code' => $code, 'file_path' => null])->save();
        });
        $vault->delete($path); // free the quota: failed analyses keep no image
        AuditLog::record('analysis_failed', null, $uid, ['code' => $code]);
    }
}

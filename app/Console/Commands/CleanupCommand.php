<?php

namespace App\Console\Commands;

use App\Models\Analysis;
use App\Services\FileVault;
use Illuminate\Console\Command;

class CleanupCommand extends Command
{
    protected $signature = 'hulagwai:cleanup';
    protected $description = 'Purge abandoned guest analyses, stale failed/cancelled rows and their encrypted files';

    public function handle(FileVault $vault): int
    {
        $guestCutoff = now()->subMinutes((int) config('hulagwai.guest.stale_minutes'));
        $failedCutoff = now()->subHour();

        $stale = Analysis::query()
            ->where(fn ($q) => $q->whereNull('user_id')->where('created_at', '<', $guestCutoff))
            ->orWhere(fn ($q) => $q->whereIn('status', ['failed', 'cancelled'])->where('updated_at', '<', $failedCutoff))
            ->orWhere(fn ($q) => $q->whereIn('status', ['queued', 'preprocessing', 'analyzing', 'finalizing'])->where('updated_at', '<', now()->subMinutes(30)))
            ->get();

        foreach ($stale as $a) {
            foreach ([$a->file_path, $a->preview_path, $a->thumb_path, $a->heatmap_path] as $p) {
                $vault->delete($p);
            }
            $a->delete();
        }
        $this->info("Removed {$stale->count()} stale analyses.");

        return self::SUCCESS;
    }
}

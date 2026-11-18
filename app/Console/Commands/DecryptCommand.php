<?php

namespace App\Console\Commands;

use App\Models\Analysis;
use App\Services\FileVault;
use Illuminate\Console\Command;

class DecryptCommand extends Command
{
    protected $signature = 'hulagwai:decrypt {id : analysis id (ULID)} {out : output file path} {--kind=original : original|preview|thumb}';
    protected $description = 'Admin tool: decrypt one stored image blob and write it to a file';

    public function handle(FileVault $vault): int
    {
        $kind = $this->option('kind');
        if (! in_array($kind, ['original', 'preview', 'thumb'], true)) {
            $this->error('kind must be original, preview or thumb');

            return self::INVALID;
        }
        $a = Analysis::where('uuid', strtoupper($this->argument('id')))->first();
        $path = $a ? match ($kind) { 'original' => $a->file_path, 'preview' => $a->preview_path, 'thumb' => $a->thumb_path } : null;
        if (! $a || ! $path) {
            $this->error('Analysis or blob not found (guest originals are never kept).');

            return self::FAILURE;
        }
        file_put_contents($this->argument('out'), $vault->get($path, $a->uuid.':'.$kind));
        $this->info('Decrypted '.$kind.' written to '.$this->argument('out'));
        $this->line('Original name: '.$a->original_name);

        return self::SUCCESS;
    }
}

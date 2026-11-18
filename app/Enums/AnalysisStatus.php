<?php

namespace App\Enums;

enum AnalysisStatus: string
{
    case Queued = 'queued';
    case Preprocessing = 'preprocessing';
    case Analyzing = 'analyzing';
    case Finalizing = 'finalizing';
    case Done = 'done';
    case Failed = 'failed';
    case Cancelled = 'cancelled';

    /** @return list<string> */
    public static function inFlight(): array
    {
        return [self::Queued->value, self::Preprocessing->value, self::Analyzing->value, self::Finalizing->value];
    }

    public function isFinal(): bool
    {
        return in_array($this, [self::Done, self::Failed, self::Cancelled], true);
    }
}

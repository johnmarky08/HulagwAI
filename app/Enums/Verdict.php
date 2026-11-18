<?php

namespace App\Enums;

enum Verdict: string
{
    case Real = 'real';
    case AiGenerated = 'ai_generated';
    case Inconclusive = 'inconclusive';

    public function label(): string
    {
        return match ($this) {
            self::Real => 'Likely real',
            self::AiGenerated => 'Likely AI-generated',
            self::Inconclusive => 'Inconclusive',
        };
    }
}

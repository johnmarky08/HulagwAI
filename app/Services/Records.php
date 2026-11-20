<?php

namespace App\Services;

use App\Models\Analysis;

/**
 * "Records" are plain arrays describing one analysis. The same shape is used
 * for DB rows (signed-in users) and session items (guests), so presenters,
 * history filters, exports and the PDF report work identically for both.
 */
final class Records
{
    /** @return array<string,mixed> */
    public static function fromModel(Analysis $a, bool $withDetails = true): array
    {
        return [
            'id' => $a->uuid,
            'status' => $a->status->value,
            'stage' => $a->stage,
            'progress' => (int) $a->progress,
            'verdict' => $a->verdict?->value,
            'ai_probability' => $a->ai_probability,
            'confidence' => $a->confidence,
            'filename' => $a->original_name,
            'format' => $a->format,
            'mime' => $a->mime_type,
            'width' => (int) $a->width,
            'height' => (int) $a->height,
            'size_bytes' => (int) $a->size_bytes,
            'sha256' => $a->sha256,
            'analyzed_at' => $a->analyzed_at?->toIso8601String(),
            'created_at' => $a->created_at?->toIso8601String(),
            'error_code' => $a->error_code,
            'model_version_id' => $a->model_version_id,
            'details' => $withDetails ? ($a->details ?? []) : null,
            'has_heatmap' => (bool) $a->heatmap_path,
            'persisted' => $a->user_id !== null,
        ];
    }
}

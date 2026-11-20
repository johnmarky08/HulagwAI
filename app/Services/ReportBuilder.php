<?php

namespace App\Services;

use App\Models\ModelVersion;
use RuntimeException;

/** Builds the PDF analysis report (per-image findings + model evaluation metrics). */
final class ReportBuilder
{
    public function __construct(private readonly Presenter $presenter) {}

    /** @param array<string,mixed> $rec @return array<string,mixed> */
    public function viewData(array $rec, ?ModelVersion $model, ?string $imageJpeg, ?string $heatmapJpeg = null): array
    {
        $full = $this->presenter->full($rec);

        return [
            'rec' => $rec,
            'full' => $full,
            'details' => (array) ($rec['details'] ?? []),
            'model' => $model,
            'metrics' => (array) ($model?->metrics ?? []),
            'image' => $imageJpeg ? 'data:image/jpeg;base64,'.base64_encode($imageJpeg) : null,
            'heatmap' => $heatmapJpeg ? 'data:image/jpeg;base64,'.base64_encode($heatmapJpeg) : null,
            'generatedAt' => now()->toDayDateTimeString().' '.config('app.timezone'),
        ];
    }

    /** @param array<string,mixed> $data */
    public function pdf(array $data): string
    {
        $facade = 'Barryvdh\\DomPDF\\Facade\\Pdf';
        if (! class_exists($facade)) {
            throw new RuntimeException('PDF engine missing. Run: composer require barryvdh/laravel-dompdf');
        }

        return $facade::loadView('reports.analysis', $data)->setPaper('a4')->output();
    }
}

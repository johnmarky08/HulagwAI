<?php

namespace App\Services;

use App\Enums\Verdict;

/** Turns records into the JSON the frontend consumes (shapes follow the Figma screens). */
final class Presenter
{
    public const DISCLAIMER = 'Confidence shows how strongly the model favors its prediction. It is not the probability that the image is authentic and does not guarantee the result is correct.';

    /** @param array<string,mixed> $r @return array<string,mixed> */
    public function status(array $r): array
    {
        $out = [
            'id' => $r['id'],
            'status' => $r['status'],
            'stage' => $r['stage'],
            'progress' => $r['progress'],
            'steps' => $this->steps((string) $r['status']),
            'file' => $this->file($r),
            'links' => $this->links($r),
        ];
        if ($r['status'] === 'failed') {
            $out['error'] = ['code' => $r['error_code'], 'message' => $this->errorMessage((string) $r['error_code'])];
        }

        return $out;
    }

    /** @param array<string,mixed> $r @return array<string,mixed> */
    public function full(array $r): array
    {
        $p = (float) $r['ai_probability'];
        $verdict = Verdict::from((string) $r['verdict']);
        $details = (array) ($r['details'] ?? []);

        return [
            ...$this->status($r),
            'result' => [
                'verdict' => $verdict->value,
                'label' => $verdict->label(),
                'ai_probability' => $p,
                'real_probability' => round(1 - $p, 5),
                'ai_percent' => (int) round($p * 100),
                'real_percent' => (int) round((1 - $p) * 100),
                'confidence' => (float) $r['confidence'],
                'confidence_percent' => (int) round(((float) $r['confidence']) * 100),
                'explanation' => $this->explanation($verdict, $details),
                'how_to_read' => self::DISCLAIMER,
                'warnings' => array_values((array) ($details['warnings'] ?? [])),
                'decision_source' => $details['decision']['source'] ?? 'model',
                'findings' => array_values((array) ($details['metadata']['findings'] ?? [])),
                'components' => (array) ($details['components'] ?? []),
            ],
            'analyzed_at' => $r['analyzed_at'],
            'saved_to_history' => true, // signed-in: MySQL; guest: encrypted session
            'persisted' => (bool) $r['persisted'],
        ];
    }

    /** @param array<string,mixed> $r @return array<string,mixed> */
    public function listItem(array $r): array
    {
        $verdict = Verdict::from((string) $r['verdict']);

        return [
            'id' => $r['id'],
            'filename' => $r['filename'],
            'format' => $r['format'],
            'verdict' => $verdict->value,
            'label' => $verdict->label(),
            'ai_probability' => (float) $r['ai_probability'],
            'confidence_percent' => (int) round(((float) $r['confidence']) * 100),
            'analyzed_at' => $r['analyzed_at'],
            'thumb_url' => "/api/v1/analyses/{$r['id']}/image?variant=thumb",
            'result_url' => "/api/v1/analyses/{$r['id']}",
        ];
    }

    /** @param array<string,mixed> $r @return array<string,mixed> */
    private function file(array $r): array
    {
        $name = (string) $r['filename'];

        return [
            'filename' => $name,
            'name' => pathinfo($name, PATHINFO_FILENAME),
            'format' => $r['format'],
            'size_bytes' => $r['size_bytes'],
            'size_mb' => round($r['size_bytes'] / 1048576, 2),
            'width' => $r['width'],
            'height' => $r['height'],
        ];
    }

    /** @param array<string,mixed> $r @return array<string,string> */
    private function links(array $r): array
    {
        $b = "/api/v1/analyses/{$r['id']}";

        return ['self' => $b, 'preview' => "$b/image?variant=preview", 'thumb' => "$b/image?variant=thumb", 'report' => "$b/report"];
    }

    /** @return list<array{key:string,label:string,state:string}> */
    private function steps(string $status): array
    {
        $state = match ($status) {
            'queued' => ['up_next', 'up_next', 'up_next'],
            'preprocessing' => ['in_progress', 'up_next', 'up_next'],
            'analyzing' => ['complete', 'in_progress', 'up_next'],
            'finalizing' => ['complete', 'complete', 'in_progress'],
            'done' => ['complete', 'complete', 'complete'],
            default => ['up_next', 'up_next', 'up_next'],
        };
        $labels = [['image_prepared', 'Image prepared'], ['visual_pattern_analysis', 'Visual pattern analysis'], ['generating_prediction', 'Generating prediction']];

        return array_map(fn ($l, $s) => ['key' => $l[0], 'label' => $l[1], 'state' => $s], $labels, $state);
    }

    /** @param array<string,mixed> $details */
    private function explanation(Verdict $v, array $details): string
    {
        $base = match ($v) {
            Verdict::AiGenerated => 'The model found patterns it associates with AI-generated images. This is a prediction, not proof; consider verifying the image\'s source.',
            Verdict::Real => 'The model found no strong signs of AI generation. This is a prediction, not proof; consider verifying the image\'s source.',
            Verdict::Inconclusive => 'The signals were weak or mixed, so no reliable call can be made. A higher-quality, original-resolution file may help.',
        };
        if (($details['decision']['source'] ?? '') === 'provenance') {
            $base = 'The file itself carries embedded provenance data declaring AI generation. '.$base;
        }

        return $base;
    }

    private function errorMessage(string $code): string
    {
        return match ($code) {
            'model_not_ready' => 'The detection model is not installed on this server yet.',
            'ml_unreachable', 'ml_not_configured' => 'The analysis service is currently unavailable. Please try again shortly.',
            'image_rejected' => 'The analysis service could not read this image.',
            default => 'The analysis could not be completed. Please try again.',
        };
    }
}

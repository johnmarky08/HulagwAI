<?php

namespace App\Services;

use App\Enums\Verdict;
use App\Exceptions\MlException;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;

/**
 * Talks to the Python ML service (FastAPI, loopback only, shared-secret header).
 * The response is treated as untrusted input: schema, ranges and sizes are
 * validated and only whitelisted keys are kept.
 */
final class MlClient
{
    private const DETAIL_KEYS = ['components', 'metadata', 'warnings', 'decision', 'thresholds', 'timings_ms'];
    private const STRENGTH = ['strong', 'moderate', 'weak'];

    /** @return array<string,mixed> */
    public function analyze(string $bytes): array
    {
        $resp = $this->request()->attach('image', $bytes, 'upload.bin')->post($this->url('/v1/analyze'));

        return match (true) {
            $resp->status() === 503 => throw new MlException('model_not_ready'),
            in_array($resp->status(), [400, 413, 415, 422], true) => throw new MlException('image_rejected'),
            ! $resp->successful() => throw new MlException('ml_error'),
            default => $this->validate($resp->json()),
        };
    }

    /** @return array<string,mixed> model name/version/hash, thresholds and evaluation metrics */
    public function modelInfo(): array
    {
        $resp = $this->request()->get($this->url('/v1/model'));
        $json = $resp->successful() ? $resp->json() : null;
        if (! is_array($json) || strlen((string) json_encode($json)) > 300_000) {
            throw new MlException('ml_error');
        }

        return $json;
    }

    /** @return array<string,mixed> */
    public function health(): array
    {
        try {
            $resp = $this->request()->timeout(3)->get($this->url('/v1/health'));

            return $resp->successful() && is_array($resp->json()) ? $resp->json() : ['status' => 'error'];
        } catch (\Throwable) {
            return ['status' => 'unreachable'];
        }
    }

    private function request(): \Illuminate\Http\Client\PendingRequest
    {
        $cfg = config('hulagwai.ml');
        if (empty($cfg['token']) || strlen((string) $cfg['token']) < 32) {
            throw new MlException('ml_not_configured');
        }

        return Http::withHeaders(['X-Internal-Token' => $cfg['token']])
            ->acceptJson()
            ->connectTimeout($cfg['connect_timeout'])
            ->timeout($cfg['timeout'])
            ->withOptions(['allow_redirects' => false]);
    }

    private function url(string $path): string
    {
        return rtrim((string) config('hulagwai.ml.url'), '/').$path; // base URL comes from config only, never from users
    }

    /** @param mixed $r @return array<string,mixed> */
    private function validate(mixed $r): array
    {
        $bad = fn () => new MlException('ml_bad_response');

        if (! is_array($r) || ! isset($r['ai_probability'], $r['confidence'], $r['verdict'], $r['model'], $r['image'])) {
            throw $bad();
        }
        foreach (['ai_probability', 'confidence'] as $k) {
            if (! is_numeric($r[$k]) || $r[$k] < 0 || $r[$k] > 1) {
                throw $bad();
            }
        }
        if (Verdict::tryFrom((string) $r['verdict']) === null) {
            throw $bad();
        }
        $m = $r['model'];
        if (! is_array($m) || ! is_string($m['name'] ?? null) || ! is_string($m['version'] ?? null)
            || ! preg_match('/^[a-f0-9]{64}$/', (string) ($m['weights_sha256'] ?? ''))) {
            // metadata-only mode reports an all-zero hash, which still matches the pattern
            throw $bad();
        }

        $preview = $this->jpeg($r['preview_jpeg_b64'] ?? null, 700_000);
        $thumb = $this->jpeg($r['thumb_jpeg_b64'] ?? null, 120_000);

        $heat = ! empty($r['heatmap_jpeg_b64']) ? $this->jpeg($r['heatmap_jpeg_b64'], 150_000) : null;

        $details = [];
        foreach (self::DETAIL_KEYS as $k) {
            if (isset($r[$k]) && is_array($r[$k])) {
                $details[$k] = $r[$k];
            }
        }
        $details['attribution'] = $this->cleanAttribution($r['attribution'] ?? null);
        $details['evidence'] = $this->cleanEvidence($r['evidence'] ?? null);
        if (strlen((string) json_encode($details)) > 60_000) {
            unset($details['metadata']['raw'], $details['timings_ms']);
            if (strlen((string) json_encode($details)) > 60_000) {
                throw $bad();
            }
        }

        return [
            'ai_probability' => round((float) $r['ai_probability'], 5),
            'confidence' => round((float) $r['confidence'], 5),
            'verdict' => (string) $r['verdict'],
            'model' => [
                'name' => mb_substr($m['name'], 0, 80),
                'version' => mb_substr($m['version'], 0, 40),
                'weights_sha256' => $m['weights_sha256'],
            ],
            'details' => $details,
            'preview' => $preview,
            'thumb' => $thumb,
            'heatmap' => $heat,
        ];
    }

    private function jpeg(mixed $b64, int $maxBytes): string
    {
        $raw = is_string($b64) ? base64_decode($b64, true) : false;
        if ($raw === false || $raw === '' || strlen($raw) > $maxBytes || ! str_starts_with($raw, "\xFF\xD8\xFF")) {
            throw new MlException('ml_bad_response');
        }

        return $raw;
    }

    // ---- sanitisers for "which generator / why it looks AI" (untrusted input from the ML process) --------------

    private function str(mixed $v, int $max): string
    {
        $s = is_scalar($v) ? (string) $v : '';
        $s = (string) preg_replace('/[\x00-\x1F\x7F\x{202A}-\x{202E}\x{2066}-\x{2069}]/u', ' ', mb_scrub($s));

        return mb_substr(trim($s), 0, $max);
    }

    private function prob(mixed $v): float
    {
        return is_numeric($v) ? round(min(1.0, max(0.0, (float) $v)), 4) : 0.0;
    }

    /** @return array<string,mixed> */
    private function cleanAttribution(mixed $a): array
    {
        if (! is_array($a) || empty($a['available'])) {
            $reason = is_array($a) ? $this->str($a['reason'] ?? '', 40) : '';

            return ['available' => false, 'reason' => preg_match('/^[a-z_]{1,40}$/', $reason) ? $reason : 'not_computed'];
        }
        $top = [];
        foreach (array_slice((array) ($a['top'] ?? []), 0, 3) as $t) {
            if (is_array($t) && is_string($t['family'] ?? null) && preg_match('/^[a-z0-9_]{1,24}$/', $t['family'])) {
                $top[] = ['family' => $t['family'], 'label' => $this->str($t['label'] ?? $t['family'], 60), 'p' => $this->prob($t['p'] ?? 0)];
            }
        }
        if (! $top) {
            return ['available' => false, 'reason' => 'no_candidates'];
        }

        return [
            'available' => true,
            'source' => ($a['source'] ?? '') === 'metadata' ? 'metadata' : 'model',
            'decision' => ($a['decision'] ?? '') === 'unknown' ? 'unknown' : 'family',
            'top' => $top,
            'tau' => $this->prob($a['tau'] ?? 0),
            'note' => $this->str($a['note'] ?? '', 160),
        ];
    }

    /** @return array<string,mixed> */
    private function cleanEvidence(mixed $e): array
    {
        $out = ['flags' => [], 'regions' => [], 'heatmap' => ['available' => false], 'note' => ''];
        if (! is_array($e)) {
            return $out;
        }
        foreach (array_slice((array) ($e['flags'] ?? []), 0, 12) as $f) {
            if (! is_array($f)) {
                continue;
            }
            $out['flags'][] = [
                'id' => (string) preg_replace('/[^a-z0-9_]/', '', strtolower($this->str($f['id'] ?? '', 40))),
                'category' => $this->str($f['category'] ?? '', 40),
                'strength' => in_array($f['strength'] ?? '', self::STRENGTH, true) ? $f['strength'] : 'weak',
                'title' => $this->str($f['title'] ?? '', 120),
                'detail' => $this->str($f['detail'] ?? '', 300),
                'source' => $this->str($f['source'] ?? '', 16),
            ];
        }
        foreach (array_slice((array) ($e['regions'] ?? []), 0, 3) as $r) {
            if (is_array($r)) {
                $out['regions'][] = ['x' => $this->prob($r['x'] ?? 0), 'y' => $this->prob($r['y'] ?? 0), 'w' => $this->prob($r['w'] ?? 0),
                    'h' => $this->prob($r['h'] ?? 0), 'score' => $this->prob($r['score'] ?? 0), 'where' => $this->str($r['where'] ?? '', 30)];
            }
        }
        $h = $e['heatmap'] ?? null;
        if (is_array($h) && ! empty($h['available']) && is_array($h['scores'] ?? null)) {
            $grid = array_map(fn ($row) => array_map(fn ($v) => $this->prob($v), array_slice((array) $row, 0, 3)), array_slice($h['scores'], 0, 3));
            $out['heatmap'] = ['available' => true, 'grid' => [count($grid), count($grid[0] ?? [])], 'scores' => $grid];
        }
        $out['note'] = $this->str($e['note'] ?? '', 300);

        return $out;
    }
}

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

        $details = [];
        foreach (self::DETAIL_KEYS as $k) {
            if (isset($r[$k]) && is_array($r[$k])) {
                $details[$k] = $r[$k];
            }
        }
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
}

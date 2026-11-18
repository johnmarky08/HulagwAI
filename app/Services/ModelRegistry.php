<?php

namespace App\Services;

use App\Models\ModelVersion;

/** Keeps `model_versions` (and its evaluation metrics) in sync with the loaded ML bundle. */
final class ModelRegistry
{
    public function __construct(private readonly MlClient $ml) {}

    /** @param array{name:string,version:string,weights_sha256:string} $model */
    public function resolve(array $model): ModelVersion
    {
        $keys = ['name' => $model['name'], 'version' => $model['version'], 'weights_sha256' => $model['weights_sha256']];
        $existing = ModelVersion::where($keys)->first();
        if ($existing && $existing->metrics !== null) {
            return $existing;
        }

        $info = [];
        try {
            $info = $this->ml->modelInfo();
        } catch (\Throwable) {
            // metrics are optional; the analysis itself must not fail because of them
        }

        $evaluatedAt = isset($info['evaluated_at']) && is_string($info['evaluated_at']) ? $info['evaluated_at'] : null;

        return ModelVersion::updateOrCreate($keys, [
            'thresholds' => is_array($info['thresholds'] ?? null) ? $info['thresholds'] : null,
            'metrics' => is_array($info['metrics'] ?? null) ? $info['metrics'] : null,
            'evaluated_at' => $evaluatedAt ? date('Y-m-d H:i:s', (int) strtotime($evaluatedAt)) : null,
        ]);
    }
}

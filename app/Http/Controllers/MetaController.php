<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use App\Models\ModelVersion;
use App\Services\MlClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MetaController extends Controller
{
    /** GET /api/v1/me  -> who am I + quota/limits (drives the upload UI hints) */
    public function me(Request $request): JsonResponse
    {
        $user = $request->user();
        $limit = (int) config('hulagwai.quota.user_bytes');
        $used = $user ? (int) Analysis::where('user_id', $user->getAuthIdentifier())->whereNotIn('status', ['failed', 'cancelled'])->sum('size_bytes') : 0;

        return response()->json([
            'authenticated' => (bool) $user,
            'user' => $user ? ['id' => $user->id, 'name' => $user->name, 'email' => $user->email] : null,
            'history_mode' => $user ? 'account' : 'session',
            'quota' => $user ? ['used_bytes' => $used, 'limit_bytes' => $limit, 'remaining_bytes' => max(0, $limit - $used)] : null,
            'upload' => [
                'max_bytes' => config('hulagwai.upload.max_bytes'),
                'extensions' => array_keys(config('hulagwai.upload.extensions')),
            ],
        ]);
    }

    /** GET /api/v1/model  -> public summary of the active model (for the About page) */
    public function model(): JsonResponse
    {
        $m = ModelVersion::orderByDesc('id')->first();
        $t = $m?->metrics['test'] ?? null;

        return response()->json([
            'name' => $m?->name, 'version' => $m?->version, 'evaluated_at' => $m?->evaluated_at?->toIso8601String(),
            'summary' => $t ? array_intersect_key($t, array_flip(['n', 'accuracy', 'precision', 'recall', 'f1', 'roc_auc'])) : null,
        ]);
    }

    /** GET /api/v1/health */
    public function health(MlClient $ml): JsonResponse
    {
        $h = $ml->health();

        return response()->json(['app' => 'ok', 'ml' => ['status' => $h['status'] ?? 'unknown', 'model_loaded' => (bool) ($h['model_loaded'] ?? false)]]);
    }
}

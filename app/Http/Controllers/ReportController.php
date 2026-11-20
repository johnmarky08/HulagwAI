<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use App\Models\AuditLog;
use App\Models\ModelVersion;
use App\Services\AnalysisAccess;
use App\Services\FileVault;
use App\Services\ReportBuilder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class ReportController extends Controller
{
    /** GET /api/v1/analyses/{id}/report  -> application/pdf */
    public function show(Request $request, string $id, AnalysisAccess $access, ReportBuilder $builder, FileVault $vault): Response|JsonResponse
    {
        $rec = $access->record($request, $id);
        if (! $rec || $rec['status'] !== 'done') {
            return response()->json(['code' => 'not_found', 'message' => 'Analysis not found.'], 404);
        }

        $jpeg = null;
        $heat = null;
        if ($request->user()) {
            $row = Analysis::where('uuid', $rec['id'])->where('user_id', $request->user()->getAuthIdentifier())->first();
            $jpeg = $row?->preview_path ? $vault->get($row->preview_path, $rec['id'].':preview') : null;
            $heat = $row?->heatmap_path ? $vault->get($row->heatmap_path, $rec['id'].':heatmap') : null;
        } elseif (! empty($rec['thumb_b64'])) {
            $jpeg = base64_decode($rec['thumb_b64'], true) ?: null;
            $heat = ! empty($rec['heatmap_b64']) ? (base64_decode($rec['heatmap_b64'], true) ?: null) : null;
        }

        $model = $rec['model_version_id'] ? ModelVersion::find($rec['model_version_id']) : null;

        try {
            $pdf = $builder->pdf($builder->viewData($rec, $model, $jpeg, $heat));
        } catch (\RuntimeException $e) {
            return response()->json(['code' => 'pdf_unavailable', 'message' => 'PDF engine is not installed on the server.'], 501);
        }
        AuditLog::record('report_downloaded', $request);

        return response($pdf, 200, [
            'Content-Type' => 'application/pdf',
            'Content-Disposition' => 'attachment; filename="hulagwai-report-'.$rec['id'].'.pdf"',
            'X-Content-Type-Options' => 'nosniff',
            'Cache-Control' => 'private, no-store',
        ]);
    }
}

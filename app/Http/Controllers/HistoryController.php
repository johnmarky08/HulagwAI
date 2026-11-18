<?php

namespace App\Http\Controllers;

use App\Http\Requests\HistoryQueryRequest;
use App\Models\Analysis;
use App\Models\AuditLog;
use App\Services\FileVault;
use App\Services\GuestHistory;
use App\Services\HistoryService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Symfony\Component\HttpFoundation\StreamedResponse;

class HistoryController extends Controller
{
    public function __construct(private readonly HistoryService $history) {}

    /** GET /api/v1/history?search=&result=&range=&sort=&page= */
    public function index(HistoryQueryRequest $request): JsonResponse
    {
        return response()->json($this->history->query($request, $request->validated()));
    }

    /** GET /api/v1/history/export?format=csv|json */
    public function export(HistoryQueryRequest $request): StreamedResponse|JsonResponse
    {
        $rows = $this->history->exportRows($request);
        AuditLog::record('history_exported', $request);

        if (($request->validated()['format'] ?? 'csv') === 'json') {
            return response()->json(['exported_at' => now()->toIso8601String(), 'items' => $rows], 200, [
                'Content-Disposition' => 'attachment; filename="hulagwai-history.json"',
            ]);
        }

        return response()->streamDownload(function () use ($rows) {
            $out = fopen('php://output', 'w');
            fputcsv($out, array_keys($rows[0] ?? ['id' => 1, 'filename' => 1, 'verdict' => 1]));
            foreach ($rows as $row) {
                // CSV-injection guard: neutralise cells that spreadsheets would treat as formulas.
                fputcsv($out, array_map(fn ($v) => is_string($v) && preg_match('/^[=+\-@\t\r]/', $v) ? "'".$v : $v, $row));
            }
            fclose($out);
        }, 'hulagwai-history.csv', ['Content-Type' => 'text/csv; charset=UTF-8', 'X-Content-Type-Options' => 'nosniff']);
    }

    /** DELETE /api/v1/history  -> clear everything the visitor has */
    public function clear(Request $request, FileVault $vault, GuestHistory $guest): JsonResponse
    {
        if ($user = $request->user()) {
            $paths = [];
            DB::transaction(function () use ($user, &$paths) {
                foreach (Analysis::where('user_id', $user->getAuthIdentifier())->lockForUpdate()->get() as $a) {
                    array_push($paths, $a->file_path, $a->preview_path, $a->thumb_path);
                    $a->delete();
                }
            });
            array_map(fn ($p) => $vault->delete($p), $paths);
        } else {
            $guest->clear();
        }
        AuditLog::record('history_cleared', $request);

        return response()->json(['ok' => true]);
    }
}

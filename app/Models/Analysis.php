<?php

namespace App\Models;

use App\Enums\AnalysisStatus;
use App\Enums\Verdict;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * One uploaded image and its result.
 *
 * Encrypted at rest: original_name + details (Laravel encrypter, AES-256 + HMAC,
 * keyed from APP_KEY) and the image blobs (FileVault, XChaCha20-Poly1305).
 * Everything is decryptable server-side with the APP_KEY; nothing is exposed
 * through route-model binding - controllers always scope by owner (no IDOR).
 */
class Analysis extends Model
{
    protected $fillable = [
        'uuid', 'user_id', 'status', 'stage', 'progress', 'verdict', 'ai_probability', 'confidence',
        'model_version_id', 'sha256', 'original_name', 'mime_type', 'format', 'width', 'height', 'size_bytes',
        'file_path', 'preview_path', 'thumb_path', 'heatmap_path', 'details', 'error_code', 'analyzed_at',
    ];

    protected $hidden = ['id', 'file_path', 'preview_path', 'thumb_path', 'heatmap_path', 'details', 'original_name'];

    protected function casts(): array
    {
        return [
            'status' => AnalysisStatus::class,
            'verdict' => Verdict::class,
            'ai_probability' => 'float',
            'confidence' => 'float',
            'original_name' => 'encrypted',
            'details' => 'encrypted:array',
            'analyzed_at' => 'datetime',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function modelVersion(): BelongsTo
    {
        return $this->belongsTo(ModelVersion::class);
    }
}

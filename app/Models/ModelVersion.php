<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ModelVersion extends Model
{
    protected $fillable = ['name', 'version', 'weights_sha256', 'thresholds', 'metrics', 'evaluated_at'];

    protected function casts(): array
    {
        return ['thresholds' => 'array', 'metrics' => 'array', 'evaluated_at' => 'datetime'];
    }
}

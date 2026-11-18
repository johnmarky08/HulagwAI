<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('model_versions', function (Blueprint $table) {
            $table->id();
            $table->string('name', 80);
            $table->string('version', 40);
            $table->char('weights_sha256', 64)->default(str_repeat('0', 64));
            $table->json('thresholds')->nullable();
            // Evaluation report produced by training/07_evaluate.py (accuracy, recall, MAE ...)
            $table->json('metrics')->nullable();
            $table->timestamp('evaluated_at')->nullable();
            $table->timestamps();

            $table->unique(['name', 'version', 'weights_sha256']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('model_versions');
    }
};

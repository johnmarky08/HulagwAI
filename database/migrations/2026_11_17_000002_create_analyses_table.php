<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('analyses', function (Blueprint $table) {
            $table->id();
            $table->char('uuid', 26)->unique();                         // public id (ULID) - never the auto-increment id
            $table->foreignId('user_id')->nullable()->constrained()->cascadeOnDelete();

            $table->string('status', 20)->index();
            $table->string('stage', 32)->nullable();
            $table->unsignedTinyInteger('progress')->default(0);

            $table->string('verdict', 16)->nullable();                  // real | ai_generated | inconclusive
            $table->decimal('ai_probability', 6, 5)->nullable();
            $table->decimal('confidence', 6, 5)->nullable();
            $table->foreignId('model_version_id')->nullable()->constrained('model_versions')->nullOnDelete();

            $table->char('sha256', 64)->index();                        // of the original bytes (duplicate lookup)
            $table->text('original_name');                              // encrypted (AES-256, Laravel encrypter)
            $table->string('mime_type', 32);
            $table->string('format', 8);
            $table->unsignedInteger('width');
            $table->unsignedInteger('height');
            $table->unsignedInteger('size_bytes');

            $table->string('file_path')->nullable();                    // encrypted blob (XChaCha20-Poly1305) on the private disk
            $table->string('preview_path')->nullable();
            $table->string('thumb_path')->nullable();

            $table->longText('details')->nullable();                    // encrypted JSON: component scores, metadata findings ...
            $table->string('error_code', 40)->nullable();

            $table->timestamp('analyzed_at')->nullable();
            $table->timestamps();

            $table->index(['user_id', 'created_at']);
            $table->index(['user_id', 'verdict']);
            $table->index(['status', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('analyses');
    }
};

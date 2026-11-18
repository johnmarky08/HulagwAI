<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('audit_logs', function (Blueprint $table) {
            $table->id();
            $table->string('event', 48)->index();
            $table->foreignId('user_id')->nullable()->constrained()->nullOnDelete();
            $table->char('ip_hash', 64)->nullable();                    // HMAC(APP_KEY, ip) - no raw IPs stored
            $table->string('user_agent', 160)->nullable();
            $table->json('context')->nullable();
            $table->timestamp('created_at')->useCurrent()->index();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('audit_logs');
    }
};

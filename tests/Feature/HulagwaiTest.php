<?php

namespace Tests\Feature;

use App\Models\Analysis;
use App\Models\ModelVersion;
use App\Models\User;
use App\Services\FileVault;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class HulagwaiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('local');
        config(['hulagwai.ml.token' => str_repeat('t', 40)]);
        $this->fakeMl();
    }

    private function jpegB64(): string
    {
        $im = imagecreatetruecolor(8, 8);
        ob_start();
        imagejpeg($im);

        return base64_encode((string) ob_get_clean());
    }

    private function fakeMl(float $p = 0.88, string $verdict = 'ai_generated'): void
    {
        $b = $this->jpegB64();
        Http::fake([
            '*/v1/analyze' => Http::response([
                'ai_probability' => $p, 'confidence' => max($p, 1 - $p), 'verdict' => $verdict,
                'model' => ['name' => 'hulagwai-ensemble', 'version' => '1.0.0', 'weights_sha256' => str_repeat('a', 64)],
                'image' => ['width' => 64, 'height' => 64, 'format' => 'PNG'],
                'components' => ['clip' => ['p' => 0.9, 'weight' => 0.5, 'role' => 'semantic']],
                'metadata' => ['findings' => []], 'warnings' => [], 'decision' => ['source' => 'model', 'disagreement' => 0.05],
                'thresholds' => ['real_max' => 0.4, 'ai_min' => 0.6],
                'preview_jpeg_b64' => $b, 'thumb_jpeg_b64' => $b,
            ]),
            '*/v1/model' => Http::response([
                'name' => 'hulagwai-ensemble', 'version' => '1.0.0', 'thresholds' => ['real_max' => 0.4, 'ai_min' => 0.6],
                'metrics' => ['test' => ['n' => 100, 'accuracy' => 0.97, 'recall' => 0.96, 'precision' => 0.98, 'mae' => 0.05,
                    'confusion' => ['tn' => 49, 'fp' => 1, 'fn' => 2, 'tp' => 48]]],
                'evaluated_at' => '2026-11-01T00:00:00Z',
            ]),
        ]);
    }

    private function refake(array $stubs): void
    {
        Http::clearResolvedInstance(\Illuminate\Http\Client\Factory::class);
        $this->app->forgetInstance(\Illuminate\Http\Client\Factory::class);
        Http::fake($stubs);
    }

    private function png(string $name = 'sample_image.png', int $kb = 0): UploadedFile
    {
        return UploadedFile::fake()->image($name, 64, 64)->size($kb ?: 1);
    }

    public function test_guest_flow_keeps_nothing_in_the_database(): void
    {
        $r = $this->postJson('/api/v1/analyses', ['image' => $this->png()])->assertStatus(202);
        $id = $r->json('id');

        $show = $this->getJson("/api/v1/analyses/$id")->assertOk();
        $this->assertSame('done', $show->json('status'));
        $this->assertSame('ai_generated', $show->json('result.verdict'));
        $this->assertSame(88, $show->json('result.ai_percent'));
        $this->assertSame(12, $show->json('result.real_percent'));

        $this->assertSame(0, Analysis::count(), 'guest rows must be gone once claimed');
        $this->assertSame([], Storage::disk('local')->allFiles('vault'), 'guest blobs must be gone');

        $this->getJson("/api/v1/analyses/$id")->assertOk();           // served from the session
        $this->getJson('/api/v1/history')->assertOk()->assertJsonPath('stats.total', 1);
        $this->get("/api/v1/analyses/$id/image?variant=thumb")->assertOk()->assertHeader('Content-Type', 'image/jpeg');
    }

    public function test_signed_in_user_gets_encrypted_persistent_history(): void
    {
        $u = User::factory()->create();
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png('secret_name.png')])->assertStatus(202)->json('id');

        $row = Analysis::where('uuid', $id)->firstOrFail();
        $this->assertSame('done', $row->status->value);
        $this->assertSame('secret_name.png', $row->original_name);
        $raw = \DB::table('analyses')->where('uuid', $id)->first();
        $this->assertStringNotContainsString('secret_name', $raw->original_name, 'filename must be encrypted at rest');
        $this->assertStringNotContainsString('ai_generated', (string) $raw->details);
        $this->assertCount(3, Storage::disk('local')->allFiles('vault'));
        $this->assertStringNotContainsString('PNG', Storage::disk('local')->get($row->file_path), 'blob must not be plaintext');

        $this->getJson("/api/v1/analyses/$id")->assertOk()->assertJsonPath('result.label', 'Likely AI-generated');
        $this->assertNotNull(ModelVersion::first()->metrics);
        $this->getJson('/api/v1/history?result=real')->assertOk()->assertJsonPath('meta.total', 0);
        $this->getJson('/api/v1/history?search=SECRET')->assertOk()->assertJsonPath('meta.total', 1);
    }

    public function test_other_users_cannot_read_or_delete_my_analysis(): void
    {
        [$a, $b] = [User::factory()->create(), User::factory()->create()];
        $id = $this->actingAs($a)->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');

        $this->actingAs($b)->getJson("/api/v1/analyses/$id")->assertNotFound();
        $this->actingAs($b)->get("/api/v1/analyses/$id/image")->assertNotFound();
        $this->actingAs($b)->deleteJson("/api/v1/analyses/$id")->assertNotFound();
        $this->assertSame(1, Analysis::count());
        $this->flushSession();
        auth()->logout();
        $this->getJson("/api/v1/analyses/$id")->assertNotFound();  // guest
        $this->actingAs($a)->deleteJson("/api/v1/analyses/$id")->assertOk();
        $this->assertSame(0, Analysis::count());
        $this->assertSame([], Storage::disk('local')->allFiles('vault'));
    }

    public function test_upload_validation_rejects_bad_files(): void
    {
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->createWithContent('evil.png', '<?php echo 1;')])->assertStatus(422);
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->createWithContent('a.gif', base64_decode('R0lGODlhAQABAAAAACw='))])->assertStatus(422);
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->image('x.jpg', 64, 64)->size(6000)])->assertStatus(422);
        $png = UploadedFile::fake()->image('real.png', 64, 64);
        $this->postJson('/api/v1/analyses', ['image' => new UploadedFile($png->getPathname(), 'renamed.jpg', 'image/jpeg', null, true)])->assertStatus(422); // ext/content mismatch
        $this->postJson('/api/v1/analyses', [])->assertStatus(422);
        $this->assertSame(0, Analysis::count());
    }

    public function test_quota_is_enforced_per_user(): void
    {
        config(['hulagwai.quota.user_bytes' => 5000]);
        $u = User::factory()->create();
        $this->actingAs($u);
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->image('a.png', 400, 400)->size(1)])->assertStatus(202);
        $size = Analysis::first()->size_bytes;
        config(['hulagwai.quota.user_bytes' => $size + 10]);
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->image('b.jpg', 64, 64)])->assertStatus(413)->assertJsonPath('code', 'quota_exceeded');
        $this->assertSame(1, Analysis::count());
        $this->assertCount(3, Storage::disk('local')->allFiles('vault'), 'rejected upload must not leave a blob behind');
    }

    public function test_duplicate_upload_reuses_result_without_calling_ml(): void
    {
        $u = User::factory()->create();
        $file = $this->png('dup.png');
        $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $file])->assertStatus(202);
        Http::fake(['*' => Http::response([], 500)]);
        $again = new UploadedFile($file->getPathname(), 'dup.png', 'image/png', null, true);
        $this->postJson('/api/v1/analyses', ['image' => $again])->assertOk()->assertJsonPath('duplicate', true);
        $this->assertSame(1, Analysis::count());
    }

    public function test_ml_outage_marks_failure_and_frees_storage(): void
    {
        $this->refake(['*/v1/analyze' => Http::response(['detail' => 'model_not_ready'], 503)]);
        $u = User::factory()->create();
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $this->getJson("/api/v1/analyses/$id")->assertOk()->assertJsonPath('status', 'failed')->assertJsonPath('error.code', 'model_not_ready');
        $this->assertSame([], Storage::disk('local')->allFiles('vault'));
    }

    public function test_malformed_ml_response_is_rejected(): void
    {
        $this->refake(['*/v1/analyze' => Http::response(['ai_probability' => 7, 'confidence' => 1, 'verdict' => 'x'])]);
        $id = $this->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $this->getJson("/api/v1/analyses/$id")->assertJsonPath('status', 'failed')->assertJsonPath('error.code', 'ml_bad_response');
    }

    public function test_auth_register_login_lockout_and_logout(): void
    {
        $this->postJson('/register', ['name' => 'Mark', 'email' => 'M@Example.com', 'password' => 'weak', 'password_confirmation' => 'weak'])->assertStatus(422);
        $this->postJson('/register', ['name' => 'Mark', 'email' => 'M@Example.com', 'password' => 'Str0ngPassw0rd', 'password_confirmation' => 'Str0ngPassw0rd'])->assertOk();
        $this->assertSame('m@example.com', User::first()->email);
        $this->assertNotSame('Str0ngPassw0rd', User::first()->password);
        $this->postJson('/logout')->assertOk();

        for ($i = 0; $i < 5; $i++) {
            $this->postJson('/login', ['email' => 'm@example.com', 'password' => 'nope'])->assertStatus(422);
        }
        $this->postJson('/login', ['email' => 'm@example.com', 'password' => 'Str0ngPassw0rd'])->assertStatus(429); // locked even with right password
    }

    public function test_csv_export_neutralises_formulas(): void
    {
        $u = User::factory()->create();
        $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png('=1+1.png')])->assertStatus(202);
        $csv = $this->get('/api/v1/history/export?format=csv')->assertOk()->streamedContent();
        $this->assertStringContainsString("'=1+1.png", $csv);
        $this->assertStringNotContainsString(",=1+1.png", $csv);
    }

    public function test_security_headers_and_json_errors(): void
    {
        $this->withoutVite();
        $r = $this->get('/about');
        $r->assertHeader('X-Content-Type-Options', 'nosniff')->assertHeader('X-Frame-Options', 'DENY');
        $this->assertStringContainsString("frame-ancestors 'none'", $r->headers->get('Content-Security-Policy'));
        $this->assertStringNotContainsString('[::1]', $r->headers->get('Content-Security-Policy'));
        $this->getJson('/api/v1/analyses/not-an-id')->assertNotFound()->assertJsonPath('code', 'not_found');
        $this->postJson('/api/v1/account/delete', ['password' => 'x'])->assertUnauthorized();
    }

    public function test_account_deletion_erases_everything(): void
    {
        $u = User::factory()->create(['password' => bcrypt('Str0ngPassw0rd')]);
        $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->assertStatus(202);
        $this->postJson('/api/v1/account/delete', ['password' => 'wrong'])->assertStatus(422);
        $this->postJson('/api/v1/account/delete', ['password' => 'Str0ngPassw0rd'])->assertOk();
        $this->assertSame(0, User::count());
        $this->assertSame(0, Analysis::count());
        $this->assertSame([], Storage::disk('local')->allFiles('vault'));
    }

    public function test_report_template_renders_with_and_without_metrics(): void
    {
        $u = User::factory()->create();
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $builder = app(\App\Services\ReportBuilder::class);
        $rec = \App\Services\Records::fromModel(Analysis::where('uuid', $id)->first());
        $html = view('reports.analysis', $builder->viewData($rec, ModelVersion::first(), null))->render();
        $this->assertStringContainsString('Recall / sensitivity', $html);
        $this->assertStringContainsString('96.00%', $html);
        $html2 = view('reports.analysis', $builder->viewData($rec, null, null))->render();
        $this->assertStringContainsString('has not been evaluated yet', $html2);
    }

    public function test_vault_roundtrip_and_tamper_detection(): void
    {
        $v = app(FileVault::class);
        $p = $v->put('hello', 'A:original');
        $this->assertSame('hello', $v->get($p, 'A:original'));
        $this->expectException(\RuntimeException::class);
        $v->get($p, 'B:original'); // blob re-bound to another record must fail
    }
}

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
                'attribution' => ['available' => true, 'source' => 'model', 'decision' => 'family', 'tau' => 0.55,
                    'top' => [['family' => 'midjourney', 'label' => 'Midjourney', 'p' => 0.71], ['family' => 'flux', 'label' => 'FLUX', 'p' => 0.2], ['family' => 'dalle', 'label' => 'DALL·E', 'p' => 0.05]]],
                'evidence' => ['flags' => [['id' => 'signal_cnn', 'category' => 'Pixel-level texture', 'strength' => 'strong', 'title' => 'Pixel-level texture signal', 'detail' => 'x', 'source' => 'cnn']],
                    'regions' => [['x' => 0, 'y' => 0, 'w' => 0.5, 'h' => 0.5, 'score' => 0.9, 'where' => 'upper-left']],
                    'heatmap' => ['available' => true, 'grid' => [2, 2], 'scores' => [[0.9, 0.2], [0.1, 0.3]]], 'note' => 'n'],
                'heatmap_jpeg_b64' => $b,
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
        $r = $this->postJson('/api/v1/analyses', ['image' => $this->png()])->assertSuccessful();
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
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png('secret_name.png')])->assertSuccessful()->json('id');

        $row = Analysis::where('uuid', $id)->firstOrFail();
        $this->assertSame('done', $row->status->value);
        $this->assertSame('secret_name.png', $row->original_name);
        $raw = \Illuminate\Support\Facades\DB::table('analyses')->where('uuid', $id)->first();
        $this->assertStringNotContainsString('secret_name', $raw->original_name, 'filename must be encrypted at rest');
        $this->assertStringNotContainsString('ai_generated', (string) $raw->details);
        $this->assertCount(4, Storage::disk('local')->allFiles('vault'));
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
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->image('a.png', 400, 400)->size(1)])->assertSuccessful();
        $size = Analysis::first()->size_bytes;
        config(['hulagwai.quota.user_bytes' => $size + 10]);
        $this->postJson('/api/v1/analyses', ['image' => UploadedFile::fake()->image('b.jpg', 64, 64)])->assertStatus(413)->assertJsonPath('code', 'quota_exceeded');
        $this->assertSame(1, Analysis::count());
        $this->assertCount(4, Storage::disk('local')->allFiles('vault'), 'rejected upload must not leave a blob behind');
    }

    public function test_duplicate_upload_reuses_result_without_calling_ml(): void
    {
        $u = User::factory()->create();
        $file = $this->png('dup.png');
        $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $file])->assertSuccessful();
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
        $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png('=1+1.png')])->assertSuccessful();
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
        $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->assertSuccessful();
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

    public function test_evaluation_endpoint_and_notices(): void
    {
        $this->getJson('/api/v1/model/evaluation')->assertOk()->assertJsonPath('evaluated', false)->assertJsonPath('notice.intended_use', config('hulagwai.notice.intended_use'));

        $id = $this->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $res = $this->getJson("/api/v1/analyses/$id")->assertOk();
        $this->assertNotEmpty($res->json('notice.limitations'));

        $this->getJson('/api/v1/model/evaluation')->assertOk()
            ->assertJsonPath('evaluated', true)
            ->assertJsonPath('metrics.test.confusion.tp', 48)
            ->assertJsonPath('model.version', '1.0.0');
        $this->getJson('/api/v1/me')->assertJsonPath('notice.privacy', config('hulagwai.notice.privacy'));
    }

    public function test_attribution_and_evidence_are_returned_stored_and_served(): void
    {
        $u = User::factory()->create();
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->assertSuccessful()->json('id');
        $r = $this->getJson("/api/v1/analyses/$id")->assertOk();
        $r->assertJsonPath('result.attribution.available', true)->assertJsonPath('result.attribution.headline', 'Midjourney')
            ->assertJsonPath('result.attribution.top.0.percent', 71)->assertJsonPath('result.evidence.flags.0.strength', 'strong')
            ->assertJsonPath('result.evidence.heatmap.available', true);
        $this->assertNotEmpty($r->json('result.evidence.heatmap.image_url'));
        $this->assertNotEmpty($r->json('result.attribution.disclaimer'));
        $raw = \DB::table('analyses')->where('uuid', $id)->first();
        $this->assertStringNotContainsString('Midjourney', (string) $raw->details, 'attribution must be encrypted at rest');
        $this->get("/api/v1/analyses/$id/image?variant=heatmap")->assertOk()->assertHeader('Content-Type', 'image/jpeg');
        $this->assertCount(4, Storage::disk('local')->allFiles('vault'));          // original, preview, thumb, heat map
        $this->actingAs(User::factory()->create())->get("/api/v1/analyses/$id/image?variant=heatmap")->assertNotFound();
        $this->actingAs($u)->deleteJson("/api/v1/analyses/$id")->assertOk();
        $this->assertSame([], Storage::disk('local')->allFiles('vault'));
    }

    public function test_guest_keeps_heatmap_in_session_only(): void
    {
        $id = $this->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $this->getJson("/api/v1/analyses/$id")->assertOk()->assertJsonPath('result.attribution.headline', 'Midjourney');
        $this->assertSame([], Storage::disk('local')->allFiles('vault'));
        $this->assertSame(0, Analysis::count());
        $this->get("/api/v1/analyses/$id/image?variant=heatmap")->assertOk()->assertHeader('Content-Type', 'image/jpeg');
    }

    public function test_hostile_attribution_and_evidence_fields_are_sanitised(): void
    {
        $b = $this->jpegB64();
        $this->refake(['*/v1/analyze' => Http::response([
            'ai_probability' => 0.9, 'confidence' => 0.9, 'verdict' => 'ai_generated',
            'model' => ['name' => 'm', 'version' => '1', 'weights_sha256' => str_repeat('a', 64)], 'image' => [],
            'attribution' => ['available' => true, 'top' => [['family' => '../../etc/passwd', 'label' => 'x', 'p' => 5], ['family' => 'flux', 'label' => "Fl\x00ux\u{202E}", 'p' => 9]]],
            'evidence' => ['flags' => [['id' => '<b>X</b>', 'strength' => 'EVIL', 'title' => str_repeat('A', 999), 'detail' => 'd', 'category' => 'c', 'source' => 's']],
                'regions' => [['x' => 7, 'y' => -3, 'w' => 'z', 'h' => 1, 'score' => 99]]],
            'preview_jpeg_b64' => $b, 'thumb_jpeg_b64' => $b,
        ])]);
        $u = User::factory()->create();
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $r = $this->getJson("/api/v1/analyses/$id")->assertOk();
        $this->assertSame('flux', $r->json('result.attribution.top.0.family'));       // path-like family dropped
        $this->assertSame(100, $r->json('result.attribution.top.0.percent'));          // probability clamped to 1.0
        $this->assertStringNotContainsString("\x00", (string) $r->json('result.attribution.top.0.label'));
        $this->assertStringNotContainsString("\u{202E}", (string) $r->json('result.attribution.top.0.label'));
        $this->assertSame('weak', $r->json('result.evidence.flags.0.strength'));       // unknown enum -> weak
        $this->assertMatchesRegularExpression('/^[a-z0-9_]*$/', $r->json('result.evidence.flags.0.id'));
        $this->assertLessThanOrEqual(120, mb_strlen($r->json('result.evidence.flags.0.title')));
        $this->assertEquals(1.0, $r->json('result.evidence.regions.0.x'));
        $this->assertEquals(0.0, $r->json('result.evidence.regions.0.y'));
        $this->assertNull($r->json('result.evidence.heatmap.image_url'));              // no heat map supplied
    }

    public function test_old_analyses_without_new_fields_still_render(): void
    {
        $this->refake(['*/v1/analyze' => Http::response([
            'ai_probability' => 0.2, 'confidence' => 0.8, 'verdict' => 'real',
            'model' => ['name' => 'm', 'version' => '1', 'weights_sha256' => str_repeat('a', 64)], 'image' => [],
            'preview_jpeg_b64' => $this->jpegB64(), 'thumb_jpeg_b64' => $this->jpegB64(),
        ])]);
        $id = $this->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $this->getJson("/api/v1/analyses/$id")->assertOk()
            ->assertJsonPath('result.attribution.available', false)->assertJsonPath('result.evidence.flags', []);
    }

    public function test_report_contains_generator_and_evidence_sections(): void
    {
        $u = User::factory()->create();
        $id = $this->actingAs($u)->postJson('/api/v1/analyses', ['image' => $this->png()])->json('id');
        $rec = \App\Services\Records::fromModel(Analysis::where('uuid', $id)->first());
        $html = view('reports.analysis', app(\App\Services\ReportBuilder::class)->viewData($rec, ModelVersion::first(), null, null))->render();
        foreach (['Likely generator', 'Midjourney', '71%', 'Why it may look AI-generated', 'Pixel-level texture signal', 'closed-set estimate', 'Recall / sensitivity'] as $needle) {
            $this->assertStringContainsString($needle, $html, $needle);
        }
        if (class_exists(\Barryvdh\DomPDF\Facade\Pdf::class)) {
            $this->get("/api/v1/analyses/$id/report")->assertOk()->assertHeader('Content-Type', 'application/pdf');
        }
    }

    public function test_new_frontend_pages_are_routed(): void
    {
        $this->withoutVite();
        $this->get('/dashboard')->assertOk();
        $this->get('/profile')->assertRedirect('/login');
        $this->actingAs(User::factory()->create())->get('/profile')->assertOk();
    }

    public function test_upload_returns_full_result_when_job_already_ran_and_202_when_queued(): void
    {
        $this->postJson('/api/v1/analyses', ['image' => $this->png()])->assertOk()      // sync queue in tests
            ->assertJsonPath('status', 'done')->assertJsonPath('result.attribution.headline', 'Midjourney');

        \Illuminate\Support\Facades\Queue::fake();
        $this->actingAs(User::factory()->create())->postJson('/api/v1/analyses', ['image' => $this->png('q.png')])
            ->assertStatus(202)->assertJsonPath('status', 'queued')->assertJsonMissingPath('result');
    }

    public function test_failed_guest_analyses_do_not_lock_out_new_uploads(): void
    {
        // Two failed in-flight guest rows listed in the session used to hit the pending limit (2) for 15 minutes.
        $ids = [];
        foreach (['01HZZZZZZZZZZZZZZZZZZZZZZ1', '01HZZZZZZZZZZZZZZZZZZZZZZ2'] as $id) {
            Analysis::create([
                'uuid' => $id, 'user_id' => null, 'status' => 'failed', 'stage' => 'failed', 'progress' => 0,
                'sha256' => str_repeat('a', 64), 'original_name' => 'x.png', 'mime_type' => 'image/png', 'format' => 'PNG',
                'width' => 32, 'height' => 32, 'size_bytes' => 10, 'error_code' => 'ml_error',
            ]);
            $ids[] = $id;
        }

        $this->withSession(['guest.pending' => $ids])
            ->postJson('/api/v1/analyses', ['image' => $this->png()])
            ->assertOk()->assertJsonPath('status', 'done');
    }

    public function test_json_login_returns_the_intended_same_site_path(): void
    {
        $user = User::factory()->create(['password' => 'Password12345']);

        $this->get('/extension/connect')->assertRedirect('/login'); // remembers the intended page
        $this->postJson('/login', ['email' => $user->email, 'password' => 'Password12345'])
            ->assertOk()->assertJsonPath('redirect', '/extension/connect');
    }

    public function test_json_login_never_returns_an_off_site_redirect(): void
    {
        $user = User::factory()->create(['password' => 'Password12345']);

        $this->withSession(['url.intended' => 'https://evil.example/phish'])
            ->postJson('/login', ['email' => $user->email, 'password' => 'Password12345'])
            ->assertOk()->assertJsonPath('redirect', '/dashboard');
    }
}

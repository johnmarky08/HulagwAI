<?php

namespace Tests\Feature;

use App\Mail\PasswordResetMail;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Facades\Password;
use Tests\TestCase;

/** Forgot-password email flow and Google sign-in. */
class AccountRecoveryTest extends TestCase
{
    use RefreshDatabase;

    private const STRONG = 'NewPassword123';

    // ---- forgot / reset password ----------------------------------------------------------------------------------

    public function test_forgot_password_emails_a_branded_link_built_from_app_url(): void
    {
        Mail::fake();
        config(['app.url' => 'https://hulagwai.test']);
        $user = User::factory()->create(['email' => 'ana@example.com']);

        // A forged Host header must not end up in the emailed link (reset poisoning).
        $this->withHeader('Host', 'evil.example')
            ->postJson('/forgot-password', ['email' => 'ANA@example.com'])
            ->assertOk()->assertJsonPath('ok', true);

        Mail::assertSent(PasswordResetMail::class, function (PasswordResetMail $mail) use ($user) {
            return $mail->hasTo($user->email)
                && str_starts_with($mail->resetUrl, 'https://hulagwai.test/reset-password/')
                && ! str_contains($mail->resetUrl, 'evil.example');
        });
    }

    public function test_forgot_password_gives_the_same_answer_for_unknown_emails(): void
    {
        Mail::fake();
        User::factory()->create(['email' => 'known@example.com']);

        $known = $this->postJson('/forgot-password', ['email' => 'known@example.com'])->assertOk()->json('message');
        $unknown = $this->postJson('/forgot-password', ['email' => 'nobody@example.com'])->assertOk()->json('message');

        $this->assertSame($known, $unknown);
        Mail::assertSentCount(1);
    }

    public function test_password_reset_email_renders_with_logo_and_link(): void
    {
        $html = (new PasswordResetMail('Ana <b>', 'https://hulagwai.test/reset-password/abc?email=a%40b.c', 60))->render();

        $this->assertStringContainsString('Reset password', $html);
        $this->assertStringContainsString('https://hulagwai.test/reset-password/abc', $html);
        $this->assertStringContainsString('Ana &lt;b&gt;', $html); // user data is escaped
        // Logo is embedded (CID attachment when sent, data URI in a preview render), never hot-linked.
        $this->assertMatchesRegularExpression('/<img src="(cid:|data:image\/png;base64,)/', $html);
    }

    public function test_valid_token_resets_password_and_revokes_remember_token(): void
    {
        $user = User::factory()->create(['remember_token' => 'old-token']);
        $token = Password::createToken($user);

        $this->postJson('/reset-password', [
            'token' => $token, 'email' => $user->email,
            'password' => self::STRONG, 'password_confirmation' => self::STRONG,
        ])->assertOk()->assertJsonPath('ok', true);

        $user->refresh();
        $this->assertTrue(Hash::check(self::STRONG, $user->password));
        $this->assertNotSame('old-token', $user->remember_token);

        // Tokens are single-use.
        $this->postJson('/reset-password', [
            'token' => $token, 'email' => $user->email,
            'password' => 'Another123456', 'password_confirmation' => 'Another123456',
        ])->assertStatus(422);
    }

    public function test_invalid_token_and_weak_password_are_rejected(): void
    {
        $user = User::factory()->create();

        $this->postJson('/reset-password', [
            'token' => 'wrong', 'email' => $user->email,
            'password' => self::STRONG, 'password_confirmation' => self::STRONG,
        ])->assertStatus(422)->assertJsonValidationErrors('email');

        $this->postJson('/reset-password', [
            'token' => Password::createToken($user), 'email' => $user->email,
            'password' => 'short', 'password_confirmation' => 'short',
        ])->assertStatus(422)->assertJsonValidationErrors('password');
    }

    public function test_reset_pages_render_for_guests(): void
    {
        $this->withoutVite();
        $this->get('/forgot-password')->assertOk();
        $this->get('/reset-password/sometoken?email=a@b.c')->assertOk();
        $this->actingAs(User::factory()->create())->get('/forgot-password')->assertRedirect('/profile');
    }

    // ---- Google sign-in -------------------------------------------------------------------------------------------

    private function enableGoogle(): void
    {
        config(['services.google' => [
            'client_id' => 'client-id', 'client_secret' => 'client-secret',
            'redirect' => 'https://hulagwai.test/auth/google/callback',
        ]]);
    }

    private function fakeGoogle(array $profile): void
    {
        Http::fake([
            'oauth2.googleapis.com/token' => Http::response(['access_token' => 'at', 'token_type' => 'Bearer']),
            'openidconnect.googleapis.com/v1/userinfo' => Http::response($profile),
        ]);
    }

    /** Starts the flow and returns the state the server generated. */
    private function startGoogle(): string
    {
        $location = $this->get('/auth/google/redirect')->assertRedirect()->headers->get('Location');
        $this->assertStringStartsWith('https://accounts.google.com/o/oauth2/v2/auth?', $location);
        parse_str((string) parse_url($location, PHP_URL_QUERY), $q);
        $this->assertSame('S256', $q['code_challenge_method']);

        return $q['state'];
    }

    public function test_google_redirect_is_refused_when_not_configured(): void
    {
        config(['services.google.client_id' => null]);
        $this->get('/auth/google/redirect')->assertRedirect('/login?error=google_unavailable');
        $this->getJson('/api/v1/me')->assertJsonPath('auth.google', false);
    }

    public function test_google_sign_in_creates_an_account_without_password(): void
    {
        $this->enableGoogle();
        $this->getJson('/api/v1/me')->assertJsonPath('auth.google', true);
        $this->fakeGoogle(['sub' => 'g-123', 'email' => 'New.Person@gmail.com', 'email_verified' => true, 'name' => 'New Person']);

        $state = $this->startGoogle();
        $this->get("/auth/google/callback?state=$state&code=abc")->assertRedirect('/dashboard');

        $user = User::where('email', 'new.person@gmail.com')->firstOrFail();
        $this->assertAuthenticatedAs($user);
        $this->assertSame('g-123', $user->google_id);
        $this->assertNull($user->password);
        $this->getJson('/api/v1/me')->assertJsonPath('user.has_password', false)->assertJsonPath('user.google_connected', true);
    }

    public function test_google_sign_in_links_existing_account_by_verified_email(): void
    {
        $this->enableGoogle();
        $user = User::factory()->create(['email' => 'ana@example.com']);
        $this->fakeGoogle(['sub' => 'g-ana', 'email' => 'ana@example.com', 'email_verified' => 'true', 'name' => 'Ana']);

        $state = $this->startGoogle();
        $this->get("/auth/google/callback?state=$state&code=abc")->assertRedirect('/dashboard');

        $this->assertAuthenticatedAs($user);
        $this->assertSame('g-ana', $user->fresh()->google_id);
    }

    public function test_google_callback_rejects_bad_state_and_unverified_email(): void
    {
        $this->enableGoogle();
        $this->fakeGoogle(['sub' => 'g-x', 'email' => 'x@example.com', 'email_verified' => false]);

        $this->startGoogle();
        $this->get('/auth/google/callback?state=forged&code=abc')->assertRedirect('/login?error=google_failed');
        $this->assertGuest();

        $state = $this->startGoogle();
        $this->get("/auth/google/callback?state=$state&code=abc")->assertRedirect('/login?error=google_email_unverified');
        $this->assertGuest();
        $this->assertDatabaseMissing('users', ['email' => 'x@example.com']);
    }

    public function test_google_only_account_can_set_password_then_unlink(): void
    {
        $user = User::factory()->create(['password' => null]);
        $user->forceFill(['google_id' => 'g-1'])->save();

        $this->actingAs($user)->deleteJson('/api/v1/account/google')->assertStatus(422); // would lock the user out

        $this->putJson('/api/v1/account/password', ['password' => self::STRONG, 'password_confirmation' => self::STRONG])->assertOk();
        $this->deleteJson('/api/v1/account/google')->assertOk();
        $this->assertNull($user->fresh()->google_id);
    }

    public function test_google_only_account_deletion_is_confirmed_with_email(): void
    {
        $user = User::factory()->create(['password' => null, 'email' => 'g@example.com']);

        $this->actingAs($user)->postJson('/api/v1/account/delete', ['password' => 'wrong@example.com'])->assertStatus(422);
        $this->postJson('/api/v1/account/delete', ['password' => 'G@example.com'])->assertOk();
        $this->assertDatabaseMissing('users', ['id' => $user->id]);
    }

    public function test_password_login_never_works_for_google_only_accounts(): void
    {
        $user = User::factory()->create(['password' => null]);
        $this->postJson('/login', ['email' => $user->email, 'password' => ''])->assertStatus(422);
        $this->postJson('/login', ['email' => $user->email, 'password' => 'anything'])->assertStatus(422);
        $this->assertGuest();
    }
}

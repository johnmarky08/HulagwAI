<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class ProfileManagementTest extends TestCase
{
    use RefreshDatabase;

    public function test_signed_in_user_is_redirected_away_from_login_page(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/login')->assertRedirect('/dashboard');
    }

    public function test_signed_in_user_can_update_name_and_email(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->putJson('/api/v1/account/profile', [
            'name' => 'Alex Morgan',
            'email' => 'ALEX.MORGAN@example.com',
        ])->assertOk()
            ->assertJsonPath('user.name', 'Alex Morgan')
            ->assertJsonPath('user.email', 'alex.morgan@example.com');

        $this->assertDatabaseHas('users', [
            'id' => $user->id,
            'name' => 'Alex Morgan',
            'email' => 'alex.morgan@example.com',
        ]);
    }

    public function test_user_can_change_password_after_confirming_current_password(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->putJson('/api/v1/account/password', [
            'current_password' => 'password',
            'password' => 'NewPassword123',
            'password_confirmation' => 'NewPassword123',
        ])->assertOk()->assertJsonPath('ok', true);

        $this->assertTrue(Hash::check('NewPassword123', $user->fresh()->password));
    }

    public function test_password_change_rejects_an_incorrect_current_password(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->putJson('/api/v1/account/password', [
            'current_password' => 'wrong-password',
            'password' => 'NewPassword123',
            'password_confirmation' => 'NewPassword123',
        ])->assertUnprocessable()->assertJsonValidationErrors('current_password');

        $this->assertTrue(Hash::check('password', $user->fresh()->password));
    }
}

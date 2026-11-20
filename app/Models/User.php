<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use App\Mail\PasswordResetMail;
use Database\Factories\UserFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Illuminate\Support\Facades\Mail;

class User extends Authenticatable
{
    /** @use HasFactory<UserFactory> */
    use HasFactory, Notifiable;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'name',
        'email',
        'password',
    ];

    /**
     * The attributes that should be hidden for serialization.
     *
     * @var list<string>
     */
    protected $hidden = [
        'password',
        'remember_token',
        'google_id',
    ];

    /**
     * Called by the password broker. The link is built from APP_URL, never from the request's Host header,
     * so a forged Host cannot redirect reset tokens to an attacker's site (password-reset poisoning).
     */
    public function sendPasswordResetNotification($token): void
    {
        $url = rtrim((string) config('app.url'), '/').'/reset-password/'.rawurlencode($token)
            .'?email='.rawurlencode($this->email);

        Mail::to($this->email)->send(new PasswordResetMail(
            $this->name,
            $url,
            (int) config('auth.passwords.users.expire', 60),
        ));
    }

    /** JSON shape the frontend uses for the signed-in account (see GET /api/v1/me). */
    public function toAccountArray(): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'email' => $this->email,
            'has_password' => $this->password !== null,
            'google_connected' => $this->google_id !== null,
        ];
    }

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
        ];
    }
}

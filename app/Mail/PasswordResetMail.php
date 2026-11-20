<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

/** Branded "reset your password" email (HTML + plain text). The logo is embedded inline (CID), not hot-linked. */
class PasswordResetMail extends Mailable
{
    use Queueable, SerializesModels;

    public function __construct(
        public readonly string $name,
        public readonly string $resetUrl,
        public readonly int $expiresMinutes,
    ) {}

    public function envelope(): Envelope
    {
        return new Envelope(subject: 'Reset your HulagwAI password');
    }

    public function content(): Content
    {
        return new Content(
            view: 'mail.password-reset',
            text: 'mail.password-reset-text',
            with: ['logoPath' => public_path('icons/hulagwai-128.png')],
        );
    }
}

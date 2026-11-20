<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="dark light">
    <meta name="supported-color-schemes" content="dark light">
    <title>Reset your HulagwAI password</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0c13;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;">
    {{-- Preheader (inbox preview text) --}}
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
        Use this link within {{ $expiresMinutes }} minutes to choose a new HulagwAI password.
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#0a0c13;">
        <tr>
            <td align="center" style="padding:32px 16px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
                    {{-- Logo --}}
                    <tr>
                        <td align="center" style="padding-bottom:24px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td style="padding-right:10px;vertical-align:middle;">
                                        <img src="{{ $message->embed($logoPath) }}" width="40" height="40" alt="" style="display:block;border:0;border-radius:10px;">
                                    </td>
                                    <td style="vertical-align:middle;font-size:24px;font-weight:800;letter-spacing:-0.5px;color:#f1f5f9;">
                                        Hulagw<span style="color:#818cf8;">AI</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {{-- Card --}}
                    <tr>
                        <td style="background-color:#111521;border:1px solid #4f46e5;border-radius:16px;padding:0;">
                            <div style="height:4px;background-color:#6366f1;background-image:linear-gradient(90deg,#a78bfa,#6366f1);border-radius:16px 16px 0 0;"></div>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td style="padding:32px 32px 8px;">
                                        <p style="margin:0 0 8px;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#818cf8;">Password reset</p>
                                        <h1 style="margin:0;font-size:26px;line-height:1.25;font-weight:800;color:#ffffff;">Choose a new password</h1>
                                        <p style="margin:16px 0 0;font-size:15px;line-height:1.6;color:#cbd5e1;">
                                            Hi {{ $name }}, we received a request to reset the password for your HulagwAI account.
                                            Click the button below to choose a new one.
                                        </p>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding:28px 32px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td align="center" style="border-radius:12px;background-color:#4f46e5;">
                                                    <a href="{{ $resetUrl }}" target="_blank" rel="noopener" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:12px;border:1px solid #818cf8;">Reset password</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:0 32px 8px;">
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#1e1b4b;border:1px solid #4338ca;border-radius:12px;">
                                            <tr>
                                                <td style="padding:14px 16px;font-size:13px;line-height:1.55;color:#c7d2fe;">
                                                    <strong style="color:#e0e7ff;">This link expires in {{ $expiresMinutes }} minutes</strong> and can only be used once.
                                                    If you did not ask for a reset, you can ignore this email; your password will not change.
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:20px 32px 32px;">
                                        <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;">
                                            Button not working? Copy this address into your browser:
                                        </p>
                                        <p style="margin:6px 0 0;font-size:12px;line-height:1.5;word-break:break-all;">
                                            <a href="{{ $resetUrl }}" target="_blank" rel="noopener" style="color:#a5b4fc;text-decoration:underline;">{{ $resetUrl }}</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {{-- Footer --}}
                    <tr>
                        <td align="center" style="padding:24px 16px 0;font-size:12px;line-height:1.6;color:#64748b;">
                            HulagwAI never asks for your password by email.<br>
                            &copy; {{ date('Y') }} HulagwAI &middot; Discover what's real. Detect what's AI.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>

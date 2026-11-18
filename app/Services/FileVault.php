<?php

namespace App\Services;

use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use RuntimeException;

/**
 * Authenticated encryption for image blobs (XChaCha20-Poly1305 via libsodium).
 *
 *  - key: HKDF-SHA256 of APP_KEY with a purpose label (separate from the DB encrypter key)
 *  - nonce: random 24 bytes per file
 *  - AAD: "<analysis uuid>:<kind>" -> a blob copied onto another row fails to decrypt
 *  - files live on the *private* disk (storage/app/private), never under /public
 */
final class FileVault
{
    private const MAGIC = 'HV1';

    private string $key;

    public function __construct()
    {
        $raw = (string) config('app.key');
        if (str_starts_with($raw, 'base64:')) {
            $raw = (string) base64_decode(substr($raw, 7), true);
        }
        if ($raw === '') {
            throw new RuntimeException('APP_KEY is not set. Run: php artisan key:generate');
        }
        $this->key = hash_hkdf('sha256', $raw, \SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_KEYBYTES, 'hulagwai/filevault/v1');
    }

    public function put(string $plain, string $aad): string
    {
        $nonce = random_bytes(\SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
        $cipher = sodium_crypto_aead_xchacha20poly1305_ietf_encrypt($plain, $aad, $nonce, $this->key);

        $id = (string) Str::ulid();
        $path = 'vault/'.substr(strtolower($id), -2).'/'.$id.'.bin';
        Storage::disk('local')->put($path, self::MAGIC.$nonce.$cipher);

        return $path;
    }

    public function get(string $path, string $aad): string
    {
        $blob = Storage::disk('local')->get($path);
        $hdr = strlen(self::MAGIC) + \SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES;
        if (! is_string($blob) || strlen($blob) <= $hdr + \SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_ABYTES
            || ! str_starts_with($blob, self::MAGIC)) {
            throw new RuntimeException('Vault blob missing or malformed.');
        }
        $nonce = substr($blob, strlen(self::MAGIC), \SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
        $plain = sodium_crypto_aead_xchacha20poly1305_ietf_decrypt(substr($blob, $hdr), $aad, $nonce, $this->key);
        if ($plain === false) {
            throw new RuntimeException('Vault blob failed authentication.');
        }

        return $plain;
    }

    public function delete(?string $path): void
    {
        if ($path !== null && $path !== '' && str_starts_with($path, 'vault/') && ! str_contains($path, '..')) {
            Storage::disk('local')->delete($path);
        }
    }
}

<?php

namespace App\Services;

use Illuminate\Http\UploadedFile;
use Illuminate\Validation\ValidationException;

/**
 * Server-side gatekeeper for uploads. Never trusts the client's MIME type or
 * filename: content is sniffed (finfo + image header parse), dimensions are
 * bounded (decompression-bomb guard) and the name is sanitised.
 */
final class ImageGuard
{
    /**
     * @return array{bytes:string,mime:string,format:string,width:int,height:int,size:int,sha256:string,name:string}
     */
    public function inspect(UploadedFile $file): array
    {
        $cfg = config('hulagwai.upload');

        if (! $file->isValid()) {
            $this->reject('The upload failed. Please try again.');
        }

        $ext = strtolower($file->getClientOriginalExtension());
        if (! isset($cfg['extensions'][$ext])) {
            $this->reject('Unsupported file type. Please use JPG, JPEG, PNG or WEBP.');
        }

        // The bytes we actually read are authoritative - never the client-reported size.
        $bytes = file_get_contents($file->getRealPath(), false, null, 0, $cfg['max_bytes'] + 1);
        $size = $bytes === false ? 0 : strlen($bytes);
        if ($size <= 0 || $size > $cfg['max_bytes']) {
            $this->reject('Image must be between 1 byte and '.round($cfg['max_bytes'] / 1048576).' MB.');
        }

        $mime = (new \finfo(FILEINFO_MIME_TYPE))->buffer($bytes);
        if (! in_array($mime, $cfg['extensions'], true) || $mime !== $cfg['extensions'][$ext]) {
            $this->reject('File content does not match its extension, or is not a supported image.');
        }

        $info = @getimagesizefromstring($bytes);
        if ($info === false || image_type_to_mime_type($info[2]) !== $mime) {
            $this->reject('The file is not a valid image.');
        }

        [$w, $h] = [(int) $info[0], (int) $info[1]];
        if (min($w, $h) < $cfg['min_side'] || max($w, $h) > $cfg['max_side'] || $w * $h > $cfg['max_pixels']) {
            $this->reject("Image dimensions are out of range ({$cfg['min_side']}px minimum, {$cfg['max_side']}px maximum side, ".number_format($cfg['max_pixels'] / 1e6, 0).' MP maximum).');
        }

        return [
            'bytes' => $bytes,
            'mime' => $mime,
            'format' => match ($mime) {
                'image/jpeg' => 'JPEG', 'image/png' => 'PNG', default => 'WEBP',
            },
            'width' => $w,
            'height' => $h,
            'size' => $size,
            'sha256' => hash('sha256', $bytes),
            'name' => $this->safeName($file->getClientOriginalName(), $ext),
        ];
    }

    private function safeName(string $name, string $ext): string
    {
        $name = basename(str_replace('\\', '/', $name));
        $name = mb_scrub($name);
        $name = (string) preg_replace('/[\x00-\x1F\x7F\x{202A}-\x{202E}\x{2066}-\x{2069}]/u', '', $name); // control + bidi chars
        $name = mb_substr(trim($name), 0, 120);

        return $name !== '' ? $name : 'image.'.$ext;
    }

    private function reject(string $message): never
    {
        throw ValidationException::withMessages(['image' => [$message]]);
    }
}

<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class UploadImageRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        // Real content checks (magic bytes, dimensions, name) happen in App\Services\ImageGuard.
        return ['image' => ['required', 'file', 'max:'.(int) (config('hulagwai.upload.max_bytes') / 1024)]];
    }

    public function messages(): array
    {
        return ['image.max' => 'Image must be 5 MB or smaller.', 'image.required' => 'Please choose an image to analyze.'];
    }
}

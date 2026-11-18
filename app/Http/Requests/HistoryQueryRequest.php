<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class HistoryQueryRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'search' => ['nullable', 'string', 'max:100'],
            'result' => ['nullable', Rule::in(['all', 'real', 'ai_generated', 'inconclusive'])],
            'range' => ['nullable', Rule::in(['all', '7d', '30d', '90d'])],
            'sort' => ['nullable', Rule::in(['newest', 'oldest', 'confidence_desc', 'confidence_asc'])],
            'page' => ['nullable', 'integer', 'min:1', 'max:10000'],
            'per_page' => ['nullable', 'integer', 'min:1', 'max:50'],
            'format' => ['nullable', Rule::in(['csv', 'json'])],
        ];
    }
}

<?php

namespace App\Exceptions;

use RuntimeException;

class QuotaExceeded extends RuntimeException
{
    public function __construct(public readonly int $used, public readonly int $limit)
    {
        parent::__construct('quota_exceeded');
    }
}

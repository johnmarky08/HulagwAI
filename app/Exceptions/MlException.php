<?php

namespace App\Exceptions;

use RuntimeException;
use Throwable;

/** Failure talking to (or understanding) the ML service. $errorCode is safe to show users. */
class MlException extends RuntimeException
{
    public function __construct(public readonly string $errorCode, ?Throwable $previous = null)
    {
        parent::__construct($errorCode, 0, $previous);
    }
}

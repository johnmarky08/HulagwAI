<?php

namespace App\Http\Controllers;

use Inertia\Inertia;
use Inertia\Response;

/** Inertia page shells. Data is loaded through the JSON API (/api/v1/...) so any frontend can reuse it. */
class PageController extends Controller
{
    public function home(): Response
    {
        return Inertia::render('Home');
    }

    public function detection(): Response
    {
        return Inertia::render('Detection');
    }

    public function history(): Response
    {
        return Inertia::render('History');
    }

    public function about(): Response
    {
        return Inertia::render('About');
    }
}

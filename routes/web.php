<?php

use App\Http\Controllers\AccountController;
use App\Http\Controllers\AnalysisController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\HistoryController;
use App\Http\Controllers\MetaController;
use App\Http\Controllers\PageController;
use App\Http\Controllers\ReportController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Pages (Inertia shells - safe for the frontend team to replace)
|--------------------------------------------------------------------------
*/
Route::get('/', [PageController::class, 'home'])->name('home');
Route::get('/detect', [PageController::class, 'detection'])->name('detection');
Route::get('/history', [PageController::class, 'history'])->name('history');
Route::get('/about', [PageController::class, 'about'])->name('about');

Route::middleware('throttle:auth')->group(function () {
    Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
    Route::post('/login', [AuthController::class, 'login']);
    Route::get('/register', [AuthController::class, 'showRegister'])->name('register');
    Route::post('/register', [AuthController::class, 'register'])->middleware('throttle:register');
    Route::post('/logout', [AuthController::class, 'logout'])->name('logout');
});

/*
|--------------------------------------------------------------------------
| JSON API  (session cookie + CSRF protected; see docs/API.md)
|--------------------------------------------------------------------------
*/
Route::prefix('api/v1')->middleware('throttle:api')->group(function () {
    Route::get('/me', [MetaController::class, 'me']);
    Route::get('/model', [MetaController::class, 'model']);
    Route::get('/health', [MetaController::class, 'health']);

    Route::post('/analyses', [AnalysisController::class, 'store'])->middleware('throttle:analyze');
    Route::get('/analyses/{id}', [AnalysisController::class, 'show']);
    Route::get('/analyses/{id}/image', [AnalysisController::class, 'image']);
    Route::get('/analyses/{id}/report', [ReportController::class, 'show'])->middleware('throttle:report');
    Route::delete('/analyses/{id}', [AnalysisController::class, 'destroy']);

    Route::get('/history', [HistoryController::class, 'index']);
    Route::get('/history/export', [HistoryController::class, 'export'])->middleware('throttle:report');
    Route::delete('/history', [HistoryController::class, 'clear']);

    Route::post('/account/delete', [AccountController::class, 'destroy'])->middleware('auth');
});

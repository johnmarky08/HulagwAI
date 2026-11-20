<?php

use App\Http\Controllers\AccountController;
use App\Http\Controllers\AnalysisController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\ExtensionAuthController;
use App\Http\Controllers\GoogleAuthController;
use App\Http\Controllers\HistoryController;
use App\Http\Controllers\MetaController;
use App\Http\Controllers\PageController;
use App\Http\Controllers\PasswordResetController;
use App\Http\Controllers\ReportController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Pages (Inertia shells - safe for the frontend team to replace)
|--------------------------------------------------------------------------
*/
Route::get('/', [PageController::class, 'home'])->name('home');
Route::get('/dashboard', [PageController::class, 'dashboard'])->name('dashboard');
Route::get('/detect', [PageController::class, 'detection'])->name('detection');
Route::get('/history', [PageController::class, 'history'])->name('history');
Route::get('/extension', [PageController::class, 'extension'])->name('extension');
Route::get('/about', [PageController::class, 'about'])->name('about');
Route::get('/evaluation', [PageController::class, 'evaluation'])->name('evaluation');
Route::get('/profile', [PageController::class, 'profile'])->middleware('auth')->name('profile');
Route::get('/extension/connect', [PageController::class, 'extensionConnect'])->middleware('auth')->name('extension.connect');

Route::middleware('throttle:auth')->group(function () {
    Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
    Route::post('/login', [AuthController::class, 'login']);
    Route::get('/register', [AuthController::class, 'showRegister'])->name('register');
    Route::post('/register', [AuthController::class, 'register'])->middleware('throttle:register');
    Route::post('/logout', [AuthController::class, 'logout'])->name('logout');
    Route::get('/forgot-password', [PasswordResetController::class, 'showForgot'])->name('password.request');
    Route::post('/forgot-password', [PasswordResetController::class, 'sendLink'])->middleware('throttle:password-reset')->name('password.email');
    Route::get('/reset-password/{token}', [PasswordResetController::class, 'showReset'])->name('password.reset');
    Route::post('/reset-password', [PasswordResetController::class, 'reset'])->middleware('throttle:password-reset')->name('password.update');
    Route::get('/auth/google/redirect', [GoogleAuthController::class, 'redirect'])->name('auth.google');
    Route::get('/auth/google/callback', [GoogleAuthController::class, 'callback'])->name('auth.google.callback');
});

/*
|--------------------------------------------------------------------------
| JSON API  (session cookie + CSRF protected; see docs/API.md)
|--------------------------------------------------------------------------
*/
Route::prefix('api/v1')->middleware('throttle:api')->group(function () {
    Route::get('/me', [MetaController::class, 'me']);
    Route::get('/model', [MetaController::class, 'model']);
    Route::get('/model/evaluation', [MetaController::class, 'evaluation']);
    Route::get('/health', [MetaController::class, 'health']);

    Route::post('/extension/pair', [ExtensionAuthController::class, 'pair'])->middleware('auth');
    Route::post('/extension/exchange', [ExtensionAuthController::class, 'exchange']);
    Route::delete('/extension/token', [ExtensionAuthController::class, 'revoke'])->middleware('extension.token:required');
    Route::post('/extension/analyses', [AnalysisController::class, 'store'])->middleware(['extension.token:required', 'throttle:analyze']);
    Route::get('/extension/analyses/{id}', [AnalysisController::class, 'show'])->middleware('extension.token:required');

    Route::post('/analyses', [AnalysisController::class, 'store'])->middleware('throttle:analyze');
    Route::get('/analyses/{id}', [AnalysisController::class, 'show']);
    // Optional extension token lets the popup show thumbnails of its own analyses.
    Route::get('/analyses/{id}/image', [AnalysisController::class, 'image'])->middleware('extension.token:optional');
    Route::get('/analyses/{id}/report', [ReportController::class, 'show'])->middleware('throttle:report');
    Route::delete('/analyses/{id}', [AnalysisController::class, 'destroy']);

    Route::get('/history', [HistoryController::class, 'index']);
    Route::get('/history/export', [HistoryController::class, 'export'])->middleware('throttle:report');
    Route::delete('/history', [HistoryController::class, 'clear']);

    Route::put('/account/profile', [AccountController::class, 'updateProfile'])->middleware('auth');
    Route::put('/account/password', [AccountController::class, 'updatePassword'])->middleware('auth');
    Route::post('/account/delete', [AccountController::class, 'destroy'])->middleware('auth');
    Route::delete('/account/google', [GoogleAuthController::class, 'unlink'])->middleware('auth');
});

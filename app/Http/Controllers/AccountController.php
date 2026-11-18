<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use App\Models\AuditLog;
use App\Services\FileVault;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

class AccountController extends Controller
{
    /** POST /api/v1/account/delete  {password}  -> erases the account and every stored image */
    public function destroy(Request $request, FileVault $vault): JsonResponse|RedirectResponse
    {
        $request->validate(['password' => ['required', 'string', 'max:128']]);
        $user = $request->user();

        if (! Hash::check($request->input('password'), $user->password)) {
            throw ValidationException::withMessages(['password' => ['Password is incorrect.']]);
        }

        // Log out FIRST: logout() rotates the remember token with a save(), which would re-insert a deleted user.
        Auth::guard('web')->logout();

        $paths = [];
        DB::transaction(function () use ($user, &$paths) {
            foreach (Analysis::where('user_id', $user->id)->get() as $a) {
                array_push($paths, $a->file_path, $a->preview_path, $a->thumb_path);
            }
            $user->delete(); // analyses cascade
        });
        array_map(fn ($p) => $vault->delete($p), $paths);

        AuditLog::record('account_deleted', $request, null);
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return $request->expectsJson() ? response()->json(['ok' => true]) : redirect('/');
    }
}

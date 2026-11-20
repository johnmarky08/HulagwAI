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
use Illuminate\Validation\Rule;
use Illuminate\Validation\Rules\Password;
use Illuminate\Validation\ValidationException;

class AccountController extends Controller
{
    /** PUT /api/v1/account/profile {name, email} */
    public function updateProfile(Request $request): JsonResponse
    {
        $user = $request->user();
        $request->merge(['email' => mb_strtolower(trim((string) $request->input('email')))]);
        $data = $request->validate([
            'name' => ['required', 'string', 'min:2', 'max:60'],
            'email' => ['required', 'email:rfc', 'max:190', Rule::unique('users', 'email')->ignore($user->id)],
        ]);
        $user->fill($data)->save();
        AuditLog::record('profile_updated', $request, $user->id);

        return response()->json(['user' => ['id' => $user->id, 'name' => $user->name, 'email' => $user->email]]);
    }

    /** PUT /api/v1/account/password {current_password, password, password_confirmation} */
    public function updatePassword(Request $request): JsonResponse
    {
        $request->validate([
            'current_password' => ['required', 'string', 'max:128'],
            'password' => ['required', 'string', 'max:128', 'confirmed', Password::defaults()],
        ]);
        $user = $request->user();
        if (! Hash::check($request->input('current_password'), $user->password)) {
            throw ValidationException::withMessages(['current_password' => ['Current password is incorrect.']]);
        }
        $user->password = $request->input('password');
        $user->save();
        AuditLog::record('password_changed', $request, $user->id);

        return response()->json(['ok' => true]);
    }

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

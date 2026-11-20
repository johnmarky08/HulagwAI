import { auth } from "../api/auth";
import { session } from "../api/session.svelte.js";
import { errorMessage } from "../api/client";

export const profile = $state({
    me: null,
    name: "",
    email: "",
    loading: true,
    saving: false,
    saved: false,
    passwordChanged: false,
    changingPassword: false,
    passwordFormOpen: false,
    currentPassword: "",
    newPassword: "",
    newPasswordConfirmation: "",
    deleting: false,
    confirmDeleteOpen: false,
    password: "",
    error: "",
});

export async function loadProfile() {
    // This state outlives the page: clear banners and half-filled forms from an earlier visit.
    Object.assign(profile, {
        saved: false,
        passwordChanged: false,
        passwordFormOpen: false,
        currentPassword: "",
        newPassword: "",
        newPasswordConfirmation: "",
        confirmDeleteOpen: false,
        password: "",
        error: "",
    });
    // Show the known account straight away on navigation; the fresh /me result then replaces it.
    const cached = session.value;
    if (cached?.authenticated) {
        profile.me = { ...cached };
        profile.name = cached.user.name;
        profile.email = cached.user.email;
        profile.loading = false;
    }
    try {
        const fresh = await auth.me();
        session.value = fresh;
        profile.me = fresh;
        if (!profile.me?.authenticated) {
            window.location.assign("/login");
            return;
        }
        profile.name = profile.me.user.name;
        profile.email = profile.me.user.email;
    } catch {
        window.location.assign("/login");
    } finally {
        profile.loading = false;
    }
}

export async function saveProfile(event) {
    event.preventDefault();
    profile.saving = true;
    profile.saved = false;
    profile.passwordChanged = false;
    profile.error = "";
    try {
        const result = await auth.updateProfile(profile.name, profile.email);
        profile.me.user = result.user;
        profile.name = result.user.name;
        profile.email = result.user.email;
        profile.saved = true;
        window.dispatchEvent(new CustomEvent("hulagwai:profile-updated", { detail: result.user }));
    } catch (error) {
        profile.error = errorMessage(error);
    } finally {
        profile.saving = false;
    }
}

export async function changeProfilePassword(event) {
    event.preventDefault();
    profile.changingPassword = true;
    profile.passwordChanged = false;
    profile.saved = false;
    profile.error = "";
    try {
        await auth.changePassword(
            profile.currentPassword,
            profile.newPassword,
            profile.newPasswordConfirmation,
        );
        profile.passwordFormOpen = false;
        profile.currentPassword = "";
        profile.newPassword = "";
        profile.newPasswordConfirmation = "";
        profile.passwordChanged = true;
        if (profile.me?.user) profile.me.user.has_password = true;
    } catch (error) {
        profile.error = errorMessage(error);
    } finally {
        profile.changingPassword = false;
    }
}

export async function logoutProfile() {
    try {
        await auth.logout();
        window.location.assign("/");
    } catch (error) {
        profile.error = errorMessage(error);
    }
}

export async function deleteProfile(event) {
    event.preventDefault();
    if (!window.confirm("Permanently delete your account and all saved analysis history? This cannot be undone.")) return;
    profile.deleting = true;
    profile.error = "";
    try {
        await auth.deleteAccount(profile.password);
        window.location.assign("/");
    } catch (error) {
        profile.error = errorMessage(error);
    } finally {
        profile.deleting = false;
    }
}

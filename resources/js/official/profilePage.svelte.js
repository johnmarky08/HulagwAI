import { auth } from "../api/auth";
import { errorMessage } from "../api/client";

export const profile = $state({ me: null, loading: true, deleting: false, password: "", error: "" });

export async function loadProfile() {
    try {
        profile.me = await auth.me();
        if (!profile.me?.authenticated) window.location.assign("/login");
    } catch {
        window.location.assign("/login");
    } finally {
        profile.loading = false;
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

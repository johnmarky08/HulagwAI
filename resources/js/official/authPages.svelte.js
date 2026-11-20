import { auth } from "../api/auth";
import { errorMessage } from "../api/client";

export const loginForm = $state({ email: "", password: "", error: "", busy: false, showPassword: false });
export const registerForm = $state({ name: "", email: "", password: "", confirm: "", error: "", busy: false, showPassword: false });

export async function submitLogin(event) {
    event.preventDefault();
    loginForm.busy = true;
    loginForm.error = "";
    try {
        await auth.login(loginForm.email, loginForm.password);
        window.location.assign("/dashboard");
    } catch (error) {
        loginForm.error = errorMessage(error);
    } finally {
        loginForm.busy = false;
    }
}

export async function submitRegister(event) {
    event.preventDefault();
    registerForm.busy = true;
    registerForm.error = "";
    try {
        await auth.register(registerForm.name, registerForm.email, registerForm.password, registerForm.confirm);
        window.location.assign("/dashboard");
    } catch (error) {
        registerForm.error = errorMessage(error);
    } finally {
        registerForm.busy = false;
    }
}

export function toggleLoginPassword() {
    loginForm.showPassword = !loginForm.showPassword;
}

export function toggleRegisterPassword() {
    registerForm.showPassword = !registerForm.showPassword;
}

/** Messages for ?error= codes set by the Google sign-in callback (GoogleAuthController). */
const googleErrors = {
    google_unavailable: "Google sign-in is not configured on this server yet.",
    google_cancelled: "Google sign-in was cancelled.",
    google_failed: "Google sign-in could not be completed. Please try again.",
    google_email_unverified: "Your Google account's email address is not verified.",
    google_in_use: "That Google account is already linked to another HulagwAI account.",
};

export function googleErrorFromUrl() {
    if (typeof location === "undefined") return "";
    return googleErrors[new URLSearchParams(location.search).get("error")] ?? "";
}

export const forgotForm = $state({ email: "", error: "", message: "", busy: false });
export const resetForm = $state({ password: "", confirm: "", error: "", message: "", busy: false, showPassword: false });

export async function submitForgot(event) {
    event.preventDefault();
    forgotForm.busy = true;
    forgotForm.error = "";
    forgotForm.message = "";
    try {
        forgotForm.message = (await auth.forgotPassword(forgotForm.email)).message;
    } catch (error) {
        forgotForm.error = errorMessage(error);
    } finally {
        forgotForm.busy = false;
    }
}

export async function submitReset(event, token, email) {
    event.preventDefault();
    resetForm.busy = true;
    resetForm.error = "";
    resetForm.message = "";
    try {
        resetForm.message = (await auth.resetPassword(token, email, resetForm.password, resetForm.confirm)).message;
        resetForm.password = "";
        resetForm.confirm = "";
    } catch (error) {
        resetForm.error = errorMessage(error);
    } finally {
        resetForm.busy = false;
    }
}

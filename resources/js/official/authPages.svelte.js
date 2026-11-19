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

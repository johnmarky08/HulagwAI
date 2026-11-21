<script>
    import { onMount } from "svelte";
    import GoogleSignInButton from "./GoogleSignInButton.svelte";
    import { inertia } from "@inertiajs/svelte";
    import {
        loginForm as form,
        submitLogin,
        toggleLoginPassword,
    } from "../../official/authPages.svelte.js";

    let { onClose } = $props();

    // Move the overlay to <body>. Inside .route-page, transform/filter make position:fixed act like absolute.
    function portal(node) {
        document.body.append(node);
        return {
            destroy() {
                node.remove();
            },
        };
    }

    onMount(() => {
        const onKeydown = (event) => {
            if (event.key === "Escape") onClose();
        };
        window.addEventListener("keydown", onKeydown);
        return () => window.removeEventListener("keydown", onKeydown);
    });
</script>

<div
    use:portal
    class="login-overlay fixed inset-0 z-[100] grid place-items-center overflow-y-auto bg-slate-950/75 px-4 py-8 backdrop-blur-sm"
    role="presentation"
    onclick={(event) => {
        if (event.target === event.currentTarget) onClose();
    }}
>
    <div
        class="login-dialog relative w-full max-w-md rounded-2xl border border-indigo-400/30 bg-[#111521] p-6 shadow-2xl shadow-indigo-950/50 sm:p-8"
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-dialog-title"
        tabindex="-1"
    >
        <button
            type="button"
            class="absolute right-4 top-4 grid size-9 place-items-center rounded-lg text-xl text-slate-400 transition hover:bg-slate-800 hover:text-white"
            aria-label="Close login"
            onclick={onClose}>×</button
        >
        <span
            class="inline-flex rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[.14em] text-indigo-300"
            >Welcome back</span
        >
        <h2
            id="login-dialog-title"
            class="mt-4 text-2xl font-extrabold text-white"
        >
            Log In to HulagwAI
        </h2>
        <p class="mt-2 pr-5 text-sm leading-6 text-slate-400">
            Log in to save your scans and revisit your analysis history.
        </p>

        <div class="mt-6">
            <GoogleSignInButton />
        </div>
        <div class="my-6 flex items-center gap-3 text-xs text-slate-500">
            <span class="h-px flex-1 bg-slate-800"></span>or continue with email<span
                class="h-px flex-1 bg-slate-800"
            ></span>
        </div>

        {#if form.error}
            <p
                class="mt-5 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                role="alert"
            >
                {form.error}
            </p>
        {/if}
        <form class="mt-6 space-y-4" onsubmit={(event) => submitLogin(event, true)}>
            <label class="block text-sm font-medium text-slate-200"
                >Email
                <input
                    class="auth-input mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                    type="email"
                    placeholder="you@example.com"
                    bind:value={form.email}
                    autocomplete="email"
                    required
                />
            </label>
            <label class="block text-sm font-medium text-slate-200"
                >Password
                <span class="relative mt-2 block">
                    <input
                        class="auth-input w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 pr-14 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                        type={form.showPassword ? "text" : "password"}
                        placeholder="Enter your password"
                        bind:value={form.password}
                        autocomplete="current-password"
                        required
                    />
                    <button
                        type="button"
                        class="absolute inset-y-0 right-3 text-xs text-slate-400 hover:text-indigo-300"
                        onclick={toggleLoginPassword}
                        aria-label={form.showPassword
                            ? "Hide password"
                            : "Show password"}
                        >{form.showPassword ? "Hide" : "Show"}</button
                    >
                </span>
            </label>
            <div class="text-right">
                <a
                    use:inertia
                    class="text-xs text-indigo-300 underline-offset-4 hover:underline py-2.5 -my-2.5 sm:py-0 sm:my-0"
                    href="/forgot-password">Forgot password?</a
                >
            </div>
            <button
                class="w-full rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
                disabled={form.busy}
                >{form.busy ? "Logging in…" : "Log In"}</button
            >
        </form>
        <p class="mt-5 text-center text-sm text-slate-400">
            New to HulagwAI?
            <a
                use:inertia
                class="font-semibold text-white underline decoration-indigo-400 underline-offset-4 hover:text-indigo-300"
                href="/register">Create an account</a
            >
        </p>
        <p
            class="mt-5 border-t border-slate-800 pt-4 text-center text-xs text-slate-500"
        >
            You can also <button
                type="button"
                class="text-indigo-300 underline underline-offset-2 hover:text-indigo-200"
                onclick={onClose}>continue browsing</button
            > without logging in.
        </p>
    </div>
</div>

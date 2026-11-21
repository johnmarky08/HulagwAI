<script>
    import GoogleSignInButton from "../Components/GoogleSignInButton.svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "../Components/Layout.svelte";
    import {
        loginForm as form,
        submitLogin,
        toggleLoginPassword,
        googleErrorFromUrl,
    } from "../../official/authPages.svelte.js";

    const googleError = googleErrorFromUrl();
</script>

<svelte:head><title>HulagwAI · Log In</title></svelte:head>
<Layout active="">
    <main class="grid min-h-[calc(100vh-80px)] place-items-center px-5 py-12">
        <div class="w-full max-w-[480px]">
            <section
                class="rounded-2xl border border-slate-800 bg-slate-900/70 p-7 shadow-2xl shadow-black/20 sm:p-8"
            >
                <h1 class="text-3xl font-extrabold tracking-tight">
                    Welcome Back
                </h1>
                <p class="mt-2 text-sm text-slate-400">
                    Log in to revisit your saved analysis results.
                </p>
                <div class="mt-6">
                    <GoogleSignInButton label="Continue with Google" />
                </div>
                <div
                    class="my-6 flex items-center gap-3 text-xs text-slate-500"
                >
                    <span class="h-px flex-1 bg-slate-800"></span>or continue
                    with email<span class="h-px flex-1 bg-slate-800"></span>
                </div>
                {#if googleError && !form.error}<p
                        class="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                        role="alert"
                    >
                        {googleError}
                    </p>{/if}
                {#if form.error}<p
                        class="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                        role="alert"
                    >
                        {form.error}
                    </p>{/if}
                <form class="space-y-4" onsubmit={submitLogin}>
                    <label class="block text-sm font-medium"
                        >Email<input
                            class="auth-input mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                            type="email"
                            placeholder="you@example.com"
                            bind:value={form.email}
                            autocomplete="email"
                            required
                        /></label
                    >
                    <label class="block text-sm font-medium"
                        >Password<span class="relative mt-2 block"
                            ><input
                                class="auth-input w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 pr-14 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                                type={form.showPassword ? "text" : "password"}
                                placeholder="Enter your password"
                                bind:value={form.password}
                                autocomplete="current-password"
                                required
                            /><button
                                type="button"
                                class="absolute inset-y-0 right-3 text-xs text-slate-400 hover:text-indigo-300"
                                onclick={toggleLoginPassword}
                                aria-label={form.showPassword
                                    ? "Hide password"
                                    : "Show password"}
                                >{form.showPassword ? "Hide" : "Show"}</button
                            ></span
                        ></label
                    >
                    <div class="text-right">
                        <a
                            use:inertia
                            class="text-xs text-indigo-300 underline-offset-4 hover:underline py-2.5 -my-2.5 sm:py-0 sm:my-0"
                            href="/forgot-password">Forgot password?</a
                        >
                    </div>
                    <button
                        class="w-full rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:-translate-y-0.5 hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
                        disabled={form.busy}
                        >{form.busy ? "Logging in…" : "Log In"}</button
                    >
                </form>
                <p class="mt-6 text-center text-sm text-slate-400">
                    New to HulagwAI? <a
                        use:inertia
                        class="font-semibold text-white underline decoration-indigo-400 underline-offset-4 hover:text-indigo-300 py-2.5 -my-2.5 sm:py-0 sm:my-0"
                        href="/register">Sign up</a
                    >
                </p>
            </section>
            <div class="mt-6 text-center">
                <a
                    use:inertia
                    class="text-sm text-slate-400 underline underline-offset-4 transition hover:text-indigo-300 py-2.5 -my-2.5 sm:py-0 sm:my-0"
                    href="/detect">Continue without an account</a
                >
                <p class="mt-2 text-xs text-slate-500">
                    An account is only needed to save your history.
                </p>
            </div>
        </div>
    </main>
</Layout>

<script>
    import GoogleSignInButton from "../Components/GoogleSignInButton.svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "../Components/Layout.svelte";
    import {
        registerForm as form,
        submitRegister,
        toggleRegisterPassword,
    } from "../../official/authPages.svelte.js";
</script>

<svelte:head><title>HulagwAI · Create account</title></svelte:head>
<Layout active="">
    <main class="grid min-h-[calc(100vh-80px)] place-items-center px-5 py-12">
        <div class="w-full max-w-[480px]">
            <section
                class="rounded-2xl border border-slate-800 bg-slate-900/70 p-7 shadow-2xl shadow-black/20 sm:p-8"
            >
                <h1 class="text-3xl font-extrabold tracking-tight">
                    Save your analysis history
                </h1>
                <p class="mt-2 text-sm text-slate-400">
                    Create a free account to keep your results in one place.
                </p>
                <div class="mt-6">
                    <GoogleSignInButton label="Sign up with Google" />
                </div>
                <div
                    class="my-6 flex items-center gap-3 text-xs text-slate-500"
                >
                    <span class="h-px flex-1 bg-slate-800"></span>or continue
                    with email<span class="h-px flex-1 bg-slate-800"></span>
                </div>
                {#if form.error}<p
                        class="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                        role="alert"
                    >
                        {form.error}
                    </p>{/if}
                <form class="space-y-4" onsubmit={submitRegister}>
                    <label class="block text-sm font-medium"
                        >Name<input
                            class="auth-input mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                            placeholder="Your name"
                            bind:value={form.name}
                            autocomplete="name"
                            required
                        /></label
                    >
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
                                placeholder="Create a password"
                                bind:value={form.password}
                                autocomplete="new-password"
                                required
                                minlength="10"
                            /><button
                                type="button"
                                class="absolute inset-y-0 right-3 text-xs text-slate-400 hover:text-indigo-300"
                                onclick={toggleRegisterPassword}
                                aria-label={form.showPassword
                                    ? "Hide password"
                                    : "Show password"}
                                >{form.showPassword ? "Hide" : "Show"}</button
                            ></span
                        ><span class="mt-1 block text-xs text-slate-500"
                            >Use at least 10 characters, with uppercase, lowercase, and a number.</span
                        ></label
                    >
                    <label class="block text-sm font-medium">
                        Confirm password
                        <input
                            class="auth-input mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                            type="password"
                            placeholder="Re-enter your password"
                            bind:value={form.confirm}
                            autocomplete="new-password"
                            required
                            minlength="10"
                        />
                    </label>
                    <button
                        class="w-full rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:-translate-y-0.5 hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
                        disabled={form.busy}
                        >{form.busy
                            ? "Creating account…"
                            : "Create account"}</button
                    >
                </form>
                <p class="mt-4 text-center text-xs leading-5 text-slate-500">
                    By creating an account, you agree to our Terms of Service
                    and Privacy Policy.
                </p>
                <p class="mt-6 text-center text-sm text-slate-400">
                    Already have an account? <a
                        use:inertia
                        class="font-semibold text-white underline decoration-indigo-400 underline-offset-4 hover:text-indigo-300"
                        href="/login">Log in</a
                    >
                </p>
            </section>
            <div class="mt-6 text-center">
                <a
                    use:inertia
                    class="text-sm text-slate-400 underline underline-offset-4 transition hover:text-indigo-300"
                    href="/detect">Continue without an account</a
                >
                <p class="mt-2 text-xs text-slate-500">
                    An account is only needed to save your history.
                </p>
            </div>
        </div>
    </main>
</Layout>

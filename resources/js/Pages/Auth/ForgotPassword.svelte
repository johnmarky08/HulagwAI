<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "../Components/Layout.svelte";
    import {
        forgotForm as form,
        submitForgot,
    } from "../../official/authPages.svelte.js";

    // The form state lives in a shared module: drop the result of an earlier visit.
    onMount(() => {
        form.error = "";
        form.message = "";
    });
</script>

<svelte:head><title>HulagwAI · Forgot Password</title></svelte:head>
<Layout active="">
    <main class="grid min-h-[calc(100vh-80px)] place-items-center px-5 py-12">
        <div class="w-full max-w-[480px]">
            <section
                class="rounded-2xl border border-slate-800 bg-slate-900/70 p-7 shadow-2xl shadow-black/20 sm:p-8"
            >
                <h1 class="text-3xl font-extrabold tracking-tight">
                    Forgot Your Password?
                </h1>
                <p class="mt-2 text-sm text-slate-400">
                    Enter your account email and we'll send you a link to
                    choose a new password.
                </p>
                {#if form.error}<p
                        class="mt-6 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                        role="alert"
                    >
                        {form.error}
                    </p>{/if}
                {#if form.message}
                    <p
                        class="mt-6 rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-300"
                        role="status"
                    >
                        {form.message}
                    </p>
                {/if}
                <form class="mt-6 space-y-4" onsubmit={submitForgot}>
                    <label class="block text-sm font-medium"
                        >Email<input
                            class="auth-input mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                            type="email"
                            placeholder="you@example.com"
                            bind:value={form.email}
                            autocomplete="email"
                            maxlength="190"
                            required
                        /></label
                    >
                    <button
                        class="w-full rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:-translate-y-0.5 hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
                        disabled={form.busy}
                        >{form.busy ? "Sending…" : "Send Reset Link"}</button
                    >
                </form>
                <p class="mt-6 text-center text-sm text-slate-400">
                    Remembered it? <a
                        use:inertia
                        class="font-semibold text-white underline decoration-indigo-400 underline-offset-4 hover:text-indigo-300 py-2.5 -my-2.5 sm:py-0 sm:my-0"
                        href="/login">Back to log in</a
                    >
                </p>
            </section>
        </div>
    </main>
</Layout>

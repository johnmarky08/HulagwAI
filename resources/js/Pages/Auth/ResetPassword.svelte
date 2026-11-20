<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "../Components/Layout.svelte";
    import {
        resetForm as form,
        submitReset,
    } from "../../official/authPages.svelte.js";

    // Props come from PasswordResetController@showReset (token in the path, email in the query string).
    let { token = "", email = "" } = $props();

    // The form state lives in a shared module: a new reset link must show the form, not the last result.
    onMount(() => {
        form.error = "";
        form.message = "";
        form.password = "";
        form.confirm = "";
    });
</script>

<svelte:head><title>HulagwAI · Reset Password</title></svelte:head>
<Layout active="">
    <main class="grid min-h-[calc(100vh-80px)] place-items-center px-5 py-12">
        <div class="w-full max-w-[480px]">
            <section
                class="rounded-2xl border border-slate-800 bg-slate-900/70 p-7 shadow-2xl shadow-black/20 sm:p-8"
            >
                <h1 class="text-3xl font-extrabold tracking-tight">
                    Choose a New Password
                </h1>
                <p class="mt-2 text-sm text-slate-400">
                    {#if email}For <span class="text-slate-200">{email}</span
                        >.{/if} Use at least 10 characters with upper- and
                    lower-case letters and a number.
                </p>
                {#if form.error}<p
                        class="mt-6 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                        role="alert"
                    >
                        {form.error}
                        <a
                            use:inertia
                            class="underline underline-offset-2"
                            href="/forgot-password">Request a new link</a
                        >
                    </p>{/if}
                {#if form.message}
                    <p
                        class="mt-6 rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-300"
                        role="status"
                    >
                        {form.message}
                        <a
                            use:inertia
                            class="font-semibold underline underline-offset-2"
                            href="/login">Log in</a
                        >
                    </p>
                {:else}
                    <form
                        class="mt-6 space-y-4"
                        onsubmit={(event) => submitReset(event, token, email)}
                    >
                        <label class="block text-sm font-medium"
                            >New password<span class="relative mt-2 block"
                                ><input
                                    class="auth-input w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 pr-14 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                                    type={form.showPassword ? "text" : "password"}
                                    bind:value={form.password}
                                    autocomplete="new-password"
                                    maxlength="128"
                                    required
                                /><button
                                    type="button"
                                    class="absolute inset-y-0 right-3 text-xs text-slate-400 hover:text-indigo-300"
                                    onclick={() =>
                                        (form.showPassword = !form.showPassword)}
                                    aria-label={form.showPassword
                                        ? "Hide password"
                                        : "Show password"}
                                    >{form.showPassword ? "Hide" : "Show"}</button
                                ></span
                            ></label
                        >
                        <label class="block text-sm font-medium"
                            >Confirm new password<input
                                class="auth-input mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                                type={form.showPassword ? "text" : "password"}
                                bind:value={form.confirm}
                                autocomplete="new-password"
                                maxlength="128"
                                required
                            /></label
                        >
                        <button
                            class="w-full rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:-translate-y-0.5 hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
                            disabled={form.busy || !token}
                            >{form.busy ? "Saving…" : "Reset Password"}</button
                        >
                    </form>
                {/if}
            </section>
        </div>
    </main>
</Layout>

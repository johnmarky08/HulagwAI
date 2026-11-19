<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import {
        profile,
        loadProfile,
        logoutProfile,
        deleteProfile,
    } from "../official/profilePage.svelte.js";

    onMount(() => {
        void loadProfile();
    });
</script>

<svelte:head><title>HulagwAI · Your profile</title></svelte:head>
<Layout active="">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-800px px-5 py-10">
        <header class="mb-6">
            <h1 class="text-3xl font-extrabold">Your profile</h1>
            <p class="mt-2 text-sm text-slate-400">
                Manage your account and saved history.
            </p>
            <div class="mt-3 flex gap-5 text-xs">
                <a
                    use:inertia
                    class="text-slate-400 hover:text-indigo-300"
                    href="/history">← Back to history</a
                ><button
                    class="text-slate-300 hover:text-indigo-300"
                    onclick={logoutProfile}>Log out</button
                >
            </div>
        </header>
        {#if profile.error}<p
                class="mb-4 rounded-xl border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                role="alert"
            >
                {profile.error}
            </p>{/if}

        {#if profile.loading}<p
                class="py-16 text-center text-sm text-slate-400"
            >
                Loading account…
            </p>{:else if profile.me?.user}
            <section
                class="mb-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-7"
            >
                <h2 class="font-bold">Account details</h2>
                <p class="mt-1 text-xs text-slate-500">
                    Profile editing and password changes are in development.
                </p>
                <div class="mt-5 grid gap-4 sm:grid-cols-2">
                    <label class="text-sm"
                        >Name<input
                            class="mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200"
                            value={profile.me.user.name}
                            readonly
                        /></label
                    ><label class="text-sm"
                        >Email<input
                            class="mt-2 block w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200"
                            value={profile.me.user.email}
                            readonly
                        /></label
                    >
                </div>
                <div
                    class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4"
                >
                    <span class="text-sm"
                        >Password <span
                            class="mt-1 block text-xs text-slate-500"
                            >•••••••••••</span
                        ></span
                    ><button
                        class="rounded-xl border border-slate-700 bg-slate-800/70 px-4 py-3 text-sm text-slate-400"
                        disabled
                        title="Password management is in development"
                        >Change password · In Development</button
                    >
                </div>
            </section>
            <section
                class="mb-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-7"
            >
                <h2 class="font-bold">Connected accounts</h2>
                <p class="mt-1 text-xs text-slate-400">
                    A quicker way to log in to your history.
                </p>
                <div class="mt-5 space-y-4">
                    {#each ["Google", "Microsoft"] as provider}<div
                            class="flex items-center justify-between"
                        >
                            <span class="flex items-center gap-3"
                                ><span
                                    class="grid size-9 place-items-center rounded-lg bg-slate-800 text-lg"
                                    >{provider === "Google" ? "🌐" : "▦"}</span
                                ><span class="text-sm"
                                    >{provider}<small
                                        class="mt-1 block text-xs text-slate-500"
                                        >Not connected · OAuth in development</small
                                    ></span
                                ></span
                            ><button
                                class="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-500"
                                disabled>Connect</button
                            >
                        </div>{/each}
                </div>
            </section>
            <section
                class="rounded-2xl border border-rose-900/70 bg-rose-950/25 p-6 sm:p-7"
            >
                <h2 class="font-bold text-rose-300">Delete account</h2>
                <p class="mt-2 text-sm leading-6 text-slate-400">
                    Permanently delete your account and all saved analysis
                    history. This cannot be undone.
                </p>
                <form
                    class="mt-5 flex flex-col gap-3 sm:flex-row"
                    onsubmit={deleteProfile}
                >
                    <input
                        class="min-w-0 flex-1 rounded-xl border border-rose-900/70 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none focus:border-rose-500"
                        type="password"
                        bind:value={profile.password}
                        autocomplete="current-password"
                        placeholder="Confirm with your password"
                        required
                    /><button
                        class="rounded-xl border border-rose-800 bg-rose-950/50 px-5 py-3 text-sm font-semibold text-rose-300 transition hover:bg-rose-900/70 disabled:opacity-50"
                        disabled={profile.deleting}
                        >{profile.deleting
                            ? "Deleting…"
                            : "Delete account"}</button
                    >
                </form>
            </section>
        {:else}<p class="py-16 text-center text-sm text-slate-400">
                Sign in to view your account.
            </p>{/if}
    </main>
</Layout>

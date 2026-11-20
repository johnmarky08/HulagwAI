<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import {
        profile,
        loadProfile,
        saveProfile,
        changeProfilePassword,
        logoutProfile,
        deleteProfile,
    } from "../official/profilePage.svelte.js";
    import {
        ui,
        exportHistory,
        clearAllHistory,
    } from "../official/controller.svelte.js";
    import { auth } from "../api/auth";
    import { errorMessage } from "../api/client";
    import {
        session,
        refreshSession,
    } from "../api/session.svelte.js";
    import { googleErrorFromUrl } from "../official/authPages.svelte.js";

    let cleared = $state(false);
    let unlinking = $state(false);
    const linkedNow =
        typeof location !== "undefined" &&
        new URLSearchParams(location.search).get("google") === "linked";
    const googleError = googleErrorFromUrl();
    const hasPassword = $derived(profile.me?.user?.has_password !== false);
    const googleConnected = $derived(profile.me?.user?.google_connected === true);
    const googleAvailable = $derived(
        (profile.me?.auth ?? session.value?.auth)?.google === true,
    );

    async function unlinkGoogle() {
        if (!window.confirm("Disconnect Google from your HulagwAI account?")) return;
        unlinking = true;
        profile.error = "";
        try {
            await auth.unlinkGoogle();
            if (profile.me?.user) profile.me.user.google_connected = false;
            void refreshSession();
        } catch (error) {
            profile.error = errorMessage(error);
        } finally {
            unlinking = false;
        }
    }
    const mb = (bytes) => (bytes / 1048576).toFixed(1);
    const quota = $derived(profile.me?.quota ?? null);
    const quotaShare = $derived(
        quota?.limit_bytes
            ? Math.min(
                  100,
                  Math.round((quota.used_bytes / quota.limit_bytes) * 100),
              )
            : 0,
    );

    async function clearHistory() {
        cleared = false;
        if (await clearAllHistory()) {
            cleared = true;
            // Refresh the storage figure after the images are gone.
            try {
                const fresh = await auth.me();
                if (profile.me) profile.me.quota = fresh.quota;
            } catch {
                /* the next page load refreshes it */
            }
        }
    }

    onMount(() => {
        ui.historyError = "";
        void loadProfile();
    });
</script>

<svelte:head>
    <title>HulagwAI · Your profile</title>
    <meta
        name="description"
        content="Manage your HulagwAI account and saved history."
    />
</svelte:head>

<Layout active="">
    <main
        class="mx-auto min-h-[calc(100vh-80px)] max-w-848px px-5 py-10 sm:px-8"
    >
        <header class="mb-6">
            <h1 class="text-3xl font-extrabold tracking-tight text-white">
                Your profile
            </h1>
            <p class="mt-2 text-sm text-slate-400">
                Manage your account and saved history.
            </p>
            <div class="mt-5 flex flex-wrap gap-3">
                <a
                    use:inertia
                    class="inline-flex min-h-10 items-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-950/35 px-4 py-2.5 text-sm font-semibold text-indigo-200 shadow-sm shadow-indigo-950/20 transition hover:border-indigo-400 hover:bg-indigo-900/50 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
                    href="/history"
                >
                    <span aria-hidden="true">←</span> Back to history
                </a>
                <button
                    class="inline-flex min-h-10 items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2.5 text-sm font-semibold text-slate-200 shadow-sm transition hover:border-rose-500/60 hover:bg-rose-950/35 hover:text-rose-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-400"
                    onclick={logoutProfile}
                >
                    <span aria-hidden="true">↪</span> Log out
                </button>
            </div>
        </header>

        {#if profile.error}
            <p
                class="mb-4 rounded-xl border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                role="alert"
            >
                {profile.error}
            </p>
        {/if}
        {#if profile.saved}
            <p
                class="mb-4 rounded-xl border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-300"
                role="status"
            >
                Your account details have been saved.
            </p>
        {/if}
        {#if linkedNow && !profile.error}
            <p
                class="mb-4 rounded-xl border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-300"
                role="status"
            >
                Your Google account is now connected.
            </p>
        {/if}
        {#if googleError && !profile.error}
            <p
                class="mb-4 rounded-xl border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-300"
                role="alert"
            >
                {googleError}
            </p>
        {/if}
        {#if profile.passwordChanged}
            <p
                class="mb-4 rounded-xl border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-300"
                role="status"
            >
                Your password has been updated.
            </p>
        {/if}

        {#if profile.loading}
            <p class="py-16 text-center text-sm text-slate-400">
                Loading account…
            </p>
        {:else if profile.me?.user}
            <section
                class="mb-6 rounded-2xl border border-slate-800 bg-[#111521] p-6 sm:p-7"
            >
                <h2 class="text-base font-bold text-slate-100">
                    Account details
                </h2>
                <form onsubmit={saveProfile}>
                    <div class="mt-5 grid gap-4 sm:grid-cols-2">
                        <label class="text-sm text-slate-200"
                            >Name
                            <input
                                class="mt-2 block w-full rounded-xl border border-slate-800 bg-[#0a0c13] px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                                type="text"
                                minlength="2"
                                maxlength="60"
                                autocomplete="name"
                                bind:value={profile.name}
                                required
                            />
                        </label>
                        <label class="text-sm text-slate-200"
                            >Email
                            <input
                                class="mt-2 block w-full rounded-xl border border-slate-800 bg-[#0a0c13] px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                                type="email"
                                maxlength="190"
                                autocomplete="email"
                                bind:value={profile.email}
                                required
                            />
                        </label>
                    </div>
                    <div
                        class="mt-5 flex flex-wrap items-center justify-between gap-4"
                    >
                        <div class="text-sm text-slate-200">
                            Password{#if hasPassword}<span
                                    class="mt-1 block text-xs tracking-[.2em] text-slate-400"
                                    aria-label="Password is hidden"
                                    >•••••••••••</span
                                >{:else}<span
                                    class="mt-1 block text-xs text-slate-400"
                                    >Not set. You sign in with Google.</span
                                >{/if}
                        </div>
                        <button
                            type="button"
                            class="rounded-xl border border-slate-700 bg-slate-800/70 px-5 py-3 text-sm text-slate-100 transition hover:border-indigo-400"
                            onclick={() => {
                                profile.passwordFormOpen =
                                    !profile.passwordFormOpen;
                                profile.error = "";
                            }}
                        >
                            {profile.passwordFormOpen
                                ? "Cancel"
                                : hasPassword
                                  ? "Change password"
                                  : "Set a password"}
                        </button>
                    </div>
                    <button
                        class="mt-5 rounded-xl border border-indigo-500 bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
                        type="submit"
                        disabled={profile.saving}
                    >
                        {profile.saving ? "Saving…" : "Save changes"}
                    </button>
                </form>
                {#if profile.passwordFormOpen}
                    <form
                        class="mt-5 grid gap-4 border-t border-slate-800 pt-5 sm:grid-cols-2"
                        onsubmit={changeProfilePassword}
                    >
                        {#if hasPassword}<label class="text-sm text-slate-200 sm:col-span-2"
                            >Current password
                            <input
                                class="mt-2 block w-full rounded-xl border border-slate-800 bg-[#0a0c13] px-4 py-3 text-sm text-slate-100 outline-none focus:border-indigo-500"
                                type="password"
                                autocomplete="current-password"
                                bind:value={profile.currentPassword}
                                required
                            />
                        </label>{/if}
                        <label class="text-sm text-slate-200"
                            >New password
                            <input
                                class="mt-2 block w-full rounded-xl border border-slate-800 bg-[#0a0c13] px-4 py-3 text-sm text-slate-100 outline-none focus:border-indigo-500"
                                type="password"
                                autocomplete="new-password"
                                bind:value={profile.newPassword}
                                required
                            />
                        </label>
                        <label class="text-sm text-slate-200"
                            >Confirm new password
                            <input
                                class="mt-2 block w-full rounded-xl border border-slate-800 bg-[#0a0c13] px-4 py-3 text-sm text-slate-100 outline-none focus:border-indigo-500"
                                type="password"
                                autocomplete="new-password"
                                bind:value={profile.newPasswordConfirmation}
                                required
                            />
                        </label>
                        <div class="sm:col-span-2">
                            <button
                                class="rounded-xl border border-indigo-500 bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
                                type="submit"
                                disabled={profile.changingPassword}
                            >
                                {profile.changingPassword
                                    ? "Saving…"
                                    : hasPassword
                                      ? "Update password"
                                      : "Set password"}
                            </button>
                        </div>
                    </form>
                {/if}
            </section>

            <section
                class="mb-6 rounded-2xl border border-slate-800 bg-[#111521] p-6 sm:p-7"
                aria-labelledby="connected-heading"
            >
                <h2
                    id="connected-heading"
                    class="text-base font-bold text-slate-100"
                >
                    Connected accounts
                </h2>
                <p class="mt-1 text-xs text-slate-400">
                    A quicker way to log in to your history.
                </p>
                <div class="mt-5 flex items-center justify-between gap-4">
                    <span class="flex items-center gap-3">
                        <span
                            class="grid size-8 place-items-center text-xl font-bold text-emerald-400"
                            aria-hidden="true">G</span
                        >
                        <span class="text-sm text-slate-100"
                            >Google<small
                                class="mt-1 block text-xs text-slate-400"
                                >{googleConnected
                                    ? `Connected as ${profile.me.user.email}`
                                    : "Not connected"}</small
                            ></span
                        >
                    </span>
                    {#if googleConnected}
                        <button
                            type="button"
                            class="rounded-lg border border-slate-700 bg-slate-800/70 px-4 py-2 text-xs text-slate-100 transition hover:border-rose-500/60 disabled:opacity-50"
                            disabled={unlinking || !hasPassword}
                            title={hasPassword
                                ? "Disconnect Google"
                                : "Set a password first so you can still log in"}
                            onclick={unlinkGoogle}
                            >{unlinking ? "Disconnecting…" : "Disconnect"}</button
                        >
                    {:else if googleAvailable}
                        <a
                            class="rounded-lg border border-indigo-500 bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500"
                            href={auth.googleUrl}>Connect</a
                        >
                    {:else}
                        <button
                            type="button"
                            class="rounded-lg border border-slate-800 bg-slate-800/50 px-4 py-2 text-xs text-slate-500"
                            disabled
                            title="Google sign-in is not configured on this server"
                            >Connect</button
                        >
                    {/if}
                </div>
                {#if googleConnected && !hasPassword}
                    <p class="mt-3 text-xs text-slate-400">
                        Set a password above before disconnecting Google, so you
                        can still log in.
                    </p>
                {/if}
            </section>

            <section
                class="mb-6 rounded-2xl border border-slate-800 bg-[#111521] p-6 sm:p-7"
                aria-labelledby="storage-heading"
            >
                <h2
                    id="storage-heading"
                    class="text-base font-bold text-slate-100"
                >
                    Storage & data
                </h2>
                <p class="mt-1 text-xs text-slate-400">
                    Uploaded images are stored encrypted until you delete them.
                </p>
                {#if quota}
                    <div class="mt-5">
                        <div
                            class="flex items-baseline justify-between gap-3 text-sm text-slate-200"
                        >
                            <span>Storage used</span>
                            <span class="tabular-nums text-slate-400"
                                >{mb(quota.used_bytes)} / {mb(
                                    quota.limit_bytes,
                                )} MB</span
                            >
                        </div>
                        <div
                            class="mt-2 h-2 overflow-hidden rounded-full bg-slate-800"
                        >
                            <span
                                class="block h-full rounded-full"
                                class:bg-indigo-500={quotaShare < 90}
                                class:bg-rose-500={quotaShare >= 90}
                                style={`width:${Math.max(2, quotaShare)}%`}
                            ></span>
                        </div>
                    </div>
                {/if}
                <div class="mt-5 flex flex-wrap gap-3">
                    <button
                        type="button"
                        class="rounded-xl border border-slate-700 bg-slate-800/70 px-5 py-3 text-sm text-slate-100 transition hover:border-indigo-400"
                        onclick={() => exportHistory("csv")}
                        >↓ &nbsp;Export history (CSV)</button
                    >
                    <button
                        type="button"
                        class="rounded-xl border border-slate-700 bg-slate-800/70 px-5 py-3 text-sm text-slate-100 transition hover:border-indigo-400"
                        onclick={() => exportHistory("json")}
                        >↓ &nbsp;Export history (JSON)</button
                    >
                    <button
                        type="button"
                        class="rounded-xl border border-rose-800 bg-rose-950/50 px-5 py-3 text-sm font-semibold text-rose-300 transition hover:bg-rose-900/70 disabled:opacity-50"
                        disabled={ui.clearingHistory}
                        onclick={clearHistory}
                        >{ui.clearingHistory
                            ? "Clearing…"
                            : "Clear analysis history"}</button
                    >
                </div>
                {#if ui.historyError}
                    <p class="mt-3 text-sm text-rose-300" role="alert">
                        {ui.historyError}
                    </p>
                {/if}
                {#if cleared}
                    <p class="mt-3 text-sm text-emerald-300" role="status">
                        Your analysis history has been cleared.
                    </p>
                {/if}
            </section>

            <section
                class="rounded-2xl border border-rose-900/70 bg-rose-950/25 p-6 sm:p-7"
            >
                <h2
                    class="flex items-center gap-2 text-base font-bold text-slate-100"
                >
                    <span class="text-lg text-rose-500" aria-hidden="true"
                        >▤</span
                    > Delete account
                </h2>
                <p class="mt-4 text-sm leading-6 text-slate-400">
                    Permanently delete your account and all saved analysis
                    history. This cannot be undone.
                </p>
                {#if !profile.confirmDeleteOpen}
                    <button
                        type="button"
                        class="mt-5 rounded-xl border border-rose-800 bg-rose-950/50 px-5 py-3 text-sm font-semibold text-rose-300 transition hover:bg-rose-900/70"
                        onclick={() => {
                            profile.confirmDeleteOpen = true;
                        }}
                    >
                        Delete account…
                    </button>
                {:else}
                    <form
                        class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end"
                        onsubmit={deleteProfile}
                    >
                        <label class="min-w-0 flex-1 text-xs text-slate-400"
                            >{hasPassword
                                ? "Confirm with your password"
                                : "Type your account email to confirm"}
                            <input
                                class="mt-2 block w-full rounded-xl border border-rose-900/70 bg-[#0a0c13] px-4 py-3 text-sm text-slate-100 outline-none focus:border-rose-500"
                                type={hasPassword ? "password" : "email"}
                                bind:value={profile.password}
                                autocomplete={hasPassword
                                    ? "current-password"
                                    : "off"}
                                required
                            />
                        </label>
                        <button
                            class="rounded-xl border border-rose-800 bg-rose-950/50 px-5 py-3 text-sm font-semibold text-rose-300 transition hover:bg-rose-900/70 disabled:opacity-50"
                            disabled={profile.deleting}
                            >{profile.deleting
                                ? "Deleting…"
                                : "Permanently delete"}</button
                        >
                        <button
                            type="button"
                            class="rounded-xl border border-slate-700 px-5 py-3 text-sm text-slate-300"
                            onclick={() => {
                                profile.confirmDeleteOpen = false;
                                profile.password = "";
                            }}>Cancel</button
                        >
                    </form>
                {/if}
            </section>
        {:else}
            <p class="py-16 text-center text-sm text-slate-400">
                Sign in to view your account.
            </p>
        {/if}
    </main>
</Layout>

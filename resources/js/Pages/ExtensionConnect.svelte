<script>
    import { onDestroy, onMount } from "svelte";
    import Layout from "./Components/Layout.svelte";
    import { errorMessage, http } from "../api/client";

    let code = $state("");
    let loading = $state(false);
    let copied = $state(false);
    let error = $state("");
    let secondsLeft = $state(0);
    let expiryTimer;

    async function createCode() {
        loading = true;
        error = "";
        code = "";
        try {
            const { data } = await http.post("/extension/pair", {});
            code = data.code;
            secondsLeft = data.expires_in || 180;
            clearInterval(expiryTimer);
            expiryTimer = setInterval(() => {
                secondsLeft = Math.max(0, secondsLeft - 1);
                if (!secondsLeft) code = "";
            }, 1000);
        } catch (exception) {
            error = errorMessage(exception);
        } finally {
            loading = false;
        }
    }

    async function copyCode() {
        if (!code) return;
        try {
            await navigator.clipboard.writeText(code);
            copied = true;
            setTimeout(() => (copied = false), 1600);
        } catch {
            error =
                "Clipboard access was blocked. Select and copy the code manually.";
        }
    }

    onMount(() => void createCode());
    onDestroy(() => clearInterval(expiryTimer));
</script>

<svelte:head>
    <title>HulagwAI · Pair browser extension</title>
</svelte:head>

<Layout active="profile">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-3xl px-5 py-10 sm:px-8">
        <section
            class="rounded-2xl border border-indigo-500/40 bg-slate-900/70 p-5 sm:p-8"
        >
            <p
                class="text-xs font-bold uppercase tracking-[.16em] text-indigo-400"
            >
                One-time browser pairing
            </p>
            <h1 class="mt-3 text-2xl font-extrabold text-white sm:text-3xl">
                Connect the Facebook scanner
            </h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
                This short-lived code lets the unpacked browser extension
                request a revocable HulagwAI token. Scanning and confirmation
                happen on Facebook; this page is only for secure account
                pairing.
            </p>

            <div
                class="mt-7 rounded-xl border border-slate-700 bg-slate-950 p-5 text-center"
            >
                {#if code}
                    <code
                        class="block break-all text-lg font-bold tracking-[.12em] text-indigo-200 sm:text-2xl"
                        >{code}</code
                    >
                    <p class="mt-3 text-xs text-slate-400">
                        Expires in {Math.floor(secondsLeft / 60)}:{String(
                            secondsLeft % 60,
                        ).padStart(2, "0")}. It can only be used once.
                    </p>
                    <button
                        class="mt-4 rounded-lg border border-indigo-400/50 bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500"
                        type="button"
                        onclick={copyCode}
                        >{copied ? "Copied" : "Copy pairing code"}</button
                    >
                {:else if loading}
                    <p class="text-sm text-slate-300">
                        Generating a one-time code…
                    </p>
                {:else}
                    <p class="text-sm text-slate-400">
                        This code expired or could not be created.
                    </p>
                    <button
                        class="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
                        type="button"
                        onclick={createCode}>Generate a new code</button
                    >
                {/if}
                {#if error}<p class="mt-4 text-sm text-rose-300" role="alert">
                        {error}
                    </p>{/if}
            </div>

            <ol class="mt-6 grid gap-3 text-sm text-slate-300 sm:grid-cols-3">
                <li
                    class="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                >
                    <b class="text-indigo-300">1.</b> Copy this code.
                </li>
                <li
                    class="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                >
                    <b class="text-indigo-300">2.</b> Open the extension popup on
                    Facebook and paste it.
                </li>
                <li
                    class="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                >
                    <b class="text-indigo-300">3.</b> The extension stores a revocable
                    token, not this code.
                </li>
            </ol>
            <p class="mt-5 text-xs leading-5 text-slate-500">
                Never share the code or extension token. You can disconnect the
                browser from the extension popup; tokens expire automatically
                after 30 days.
            </p>
        </section>
    </main>
</Layout>

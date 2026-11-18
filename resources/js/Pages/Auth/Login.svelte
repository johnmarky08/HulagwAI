<script>
    import Layout from "../../Layouts/TestLayout.svelte";
    import { auth } from "../../api/auth";
    import { errorMessage } from "../../api/client";

    let name = $state(""), email = $state(""), password = $state(""), confirm = $state(""), error = $state(""), busy = $state(false);
    async function submit(e) {
        e.preventDefault(); busy = true; error = "";
        try {
            await auth.login(email, password);
            location.href = "/";
        } catch (err) { error = errorMessage(err); } finally { busy = false; }
    }
</script>

<Layout>
    <h1 class="mb-4 text-3xl font-bold">Log in</h1>
    <p class="mb-4 text-sm text-slate-400">Accounts are optional. Without one, your results live in this browser session only.</p>
    {#if error}<div class="mb-3 rounded border border-red-500 bg-red-950 p-2 text-red-200">{error}</div>{/if}
    <form class="flex max-w-sm flex-col gap-3" onsubmit={submit}>

        <input class="rounded border border-slate-700 bg-slate-900 px-3 py-2" type="email" placeholder="Email" bind:value={email} autocomplete="email" required />
        <input class="rounded border border-slate-700 bg-slate-900 px-3 py-2" type="password" placeholder="Password" bind:value={password} autocomplete="current-password" required />

        <button class="rounded bg-indigo-600 px-4 py-2 font-semibold disabled:opacity-50" disabled={busy}>Log in</button>
    </form>
</Layout>

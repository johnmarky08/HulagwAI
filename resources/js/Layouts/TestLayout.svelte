<!-- TEST-ONLY layout. The product frontend replaces this. -->
<script>
    import { onMount } from "svelte";
    import { auth } from "../api/auth";

    let { children, active = "" } = $props();
    let me = $state(null);

    onMount(async () => {
        try { me = await auth.me(); } catch { me = null; }
    });

    async function logout() {
        await auth.logout();
        location.href = "/";
    }

    const links = [["/", "Home"], ["/detect", "Image Detection"], ["/history", "History"], ["/about", "About"]];
</script>

<div class="min-h-screen bg-slate-950 text-slate-100">
    <nav class="flex flex-wrap items-center gap-4 border-b border-indigo-500/40 px-6 py-4">
        <a href="/" class="mr-6 text-xl font-bold">Hulagw<span class="text-indigo-400">AI</span></a>
        {#each links as [href, label]}
            <a {href} class="rounded px-3 py-1 {active === href ? 'bg-indigo-900' : 'hover:bg-slate-800'}">{label}</a>
        {/each}
        <span class="ml-auto text-sm text-slate-400">
            {#if me?.authenticated}
                {me.user.name} ·
                {(me.quota.used_bytes / 1048576).toFixed(1)}/{(me.quota.limit_bytes / 1048576).toFixed(0)} MB ·
                <button class="underline" onclick={logout}>Log out</button>
            {:else if me}
                Guest (history kept for this session only) · <a class="underline" href="/login">Log in</a> · <a class="underline" href="/register">Sign up</a>
            {/if}
        </span>
    </nav>
    <main class="mx-auto max-w-4xl p-6">{@render children()}</main>
</div>

<script>
    import { inertia } from "@inertiajs/svelte";
    import { navigation } from "../../official/navigation.js";
    import { ui, toggleTheme } from "../../official/controller.svelte.js";

    let { active = "home" } = $props();
</script>

<header
    class="sticky top-0 theme-header border-b border-indigo-500/70 z-50 bg-[#111521] px-5 md:px-10"
>
    <div class="mx-auto flex min-h-20 max-w-1440px items-center gap-5">
        <a
            use:inertia
            class="flex shrink-0 items-center gap-3 font-sans text-2xl font-extrabold tracking-tight"
            href="/"
            aria-label="HulagwAI home"
        >
            <span
                class="grid size-8 place-items-center rounded-full border border-cyan-400 text-cyan-300"
                >◉</span
            >
            <span>Hulagw<span class="text-indigo-400">AI</span></span>
        </a>
        <nav
            class="nav-links mx-auto flex min-w-0 flex-1 items-center justify-start gap-1 overflow-x-auto overflow-y-hidden md:justify-center"
            aria-label="Main navigation"
        >
            {#each navigation as item}
                <a
                    use:inertia
                    href={item.href}
                    aria-current={active === item.id ? "page" : undefined}
                    class="nav-link inline-flex items-center justify-center whitespace-nowrap rounded-xl border border-transparent px-3 py-3 text-sm text-slate-400 md:min-w-28 md:px-5"
                    >{item.label}</a
                >
            {/each}
        </nav>
        <button
            class="flex shrink-0 items-center gap-3 rounded-full px-1 py-2 text-2xl"
            onclick={toggleTheme}
            aria-label="Toggle color theme"
            aria-pressed={ui.light}
        >
            <span>☼</span><span
                class="relative h-6 w-11 rounded-full bg-indigo-600"
                ><span
                    class="absolute top-1 size-4 rounded-full bg-slate-950 transition-all"
                    class:left-1={ui.light}
                    class:right-1={!ui.light}
                ></span></span
            >
        </button>
    </div>
</header>

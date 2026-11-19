<script>
    import { inertia } from "@inertiajs/svelte";
    import { navigation } from "../../official/navigation.js";
    import { onMount } from "svelte";
    import { auth } from "../../api/auth";
    import moonIcon from "../../../images/moon.svg";
    import sunIcon from "../../../images/sun.svg";
    import { ui, toggleTheme } from "../../official/controller.svelte.js";

    let { active = "home" } = $props();
    let me = $state(null);
    onMount(async () => {
        try {
            me = await auth.me();
        } catch {
            me = null;
        }
    });
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
                    class="hover:text-white nav-link inline-flex items-center justify-center whitespace-nowrap rounded-xl border border-transparent px-3 py-3 text-sm font-bold text-slate-400 md:min-w-28 md:px-5 transition-all duration-300 ease-in-out"
                    >{item.label}</a
                >
            {/each}
        </nav>
        <a
            use:inertia
            href={me?.authenticated ? "/profile" : "/login"}
            class="hidden shrink-0 rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2 text-sm font-medium transition hover:border-indigo-400 hover:bg-indigo-950/70 sm:inline-flex"
            >♙ &nbsp;{me?.authenticated ? "Profile" : "Log in"}</a
        >
        <button
            class="theme-toggle flex size-11 shrink-0 items-center justify-center rounded-full"
            onclick={toggleTheme}
            aria-label={ui.light
                ? "Switch to dark mode"
                : "Switch to light mode"}
            aria-pressed={ui.light}
        >
            <span
                class="grid size-9 cursor-pointer place-items-center rounded-full border border-indigo-400/30 bg-indigo-500/10"
            >
                <img
                    src={ui.light ? sunIcon : moonIcon}
                    alt=""
                    class="theme-icon size-6 transition-transform duration-300 ease-in-out"
                    class:rotate-180={ui.light}
                />
            </span>
        </button>
    </div>
</header>

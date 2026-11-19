<script>
    import { inertia } from "@inertiajs/svelte";
    import { onMount } from "svelte";
    import { fly } from "svelte/transition";
    import { navigation } from "../../official/navigation.js";
    import { auth } from "../../api/auth";
    import moonIcon from "../../../images/moon.svg";
    import sunIcon from "../../../images/sun.svg";
    import { ui, toggleTheme } from "../../official/controller.svelte.js";

    let { active = "home" } = $props();
    let me = $state(null);
    let menuOpen = $state(false);

    onMount(async () => {
        try {
            me = await auth.me();
        } catch {
            me = null;
        }
    });

    function closeMenu() {
        menuOpen = false;
    }

    function flyTransition(y, duration, delay = 0) {
        const reducedMotion =
            typeof window !== "undefined" &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        return {
            y: reducedMotion ? 0 : y,
            duration: reducedMotion ? 0 : duration,
            delay: reducedMotion ? 0 : delay,
        };
    }
</script>

<header
    class="theme-header sticky top-0 z-50 border-b border-indigo-500/70 bg-[#111521] px-5 md:px-10"
>
    <div
        class="font-bold mx-auto flex min-h-76px max-w-1440px items-center gap-5 md:min-h-20"
    >
        <a
            use:inertia
            onclick={closeMenu}
            class="flex shrink-0 items-center gap-3 font-sans text-xl font-extrabold tracking-tight md:text-2xl"
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
            class="nav-links font-bold mx-auto hidden min-w-0 flex-1 items-center justify-center gap-1 overflow-x-auto overflow-y-hidden md:flex"
            aria-label="Main navigation"
        >
            {#each navigation as item}
                <a
                    use:inertia
                    href={item.href}
                    aria-current={active === item.id ? "page" : undefined}
                    class="nav-link inline-flex min-w-28 items-center justify-center whitespace-nowrap rounded-xl border border-transparent px-3 py-3 text-sm text-slate-400 transition-all duration-300 ease-in-out hover:text-white md:px-5"
                    >{item.label}</a
                >
            {/each}
        </nav>

        <a
            use:inertia
            href={me?.authenticated ? "/profile" : "/login"}
            class="hidden shrink-0 rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2 text-sm font-medium transition hover:border-indigo-400 hover:bg-indigo-950/70 md:inline-flex"
            >♙ &nbsp;{me?.authenticated ? "Profile" : "Log in"}</a
        >

        <button
            class="theme-toggle hidden size-11 shrink-0 items-center justify-center rounded-full md:flex"
            onclick={toggleTheme}
            aria-label={ui.light
                ? "Switch to dark mode"
                : "Switch to light mode"}
            aria-pressed={ui.light}
        >
            <span
                class="grid size-9 place-items-center rounded-full border border-indigo-400/30 bg-indigo-500/10"
            >
                <img
                    src={ui.light ? sunIcon : moonIcon}
                    alt=""
                    class="theme-icon size-6 transition-transform duration-300 ease-in-out"
                    class:rotate-180={ui.light}
                />
            </span>
        </button>

        <button
            class="menu-toggle ml-auto grid size-11 shrink-0 place-items-center rounded-lg text-2xl text-slate-100 md:hidden"
            type="button"
            aria-label={menuOpen
                ? "Close navigation menu"
                : "Open navigation menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-main-menu"
            onclick={() => (menuOpen = !menuOpen)}
        >
            <span
                class="hamburger-icon"
                class:open={menuOpen}
                aria-hidden="true"><i></i><i></i><i></i></span
            >
        </button>
    </div>

    {#if menuOpen}
        <div
            id="mobile-main-menu"
            transition:fly={flyTransition(-14, 220)}
            class="font-bold mobile-menu absolute inset-x-0 top-full z-50 border-b border-indigo-500/40 bg-[#111521] px-5 pb-5 pt-3 shadow-2xl md:hidden"
        >
            <nav class="grid gap-1" aria-label="Mobile navigation">
                {#each navigation as item, index}
                    <a
                        use:inertia
                        href={item.href}
                        aria-current={active === item.id ? "page" : undefined}
                        onclick={closeMenu}
                        transition:fly={flyTransition(-7, 190, 25 + index * 32)}
                        class="mobile-nav-link rounded-xl px-4 py-3 text-sm font-medium text-slate-300 transition hover:bg-indigo-500/10 hover:text-white"
                        >{item.label}</a
                    >
                {/each}
            </nav>
            <div
                class="mt-4 flex items-center justify-between border-t border-slate-700 pt-4"
            >
                <a
                    use:inertia
                    href={me?.authenticated ? "/profile" : "/login"}
                    onclick={closeMenu}
                    class="rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-medium text-slate-100"
                    >♙ &nbsp;{me?.authenticated ? "Profile" : "Log in"}</a
                >
                <button
                    class="flex items-center gap-3 rounded-xl px-3 py-2"
                    onclick={toggleTheme}
                    aria-label={ui.light
                        ? "Switch to dark mode"
                        : "Switch to light mode"}
                    aria-pressed={ui.light}
                >
                    <span class="text-xs text-slate-400"
                        >{ui.light ? "Light mode" : "Dark mode"}</span
                    >
                    <span
                        class="grid size-9 place-items-center rounded-full border border-indigo-400/30 bg-indigo-500/10"
                        ><img
                            src={ui.light ? sunIcon : moonIcon}
                            alt=""
                            class="theme-icon size-6 transition-transform duration-300 ease-in-out"
                            class:rotate-180={ui.light}
                        /></span
                    >
                </button>
            </div>
        </div>
    {/if}
</header>

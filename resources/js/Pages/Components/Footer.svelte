<script>
    import { inertia } from "@inertiajs/svelte";
    import { navigation, footerLinks } from "../../official/navigation.js";
</script>

<footer class="theme-footer border-t border-indigo-500/50 bg-[#111521]">
    <div
        class="mx-auto grid max-w-1440px gap-8 px-6 py-8 md:grid-cols-2 md:px-12"
    >
        <div>
            <a
                use:inertia
                class="flex items-center gap-3 text-xl font-extrabold"
                href="/"
                ><span class="text-cyan-300">◉</span><span
                    >Hulagw<span class="text-indigo-400">AI</span></span
                ></a
            >
            <p class="mt-4 max-w-md text-sm leading-6 text-slate-400">
                An AI-powered platform that estimates whether an image is
                AI-generated or captured from a real-world source.
            </p>
        </div>
        <nav
            class="grid grid-cols-2 gap-3 text-sm text-slate-300"
            aria-label="Footer navigation"
        >
            {#each [...navigation, ...footerLinks] as item (item.id)}
                <a use:inertia class="hover:text-indigo-300" href={item.href}
                    >{item.label}</a
                >
            {/each}
            <a use:inertia class="hover:text-indigo-300" href="/#how-it-works"
                >How It Works</a
            >
        </nav>
    </div>
    <div
        class="border-t border-indigo-500/40 px-6 py-4 text-xs text-slate-500 md:px-12"
    >
        © 2026 HulagwAI
    </div>
</footer>

<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import {
        ui,
        sampleImage,
        loadHistory,
        formatDate,
    } from "../official/controller.svelte.js";
    import { openQuickDetection } from "../official/dashboard.js";

    onMount(() => {
        void loadHistory();
    });
    const summary = [
        {
            label: "Total images analyzed",
            key: "total",
            icon: "▧",
            color: "indigo",
            caption: "Processed analyses",
        },
        {
            label: "Likely real images",
            key: "likely_real",
            icon: "◉",
            color: "emerald",
            caption: "Likely authentic",
        },
        {
            label: "AI-generated images",
            key: "ai_generated",
            icon: "✳",
            color: "rose",
            caption: "Likely synthetic",
        },
        {
            label: "Inconclusive / mixed",
            key: "inconclusive",
            icon: "⚠",
            color: "amber",
            caption: "Needs human review",
        },
    ];
    $: total = Math.max(1, ui.stats.total);
    $: realShare = Math.round((ui.stats.likely_real / total) * 100);
    $: aiShare = Math.round((ui.stats.ai_generated / total) * 100);
    $: chartGradient = ui.stats.total
        ? `conic-gradient(#10b981 0 ${realShare}%, #ef5b63 ${realShare}% ${realShare + aiShare}%, #f3ae38 ${realShare + aiShare}% 100%)`
        : "conic-gradient(#334155 0 100%)";
</script>

<svelte:head
    ><title>HulagwAI · Dashboard</title><meta
        name="description"
        content="Your image analysis dashboard and recent results."
    /></svelte:head
>
<Layout active="dashboard">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-7xl px-5 py-9 md:px-8">
        <section
            class="dashboard-banner group relative mb-8 overflow-hidden rounded-2xl border border-indigo-500/70 bg-linear-to-r from-indigo-950 to-indigo-800 px-7 py-8 shadow-xl shadow-indigo-950/30 md:px-10"
        >
            <div class="relative z-10 max-w-2xl">
                <span
                    class="rounded-full border border-indigo-400/50 bg-indigo-400/15 px-3 py-1 text-xs text-indigo-200"
                    >Image authenticity workspace</span
                >
                <h1
                    class="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl"
                >
                    Detect AI-generated media with clarity
                </h1>
                <p class="mt-3 max-w-xl text-sm leading-6 text-indigo-100/70">
                    Review your recent image analyses, understand the result
                    mix, or start a new detection.
                </p>
                <div class="mt-6 flex flex-wrap gap-3">
                    <a
                        use:inertia
                        href="/detect"
                        class="rounded-xl bg-white px-5 py-3 text-sm font-bold text-indigo-700 shadow-lg transition hover:-translate-y-0.5 hover:bg-indigo-50"
                        >✦ &nbsp;Start new analysis</a
                    >
                    <a
                        use:inertia
                        href="/history"
                        class="rounded-xl border border-white/20 bg-slate-950/20 px-5 py-3 text-sm font-semibold transition hover:bg-white/10"
                        >View history</a
                    >
                </div>
            </div>
            <div class="banner-mark pointer-events-none absolute -right-3 -top-10 hidden text-[220px] leading-none text-indigo-300/15 md:block" aria-hidden="true">◉</div>
        </section>

        {#if ui.historyError}<p
                class="mb-5 rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300"
            >
                Could not load your analysis summary: {ui.historyError}
            </p>{/if}
        <section
            class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
            aria-label="Analysis summary"
        >
            {#each summary as card}
                <article
                    class="dashboard-card rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition duration-300 hover:-translate-y-1 hover:border-indigo-400/70 hover:shadow-xl hover:shadow-indigo-950/30"
                >
                    <div class="flex items-start justify-between gap-3">
                        <span class="text-xs font-medium text-slate-400"
                            >{card.label}</span
                        ><span
                            class="grid size-10 place-items-center rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-lg text-indigo-300"
                            >{card.icon}</span
                        >
                    </div>
                    <div class="mt-3 flex items-end justify-between">
                        <strong class="text-3xl font-extrabold"
                            >{ui.stats[card.key]}</strong
                        ><span class="text-xs text-slate-500"
                            >{card.caption}</span
                        >
                    </div>
                </article>
            {/each}
        </section>

        <div
            class="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]"
        >
            <section
                class="rounded-2xl border border-indigo-500/50 bg-slate-900/70 p-4 sm:p-6"
            >
                <div class="mb-4 flex items-center justify-between gap-3">
                    <div>
                        <h2 class="text-xl font-bold">
                            Recent analysis history
                        </h2>
                        <p class="mt-1 text-xs text-slate-400">
                            Your latest saved results
                        </p>
                    </div>
                    <a
                        use:inertia
                        href="/history"
                        class="rounded-lg border border-indigo-500/50 px-3 py-2 text-xs font-semibold text-indigo-300 transition hover:bg-indigo-500/15"
                        >View all</a
                    >
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full min-w-560px text-left text-sm">
                        <thead
                            class="border-b border-slate-700 text-xs text-slate-400"
                            ><tr
                                ><th class="p-3 font-medium"
                                    >Image / filename</th
                                ><th class="p-3 font-medium">Result</th><th
                                    class="p-3 font-medium">Confidence</th
                                ><th class="p-3 font-medium">Date</th></tr
                            ></thead
                        >
                        <tbody>
                            {#if ui.loadingHistory && !ui.rows.length}<tr
                                    ><td
                                        colspan="4"
                                        class="p-8 text-center text-slate-400"
                                        >Loading your history…</td
                                    ></tr
                                >
                            {:else if !ui.rows.length}<tr
                                    ><td
                                        colspan="4"
                                        class="p-8 text-center text-slate-400"
                                        >No saved analyses yet. <a
                                            use:inertia
                                            class="text-indigo-300 underline"
                                            href="/detect">Analyze an image</a
                                        > to get started.</td
                                    ></tr
                                >
                            {:else}{#each ui.rows.slice(0, 5) as row (row.id)}<tr
                                        class="border-b border-slate-800/80 transition hover:bg-indigo-950/40"
                                        ><td class="p-3"
                                            ><div
                                                class="flex items-center gap-3"
                                            >
                                                <img
                                                    class="size-10 rounded-lg object-cover"
                                                    src={row.thumb_url ||
                                                        sampleImage}
                                                    alt=""
                                                /><span
                                                    class="max-w-180px truncate font-medium"
                                                    >{row.filename}</span
                                                >
                                            </div></td
                                        ><td class="p-3"
                                            ><span
                                                class="rounded-full px-2.5 py-1 text-[10px] font-bold"
                                                class:bg-emerald-950={row.verdict ===
                                                    "real"}
                                                class:text-emerald-300={row.verdict ===
                                                    "real"}
                                                class:bg-rose-950={row.verdict ===
                                                    "ai_generated"}
                                                class:text-rose-300={row.verdict ===
                                                    "ai_generated"}
                                                class:bg-amber-950={row.verdict ===
                                                    "inconclusive"}
                                                class:text-amber-300={row.verdict ===
                                                    "inconclusive"}
                                                >{row.label}</span
                                            ></td
                                        ><td class="p-3"
                                            >{row.confidence_percent}%</td
                                        ><td class="p-3 text-xs text-slate-400"
                                            >{formatDate(row.analyzed_at)}</td
                                        ></tr
                                    >{/each}{/if}
                        </tbody>
                    </table>
                </div>
            </section>

            <aside class="flex flex-col gap-6">
                <section
                    class="rounded-2xl border border-indigo-500/50 bg-linear-to-br from-indigo-950/80 to-slate-900 p-5 sm:p-6"
                >
                    <h2 class="text-center text-xl font-bold">
                        Result breakdown
                    </h2>
                    <div class="flex items-center justify-center gap-6 py-5">
                        <div
                            class="relative grid size-32 shrink-0 place-items-center rounded-full"
                            style={`background: ${chartGradient}`}
                        >
                            <div
                                class="grid size-16 place-items-center rounded-full bg-slate-950 text-xs text-slate-400"
                            >
                                {ui.stats.total}
                            </div>
                        </div>
                        <div>
                            <strong class="text-3xl">{ui.stats.total}</strong>
                            <p class="text-xs text-slate-400">analyses</p>
                        </div>
                    </div>
                    <ul class="space-y-2 text-xs">
                        <li class="flex justify-between">
                            <span class="text-emerald-300"
                                >● &nbsp;Likely real</span
                            ><span>{ui.stats.likely_real}</span>
                        </li>
                        <li class="flex justify-between">
                            <span class="text-rose-300"
                                >● &nbsp;Likely AI-generated</span
                            ><span>{ui.stats.ai_generated}</span>
                        </li>
                        <li class="flex justify-between">
                            <span class="text-amber-300"
                                >● &nbsp;Inconclusive</span
                            ><span>{ui.stats.inconclusive}</span>
                        </li>
                    </ul>
                    <label
                        class="mt-6 flex min-h-16 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-indigo-400/70 bg-indigo-500/10 p-3 text-center transition hover:border-indigo-300 hover:bg-indigo-500/20"
                        ><span class="text-xs font-bold"
                            >Quick image detection</span
                        ><span class="mt-1 text-[10px] text-slate-400"
                            >Drop by browsing a JPG, PNG, or WEBP · max 5 MB</span
                        ><input
                            class="sr-only"
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            onchange={openQuickDetection}
                        /></label
                    >
                    {#if ui.error}<p
                            class="mt-2 text-xs text-rose-300"
                            role="alert"
                        >
                            {ui.error}
                        </p>{/if}
                </section>
                <div
                    class="rounded-2xl border border-slate-800 bg-slate-900/50 p-5"
                >
                    <h3 class="font-semibold">A note on results</h3>
                    <p class="mt-2 text-xs leading-5 text-slate-400">
                        These are model predictions, not proof of image origin.
                        Review the confidence and context before drawing
                        conclusions.
                    </p>
                </div>
            </aside>
        </div>
    </main>
</Layout>

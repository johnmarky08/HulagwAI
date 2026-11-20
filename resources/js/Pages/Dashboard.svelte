<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import LoginGate from "./Components/LoginGate.svelte";
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

    const tones = {
        indigo: {
            chip: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
            bar: "bg-indigo-500",
            value: "text-indigo-300",
        },
        emerald: {
            chip: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
            bar: "bg-emerald-500",
            value: "text-emerald-300",
        },
        rose: {
            chip: "border-rose-500/30 bg-rose-500/10 text-rose-300",
            bar: "bg-rose-500",
            value: "text-rose-300",
        },
        amber: {
            chip: "border-amber-500/30 bg-amber-500/10 text-amber-300",
            bar: "bg-amber-500",
            value: "text-amber-300",
        },
    };

    const summary = [
        {
            label: "Total images analyzed",
            key: "total",
            icon: "▧",
            tone: "indigo",
            caption: "Processed analyses",
        },
        {
            label: "Likely real images",
            key: "likely_real",
            icon: "◉",
            tone: "emerald",
            caption: "Likely authentic",
        },
        {
            label: "AI-generated images",
            key: "ai_generated",
            icon: "✳",
            tone: "rose",
            caption: "Likely synthetic",
        },
        {
            label: "Inconclusive / mixed",
            key: "inconclusive",
            icon: "⚠",
            tone: "amber",
            caption: "Needs human review",
        },
    ];

    const breakdown = $derived([
        {
            label: "Likely real",
            value: ui.stats.likely_real,
            share: ui.stats.total
                ? Math.round((ui.stats.likely_real / ui.stats.total) * 100)
                : 0,
            dot: "bg-emerald-400",
            text: "text-emerald-300",
        },
        {
            label: "Likely AI-generated",
            value: ui.stats.ai_generated,
            share: ui.stats.total
                ? Math.round((ui.stats.ai_generated / ui.stats.total) * 100)
                : 0,
            dot: "bg-rose-400",
            text: "text-rose-300",
        },
        {
            label: "Inconclusive",
            value: ui.stats.inconclusive,
            share: ui.stats.total
                ? Math.round((ui.stats.inconclusive / ui.stats.total) * 100)
                : 0,
            dot: "bg-amber-400",
            text: "text-amber-300",
        },
    ]);

    const chartGradient = $derived.by(() => {
        if (!ui.stats.total) return "conic-gradient(#334155 0 100%)";
        const real = Math.round((ui.stats.likely_real / ui.stats.total) * 100);
        const ai = Math.round((ui.stats.ai_generated / ui.stats.total) * 100);
        return `conic-gradient(#10b981 0 ${real}%, #ef5b63 ${real}% ${real + ai}%, #f3ae38 ${real + ai}% 100%)`;
    });
</script>

<svelte:head
    ><title>HulagwAI · Dashboard</title><meta
        name="description"
        content="Your image analysis dashboard and recent results."
    /></svelte:head
>

<Layout active="dashboard">
    <LoginGate>
        <main
            class="mx-auto min-h-[calc(100vh-80px)] max-w-7xl px-5 py-9 md:px-8"
        >
            <section
                class="dashboard-banner group relative mb-8 overflow-hidden rounded-2xl border border-indigo-500/70 bg-linear-to-r from-indigo-950 to-indigo-800 px-7 py-8 shadow-xl shadow-indigo-950/30 md:px-10"
            >
                <div class="relative z-10 max-w-2xl">
                    <span
                        class="rounded-full border border-indigo-400/50 bg-indigo-400/15 px-3 py-1 text-xs font-medium text-indigo-200"
                        >Image authenticity workspace</span
                    >
                    <h1
                        class="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl"
                    >
                        Detect AI-generated media with clarity
                    </h1>
                    <p
                        class="dashboard-banner-text mt-3 max-w-xl text-sm leading-6 text-indigo-100/80"
                    >
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
                <div
                    class="banner-mark pointer-events-none absolute -right-3 -top-10 hidden text-[220px] leading-none text-indigo-300/15 md:block"
                    aria-hidden="true"
                >
                    ◉
                </div>
            </section>

            {#if ui.historyError}
                <p
                    class="mb-5 rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300"
                    role="alert"
                >
                    Could not load your analysis summary: {ui.historyError}
                </p>
            {/if}

            <section
                class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                aria-label="Analysis summary"
            >
                {#each summary as card (card.key)}
                    {@const tone = tones[card.tone]}
                    <article
                        class="dashboard-card group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition duration-300 hover:-translate-y-1 hover:border-slate-700 hover:shadow-xl hover:shadow-indigo-950/30"
                    >
                        <span
                            class="absolute inset-x-0 top-0 h-1 {tone.bar}"
                            aria-hidden="true"
                        ></span>
                        <div class="flex items-center justify-between gap-3">
                            <span
                                class="text-xs font-semibold uppercase tracking-[.12em] text-slate-400"
                                >{card.label}</span
                            >
                            <span
                                class="grid size-10 place-items-center rounded-xl border text-lg {tone.chip}"
                                aria-hidden="true">{card.icon}</span
                            >
                        </div>
                        <strong
                            class="mt-4 block text-4xl font-extrabold tabular-nums {tone.value}"
                            >{ui.stats[card.key]}</strong
                        >
                        <span class="mt-1 block text-xs text-slate-400"
                            >{card.caption}</span
                        >
                    </article>
                {/each}
            </section>

            <div
                class="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]"
            >
                <section
                    class="rounded-2xl border border-indigo-500/40 bg-slate-900/70 p-4 sm:p-6"
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
                                class="border-b border-slate-700 text-[11px] uppercase tracking-[.12em] text-slate-400"
                            >
                                <tr>
                                    <th class="p-3 font-semibold"
                                        >Image / filename</th
                                    >
                                    <th class="p-3 font-semibold">Result</th>
                                    <th class="p-3 font-semibold">Confidence</th
                                    >
                                    <th class="p-3 font-semibold">Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#if ui.loadingHistory && !ui.rows.length}
                                    <tr
                                        ><td
                                            colspan="4"
                                            class="p-8 text-center text-slate-400"
                                            >Loading your history…</td
                                        ></tr
                                    >
                                {:else if !ui.rows.length}
                                    <tr>
                                        <td
                                            colspan="4"
                                            class="p-8 text-center text-slate-400"
                                        >
                                            No saved analyses yet. <a
                                                use:inertia
                                                class="text-indigo-300 underline"
                                                href="/detect"
                                                >Analyze an image</a
                                            > to get started.
                                        </td>
                                    </tr>
                                {:else}
                                    {#each ui.rows.slice(0, 5) as row (row.id)}
                                        <tr
                                            class="border-b border-slate-800/80 transition hover:bg-indigo-950/40"
                                        >
                                            <td class="p-3">
                                                <div
                                                    class="flex items-center gap-3"
                                                >
                                                    <img
                                                        class="size-10 rounded-lg object-cover ring-1 ring-slate-700"
                                                        src={row.thumb_url ||
                                                            sampleImage}
                                                        alt=""
                                                    />
                                                    <span
                                                        class="max-w-180px truncate font-medium"
                                                        >{row.filename}</span
                                                    >
                                                </div>
                                            </td>
                                            <td class="p-3">
                                                <span
                                                    class="rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
                                                    class:border-emerald-800={row.verdict ===
                                                        "real"}
                                                    class:bg-emerald-950={row.verdict ===
                                                        "real"}
                                                    class:text-emerald-300={row.verdict ===
                                                        "real"}
                                                    class:border-rose-800={row.verdict ===
                                                        "ai_generated"}
                                                    class:bg-rose-950={row.verdict ===
                                                        "ai_generated"}
                                                    class:text-rose-300={row.verdict ===
                                                        "ai_generated"}
                                                    class:border-amber-800={row.verdict ===
                                                        "inconclusive"}
                                                    class:bg-amber-950={row.verdict ===
                                                        "inconclusive"}
                                                    class:text-amber-300={row.verdict ===
                                                        "inconclusive"}
                                                    >{row.label}</span
                                                >
                                            </td>
                                            <td class="p-3 tabular-nums"
                                                >{row.confidence_percent}%</td
                                            >
                                            <td
                                                class="p-3 text-xs text-slate-400"
                                                >{formatDate(
                                                    row.analyzed_at,
                                                )}</td
                                            >
                                        </tr>
                                    {/each}
                                {/if}
                            </tbody>
                        </table>
                    </div>
                </section>

                <aside class="flex flex-col gap-6">
                    <section
                        class="rounded-2xl border border-indigo-500/40 bg-slate-900/70 p-5 sm:p-6"
                    >
                        <h2 class="text-lg font-bold">Result breakdown</h2>
                        <div class="mt-5 flex items-center gap-6">
                            <div
                                class="grid size-32 shrink-0 place-items-center rounded-full"
                                style={`background: ${chartGradient}`}
                            >
                                <div
                                    class="grid size-20 place-items-center rounded-full bg-slate-950 text-center"
                                >
                                    <div>
                                        <span
                                            class="block text-2xl font-extrabold tabular-nums"
                                            >{ui.stats.total}</span
                                        >
                                        <span
                                            class="block text-[10px] uppercase tracking-wider text-slate-400"
                                            >analyses</span
                                        >
                                    </div>
                                </div>
                            </div>
                            <ul class="flex-1 space-y-3 text-sm">
                                {#each breakdown as item (item.label)}
                                    <li
                                        class="flex items-center justify-between gap-3"
                                    >
                                        <span
                                            class="flex items-center gap-2 text-slate-200"
                                            ><i
                                                class="size-2.5 rounded-full {item.dot}"
                                                aria-hidden="true"
                                            ></i>{item.label}</span
                                        >
                                        <span class="tabular-nums {item.text}"
                                            >{item.value}
                                            <span class="text-xs text-slate-400"
                                                >· {item.share}%</span
                                            ></span
                                        >
                                    </li>
                                {/each}
                            </ul>
                        </div>
                        <label
                            class="mt-6 flex cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-indigo-400/60 bg-indigo-500/10 px-4 py-5 text-center transition hover:border-indigo-300 hover:bg-indigo-500/20"
                        >
                            <span
                                class="grid size-9 place-items-center rounded-full bg-indigo-500/20 text-indigo-200"
                                aria-hidden="true">⬆</span
                            >
                            <span class="text-sm font-bold text-slate-100"
                                >Quick image detection</span
                            >
                            <span class="text-[11px] text-slate-400"
                                >JPG, PNG, or WEBP · max 5 MB</span
                            >
                            <input
                                class="sr-only"
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                onchange={openQuickDetection}
                            />
                        </label>
                        {#if ui.error}
                            <p class="mt-2 text-xs text-rose-300" role="alert">
                                {ui.error}
                            </p>
                        {/if}
                    </section>
                    <div
                        class="rounded-2xl border border-slate-800 bg-slate-900/60 p-5"
                    >
                        <h3 class="font-semibold">A note on results</h3>
                        <p class="mt-2 text-xs leading-5 text-slate-400">
                            These are model predictions, not proof of image
                            origin. Review the confidence and context before
                            drawing conclusions.
                        </p>
                    </div>
                </aside>
            </div>
        </main>
    </LoginGate>
</Layout>

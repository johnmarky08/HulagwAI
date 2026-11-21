<script>
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import {
        ui,
        sampleImage,
        handleHistorySearch,
        handleResultFilter,
        handleRangeFilter,
        handleSortFilter,
        handleHistoryPage,
        previousHistoryPage,
        nextHistoryPage,
        exportHistory,
        deleteAnalysis,
        clearAllHistory,
        formatDate,
    } from "../official/controller.svelte.js";
    import LoginGate from "./Components/LoginGate.svelte";
    import Icon from "./Components/Icon.svelte";

    // Compact pager: first, last and the pages around the current one ("…" for gaps).
    const pageList = $derived.by(() => {
        const last = Math.max(1, ui.meta.last_page);
        const current = ui.meta.page;
        const wanted = new Set([1, last, current - 1, current, current + 1]);
        const pages = [...wanted].filter((p) => p >= 1 && p <= last).sort((a, b) => a - b);
        const out = [];
        pages.forEach((p, i) => {
            if (i && p - pages[i - 1] > 1) out.push(`gap-${p}`);
            out.push(p);
        });
        return out;
    });
</script>

<svelte:head><title>HulagwAI · Analysis History</title></svelte:head>

<Layout active="history">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-7xl px-5 pb-20 sm:px-8">
        <div
            class="mx-auto mb-8 mt-7 max-w-3xl text-left sm:mt-10 sm:text-center"
        >
            <h1
                class="bg-linear-to-r from-violet-200 to-indigo-500 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent sm:text-5xl"
            >
                Analysis History
            </h1>
            <p class="mt-3 text-sm text-slate-400">
                Search, filter, and revisit your previous image analyses.
            </p>
        </div>
        <LoginGate>
            <section
                class="mb-7 grid grid-cols-2 gap-4 lg:grid-cols-4"
                aria-label="Analysis summary"
            >
                {#each [{ label: "Total analyses", value: ui.stats.total, tone: "indigo", icon: "images", caption: "Processed analyses" }, { label: "Likely real", value: ui.stats.likely_real, tone: "emerald", icon: "shield-check", caption: "Likely authentic" }, { label: "AI-generated", value: ui.stats.ai_generated, tone: "rose", icon: "bot", caption: "Likely synthetic" }, { label: "Inconclusive", value: ui.stats.inconclusive, tone: "amber", icon: "triangle-alert", caption: "Needs human review" }] as card (card.label)}
                    <article
                        class="history-stat group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-4 transition duration-300 hover:-translate-y-1 hover:border-slate-700 hover:shadow-xl hover:shadow-indigo-950/30 sm:p-5"
                        data-tone={card.tone}
                    >
                        <span
                            class="absolute inset-x-0 top-0 h-1 bar"
                            aria-hidden="true"
                        ></span>
                        <div class="flex items-center justify-between gap-3">
                            <span
                                class="text-[10px] font-semibold uppercase tracking-[.06em] text-slate-400 sm:text-xs sm:tracking-[.12em]"
                                >{card.label}</span
                            >
                            <span
                                class="grid size-8 shrink-0 place-items-center rounded-xl border text-sm chip sm:size-9 sm:text-base"
                                aria-hidden="true"><Icon name={card.icon} /></span
                            >
                        </div>
                        <strong
                            class="mt-3 block text-3xl font-extrabold tabular-nums sm:text-4xl value"
                            >{card.value}</strong
                        >
                        <span class="mt-1 block text-xs text-slate-400"
                            >{card.caption}</span
                        >
                    </article>
                {/each}
            </section>
            <div
                class="mb-6 grid grid-cols-2 gap-3 md:grid-cols-[minmax(200px,1fr)_170px_170px_190px]"
            >
                <label
                    class="col-span-2 flex h-12 items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-4 md:col-span-1"
                    ><span class="text-xl text-slate-400"><Icon name="search" /></span><input
                        class="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                        placeholder="Search by filename"
                        value={ui.search}
                        oninput={handleHistorySearch}
                    /></label
                >
                <select
                    class="h-12 rounded-xl border border-slate-700 bg-slate-900 px-4 text-sm text-white"
                    aria-label="Filter by result"
                    value={ui.verdictFilter}
                    onchange={handleResultFilter}
                    ><option>All results</option><option>Real</option><option
                        >AI-generated</option
                    ><option>Inconclusive</option></select
                >
                <select
                    class="h-12 rounded-xl border border-slate-700 bg-slate-900 px-4 text-sm text-slate-300"
                    aria-label="Filter by date"
                    value={ui.dateFilter}
                    onchange={handleRangeFilter}
                    ><option>All time</option><option>Last 7 days</option
                    ><option>Last 30 days</option><option>Last 90 days</option
                    ></select
                >
                <select
                    class="col-span-2 h-12 rounded-xl border border-slate-700 bg-slate-900 px-4 text-sm text-slate-300 md:col-span-1"
                    aria-label="Sort results"
                    value={ui.sortFilter}
                    onchange={handleSortFilter}
                    ><option>Newest first</option><option>Oldest first</option
                    ><option>Highest confidence</option><option
                        >Lowest confidence</option
                    ></select
                >
            </div>
            {#if ui.historyError}<p
                    class="mb-4 rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300"
                >
                    {ui.historyError}
                </p>{/if}
            <section
                class="rounded-xl border border-indigo-500/50 bg-slate-900/80 p-3 sm:p-5"
            >
                <div
                    class="flex flex-wrap items-center justify-between gap-3 px-2"
                >
                    <div>
                        <h2 class="text-lg font-bold">Recent Analyses</h2>
                        <span class="text-xs text-slate-400"
                            >{ui.sortFilter}</span
                        >
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="h-10 rounded-xl border border-slate-700 bg-linear-to-r from-slate-900 to-slate-700 px-4 text-xs font-semibold disabled:opacity-50"
                            onclick={() => exportHistory("csv")}
                            disabled={!ui.stats.total}><Icon name="download" class="mr-1.5" />Export CSV</button
                        >
                        <button
                            type="button"
                            class="h-10 rounded-xl border border-slate-700 bg-linear-to-r from-slate-900 to-slate-700 px-4 text-xs font-semibold disabled:opacity-50"
                            onclick={() => exportHistory("json")}
                            disabled={!ui.stats.total}><Icon name="download" class="mr-1.5" />Export JSON</button
                        >
                        <button
                            type="button"
                            class="h-10 rounded-xl border border-rose-800 bg-rose-950/40 px-4 text-xs font-semibold text-rose-300 disabled:opacity-50"
                            onclick={clearAllHistory}
                            disabled={!ui.stats.total || ui.clearingHistory}
                            >{ui.clearingHistory
                                ? "Clearing…"
                                : "Clear History"}</button
                        >
                    </div>
                </div>
                <div class="mt-4 hidden overflow-x-auto md:block">
                    <table
                        class="w-full min-w-[740px] border-collapse text-left text-sm"
                    >
                        <thead class="text-xs text-slate-400"
                            ><tr
                                ><th class="p-3 font-medium"
                                    >Image / Filename</th
                                ><th class="p-3 font-medium">Result</th><th
                                    class="p-3 font-medium">Confidence</th
                                ><th class="p-3 font-medium">Date Analyzed</th
                                ><th class="p-3"></th></tr
                            ></thead
                        ><tbody>
                            {#if ui.loadingHistory}<tr
                                    ><td
                                        colspan="5"
                                        class="p-10 text-center text-slate-400"
                                        >Loading history…</td
                                    ></tr
                                >{:else if ui.rows.length === 0}<tr
                                    ><td
                                        colspan="5"
                                        class="p-10 text-center text-slate-400"
                                        >No analyses found.</td
                                    ></tr
                                >{:else}{#each ui.rows as row, index (row.id)}<tr
                                        class="border-t border-slate-800"
                                        class:bg-indigo-950={index === 0}
                                        ><td class="p-2"
                                            ><div
                                                class="flex items-center gap-4"
                                            >
                                                <a
                                                    use:inertia
                                                    class="thumb-link shrink-0"
                                                    href={"/detect?analysis=" +
                                                        row.id}
                                                    aria-label={`Open the analysis of ${row.filename}`}
                                                    ><img
                                                        class="size-12 rounded-lg object-cover"
                                                        src={row.thumb_url ||
                                                            sampleImage}
                                                        alt=""
                                                    /></a
                                                ><span>{row.filename}</span>
                                            </div></td
                                        ><td class="p-3"
                                            ><span
                                                class="rounded-full px-3 py-1 text-[10px] font-bold uppercase"
                                                class:bg-rose-950={row.verdict ===
                                                    "ai_generated"}
                                                class:text-rose-400={row.verdict ===
                                                    "ai_generated"}
                                                class:bg-emerald-950={row.verdict ===
                                                    "real"}
                                                class:text-emerald-400={row.verdict ===
                                                    "real"}
                                                class:bg-amber-950={row.verdict ===
                                                    "inconclusive"}
                                                class:text-amber-400={row.verdict ===
                                                    "inconclusive"}
                                                >{row.label}</span
                                            ></td
                                        ><td class="p-3"
                                            >{row.confidence_percent}%</td
                                        ><td class="p-3 text-slate-400"
                                            >{formatDate(row.analyzed_at)}</td
                                        ><td class="p-3"
                                            ><div
                                                class="flex items-center justify-end gap-4"
                                            >
                                                <a
                                                    use:inertia
                                                    class="text-xs font-semibold hover:text-indigo-300"
                                                    href={"/detect?analysis=" +
                                                        row.id}>View ›</a
                                                ><button
                                                    type="button"
                                                    class="text-xs font-semibold text-rose-400 hover:text-rose-300 disabled:opacity-50"
                                                    aria-label={`Delete the analysis of ${row.filename}`}
                                                    disabled={ui.deletingId ===
                                                        row.id}
                                                    onclick={() =>
                                                        deleteAnalysis(
                                                            row.id,
                                                            row.filename,
                                                        )}
                                                    >{ui.deletingId === row.id
                                                        ? "Deleting…"
                                                        : "Delete"}</button
                                                >
                                            </div></td
                                        ></tr
                                    >{/each}{/if}
                        </tbody>
                    </table>
                </div>
                <div class="mt-4 grid gap-3 md:hidden">
                    {#if ui.loadingHistory}
                        <p
                            class="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-center text-sm text-slate-400"
                        >
                            Loading history…
                        </p>
                    {:else if ui.rows.length === 0}
                        <p
                            class="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-center text-sm text-slate-400"
                        >
                            No analyses found.
                        </p>
                    {:else}
                        {#each ui.rows as row (row.id)}
                            <article
                                class="mobile-history-card flex min-w-0 gap-3 rounded-xl border border-slate-800 bg-slate-950/40 p-3"
                            >
                                <a
                                    use:inertia
                                    class="thumb-link shrink-0"
                                    href={"/detect?analysis=" + row.id}
                                    aria-label={`Open the analysis of ${row.filename}`}
                                    ><img
                                        class="size-14 rounded-lg object-cover"
                                        src={row.thumb_url || sampleImage}
                                        alt=""
                                    /></a
                                >
                                <div class="min-w-0 flex-1">
                                    <div
                                        class="flex min-w-0 items-start justify-between gap-2"
                                    >
                                        <div class="min-w-0">
                                            <p
                                                class="truncate text-sm font-semibold"
                                            >
                                                {row.filename}
                                            </p>
                                            <p
                                                class="mt-1 text-xs text-slate-400"
                                            >
                                                {formatDate(row.analyzed_at)}
                                            </p>
                                        </div>
                                        <span
                                            class="shrink-0 text-xs text-slate-400"
                                            >{row.confidence_percent}%</span
                                        >
                                    </div>
                                    <div
                                        class="mt-3 flex items-center justify-between gap-2"
                                    >
                                        <span
                                            class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase"
                                            class:bg-rose-950={row.verdict ===
                                                "ai_generated"}
                                            class:text-rose-400={row.verdict ===
                                                "ai_generated"}
                                            class:bg-emerald-950={row.verdict ===
                                                "real"}
                                            class:text-emerald-400={row.verdict ===
                                                "real"}
                                            class:bg-amber-950={row.verdict ===
                                                "inconclusive"}
                                            class:text-amber-400={row.verdict ===
                                                "inconclusive"}
                                            >{row.label}</span
                                        >
                                        <span class="flex items-center gap-3">
                                            <button
                                                type="button"
                                                class="text-xs font-semibold text-rose-400 disabled:opacity-50"
                                                aria-label={`Delete the analysis of ${row.filename}`}
                                                disabled={ui.deletingId ===
                                                    row.id}
                                                onclick={() =>
                                                    deleteAnalysis(
                                                        row.id,
                                                        row.filename,
                                                    )}
                                                >{ui.deletingId === row.id
                                                    ? "Deleting…"
                                                    : "Delete"}</button
                                            >
                                            <a
                                                use:inertia
                                                class="text-xs font-semibold text-indigo-300"
                                                href={"/detect?analysis=" +
                                                    row.id}>View Result ›</a
                                            >
                                        </span>
                                    </div>
                                </div>
                            </article>
                        {/each}
                    {/if}
                </div>
                <div
                    class="flex flex-col gap-3 px-2 pb-2 pt-6 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between"
                >
                    <span
                        >Showing {ui.meta.from ?? 0}–{ui.meta.to ?? 0} of {ui
                            .meta.total} analyses</span
                    >
                    <nav
                        class="flex flex-wrap items-center gap-2"
                        aria-label="History pages"
                    >
                        <button
                            class="inline-flex min-h-11 min-w-11 items-center justify-center px-2 text-white disabled:opacity-40 sm:min-h-0 sm:min-w-0 sm:px-0"
                            disabled={ui.meta.page <= 1 || ui.loadingHistory}
                            onclick={previousHistoryPage}>‹ Previous</button
                        >{#each pageList as page (page)}{#if typeof page === "string"}<span
                                    class="px-1 text-slate-500"
                                    aria-hidden="true">…</span
                                >{:else}<button
                                    class={`inline-flex min-h-11 min-w-11 items-center justify-center px-1 sm:min-h-0 sm:min-w-0 ${ui.meta.page === page ? "font-bold text-indigo-400" : "text-white"}`}
                                    aria-current={ui.meta.page === page
                                        ? "page"
                                        : undefined}
                                    aria-label={`Page ${page}`}
                                    data-page={page}
                                    disabled={ui.loadingHistory}
                                    onclick={handleHistoryPage}>{page}</button
                                >{/if}{/each}<button
                            class="inline-flex min-h-11 min-w-11 items-center justify-center px-2 text-white disabled:opacity-40 sm:min-h-0 sm:min-w-0 sm:px-0"
                            disabled={ui.meta.page >= ui.meta.last_page ||
                                ui.loadingHistory}
                            onclick={nextHistoryPage}>Next ›</button
                        >
                    </nav>
                </div>
            </section>
        </LoginGate>
    </main>
</Layout>

<style>
    /* Color coding for the summary cards (matches the Dashboard). */
    .history-stat[data-tone="indigo"] {
        --c: #818cf8;
        --bar: #6366f1;
    }
    .history-stat[data-tone="emerald"] {
        --c: #34d399;
        --bar: #10b981;
    }
    .history-stat[data-tone="rose"] {
        --c: #fb7185;
        --bar: #f43f5e;
    }
    .history-stat[data-tone="amber"] {
        --c: #fbbf24;
        --bar: #f59e0b;
    }
    .history-stat .bar {
        background: var(--bar);
    }
    .history-stat .chip {
        border-color: color-mix(in srgb, var(--c) 35%, transparent);
        background: color-mix(in srgb, var(--c) 12%, transparent);
        color: var(--c);
    }
    .history-stat .value {
        color: var(--c);
    }

    .thumb-link {
        border-radius: 0.5rem;
    }
    .thumb-link:hover img,
    .thumb-link:focus-visible img {
        box-shadow: 0 0 0 2px #818cf8;
    }
    .thumb-link:focus-visible {
        outline: none;
    }
    .thumb-link img {
        transition: box-shadow 0.15s ease;
    }
</style>

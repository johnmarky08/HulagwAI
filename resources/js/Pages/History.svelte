<script>
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import {
        ui,
        sampleImage,
        handleHistorySearch,
        handleResultFilter,
        handleRangeFilter,
        handleHistoryPage,
        previousHistoryPage,
        nextHistoryPage,
        exportHistory,
        formatDate,
    } from "../official/controller.svelte.js";
</script>

<svelte:head><title>HulagwAI · Analysis History</title></svelte:head>

<Layout active="history">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-1240px px-5 pb-16">
        <div class="mx-auto mb-8 mt-10 max-w-3xl text-center">
            <h1
                class="bg-linear-to-r from-violet-200 to-indigo-500 bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl"
            >
                Analyzing your image
            </h1>
            <p class="mt-3 text-sm text-slate-400">
                Looking for patterns, artifacts, and signs of AI generation.
            </p>
        </div>
        <section class="mb-7 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <article
                class="rounded-xl border border-slate-700 bg-slate-900 p-4"
            >
                <span class="text-xs text-slate-400">Total analyses</span
                ><strong
                    class="mt-2 block text-3xl font-extrabold text-indigo-400"
                    >{ui.stats.total}</strong
                >
            </article>
            <article
                class="rounded-xl border border-slate-700 bg-slate-900 p-4"
            >
                <span class="text-xs text-slate-400">Likely real</span><strong
                    class="mt-2 block text-3xl font-extrabold text-emerald-400"
                    >{ui.stats.likely_real}</strong
                >
            </article>
            <article
                class="rounded-xl border border-slate-700 bg-slate-900 p-4"
            >
                <span class="text-xs text-slate-400">AI-generated</span><strong
                    class="mt-2 block text-3xl font-extrabold text-rose-400"
                    >{ui.stats.ai_generated}</strong
                >
            </article>
            <article
                class="rounded-xl border border-amber-900 bg-amber-950/30 p-4"
            >
                <span class="text-xs text-amber-400">Inconclusive</span><strong
                    class="mt-2 block text-3xl font-extrabold text-amber-400"
                    >{ui.stats.inconclusive}</strong
                >
            </article>
        </section>
        <div
            class="mb-6 grid gap-3 md:grid-cols-[minmax(220px,1fr)_180px_180px_auto]"
        >
            <label
                class="flex h-12 items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-4"
                ><span class="text-xl text-slate-400">⌕</span><input
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
                ><option>All time</option><option>Last 7 days</option><option
                    >Last 30 days</option
                ><option>Last 90 days</option></select
            >
            <button
                class="h-12 rounded-xl border border-slate-700 bg-linear-to-r from-slate-900 to-slate-700 px-5 text-sm font-semibold"
                onclick={exportHistory}>↓ &nbsp; Export history</button
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
            <div class="flex items-center justify-between px-2">
                <h2 class="text-lg font-bold">Recent analyses</h2>
                <span class="text-xs text-slate-400">Newest first</span>
            </div>
            <div class="mt-4 overflow-x-auto">
                <table
                    class="w-full min-w-740px border-collapse text-left text-sm"
                >
                    <thead class="text-xs text-slate-400"
                        ><tr
                            ><th class="p-3 font-medium">Image / Filename</th
                            ><th class="p-3 font-medium">Result</th><th
                                class="p-3 font-medium">Confidence</th
                            ><th class="p-3 font-medium">Date analyzed</th><th
                                class="p-3"
                            ></th></tr
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
                                        ><div class="flex items-center gap-4">
                                            <img
                                                class="size-12 rounded-lg object-cover"
                                                src={row.thumb_url ||
                                                    sampleImage}
                                                alt=""
                                            /><span>{row.filename}</span>
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
                                        ><a
                                            use:inertia
                                            class="text-xs font-semibold hover:text-indigo-300"
                                            href={"/detect?analysis=" + row.id}
                                            >View ›</a
                                        ></td
                                    ></tr
                                >{/each}{/if}
                    </tbody>
                </table>
            </div>
            <div
                class="flex flex-col gap-3 px-2 pb-2 pt-6 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between"
            >
                <span
                    >Showing {ui.meta.from ?? 0}–{ui.meta.to ?? 0} of {ui.meta
                        .total} analyses</span
                >
                <div class="flex items-center gap-2">
                    <button
                        class="text-white disabled:opacity-40"
                        disabled={ui.meta.page <= 1}
                        onclick={previousHistoryPage}>Previous</button
                    >{#each Array.from({ length: Math.max(1, ui.meta.last_page) }, (_, index) => index + 1) as page}<button
                            class="px-1 text-white"
                            class:text-indigo-400={ui.meta.page === page}
                            data-page={page}
                            onclick={handleHistoryPage}>{page}</button
                        >{/each}<button
                        class="text-white disabled:opacity-40"
                        disabled={ui.meta.page >= ui.meta.last_page}
                        onclick={nextHistoryPage}>Next ›</button
                    >
                </div>
            </div>
        </section>
    </main>
</Layout>

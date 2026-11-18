<script>
    import { onMount } from "svelte";
    import Layout from "../Layouts/TestLayout.svelte";
    import { history } from "../api/history";
    import { analyses } from "../api/analyses";
    import { errorMessage } from "../api/client";

    let q = $state({ search: "", result: "all", range: "all", sort: "newest", page: 1 });
    let data = $state({ data: [], meta: { total: 0, page: 1, last_page: 1, from: 0, to: 0 }, stats: { total: 0, likely_real: 0, ai_generated: 0, inconclusive: 0 } });
    let error = $state("");

    async function load() {
        try { data = await history.list(q); error = ""; } catch (e) { error = errorMessage(e); }
    }
    onMount(load);

    function change() { q.page = 1; load(); }
    async function remove(id) { await analyses.remove(id); load(); }
    async function clearAll() { if (confirm("Delete ALL your analyses and stored images?")) { await history.clear(); load(); } }
    const badge = { ai_generated: "text-rose-300", real: "text-emerald-300", inconclusive: "text-amber-300" };
</script>

<Layout active="/history">
    <h1 class="mb-4 text-3xl font-bold">History</h1>
    <div class="mb-4 grid grid-cols-4 gap-3 text-center">
        <div class="rounded border border-slate-700 p-3">Total<div class="text-3xl font-bold text-indigo-400">{data.stats.total}</div></div>
        <div class="rounded border border-slate-700 p-3">Likely real<div class="text-3xl font-bold text-emerald-400">{data.stats.likely_real}</div></div>
        <div class="rounded border border-slate-700 p-3">AI-generated<div class="text-3xl font-bold text-rose-400">{data.stats.ai_generated}</div></div>
        <div class="rounded border border-amber-700 p-3">Inconclusive<div class="text-3xl font-bold text-amber-400">{data.stats.inconclusive}</div></div>
    </div>

    <div class="mb-4 flex flex-wrap gap-2">
        <input class="flex-1 rounded border border-slate-700 bg-slate-900 px-3 py-2" placeholder="Search by filename" bind:value={q.search} oninput={change} />
        <select class="rounded border border-slate-700 bg-slate-900 px-2" bind:value={q.result} onchange={change}>
            <option value="all">All results</option><option value="real">Real</option><option value="ai_generated">AI-generated</option><option value="inconclusive">Inconclusive</option>
        </select>
        <select class="rounded border border-slate-700 bg-slate-900 px-2" bind:value={q.range} onchange={change}>
            <option value="all">All time</option><option value="7d">7 days</option><option value="30d">30 days</option><option value="90d">90 days</option>
        </select>
        <select class="rounded border border-slate-700 bg-slate-900 px-2" bind:value={q.sort} onchange={change}>
            <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="confidence_desc">Highest confidence</option><option value="confidence_asc">Lowest confidence</option>
        </select>
        <a class="rounded border border-indigo-500 px-3 py-2" href={history.exportUrl("csv")}>Export CSV</a>
        <button class="rounded border border-red-500 px-3 py-2 text-red-300" onclick={clearAll}>Clear</button>
    </div>
    {#if error}<p class="text-red-300">{error}</p>{/if}

    <table class="w-full text-left text-sm">
        <thead class="text-slate-400"><tr><th></th><th>Image / Filename</th><th>Result</th><th>Confidence</th><th>Date analyzed</th><th></th></tr></thead>
        <tbody>
            {#each data.data as r (r.id)}
                <tr class="border-t border-slate-800">
                    <td class="py-2"><img src={r.thumb_url} alt="" class="h-10 w-10 rounded object-cover" /></td>
                    <td>{r.filename}</td>
                    <td class={badge[r.verdict]}>{r.label}</td>
                    <td>{r.confidence_percent}%</td>
                    <td>{new Date(r.analyzed_at).toLocaleDateString()}</td>
                    <td><a class="underline" href={analyses.reportUrl(r.id)}>PDF</a> · <button class="text-red-300 underline" onclick={() => remove(r.id)}>Delete</button></td>
                </tr>
            {/each}
        </tbody>
    </table>
    <div class="mt-4 flex items-center justify-between text-sm text-slate-400">
        <span>Showing {data.meta.from}–{data.meta.to} of {data.meta.total} analyses</span>
        <span>
            <button disabled={q.page <= 1} onclick={() => { q.page--; load(); }}>Previous</button>
            <span class="mx-2">{data.meta.page} / {data.meta.last_page}</span>
            <button disabled={q.page >= data.meta.last_page} onclick={() => { q.page++; load(); }}>Next</button>
        </span>
    </div>
</Layout>

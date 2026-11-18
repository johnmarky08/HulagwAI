<!-- Upload → Analyze → Results, as in the Figma flow. TEST-ONLY UI. -->
<script>
    import Layout from "../Layouts/TestLayout.svelte";
    import { analyses } from "../api/analyses";
    import { errorMessage } from "../api/client";

    const MAX = 5 * 1024 * 1024;
    let file = $state(null);
    let phase = $state("upload"); // upload | analyze | results
    let progress = $state(0);
    let steps = $state([]);
    let result = $state(null);
    let error = $state("");
    let id = $state(null);
    let signal = { cancelled: false };
    let previewUrl = $state(null);

    function choose(f) {
        error = "";
        if (!f) return;
        if (!/\.(jpe?g|png|webp)$/i.test(f.name)) { error = `"${f.name}" is not supported. Please use JPG, JPEG, PNG, WEBP`; return; }
        if (f.size > MAX) { error = "Max 5 MB per image."; return; }
        file = f;
        previewUrl = URL.createObjectURL(f);
    }

    async function start() {
        error = ""; phase = "analyze"; progress = 0; signal = { cancelled: false };
        try {
            const first = await analyses.upload(file);
            id = first.id;
            const final = await analyses.waitFor(id, (s) => { progress = s.progress; steps = s.steps; }, signal);
            if (final.status === "failed") { error = final.error?.message ?? "Analysis failed."; phase = "upload"; return; }
            if (final.status === "done") { result = final; phase = "results"; }
        } catch (e) {
            error = errorMessage(e); phase = "upload";
        }
    }

    async function cancel() {
        signal.cancelled = true;
        if (id) await analyses.remove(id).catch(() => {});
        phase = "upload"; id = null;
    }

    function again() { file = null; previewUrl = null; result = null; id = null; phase = "upload"; }
</script>

<Layout active="/detect">
    <h1 class="mb-1 text-3xl font-bold">{phase === "results" ? "Analysis Result" : phase === "analyze" ? "Analyzing your image" : "Start detecting"}</h1>
    <p class="mb-6 text-slate-400">Looking for patterns, artifacts, and signs of AI generation.</p>

    {#if error}<div class="mb-4 rounded border border-red-500 bg-red-950 p-3 text-red-200">{error}</div>{/if}

    {#if phase === "upload"}
        <label class="flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed border-indigo-500/60 p-10"
               ondragover={(e) => e.preventDefault()} ondrop={(e) => { e.preventDefault(); choose(e.dataTransfer.files[0]); }}>
            {#if previewUrl}<img src={previewUrl} alt="preview" class="max-h-64 rounded" />{:else}<span class="text-xl font-semibold">Drag and drop an image here</span>{/if}
            <span class="text-sm text-slate-400">{file ? `${file.name} · ${(file.size / 1048576).toFixed(2)} MB` : "JPG · JPEG · PNG · WEBP · Max 5 MB"}</span>
            <input type="file" class="hidden" accept=".jpg,.jpeg,.png,.webp" onchange={(e) => choose(e.target.files[0])} />
        </label>
        <button class="mt-4 rounded bg-indigo-600 px-5 py-2 font-semibold disabled:opacity-40" disabled={!file} onclick={start}>Image Detection</button>
        {#if file}<button class="ml-2 rounded border border-red-500 px-4 py-2 text-red-300" onclick={again}>Remove</button>{/if}
    {:else if phase === "analyze"}
        <div class="rounded-xl border border-indigo-500/40 p-6">
            <div class="text-5xl font-bold">{progress}%</div>
            <div class="my-3 h-2 rounded bg-slate-800"><div class="h-2 rounded bg-indigo-500 transition-all" style="width:{progress}%"></div></div>
            <ul class="space-y-1 text-sm">{#each steps as s}<li>{s.state === "complete" ? "✓" : s.state === "in_progress" ? "◉" : "○"} {s.label} <span class="text-slate-500">— {s.state.replace("_", " ")}</span></li>{/each}</ul>
        </div>
        <button class="mt-4 rounded border border-red-500 px-4 py-2 text-red-300" onclick={cancel}>Cancel Analysis</button>
    {:else if result}
        <div class="grid gap-6 md:grid-cols-2">
            <div class="rounded-xl border border-indigo-500/40 p-4">
                <img src={analyses.imageUrl(result.id)} alt="analyzed" class="rounded" />
                <dl class="mt-3 grid grid-cols-2 gap-1 text-sm text-slate-300">
                    <dt>File analyzed</dt><dd>{result.file.name}</dd><dt>Format</dt><dd>{result.file.format}</dd>
                    <dt>File size</dt><dd>{result.file.size_mb.toFixed(2)} mb</dd><dt>Analyzed on</dt><dd>{new Date(result.analyzed_at).toLocaleDateString()}</dd>
                </dl>
            </div>
            <div class="rounded-xl border border-indigo-500/40 p-4 text-center">
                <div class="mb-2 text-xs text-emerald-400">✓ ANALYSIS COMPLETE</div>
                <span class="rounded border px-3 py-1 {result.result.verdict === 'ai_generated' ? 'border-rose-500 text-rose-300' : result.result.verdict === 'real' ? 'border-emerald-500 text-emerald-300' : 'border-amber-500 text-amber-300'}">{result.result.label}</span>
                <div class="my-3 text-6xl font-bold">{result.result.ai_percent}%</div>
                <div class="text-slate-400">Estimated AI likelihood</div>
                <div class="my-3 h-2 rounded bg-slate-800"><div class="h-2 rounded bg-rose-500" style="width:{result.result.ai_percent}%"></div></div>
                <div class="flex justify-between text-sm"><span class="text-rose-400">AI-generated {result.result.ai_percent}%</span><span class="text-emerald-400">Real {result.result.real_percent}%</span></div>
                <p class="mt-3 text-sm text-slate-300">{result.result.explanation}</p>
                {#each result.result.warnings as w}<p class="text-xs text-amber-300">⚠ {w.replaceAll("_", " ")}</p>{/each}
                <p class="mt-3 rounded bg-indigo-950 p-2 text-left text-xs text-slate-300"><b>How to read this score.</b> {result.result.how_to_read}</p>
                <p class="mt-2 text-xs text-slate-500">{result.persisted ? "Saved to your analysis history" : "Kept in this browser session only (sign in to keep it)"}</p>
                <div class="mt-3 flex flex-wrap justify-center gap-2">
                    <button class="rounded border border-indigo-500 px-3 py-1" onclick={again}>Analyze another</button>
                    <a class="rounded border border-indigo-500 px-3 py-1" href="/history">View history</a>
                    <a class="rounded border border-indigo-500 px-3 py-1" href={analyses.reportUrl(result.id)}>Download report</a>
                </div>
            </div>
        </div>
    {/if}
</Layout>

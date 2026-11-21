<!--
  "Why it may look AI-generated."  Shows result.evidence (see docs/API.md): grounded detector signals,
  provenance findings, a heat map of where the pixel model fires, and what weakens the evidence.
  It deliberately never claims specific defects (e.g. "extra fingers") - the model cannot verify those.
-->
<script>
    import Icon from "../Icon.svelte";
    let { evidence = null, heatmapUrl = "", showHeatmap = false, onToggleHeatmap = () => {} } = $props();

    const tone = {
        strong: "border-rose-700 bg-rose-950/40 text-rose-300",
        moderate: "border-amber-700 bg-amber-950/30 text-amber-300",
        weak: "border-slate-600 bg-slate-800 text-slate-300",
    };
    const flags = $derived(evidence?.flags ?? []);
    const signals = $derived(flags.filter((f) => f.category !== "Limitations"));
    const limits = $derived(flags.filter((f) => f.category === "Limitations"));
</script>

<article class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6">
    <header class="flex items-start justify-between gap-3">
        <div>
            <p class="text-xs font-bold tracking-wider text-indigo-300">WHY IT MAY LOOK AI-GENERATED</p>
            <h2 class="mt-1 text-xl font-bold">
                {signals.length ? `${signals.length} Signal${signals.length > 1 ? "s" : ""} Found` : "No Strong Signals"}
            </h2>
        </div>
        {#if heatmapUrl}
            <button
                type="button"
                class="shrink-0 rounded-xl border border-indigo-500 px-3 py-2 text-xs text-indigo-300"
                aria-pressed={showHeatmap}
                onclick={onToggleHeatmap}>{showHeatmap ? "Hide Heat Map" : "Show Heat Map"}</button
            >
        {/if}
    </header>

    {#if signals.length}
        <ul class="mt-5 space-y-3">
            {#each signals as f, i (`${f.id}-${i}`)}
                <li class="rounded-xl border border-slate-700 bg-slate-950 p-4">
                    <div class="flex items-center gap-2">
                        <span class={`rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase ${tone[f.strength] ?? tone.weak}`}
                            >{f.strength}</span
                        >
                        <span class="text-xs text-slate-400">{f.category}</span>
                    </div>
                    <p class="mt-2 text-sm font-semibold">{f.title}</p>
                    {#if f.detail}<p class="mt-1 break-words text-sm text-slate-400">{f.detail}</p>{/if}
                </li>
            {/each}
        </ul>
    {:else}
        <p class="mt-4 text-sm text-slate-400">The detectors did not single out anything specific in this image.</p>
    {/if}

    {#if limits.length}
        <div class="mt-5">
            <p class="text-xs font-semibold text-slate-400">What weakens this evidence</p>
            <ul class="mt-2 space-y-1 text-sm text-slate-300">
                {#each limits as f, i (`${f.id}-${i}`)}<li class="flex items-start gap-2"><Icon name="triangle-alert" class="mt-0.5 text-amber-400" /><span>{f.detail}</span></li>{/each}
            </ul>
        </div>
    {/if}

    {#if heatmapUrl}
        <p class="mt-5 text-xs text-slate-400">
            Heat map: warmer colors mark the patches the pixel-level detector scored as more AI-like.
            Use the toggle to view it on the image.
        </p>
    {/if}
    <aside class="mt-5 rounded-xl border border-indigo-500 bg-indigo-900/80 p-4 text-xs leading-5 text-indigo-100">
        <b>What this can and cannot tell you.</b>
        {evidence?.note ??
            "These are detector signals, not verified defects. A highlighted area is where the model looks, not proof of a flaw."}
    </aside>
</article>

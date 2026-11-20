<!--
  "Which AI made it?"  Shows result.attribution (see docs/API.md).
  Built to match the existing result cards (same classes => light mode works through app.css overrides).
-->
<script>
    let { attribution = null, verdict = "inconclusive" } = $props();

    const reasonText = {
        not_ai_generated: "Only shown for images the model judges likely AI-generated.",
        attribution_model_not_installed: "The generator-attribution model is not installed yet. Retrain with the latest training scripts to enable it.",
        features_missing: "Attribution could not run for this image.",
        feature_size_mismatch: "The installed attribution model does not match the detector. Re-export the model bundle.",
        no_candidates: "No generator candidates were returned.",
        not_computed: "Attribution was not computed for this analysis (it may predate the feature).",
    };
    const unknown = $derived(attribution?.decision === "unknown");
</script>

<article class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6">
    <header class="flex items-start justify-between gap-3">
        <div>
            <p class="text-xs font-bold tracking-wider text-indigo-300">LIKELY GENERATOR</p>
            <h2 class="mt-1 text-xl font-bold">
                {#if attribution?.available}{attribution.headline}{:else}Not available{/if}
            </h2>
        </div>
        {#if attribution?.available}
            <span
                class="shrink-0 rounded-full border px-3 py-1 text-xs"
                class:border-emerald-700={attribution.source === "metadata"}
                class:text-emerald-300={attribution.source === "metadata"}
                class:border-indigo-500={attribution.source !== "metadata"}
                class:text-indigo-300={attribution.source !== "metadata"}
            >
                {attribution.source === "metadata" ? "Named in file" : unknown ? "Low confidence" : "Model estimate"}
            </span>
        {/if}
    </header>

    {#if attribution?.available}
        <ul class="mt-5 space-y-3" aria-label="Closest generator families">
            {#each attribution.top as cand, i (cand.family)}
                <li>
                    <div class="flex justify-between text-sm">
                        <span class:font-semibold={i === 0 && !unknown}>{cand.label}</span>
                        <span class="text-slate-400">{cand.percent}%</span>
                    </div>
                    <div class="mt-1 h-2 overflow-hidden rounded-full bg-slate-800">
                        <span
                            class="block h-full rounded-full"
                            class:bg-indigo-500={i === 0 && !unknown}
                            class:bg-slate-600={i > 0 || unknown}
                            style={`width:${Math.max(2, cand.percent)}%`}
                        ></span>
                    </div>
                </li>
            {/each}
        </ul>
        {#if attribution.note}<p class="mt-4 text-sm text-slate-300">{attribution.note}</p>{/if}
    {:else}
        <p class="mt-4 text-sm text-slate-400">
            {verdict === "real" ? reasonText.not_ai_generated : reasonText[attribution?.reason] ?? reasonText.not_computed}
        </p>
    {/if}
    <p class="mt-5 text-xs leading-5 text-slate-500">{attribution?.disclaimer ?? ""}</p>
</article>

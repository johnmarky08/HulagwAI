<!--
  "How the decision was made."  Shows result.components (per-detector scores), result.findings (file metadata /
  provenance), result.warnings (input-quality caveats), result.decision_source and the analysis notice.
  Uses the same card classes as the other result cards so the light theme overrides in app.css apply.
-->
<script>
    let {
        components = {},
        findings = [],
        warnings = [],
        decisionSource = "model",
        confidencePercent = 0,
        notice = null,
    } = $props();

    const detectorLabels = {
        cnn: "Pixel-level texture",
        frequency: "Spectrum / noise pattern",
        clip: "Global look & style",
    };
    const warningText = {
        low_resolution:
            "Very small image: little evidence available, so the verdict is less reliable.",
        upscaled_for_analysis:
            "Smaller than the model's input size: it was enlarged for analysis, which weakens pixel-level evidence.",
        heavily_compressed:
            "Heavy JPEG compression hides fine artefacts and weakens the evidence.",
        animated_first_frame_only:
            "Animated image: only the first frame was analysed.",
        no_ml_model:
            "The detection model is not installed on this server, so this result is based on file metadata only.",
        provenance_declares_ai:
            "The file's embedded provenance data declares that it was AI-generated.",
    };
    const severityLabel = { strong_ai: "Names an AI tool", info: "Info" };

    const detectors = $derived(
        Object.entries(components ?? {})
            .filter(([, c]) => c && typeof c.p === "number")
            .map(([name, c]) => ({
                name,
                label: detectorLabels[name] ?? name.replaceAll("_", " "),
                percent: Math.round(c.p * 100),
            })),
    );
    const sourceLabel = $derived(
        decisionSource === "provenance"
            ? "Embedded provenance metadata"
            : detectors.length
              ? "Detector ensemble"
              : "File metadata only",
    );
</script>

<article class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6">
    <p class="text-xs font-bold tracking-wider text-indigo-300">
        HOW THE DECISION WAS MADE
    </p>
    <div class="mt-3 grid grid-cols-2 gap-4">
        <div class="rounded-xl border border-slate-700 bg-slate-950 p-4">
            <p class="text-xs text-slate-400">Model confidence</p>
            <p class="mt-1 text-2xl font-bold tabular-nums">
                {confidencePercent}%
            </p>
        </div>
        <div class="rounded-xl border border-slate-700 bg-slate-950 p-4">
            <p class="text-xs text-slate-400">Decided by</p>
            <p class="mt-1 text-sm font-semibold">{sourceLabel}</p>
        </div>
    </div>

    <h3 class="mt-6 text-sm font-semibold">Detector scores</h3>
    {#if detectors.length}
        <ul class="mt-3 space-y-3" aria-label="Score from each detector">
            {#each detectors as d (d.name)}
                <li>
                    <div class="flex justify-between text-sm">
                        <span>{d.label}</span>
                        <span class="tabular-nums text-slate-400"
                            >{d.percent}% AI</span
                        >
                    </div>
                    <div
                        class="mt-1 h-2 overflow-hidden rounded-full bg-slate-800"
                    >
                        <span
                            class="block h-full rounded-full"
                            class:bg-rose-500={d.percent >= 65}
                            class:bg-amber-500={d.percent >= 40 &&
                                d.percent < 65}
                            class:bg-emerald-500={d.percent < 40}
                            style={`width:${Math.max(2, d.percent)}%`}
                        ></span>
                    </div>
                </li>
            {/each}
        </ul>
    {:else}
        <p class="mt-2 text-sm text-slate-400">
            No detector models ran for this image. The decision came from the
            file's metadata.
        </p>
    {/if}

    {#if findings.length}
        <h3 class="mt-6 text-sm font-semibold">File & provenance findings</h3>
        <ul class="mt-3 space-y-2">
            {#each findings as f, i (`${f.id}-${i}`)}
                <li class="rounded-xl border border-slate-700 bg-slate-950 p-3">
                    <div class="flex flex-wrap items-center gap-2">
                        <span
                            class="rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase"
                            class:border-rose-700={f.severity === "strong_ai"}
                            class:text-rose-300={f.severity === "strong_ai"}
                            class:border-slate-600={f.severity !== "strong_ai"}
                            class:text-slate-300={f.severity !== "strong_ai"}
                            >{severityLabel[f.severity] ?? f.severity}</span
                        >
                        <span class="text-sm font-semibold">{f.title}</span>
                    </div>
                    {#if f.evidence}<p
                            class="mt-1 wrap-break-word font-mono text-xs text-slate-400"
                        >
                            {f.evidence}
                        </p>{/if}
                </li>
            {/each}
        </ul>
    {/if}

    {#if warnings.length}
        <h3 class="mt-6 text-sm font-semibold">Quality warnings</h3>
        <ul class="mt-2 space-y-1 text-sm text-amber-300">
            {#each warnings as w, i (`${w}-${i}`)}
                <li>⚠ {warningText[w] ?? w.replaceAll("_", " ")}</li>
            {/each}
        </ul>
    {/if}

    {#if notice?.intended_use}
        <details
            class="mt-6 rounded-xl border border-indigo-500 bg-indigo-900/80 p-4 text-xs leading-5 text-indigo-100"
        >
            <summary class="font-semibold">Intended use & limitations</summary>
            <p class="mt-2">{notice.intended_use}</p>
            {#if notice.limitations?.length}
                <ul class="mt-2 list-disc pl-5">
                    {#each notice.limitations as l, i (i)}<li>{l}</li>{/each}
                </ul>
            {/if}
        </details>
    {/if}
</article>

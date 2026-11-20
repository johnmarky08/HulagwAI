<script>
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import {
        ui,
        removeFile,
        startAnalysis,
        cancelAnalysis,
        handleFileInput,
        handleFileDrop,
        allowDrop,
        clearError,
        toggleHeatmap,
    } from "../official/controller.svelte.js";
    import GeneratorCard from "./Components/Results/GeneratorCard.svelte";
    import EvidenceCard from "./Components/Results/EvidenceCard.svelte";
    import DetailsCard from "./Components/Results/DetailsCard.svelte";
    import { onMount } from "svelte";
    import { model } from "../api/model";
    import { session } from "../api/session.svelte.js";

    // Warn before uploading when the analysis service or model is offline (GET /api/v1/health).
    let service = $state(null);
    onMount(async () => {
        try {
            service = (await model.health()).ml;
        } catch {
            service = null;
        }
    });
    const serviceWarning = $derived(
        !service
            ? ""
            : service.status === "unreachable" || service.status === "error"
              ? "The analysis service is currently unavailable, so new analyses may fail. Please try again shortly."
              : service.model_loaded === false
                ? service.metadata_only
                    ? "The detection model is not installed on this server yet. Results will rely on file metadata only."
                    : "The detection model is not installed on this server yet, so analyses cannot run right now."
                : "",
    );

    const verdictTone = {
        ai: {
            pill: "border-rose-700 bg-rose-950/50 text-rose-300",
            bar: "bg-rose-500",
        },
        real: {
            pill: "border-emerald-700 bg-emerald-950 text-emerald-300",
            bar: "bg-emerald-500",
        },
        inconclusive: {
            pill: "border-amber-700 bg-amber-950/30 text-amber-300",
            bar: "bg-amber-500",
        },
    };
    const tone = $derived(verdictTone[ui.verdictClass] ?? verdictTone.ai);
</script>

<svelte:head><title>HulagwAI · Image Detection</title></svelte:head>

<Layout active="detect">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-1240px px-5 pb-16">
        <div class="scroll-reveal mx-auto mb-8 mt-10 max-w-3xl text-center">
            <h1
                class="bg-linear-to-r from-violet-200 to-indigo-500 bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl"
            >
                {ui.phase === "results"
                    ? "Analysis Result"
                    : ui.phase === "analyzing"
                      ? "Analyzing your image"
                      : "Start detecting"}
            </h1>
            <p class="mt-3 text-sm text-slate-400">
                {ui.phase === "upload"
                    ? "Upload an image to get a prediction of whether it is likely AI-generated or real."
                    : "Looking for patterns, artifacts, and signs of AI generation."}
            </p>
        </div>

        <div
            class="mx-auto mb-12 flex max-w-3xl items-center justify-center gap-2 sm:gap-5"
        >
            {#each ["Upload", "Analyze", "Results"] as label, index}
                <div
                    class="flex min-w-0 items-center justify-center gap-2 rounded-xl px-3 py-3 text-xs font-semibold  sm:min-w-40 sm:gap-3 sm:text-base"
                    class:bg-indigo-800={index ===
                        (ui.phase === "upload"
                            ? 0
                            : ui.phase === "analyzing"
                              ? 1
                              : 2)}
                    class:text-white={index ===
                        (ui.phase === "upload"
                            ? 0
                            : ui.phase === "analyzing"
                              ? 1
                              : 2)}
                    class:shadow-lg={index ===
                        (ui.phase === "upload"
                            ? 0
                            : ui.phase === "analyzing"
                              ? 1
                              : 2)}
                >
                    <span
                        class="grid size-7 shrink-0 place-items-center rounded-full bg-slate-400 text-slate-900"
                        >{index + 1}</span
                    >

                    <span 
                        >{label}</span
                    >
                </div>
                {#if index < 2}<span class="h-px w-5 bg-indigo-500 sm:w-14"
                    ></span>{/if}
            {/each}
        </div>

        {#if serviceWarning && ui.phase === "upload"}
            <p
                class="mb-6 rounded-xl border border-amber-700 bg-amber-950/30 p-4 text-sm text-amber-300"
                role="status"
            >
                ⚠ &nbsp;{serviceWarning}
            </p>
        {/if}

        {#if ui.error}
            <section
                class="flex min-h-480px flex-col items-center justify-center rounded-2xl border border-red-500 bg-rose-400 px-6 py-12 text-center text-white"
            >
                <span
                    class="mb-3 grid size-16 place-items-center rounded-2xl bg-red-500 text-4xl shadow-lg shadow-red-600/40"
                    >×</span
                >
                <h2 class="text-3xl font-extrabold">{ui.errorTitle}</h2>
                <p class="mb-5 mt-2 max-w-lg text-sm text-red-700">
                    {ui.error}
                </p>
                <button
                    class="rounded-xl bg-linear-to-br from-indigo-500 to-indigo-700 px-8 py-4 font-semibold text-white"
                    onclick={clearError}>↑ &nbsp; Try Again</button
                >
                <div class="mt-5 flex gap-1 text-[10px] text-slate-400">
                    <span class="rounded bg-slate-800 px-2 py-1">JPG</span><span
                        class="rounded bg-slate-800 px-2 py-1">JPEG</span
                    ><span class="rounded bg-slate-800 px-2 py-1">PNG</span
                    ><span class="rounded bg-slate-800 px-2 py-1">WEBP</span
                    ><span class="rounded bg-slate-800 px-2 py-1">Max 5 MB</span
                    >
                </div>
            </section>
        {:else if ui.phase === "upload" && !ui.file}
            <label
                class="upload-dropzone scroll-reveal flex min-h-420px cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-indigo-500 bg-indigo-950/40 px-6 py-12 text-center transition hover:bg-indigo-950/70 sm:min-h-590px"
                ondragover={allowDrop}
                ondrop={handleFileDrop}
            >
                <input
                    class="sr-only"
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp"
                    onchange={handleFileInput}
                />
                <span
                    class="mb-4 grid size-16 place-items-center rounded-2xl bg-linear-to-br from-indigo-400 to-indigo-700 text-4xl text-white shadow-lg shadow-indigo-500/40"
                    >⇧</span
                ><strong class="text-2xl font-bold sm:text-3xl"
                    >Drag and drop an image here</strong
                ><span class="mt-2 text-sm text-slate-500"
                    >or paste one from your clipboard</span
                ><span
                    class="mt-5 inline-flex rounded-xl bg-linear-to-br from-indigo-500 to-indigo-700 px-8 py-4 font-semibold text-white"
                    >⇧ &nbsp; Upload Image</span
                ><span class="mt-5 flex gap-1 text-[9px] text-slate-400"
                    ><i
                        class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >JPG</i
                    ><i
                        class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >JPEG</i
                    ><i
                        class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >PNG</i
                    ><i
                        class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >WEBP</i
                    ><i
                        class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >Max 5 MB</i
                    ></span
                >
            </label>
            {#if session.value?.notice?.privacy}
                <p
                    class="mx-auto mt-4 max-w-3xl text-center text-xs leading-5 text-slate-400"
                >
                    <b class="text-slate-300">Privacy.</b>
                    {session.value.notice.privacy}
                </p>
            {/if}
        {:else if ui.phase === "upload" && ui.file}
            <section
                class="upload-selected scroll-reveal rounded-2xl border border-indigo-500 bg-indigo-950/40 p-4 shadow-xl shadow-indigo-950/40 sm:p-6"
            >
                <img
                    class="upload-preview max-h-440px w-full rounded-xl bg-slate-950 object-contain"
                    src={ui.preview}
                    alt="Selected upload preview"
                />
                <div
                    class="upload-meta flex flex-wrap items-center gap-5 py-5 text-sm text-slate-300"
                >
                    <span class="font-medium text-white">{ui.file.name}</span
                    ><span
                        >{ui.file.type.split("/").at(-1)?.toUpperCase()} · {(
                            ui.file.size / 1048576
                        ).toFixed(2)} MB</span
                    ><span
                        class="rounded bg-emerald-100 px-4 py-1 text-emerald-700"
                        >Ready to analyze</span
                    >
                </div>
                <div class="flex flex-wrap gap-3">
                    <button
                        class="rounded-xl border border-indigo-500 bg-indigo-700 px-5 py-3 font-semibold text-white"
                        onclick={startAnalysis}>⌗ &nbsp; Image Detection</button
                    ><label
                        class="cursor-pointer rounded-xl border border-indigo-500 bg-slate-800 px-5 py-3 font-semibold text-white"
                        >⟳ &nbsp; Replace Image<input
                            class="sr-only"
                            type="file"
                            accept=".jpg,.jpeg,.png,.webp"
                            onchange={handleFileInput}
                        /></label
                    ><button
                        class="rounded-xl border border-red-500 bg-rose-950 px-5 py-3 font-semibold text-white"
                        onclick={removeFile}>▤ &nbsp; Remove</button
                    >
                </div>
            </section>
        {:else if ui.phase === "analyzing"}
            <section class="grid gap-6 lg:grid-cols-2">
                <article
                    class="rounded-2xl border border-indigo-500/50 bg-slate-900 p-4"
                >
                    <div
                        class="scan-image-frame relative isolate mx-auto w-full overflow-hidden rounded-xl sm:w-fit"
                        class:scan-frame-dark={!ui.light}
                        class:scan-frame-light={ui.light}
                    >
                        {#if ui.preview || ui.resultPreview}
                            <img
                                class="scan-image block h-auto w-full rounded-xl object-contain sm:w-auto sm:max-w-full"
                                class:scan-image-dark={!ui.light}
                                class:scan-image-light={ui.light}
                                src={ui.preview || ui.resultPreview}
                                alt="Authenticity scan in progress"
                            />
                        {:else}
                            <div
                                class="scan-placeholder grid w-full place-items-center rounded-xl bg-slate-950 text-5xl text-indigo-400 sm:w-96"
                                aria-label={ui.loadingResult
                                    ? "Loading the saved analysis"
                                    : "Image preview unavailable"}
                            >
                                ▧
                            </div>
                        {/if}
                        <div
                            class="scan-image-tint pointer-events-none absolute inset-0"
                            class:scan-tint-dark={!ui.light}
                            class:scan-tint-light={ui.light}
                            aria-hidden="true"
                        ></div>
                        <span
                            class="scan-beam pointer-events-none absolute inset-x-0 top-0"
                            class:scan-beam-dark={!ui.light}
                            class:scan-beam-light={ui.light}
                            aria-hidden="true"
                        ></span>
                    </div>
                    <div class="mt-5 flex justify-between text-sm">
                        <span>{ui.file?.name}</span><span class="text-slate-400"
                            >{ui.file?.type.split("/").at(-1)?.toUpperCase()} · {(
                                (ui.file?.size ?? 0) / 1048576
                            ).toFixed(2)} MB</span
                        >
                    </div>
                    <p class="mt-4 text-sm text-slate-400">
                        Your image stays in place while we inspect it.
                    </p>
                </article>
                <article
                    class="rounded-2xl border border-indigo-500/50 bg-slate-900 p-6"
                >
                    <span
                        class="text-xs font-bold tracking-wide text-indigo-400"
                        >ANALYSIS IN PROGRESS</span
                    >
                    <h2 class="mt-3 text-3xl font-bold">Finding the details</h2>
                    <p class="mt-3 text-sm text-slate-400">
                        Checking visual patterns that may indicate synthetic
                        content.
                    </p>
                    <div class="mt-12 flex items-center justify-between">
                        <strong class="text-4xl">{ui.progress}%</strong><span
                            class="text-xs text-slate-400">Image analysis</span
                        >
                    </div>
                    <div
                        class="my-5 h-2 overflow-hidden rounded-full bg-slate-800"
                    >
                        <span
                            class="progress-meter block h-full rounded-full bg-indigo-500 transition-all"
                            style={`width:${ui.progress}%`}
                        ></span>
                    </div>
                    <ul class="space-y-4 text-sm">
                        {#each ui.steps as step}<li
                                class="flex justify-between"
                                class:text-emerald-400={step.state ===
                                    "complete"}
                                class:text-indigo-400={step.state ===
                                    "in_progress"}
                            >
                                <span
                                    >{step.state === "complete"
                                        ? "✓"
                                        : step.state === "in_progress"
                                          ? "◉"
                                          : "○"} &nbsp; {step.label}</span
                                ><span class="text-slate-400"
                                    >{step.state.replaceAll("_", " ")}</span
                                >
                            </li>{/each}
                    </ul>
                    <p class="mt-10 text-xs text-slate-400">
                        This usually takes a few seconds. Please keep this page
                        open.
                    </p>
                </article>
            </section>
            <p class="mt-4 text-sm text-slate-400">
                No action needed — your result will appear when analysis is
                complete.
            </p>
            <button
                class="mt-4 rounded-xl border border-red-500 bg-rose-950 px-6 py-3 text-white"
                onclick={cancelAnalysis}>Cancel Analysis</button
            >
        {:else}
            <section class="grid items-start gap-6 lg:grid-cols-2">
                <article
                    class="rounded-2xl border border-indigo-500/40 bg-slate-950 p-3"
                >
                    <div class="relative">
                        <img
                            class="result-image mx-auto block h-auto w-full rounded-xl object-contain sm:w-auto sm:max-w-full"
                            src={ui.showHeatmap && ui.heatmapUrl
                                ? ui.heatmapUrl
                                : ui.resultPreview || ui.preview}
                            alt={ui.showHeatmap
                                ? "Detector heat map over the analysed image"
                                : "Analysis result"}
                        />
                        {#if ui.showHeatmap}<span
                                class="absolute left-3 top-3 rounded-full bg-slate-950/70 px-3 py-1 text-xs text-slate-100"
                                >Heat map</span
                            >{/if}
                    </div>
                    <dl class="grid grid-cols-2 gap-4 px-5 py-6 text-sm">
                        <dt class="text-slate-400">File analyzed</dt>
                        <dd>{ui.displayTitle}</dd>
                        <dt class="text-slate-400">Format</dt>
                        <dd>{ui.displayFormat}</dd>
                        <dt class="text-slate-400">File size</dt>
                        <dd>{ui.displaySize} MB</dd>
                        {#if ui.dimensions}
                            <dt class="text-slate-400">Dimensions</dt>
                            <dd>{ui.dimensions}</dd>
                        {/if}
                        <dt class="text-slate-400">Analyzed on</dt>
                        <dd>{ui.analyzedDate}</dd>
                    </dl>
                </article>
                <article
                    class="flex flex-col items-center rounded-2xl border border-indigo-500/40 bg-slate-900 p-6 text-center"
                >
                    <span class="text-xs font-bold text-emerald-400"
                        >✓ ANALYSIS COMPLETE</span
                    ><span
                        class={`mt-4 rounded-full border px-6 py-2 text-sm ${tone.pill}`}
                        >{ui.verdictLabel}</span
                    ><strong class="mt-5 text-6xl font-extrabold"
                        >{ui.aiPercent}%</strong
                    ><span class="mt-1 text-sm text-slate-400"
                        >Estimated AI likelihood · {ui.confidencePercent}%
                        confidence</span
                    >
                    <div
                        class="my-6 h-2 w-full overflow-hidden rounded-full bg-slate-800"
                    >
                        <span
                            class={`block h-full rounded-full ${tone.bar}`}
                            style={`width:${ui.aiPercent}%`}
                        ></span>
                    </div>
                    <div class="flex w-full justify-between text-sm">
                        <span class="text-rose-400"
                            >AI-generated {ui.aiPercent}%</span
                        ><span class="text-emerald-400"
                            >Real {ui.realPercent}%</span
                        >
                    </div>
                    <p class="mt-4 text-sm text-slate-400">{ui.explanation}</p>
                    <aside
                        class="mt-5 rounded-xl border border-indigo-500 bg-indigo-900/80 p-5 text-left text-xs leading-5 text-indigo-100"
                    >
                        <b>How to read this score.</b>
                        {ui.howToRead}
                    </aside>
                    {#if ui.duplicate}
                        <p
                            class="mt-5 w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-left text-xs text-slate-300"
                            role="status"
                        >
                            You analyzed this exact image before, so the saved
                            result is shown instead of running it again.
                        </p>
                    {/if}
                    <p class="mt-6 self-start text-xs text-slate-400">
                        {ui.persisted
                            ? "Saved to your analysis history"
                            : "Kept in this browser session only"}
                    </p>
                    <div
                        class="mt-4 flex w-full flex-wrap justify-center gap-3"
                    >
                        <button
                            type="button"
                            class="rounded-xl border border-indigo-500 bg-indigo-800 px-4 py-3 text-sm font-semibold text-white"
                            onclick={removeFile}
                            >↑ &nbsp; Analyze another</button
                        ><a
                            use:inertia
                            class="rounded-xl border border-indigo-500 px-4 py-3 text-sm text-indigo-300"
                            href="/history">View history</a
                        >{#if ui.reportUrl}<a
                                class="rounded-xl border border-indigo-500 px-4 py-3 text-sm text-indigo-300"
                                href={ui.reportUrl}
                                download>↓ &nbsp;Download report (PDF)</a
                            >{/if}
                    </div>
                </article>
            </section>
            {#if ui.result}
                <section
                    class="mt-6 grid items-start gap-6 lg:grid-cols-2"
                    aria-label="Generator and evidence"
                >
                    <GeneratorCard
                        attribution={ui.attribution}
                        verdict={ui.result?.verdict}
                    />
                    <EvidenceCard
                        evidence={ui.evidence}
                        heatmapUrl={ui.heatmapUrl}
                        showHeatmap={ui.showHeatmap}
                        onToggleHeatmap={toggleHeatmap}
                    />
                </section>
                <section class="mt-6" aria-label="How the decision was made">
                    <DetailsCard
                        components={ui.components}
                        findings={ui.findings}
                        warnings={ui.warnings}
                        decisionSource={ui.decisionSource}
                        confidencePercent={ui.confidencePercent}
                        notice={ui.notice}
                    />
                </section>
                <p class="mt-4 text-center text-xs text-slate-400">
                    Curious how accurate this is?
                    <a use:inertia class="text-indigo-300 underline" href="/evaluation"
                        >See the model evaluation</a
                    >.
                </p>
            {/if}
        {/if}
    </main>
</Layout>

<style>
    .upload-selected {
        width: min(100%, 960px);
        margin-inline: auto;
    }

    .upload-selected .upload-preview {
        width: min(100%, 820px);
        max-height: min(38vh, 340px);
        margin-inline: auto;
    }

    /* The image sets the size (capped by max-height); the frame and overlays shrink to match it. */
    .scan-image {
        max-height: min(38vh, 300px);
    }
    .scan-placeholder {
        height: min(38vh, 260px);
    }

    @media (min-width: 1024px) {
        .scan-image {
            max-height: clamp(200px, 32vh, 260px);
        }
    }

    /* Phones: full width, height follows the image. Larger screens: sized by height. */
    .result-image {
        max-height: min(34vh, 260px);
    }
    @media (min-width: 640px) {
        .result-image {
            max-height: min(26vh, 200px);
        }
    }

    .scan-image-dark {
        filter: saturate(1.48) contrast(1.14) hue-rotate(16deg) brightness(1.04);
    }

    .scan-image-light {
        filter: saturate(1.42) sepia(0.16) hue-rotate(322deg) brightness(1.06)
            contrast(1.06);
    }

    .scan-frame-dark {
        box-shadow:
            inset 0 0 0 2px rgb(129 140 248 / 55%),
            0 0 30px rgb(99 102 241 / 30%);
    }

    .scan-frame-light {
        box-shadow:
            inset 0 0 0 2px rgb(217 119 6 / 55%),
            0 0 30px rgb(244 114 182 / 24%);
    }

    .scan-tint-dark {
        background: linear-gradient(
            180deg,
            rgb(79 70 229 / 24%),
            rgb(34 211 238 / 12%) 52%,
            rgb(79 70 229 / 22%)
        );
    }

    .scan-tint-light {
        background: linear-gradient(
            180deg,
            rgb(251 191 36 / 22%),
            rgb(244 114 182 / 12%) 52%,
            rgb(251 191 36 / 22%)
        );
    }

    .scan-beam {
        z-index: 2;
        height: 4px;
        animation: scan-image-back-and-forth 2s ease-in-out infinite alternate;
    }

    .scan-beam-dark {
        background: linear-gradient(
            90deg,
            transparent 0%,
            #a5b4fc 12%,
            #67e8f9 50%,
            #a5b4fc 88%,
            transparent 100%
        );
        box-shadow:
            0 0 12px 4px rgb(103 232 249 / 85%),
            0 0 38px 12px rgb(99 102 241 / 55%);
    }

    .scan-beam-light {
        background: linear-gradient(
            90deg,
            transparent 0%,
            #f59e0b 12%,
            #f43f5e 50%,
            #f59e0b 88%,
            transparent 100%
        );
        box-shadow:
            0 0 12px 4px rgb(251 191 36 / 90%),
            0 0 38px 12px rgb(244 114 182 / 50%);
    }

    @keyframes scan-image-back-and-forth {
        from {
            top: 0;
        }
        to {
            top: calc(100% - 4px);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .scan-beam {
            top: 50%;
            animation: none;
        }
    }
</style>

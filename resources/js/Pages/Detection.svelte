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
    } from "../official/controller.svelte.js";
</script>

<svelte:head><title>HulagwAI · Image Detection</title></svelte:head>

<Layout active="detect">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-[1240px] px-5 pb-16">
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
                    class="flex min-w-0 items-center justify-center gap-2 rounded-xl px-3 py-3 text-xs font-semibold text-slate-400 sm:min-w-40 sm:gap-3 sm:text-base"
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
                    >{label}
                </div>
                {#if index < 2}<span class="h-px w-5 bg-indigo-500 sm:w-14"
                    ></span>{/if}
            {/each}
        </div>

        {#if ui.error}
            <section
                class="flex min-h-[480px] flex-col items-center justify-center rounded-2xl border border-red-500 bg-rose-400 px-6 py-12 text-center text-white"
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
                class="upload-dropzone scroll-reveal flex min-h-[420px] cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-indigo-500 bg-indigo-950/40 px-6 py-12 text-center transition hover:bg-indigo-950/70 sm:min-h-[590px]"
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
                    ><i class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic">JPG</i
                    ><i class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >JPEG</i
                    ><i class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic">PNG</i
                    ><i class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >WEBP</i
                    ><i class="upload-chip rounded bg-slate-800 px-2 py-1 not-italic"
                        >Max 5 MB</i
                    ></span
                >
            </label>
        {:else if ui.phase === "upload" && ui.file}
            <section
                class="upload-selected scroll-reveal rounded-2xl border border-indigo-500 bg-indigo-950/40 p-4 shadow-xl shadow-indigo-950/40 sm:p-6"
            >
                <img
                    class="upload-preview max-h-[440px] w-full rounded-xl bg-slate-950 object-contain"
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
                        >Uploaded</span
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
                    <img
                        class="h-[300px] w-full rounded-xl object-cover"
                        src={ui.preview || ui.resultPreview}
                        alt="Analysis in progress"
                    />
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
                    <img
                        class="h-280px w-full rounded-xl object-cover"
                        src={ui.resultPreview || ui.preview}
                        alt="Analysis result"
                    />
                    <dl class="grid grid-cols-2 gap-4 px-5 py-6 text-sm">
                        <dt class="text-slate-400">File analyzed</dt>
                        <dd>{ui.displayTitle}</dd>
                        <dt class="text-slate-400">Format</dt>
                        <dd>{ui.displayFormat}</dd>
                        <dt class="text-slate-400">File size</dt>
                        <dd>{ui.displaySize} MB</dd>
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
                        class="mt-4 rounded-full border border-rose-700 bg-rose-950/50 px-6 py-2 text-sm text-rose-300"
                        >{ui.verdictLabel}</span
                    ><strong class="mt-5 text-6xl font-extrabold"
                        >{ui.aiPercent}%</strong
                    ><span class="mt-1 text-sm text-slate-400"
                        >Estimated AI likelihood</span
                    >
                    <div
                        class="my-6 h-2 w-full overflow-hidden rounded-full bg-slate-800"
                    >
                        <span
                            class="block h-full rounded-full bg-rose-500"
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
                    <p class="mt-6 self-start text-xs text-slate-400">
                        {ui.persisted
                            ? "Saved to your analysis history"
                            : "Kept in this browser session only"}
                    </p>
                    <div
                        class="mt-4 flex w-full flex-wrap justify-center gap-3"
                    >
                        <button
                            class="rounded-xl border border-indigo-500 bg-indigo-800 px-4 py-3 text-sm font-semibold"
                            onclick={removeFile}
                            >↑ &nbsp; Analyze another</button
                        ><a
                            use:inertia
                            class="rounded-xl border border-indigo-500 px-4 py-3 text-sm text-indigo-300"
                            href="/history">View history</a
                        ><a
                            class="rounded-xl border border-indigo-500 px-4 py-3 text-sm text-indigo-300"
                            href={ui.reportUrl}>Download report</a
                        >
                    </div>
                </article>
            </section>
        {/if}
    </main>
</Layout>

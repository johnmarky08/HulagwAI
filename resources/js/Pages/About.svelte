<!-- About HulagwAI. Live data: GET /api/v1/model/evaluation (model summary + notices shared by every frontend). -->
<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import { model } from "../api/model";

    let data = $state(null);
    let failed = $state(false);
    onMount(async () => {
        try {
            data = await model.evaluation();
        } catch {
            failed = true;
        }
    });

    const notice = $derived(data?.notice ?? null);
    const test = $derived(data?.evaluated ? data.metrics?.test : null);
    const pct = (v) => (v == null ? "–" : (v * 100).toFixed(1) + "%");
    const num = (v) => (v == null ? "–" : Number(v).toFixed(3));

    const features = [
        {
            icon: "⌗",
            title: "Real vs. AI prediction",
            text: "Each image gets a verdict (likely real, likely AI-generated, or inconclusive), an AI-likelihood score and a confidence level.",
        },
        {
            icon: "⬡",
            title: "Likely generator",
            text: "For images judged AI-generated, the model estimates which family of generator made it, or answers “unknown” when unsure.",
        },
        {
            icon: "▦",
            title: "Evidence & heat map",
            text: "Detector signals, file provenance findings and a heat map of where the pixel-level detector reacts most strongly.",
        },
        {
            icon: "◷",
            title: "History & reports",
            text: "Signed-in users can search, filter, export and delete past analyses, and download a PDF report for any result.",
        },
    ];

    const pipeline = [
        {
            n: "01",
            title: "Check the file",
            text: "The upload is validated (type, size, dimensions) and re-encoded so only clean pixel data reaches the model.",
        },
        {
            n: "02",
            title: "Read the provenance",
            text: "Embedded metadata such as C2PA Content Credentials, EXIF and generator parameters is inspected for declared AI tools.",
        },
        {
            n: "03",
            title: "Run the detectors",
            text: "Independent detectors look at pixel texture, the frequency / noise spectrum and the image's overall look and style.",
        },
        {
            n: "04",
            title: "Fuse and decide",
            text: "Detector scores are combined into one calibrated probability; weak or conflicting evidence becomes “Inconclusive”.",
        },
    ];
</script>

<svelte:head>
    <title>HulagwAI · About</title>
    <meta
        name="description"
        content="What HulagwAI does, how it reaches a verdict, and how to use it responsibly."
    />
</svelte:head>

<Layout active="about">
    <main class="mx-auto min-h-[calc(100vh-80px)] max-w-1240px px-5 pb-16">
        <div class="scroll-reveal mx-auto mb-10 mt-10 max-w-3xl text-center">
            <h1
                class="bg-linear-to-r from-violet-200 to-indigo-500 bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl"
            >
                About HulagwAI
            </h1>
            <p class="mt-3 text-sm leading-6 text-slate-400">
                HulagwAI estimates whether an image is AI-generated or captured
                from a real-world source, and explains why, so people can make a
                more informed judgement about what they see online.
            </p>
        </div>

        <section
            class="scroll-reveal mb-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            aria-label="Features"
        >
            {#each features as feature (feature.title)}
                <article
                    class="rounded-2xl border border-indigo-500/50 bg-slate-950/70 p-5 text-center"
                >
                    <span
                        class="mx-auto grid size-11 place-items-center rounded-xl bg-indigo-500 text-xl text-white"
                        aria-hidden="true">{feature.icon}</span
                    >
                    <h2 class="mt-4 text-sm font-semibold">{feature.title}</h2>
                    <p class="mt-2 text-xs leading-5 text-slate-400">
                        {feature.text}
                    </p>
                </article>
            {/each}
        </section>

        <section class="scroll-reveal mb-10" aria-labelledby="pipeline-heading">
            <h2
                id="pipeline-heading"
                class="mb-6 text-center text-3xl font-extrabold tracking-tight text-indigo-400"
            >
                How a verdict is reached
            </h2>
            <ol class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {#each pipeline as step (step.n)}
                    <li
                        class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6"
                    >
                        <span class="text-xs font-bold text-indigo-400"
                            >STEP {step.n}</span
                        >
                        <h3 class="mt-2 font-semibold">{step.title}</h3>
                        <p class="mt-2 text-sm leading-6 text-slate-400">
                            {step.text}
                        </p>
                    </li>
                {/each}
            </ol>
        </section>

        <section class="mb-10 grid gap-6 lg:grid-cols-2">
            <article
                class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6"
                aria-labelledby="model-heading"
            >
                <h2 id="model-heading" class="text-xl font-bold">
                    The model at a glance
                </h2>
                {#if test}
                    <p class="mt-1 text-xs text-slate-400">
                        {data.model.name} v{data.model.version} · held-out test set
                        of {test.n?.toLocaleString() ?? "–"} images
                    </p>
                    <div class="mt-5 grid grid-cols-2 gap-4">
                        {#each [["Accuracy", pct(test.accuracy)], ["F1 score", num(test.f1)], ["ROC-AUC", num(test.roc_auc)], ["Recall", pct(test.recall)]] as [label, value] (label)}
                            <div
                                class="rounded-xl border border-slate-700 bg-slate-950 p-4"
                            >
                                <p class="text-xs text-slate-400">{label}</p>
                                <p class="mt-1 text-2xl font-bold tabular-nums">
                                    {value}
                                </p>
                            </div>
                        {/each}
                    </div>
                {:else if data && !data.evaluated}
                    <p class="mt-3 text-sm text-amber-300">{data.message}</p>
                {:else if failed}
                    <p class="mt-3 text-sm text-slate-400">
                        Model details could not be loaded right now.
                    </p>
                {:else}
                    <p class="mt-3 text-sm text-slate-400">
                        Loading model details…
                    </p>
                {/if}
                <a
                    use:inertia
                    class="mt-5 inline-flex rounded-xl border border-indigo-500 px-4 py-3 text-sm text-indigo-300"
                    href="/evaluation">See the full evaluation ›</a
                >
            </article>

            <article
                class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6"
                aria-labelledby="use-heading"
            >
                <h2 id="use-heading" class="text-xl font-bold">
                    Intended use
                </h2>
                <p class="mt-3 text-sm leading-6 text-slate-300">
                    {notice?.intended_use ??
                        "HulagwAI is an educational decision-support tool that gives a second opinion. It is not proof and must not be the only basis for judging anyone."}
                </p>
                {#if notice?.responsible_use?.length}
                    <h3 class="mt-5 text-sm font-semibold">Use it responsibly</h3>
                    <ul
                        class="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-400"
                    >
                        {#each notice.responsible_use as item (item)}<li>
                                {item}
                            </li>{/each}
                    </ul>
                {/if}
            </article>
        </section>

        <section class="mb-10 grid gap-6 lg:grid-cols-2">
            <aside
                class="rounded-xl border border-indigo-500 bg-indigo-900/80 p-5 text-sm leading-6 text-indigo-100"
                aria-labelledby="limits-heading"
            >
                <h2 id="limits-heading" class="font-bold">Limitations</h2>
                {#if notice?.limitations?.length}
                    <ul class="mt-2 list-disc pl-5">
                        {#each notice.limitations as item (item)}<li>
                                {item}
                            </li>{/each}
                    </ul>
                {:else}
                    <p class="mt-2">
                        Detection is probabilistic and can be wrong. Compression,
                        editing and new image generators may affect reliability.
                    </p>
                {/if}
            </aside>
            <aside
                class="rounded-xl border border-indigo-500 bg-indigo-900/80 p-5 text-sm leading-6 text-indigo-100"
                aria-labelledby="privacy-heading"
            >
                <h2 id="privacy-heading" class="font-bold">Privacy</h2>
                <p class="mt-2">
                    {notice?.privacy ??
                        "Guests' images are deleted right after analysis; signed-in users' images are stored encrypted until they delete them."}
                </p>
            </aside>
        </section>

        <section
            class="rounded-2xl border border-indigo-500/50 bg-indigo-950/70 p-6 text-center md:p-8"
        >
            <h2 class="text-2xl font-extrabold">Ready to check an image?</h2>
            <p class="mt-2 text-sm text-slate-300">
                Upload a JPG, PNG or WEBP up to 5 MB, or install the browser
                extension to scan images on the web.
            </p>
            <div class="mt-5 flex flex-wrap justify-center gap-3">
                <a
                    use:inertia
                    class="rounded-xl border border-indigo-400 bg-indigo-700 px-5 py-3 text-sm font-semibold text-white"
                    href="/detect">Analyze an image</a
                >
                <a
                    use:inertia
                    class="rounded-xl border border-indigo-500 px-5 py-3 text-sm text-indigo-300"
                    href="/extension">Get the extension</a
                >
            </div>
        </section>
    </main>
</Layout>

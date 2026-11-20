<!-- Model evaluation (CSST 102: present evaluation results in the app). Data: GET /api/v1/model/evaluation -->
<script>
    import { onMount } from "svelte";
    import Layout from "./Components/Layout.svelte";
    import { model } from "../api/model";
    import { errorMessage } from "../api/client";

    let data = $state(null);
    let error = $state("");
    onMount(async () => {
        try {
            data = await model.evaluation();
        } catch (e) {
            error = errorMessage(e);
        }
    });

    // Undefined ratios (e.g. precision with no positives) arrive as null/NaN: show a dash instead of "NaN%".
    const ok = (v) => v != null && Number.isFinite(Number(v));
    const pct = (v, d = 1) =>
        ok(v) ? (Number(v) * 100).toFixed(d) + "%" : "–";
    const num = (v, d = 4) => (ok(v) ? Number(v).toFixed(d) : "–");
    const roc = (r) =>
        (r?.fpr ?? [])
            .map(
                (x, i) =>
                    `${(x * 200).toFixed(1)},${(200 - (r.tpr?.[i] ?? 0) * 200).toFixed(1)}`,
            )
            .join(" ");
    const date = (v) => (v ? new Date(v).toLocaleDateString() : "date unknown");
    const card = "rounded-2xl border border-indigo-500/40 bg-slate-900 p-6";
</script>

<svelte:head><title>HulagwAI · Model evaluation</title></svelte:head>

<Layout active="evaluation">
    <main class="mx-auto max-w-1240px px-5 pb-16">
        <div class="mx-auto mb-8 mt-10 max-w-3xl text-center">
            <h1
                class="bg-linear-to-r from-violet-200 to-indigo-500 bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl"
            >
                Model evaluation
            </h1>
            <p class="mt-3 text-sm text-slate-400">
                How well the detector and the generator-attribution model did on
                images they never saw during training.
            </p>
        </div>

        {#if error}<p
                class="rounded-xl border border-red-500 bg-rose-950 p-4 text-rose-300"
            >
                {error}
            </p>{/if}
        {#if !data && !error}<p
                class="py-16 text-center text-sm text-slate-400"
            >
                Loading evaluation…
            </p>{/if}

        {#if data && !data.evaluated}
            <p class={`${card} text-amber-300`}>{data.message}</p>
        {:else if data && !data.metrics?.test}
            <p class={`${card} text-amber-300`}>
                The installed model has no held-out test results yet. Re-run the
                evaluation step and reinstall the model bundle.
            </p>
        {:else if data}
            {@const m = data.metrics}
            {@const t = m.test}
            <p class="mb-6 text-center text-xs text-slate-400">
                {data.model.name} v{data.model.version} · evaluated {date(
                    data.model.evaluated_at,
                )} · held-out test set of {t.n?.toLocaleString() ?? "–"} images
            </p>

            <aside
                class="mb-6 rounded-xl border border-indigo-500 bg-indigo-900/80 p-5 text-sm leading-6 text-indigo-100"
            >
                <b>Intended use.</b>
                {data.notice?.intended_use}
                <ul class="mt-2 list-disc pl-5">
                    {#each data.notice?.limitations ?? [] as l}<li>
                            {l}
                        </li>{/each}
                </ul>
                {#if data.notice?.responsible_use?.length}
                    <p class="mt-3"><b>Responsible use.</b></p>
                    <ul class="mt-1 list-disc pl-5">
                        {#each data.notice.responsible_use as r}<li>
                                {r}
                            </li>{/each}
                    </ul>
                {/if}
            </aside>

            <section class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                {#each [["Accuracy", pct(t.accuracy, 2)], ["Precision", pct(t.precision, 2)], ["Recall", pct(t.recall, 2)], ["Specificity", pct(t.specificity, 2)], ["F1", num(t.f1)], ["ROC-AUC", num(t.roc_auc)], ["MAE", num(t.mae)], ["RMSE", num(t.rmse)]] as [k, v]}
                    <div
                        class="rounded-2xl border border-slate-700 bg-slate-900 p-5"
                    >
                        <p class="text-sm text-slate-400">{k}</p>
                        <p class="mt-2 text-3xl font-extrabold">{v}</p>
                    </div>
                {/each}
            </section>

            <section
                class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4"
                aria-label="Probability quality"
            >
                {#each [["Balanced accuracy", pct(t.balanced_accuracy, 2)], ["MCC", num(t.mcc)], ["Average precision", num(t.average_precision)], ["MSE", num(t.mse)], ["Brier score", num(t.brier)], ["Log-loss", num(t.log_loss)], ["ECE (calibration)", num(t.ece)], ["False-positive rate", pct(t.fpr, 2)]] as [k, v]}
                    <div
                        class="rounded-2xl border border-slate-700 bg-slate-900 p-5"
                    >
                        <p class="text-sm text-slate-400">{k}</p>
                        <p class="mt-2 text-2xl font-extrabold">{v}</p>
                    </div>
                {/each}
            </section>

            <section class="mb-6 grid gap-6 lg:grid-cols-2">
                <article class={card}>
                    <h2 class="mb-4 text-xl font-bold">Confusion matrix</h2>
                    <table class="w-full text-center text-sm">
                        <thead class="text-slate-400"
                            ><tr
                                ><th></th><th class="pb-2">Predicted real</th
                                ><th class="pb-2">Predicted AI</th></tr
                            ></thead
                        >
                        <tbody>
                            <tr
                                ><th class="py-3 text-left text-slate-400"
                                    >Actually real</th
                                ><td
                                    class="rounded-lg bg-emerald-950 py-3 text-lg font-bold"
                                    >{t.confusion?.tn ?? "–"}</td
                                ><td
                                    class="rounded-lg bg-rose-950/40 py-3 text-lg font-bold"
                                    >{t.confusion?.fp ?? "–"}</td
                                ></tr
                            >
                            <tr
                                ><th class="py-3 text-left text-slate-400"
                                    >Actually AI</th
                                ><td
                                    class="rounded-lg bg-rose-950/40 py-3 text-lg font-bold"
                                    >{t.confusion?.fn ?? "–"}</td
                                ><td
                                    class="rounded-lg bg-emerald-950 py-3 text-lg font-bold"
                                    >{t.confusion?.tp ?? "–"}</td
                                ></tr
                            >
                        </tbody>
                    </table>
                </article>
                {#if m.roc}
                    <article class={card}>
                        <h2 class="mb-4 text-xl font-bold">
                            ROC curve <span
                                class="text-sm font-normal text-slate-400"
                                >AUC {num(t.roc_auc, 3)}</span
                            >
                        </h2>
                        <svg
                            viewBox="-24 -8 236 236"
                            class="mx-auto w-full max-w-xs"
                            role="img"
                            aria-label="ROC curve"
                        >
                            <rect
                                x="0"
                                y="0"
                                width="200"
                                height="200"
                                fill="none"
                                stroke="#334155"
                            />
                            <line
                                x1="0"
                                y1="200"
                                x2="200"
                                y2="0"
                                stroke="#475569"
                                stroke-dasharray="4"
                            />
                            <polyline
                                points={roc(m.roc)}
                                fill="none"
                                stroke="#818cf8"
                                stroke-width="2.5"
                            />
                            <text
                                x="100"
                                y="222"
                                fill="#94a3b8"
                                font-size="10"
                                text-anchor="middle">False-positive rate</text
                            >
                            <text
                                x="-12"
                                y="100"
                                fill="#94a3b8"
                                font-size="10"
                                text-anchor="middle"
                                transform="rotate(-90 -12 100)"
                                >True-positive rate</text
                            >
                        </svg>
                    </article>
                {/if}
            </section>

            {#if m.comparison}
                <article class={`${card} mb-6`}>
                    <h2 class="mb-4 text-xl font-bold">Model comparison</h2>
                    <div class="overflow-x-auto">
                        <table class="w-full min-w-140 text-left text-sm">
                            <thead class="text-slate-400"
                                ><tr
                                    ><th class="pb-2">Model</th><th>Accuracy</th
                                    ><th>Recall</th><th>F1</th><th>ROC-AUC</th
                                    ></tr
                                ></thead
                            >
                            <tbody
                                >{#each m.comparison.rows as r}
                                    <tr
                                        class="border-t border-slate-800"
                                        class:text-indigo-300={r.family ===
                                            "final"}
                                        class:font-bold={r.family === "final"}
                                    >
                                        <td class="py-2 pr-3">{r.name}</td><td
                                            >{pct(r.accuracy)}</td
                                        ><td>{pct(r.recall)}</td><td
                                            >{num(r.f1, 3)}</td
                                        ><td>{num(r.roc_auc, 3)}</td>
                                    </tr>
                                {/each}</tbody
                            >
                        </table>
                    </div>
                    <p class="mt-3 text-xs text-slate-400">
                        {m.comparison.basis}
                    </p>
                    {#if m.cross_validation}<p
                            class="mt-2 text-xs text-slate-400"
                        >
                            5-fold cross-validation: accuracy {pct(
                                m.cross_validation.accuracy.mean,
                                2,
                            )} ± {pct(m.cross_validation.accuracy.std, 2)},
                            ROC-AUC {num(m.cross_validation.roc_auc.mean)} ± {num(
                                m.cross_validation.roc_auc.std,
                            )}
                        </p>{/if}
                </article>
            {/if}

            {#if m.attribution?.test}
                {@const a = m.attribution}
                <article class={`${card} mb-6`}>
                    <h2 class="text-xl font-bold">Generator attribution</h2>
                    <p class="mt-1 text-sm text-slate-400">
                        Which AI family made an image, over {a.families.length} families
                        (chance level {pct(a.test.chance_level)}). It answers
                        “unknown” when confidence is below {Math.round(
                            a.tau * 100,
                        )}%.
                    </p>
                    <div class="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
                        {#each [["Accuracy", pct(a.test.accuracy)], ["Top-3 accuracy", pct(a.test.top3_accuracy)], ["Answered", pct(a.test.coverage)], ["Accuracy when answered", pct(a.test.accuracy_when_accepted)]] as [k, v]}
                            <div
                                class="rounded-xl border border-slate-700 bg-slate-950 p-4"
                            >
                                <p class="text-xs text-slate-400">{k}</p>
                                <p class="mt-1 text-2xl font-bold">{v}</p>
                            </div>
                        {/each}
                    </div>
                    <div class="mt-4 overflow-x-auto">
                        <table class="w-full min-w-105 text-left text-sm">
                            <thead class="text-slate-400"
                                ><tr
                                    ><th class="pb-2">Family</th><th>Images</th
                                    ><th>Precision</th><th>Recall</th><th>F1</th
                                    ></tr
                                ></thead
                            >
                            <tbody
                                >{#each Object.entries(a.test.per_family) as [fam, r]}
                                    <tr class="border-t border-slate-800"
                                        ><td class="py-2 pr-3"
                                            >{a.labels[fam] ?? fam}</td
                                        ><td>{r.n}</td><td
                                            >{pct(r.precision)}</td
                                        ><td>{pct(r.recall)}</td><td
                                            >{num(r.f1, 3)}</td
                                        ></tr
                                    >
                                {/each}</tbody
                            >
                        </table>
                    </div>
                    <p class="mt-3 text-xs text-slate-400">{a.note}</p>
                </article>
            {/if}

            {#if m.selective || m.calibration?.length}
                <section class="mb-6 grid gap-6 lg:grid-cols-2">
                    {#if m.selective}
                        <article class={card}>
                            <h2 class="text-xl font-bold">
                                “Inconclusive” band
                            </h2>
                            <p class="mt-1 text-sm text-slate-400">
                                Scores between {pct(m.selective.real_max, 0)} and
                                {pct(m.selective.ai_min, 0)} are reported as Inconclusive
                                instead of forcing an answer.
                            </p>
                            <div class="mt-4 grid grid-cols-3 gap-3">
                                {#each [["Answered", pct(m.selective.coverage)], ["Inconclusive", pct(m.selective.inconclusive_rate)], ["Accuracy when answered", pct(m.selective.accuracy_decided)]] as [k, v]}
                                    <div
                                        class="rounded-xl border border-slate-700 bg-slate-950 p-4"
                                    >
                                        <p class="text-xs text-slate-400">
                                            {k}
                                        </p>
                                        <p class="mt-1 text-xl font-bold">
                                            {v}
                                        </p>
                                    </div>
                                {/each}
                            </div>
                        </article>
                    {/if}
                    {#if m.calibration?.length}
                        <article class={card}>
                            <h2 class="mb-3 text-xl font-bold">Calibration</h2>
                            <div class="overflow-x-auto">
                                <table class="w-full min-w-90 text-sm">
                                    <thead class="text-left text-slate-400"
                                        ><tr
                                            ><th class="pb-2">Score range</th
                                            ><th>Images</th><th>Avg. score</th
                                            ><th>Actually AI</th></tr
                                        ></thead
                                    >
                                    <tbody
                                        >{#each m.calibration.filter((b) => b.n) as b}
                                            <tr
                                                class="border-t border-slate-800"
                                                ><td class="py-2">{b.bin}</td
                                                ><td>{b.n}</td><td
                                                    >{pct(b.mean_p)}</td
                                                ><td>{pct(b.frac_ai)}</td></tr
                                            >
                                        {/each}</tbody
                                    >
                                </table>
                            </div>
                            <p class="mt-3 text-xs text-slate-400">
                                A well-calibrated model's average score in each
                                range is close to the share of images that
                                really were AI-generated.
                            </p>
                        </article>
                    {/if}
                </section>
            {/if}

            {#if m.per_source || m.per_generator}
                <section class="mb-6 grid gap-6 lg:grid-cols-2">
                    {#if m.per_source}
                        <article class={card}>
                            <h2 class="mb-3 text-xl font-bold">Per dataset</h2>
                            <div class="overflow-x-auto">
                                <table
                                    class="w-full min-w-105 text-left text-sm"
                                >
                                    <thead class="text-slate-400"
                                        ><tr
                                            ><th class="pb-2">Source</th><th
                                                >Images</th
                                            ><th>Accuracy</th><th>Recall</th><th
                                                >Specificity</th
                                            ></tr
                                        ></thead
                                    >
                                    <tbody
                                        >{#each Object.entries(m.per_source) as [src, r]}
                                            <tr
                                                class="border-t border-slate-800"
                                                ><td class="py-2 pr-3">{src}</td
                                                ><td>{r.n}</td><td
                                                    >{pct(r.accuracy)}</td
                                                ><td>{pct(r.recall)}</td><td
                                                    >{pct(r.specificity)}</td
                                                ></tr
                                            >
                                        {/each}</tbody
                                    >
                                </table>
                            </div>
                        </article>
                    {/if}
                    {#if m.per_generator && Object.keys(m.per_generator).length}
                        <article class={card}>
                            <h2 class="mb-3 text-xl font-bold">
                                Per generator
                            </h2>
                            <table class="w-full text-sm">
                                <tbody
                                    >{#each Object.entries(m.per_generator) as [gen, r]}
                                        <tr class="border-t border-slate-800"
                                            ><td class="py-2 pr-3">{gen}</td><td
                                                class="text-slate-400"
                                                >{r.n} images</td
                                            ><td class="text-right"
                                                >{pct(r.recall)} detected</td
                                            ></tr
                                        >
                                    {/each}</tbody
                                >
                            </table>
                        </article>
                    {/if}
                </section>
            {/if}

            <section class="mb-6 grid gap-6 lg:grid-cols-2">
                {#if m.errors}
                    <article class={card}>
                        <h2 class="mb-3 text-xl font-bold">
                            Where it struggles
                        </h2>
                        <table class="w-full text-sm">
                            <tbody
                                >{#each Object.entries(m.errors.by_resolution) as [k, v]}
                                    <tr class="border-t border-slate-800"
                                        ><td class="py-2">{k}</td><td
                                            class="text-slate-400"
                                            >{v.n} images</td
                                        ><td class="text-right"
                                            >{pct(v.accuracy)}</td
                                        ></tr
                                    >
                                {/each}</tbody
                            >
                        </table>
                        <p class="mt-3 text-xs text-slate-400">
                            {m.errors.note}
                        </p>
                    </article>
                {/if}
                {#if m.robustness}
                    <article class={card}>
                        <h2 class="mb-3 text-xl font-bold">Robustness</h2>
                        <table class="w-full text-sm">
                            <tbody
                                >{#each Object.entries(m.robustness) as [k, v]}
                                    <tr class="border-t border-slate-800"
                                        ><td class="py-2"
                                            >{k.replaceAll("_", " ")}</td
                                        ><td class="text-right"
                                            >{pct(v.accuracy)}</td
                                        ></tr
                                    >
                                {/each}</tbody
                            >
                        </table>
                        {#if m.ood}<p class="mt-3 text-xs text-slate-400">
                                <b>{m.ood.name}:</b> detection rate {pct(
                                    m.ood.recall,
                                )} on {m.ood.n_fake} images{m.ood.n_real
                                    ? `; specificity ${pct(m.ood.specificity)}`
                                    : "; false-positive rate not measured (no real photos supplied)"}.
                            </p>{/if}
                    </article>
                {/if}
            </section>

            {#if m.datasets?.length}
                <article class={card}>
                    <h2 class="mb-3 text-xl font-bold">Datasets</h2>
                    <ul class="space-y-1 text-sm text-slate-300">
                        {#each m.datasets as d}<li>
                                {d.name} — {d.role}{#if d.url?.startsWith("https://")}
                                    · <a
                                        class="text-indigo-300 underline"
                                        href={d.url}
                                        rel="noopener noreferrer"
                                        target="_blank">source</a
                                    >{/if}
                            </li>{/each}
                    </ul>
                    {#if m.leakage_check}<p class="mt-3 text-xs text-slate-400">
                            Leakage check: {m.leakage_check
                                .hashes_in_multiple_splits} duplicate images found
                            across splits and kept in one split only.
                        </p>{/if}
                </article>
            {/if}
        {/if}
    </main>
</Layout>

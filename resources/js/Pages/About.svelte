<script>
    import { onMount } from "svelte";
    import Layout from "../Layouts/TestLayout.svelte";
    import { http } from "../api/client";

    let model = $state(null);
    onMount(async () => { model = (await http.get("/model")).data; });
</script>

<Layout active="/about">
    <h1 class="mb-3 text-3xl font-bold">About HulagwAI</h1>
    <p class="text-slate-300">Authenticity needs context, not certainty. Detection is probabilistic and can be wrong in either direction. Results are predictions, not proof.</p>
    {#if model?.name}
        <p class="mt-4 text-sm text-slate-400">Model: {model.name} v{model.version}
            {#if model.summary} — accuracy {(model.summary.accuracy * 100).toFixed(1)}%, recall {(model.summary.recall * 100).toFixed(1)}%, AUC {model.summary.roc_auc?.toFixed(3)} (n={model.summary.n}){/if}</p>
    {/if}
</Layout>

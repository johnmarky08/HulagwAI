<script>
    import Layout from "../Layouts/TestLayout.svelte";
</script>

<Layout active="/">
    <h1 class="mb-3 text-4xl font-bold">Discover what's real. <span class="text-indigo-400">Detect what's AI.</span></h1>
    <p class="mb-6 text-slate-300">Upload an image and HulagwAI predicts whether it is likely AI-generated or real, with a confidence score and a plain-language explanation.</p>
    <a href="/detect" class="rounded bg-indigo-600 px-5 py-2 font-semibold">Analyze image</a>
    <p class="mt-10 text-xs text-slate-500">Test UI only — the production design is built separately on top of <code>/api/v1</code>.</p>
</Layout>

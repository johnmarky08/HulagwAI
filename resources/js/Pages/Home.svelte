<script>
    import { onMount } from "svelte";
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import LoginModal from "./Components/LoginModal.svelte";
    import TechStackCarousel from "./Components/TechStackCarousel.svelte";
    import { session, refreshSession } from "../api/session.svelte.js";
    import { loginForm } from "../official/authPages.svelte.js";
    import josh from "../../images/Joshua.jpg";
    import nico from "../../images/nico.png";
    import marky from "../../images/marky.jpg";

    let loginOpen = $state(false);

    onMount(() => {
        void refreshSession();
    });

    function openLogin() {
        loginForm.error = "";
        loginOpen = true;
    }

    function closeLogin() {
        if (loginForm.busy) return;
        loginOpen = false;
        loginForm.error = "";
    }
</script>

<svelte:head>
    <title>HulagwAI · Discover What’s Real</title>
    <meta
        name="description"
        content="Assess whether an image may be AI-generated or captured from a real-world source."
    />
</svelte:head>

<Layout active="home">
    <main class="mx-auto max-w-1440px">
        <section
            class="scroll-reveal grid min-h-470px items-center gap-8 px-6 py-44 md:grid-cols-2 md:px-16 lg:min-h-485px"
        >
            <div>
                <p
                    class="mb-3 text-xs font-bold uppercase tracking-[.16em] text-indigo-400"
                >
                    Image authenticity, explained
                </p>
                <h1
                    class="font-sans text-4xl font-extrabold leading-[1.02] tracking-tight text-indigo-300 sm:text-5xl lg:text-6xl"
                >
                    <span
                        class="bg-linear-to-r from-indigo-500 to-violet-300 bg-clip-text text-transparent"
                        >Discover What’s Real.</span
                    ><br /><span
                        class="bg-linear-to-r from-indigo-950 to-indigo-700 bg-clip-text text-transparent"
                        >Detect What’s AI.</span
                    >
                </h1>
                <p class="mt-6 max-w-xl text-sm leading-6 text-slate-400">
                    Upload an image and HulagwAI predicts whether it is likely
                    AI-generated or real, with a clear confidence score and a
                    plain-language explanation.
                </p>
                <div class="mt-6 flex flex-wrap gap-4">
                    {#if session.value?.authenticated}
                        <a
                            use:inertia
                            class="inline-flex items-center gap-2 rounded-xl border border-indigo-500 bg-linear-to-br from-indigo-900 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/50 transition hover:brightness-125"
                            href="/detect"><span>↑</span> Analyze Image</a
                        >
                    {:else if session.value === undefined}
                        <span
                            class="h-11 w-40 rounded-xl border border-slate-800 bg-slate-800/50"
                            aria-hidden="true"
                        ></span>
                    {:else}
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 rounded-xl border border-indigo-500 bg-linear-to-br from-indigo-900 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/50 transition hover:brightness-125"
                            onclick={openLogin}><span>♙</span> Log in</button
                        >
                    {/if}
                    <a
                        class="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-100"
                        href="#how-it-works">Learn How It Works</a
                    >
                </div>
            </div>
            <div
                class="hero-art relative mx-auto grid h-320px w-full max-w-xl place-items-center"
                aria-label="Illustration of an image being analyzed"
            >
                <div
                    class="hero-glow absolute h-56 w-72 rounded-full bg-indigo-600/30 blur-3xl"
                ></div>
                <div
                    class="hero-image relative h-52 w-80 -rotate-2 rounded-3xl bg-linear-to-br from-violet-500 via-indigo-800 to-blue-950 p-2 shadow-[0_0_45px_#5145e899] sm:w-390px"
                >
                    <div
                        class="relative h-full overflow-hidden rounded-2xl bg-[radial-gradient(circle_at_72%_28%,#ffd68e_0,#d89b8a_13%,transparent_29%),radial-gradient(circle_at_27%_75%,#3e63dd_0,#4d59d2_25%,transparent_47%),linear-gradient(130deg,#555bd4,#141a4c_78%)]"
                    >
                        <span class="hero-scanline" aria-hidden="true"></span>
                        <span
                            class="absolute bottom-4 right-4 size-3 rounded border border-indigo-200"
                        ></span>
                    </div>
                </div>
                <div
                    class="hero-confidence absolute right-0 top-7 flex flex-col rounded-xl bg-white px-4 py-3 text-slate-900 shadow-lg"
                >
                    <small class="text-[9px] font-semibold text-slate-500"
                        >MODEL CONFIDENCE</small
                    ><strong class="text-sm">87%</strong>
                </div>
                <div
                    class="hero-verdict absolute bottom-7 left-0 flex flex-col rounded-xl bg-white px-4 py-3 text-slate-900 shadow-lg"
                >
                    <small class="text-[9px] font-semibold text-slate-500"
                        >PREDICTION · SAMPLE</small
                    ><strong class="text-xs text-rose-500"
                        >Likely AI-Generated</strong
                    >
                </div>
            </div>
        </section>

        <section
            id="how-it-works"
            class="scroll-reveal border-t border-indigo-500/60 px-6 py-12 md:px-16"
        >
            <div class="mb-8 text-center">
                <h2
                    class="text-4xl font-extrabold tracking-tight text-indigo-400"
                >
                    How It Works
                </h2>
                <p class="mt-2 text-sm text-slate-400">
                    Three simple steps from upload to a clear, explained result.
                </p>
            </div>
            <div class="mx-auto grid max-w-5xl gap-5 md:grid-cols-3">
                {#each [{ n: "01", icon: "↑", title: "Upload an Image", text: "Drag and drop, or browse for a JPG, PNG, or WEBP file." }, { n: "02", icon: "⌗", title: "AI-Powered Analysis", text: "The model examines image characteristics and patterns." }, { n: "03", icon: "✓", title: "View Detection Results", text: "Get a classification, confidence score, and what it means." }] as step}
                    <article
                        class="rounded-2xl border border-indigo-500/50 bg-linear-to-br from-slate-900 to-indigo-950/40 p-6 text-center"
                    >
                        <span class="block text-sm font-bold text-indigo-400"
                            >Step {step.n}</span
                        ><span
                            class="mx-auto my-4 grid size-12 place-items-center rounded-xl bg-linear-to-br from-indigo-300 to-indigo-600 text-2xl text-white shadow-lg shadow-indigo-500/20"
                            >{step.icon}</span
                        >
                        <h3 class="font-semibold">{step.title}</h3>
                        <p class="mt-2 text-xs leading-5 text-slate-400">
                            {step.text}
                        </p>
                    </article>
                {/each}
            </div>
        </section>

        <section
            id="about"
            class="scroll-reveal border-t border-indigo-500/60 px-6 py-12 md:px-16"
        >
            <div class="mb-8 text-center">
                <h2
                    class="text-4xl font-extrabold tracking-tight text-indigo-400"
                >
                    About
                </h2>
                <p class="mt-2 text-sm text-slate-400">
                    Tools for a more informed look at digital images.
                </p>
            </div>
            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {#each [{ icon: "⌗", title: "AI Image Detection", text: "Analyze a single image in seconds." }, { icon: "▦", title: "Confidence Score", text: "See how strongly the model favors its prediction." }, { icon: "⬡", title: "Real vs. AI Classification", text: "Likely real, likely AI-generated, or inconclusive." }, { icon: "◷", title: "Analysis History", text: "Search, filter, and revisit results." }] as feature}
                    <article
                        class="rounded-2xl border border-indigo-500/50 bg-slate-950/70 p-5 text-center"
                    >
                        <span
                            class="mx-auto grid size-11 place-items-center rounded-xl bg-indigo-500 text-xl text-white"
                            >{feature.icon}</span
                        >
                        <h3 class="mt-4 text-sm font-semibold">
                            {feature.title}
                        </h3>
                        <p class="mt-2 text-xs text-slate-400">
                            {feature.text}
                        </p>
                    </article>
                {/each}
            </div>
            <div
                class="mx-auto mt-10 grid max-w-4xl gap-6 rounded-2xl border border-indigo-500/50 bg-indigo-950/70 p-6 md:grid-cols-2 md:p-8"
            >
                <div>
                    <span
                        class="rounded-full border border-indigo-400 px-3 py-1 text-[10px] text-indigo-300"
                        >About HulagwAI</span
                    >
                    <h3 class="mt-4 text-2xl font-extrabold leading-tight">
                        Authenticity needs<br />context, not certainty.
                    </h3>
                    <p class="mt-3 text-xs leading-5 text-slate-300">
                        HulagwAI helps assess whether an image may be
                        AI-generated or real. It supports human judgment; it
                        does not replace it.
                    </p>
                    <a
                        use:inertia
                        class="mt-4 inline-flex rounded-xl border border-indigo-400 bg-indigo-700 px-5 py-2 text-sm font-semibold text-white"
                        href="/detect">Try it now</a
                    >
                </div>
                <aside
                    class="self-center rounded-xl border border-indigo-400/70 bg-indigo-900/70 p-5"
                >
                    <strong class="text-sm">Limitations</strong>
                    <p class="mt-3 text-xs leading-5 text-slate-300">
                        Detection is probabilistic and can be wrong.
                        Compression, editing, and new image generators may
                        affect reliability. Results are predictions, not proof.
                    </p>
                </aside>
            </div>
        </section>

        <section
            class="scroll-reveal border-t border-indigo-500/30 px-6 py-12 md:px-16"
        >
            <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
                <h2
                    class="text-center text-4xl font-extrabold tracking-tight text-indigo-400"
                >
                    Developers
                </h2>
            </div>
            <div class="grid gap-5 md:grid-cols-3">
                {#each [
                    { number: "01", name: "Joshua Bartolome", role: "Frontend developer", description: "Builds the upload experience, result views, and responsive interface.", img: josh }, 
                    { number: "02", name: "John Marky Natividad", role: "Backend developer", description: "Connects analysis requests, stores results, and supports analysis history.", img: marky }, 
                    { number: "03", name: "Nico Gabriel Domingo", role: "Project Designer", description: "Designs and develops intuitive user interfaces, visual layouts, and user experiences for the project.", img: nico }] 
                    as developer}
                    <article
                        class="rounded-2xl border border-indigo-500/40 bg-slate-900 p-6"
                    >
                        <span class="text-xs font-bold text-indigo-400"
                            >{developer.number}</span
                        >
                        <div
                            class="developer-avatar mx-auto my-5 grid size-20 place-items-center overflow-hidden rounded-full border border-indigo-400/50 bg-indigo-950/70 ring-4 ring-indigo-500/10"
                            aria-hidden="true"
                        >
                            {#if developer.img}
                                <img
                                    src={developer.img}
                                    alt={developer.name}
                                    class="size-20 rounded-full object-cover object-center"
                                    loading="lazy"
                                />
                            {:else}
                                <svg
                                    class="size-9 text-indigo-300"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                >
                                    <circle
                                        cx="12"
                                        cy="8"
                                        r="3.5"
                                        stroke="currentColor"
                                        stroke-width="1.7"
                                    />
                                    <path
                                        d="M5.5 20c.5-3.2 2.8-5 6.5-5s6 1.8 6.5 5"
                                        stroke="currentColor"
                                        stroke-width="1.7"
                                        stroke-linecap="round"
                                    />
                                </svg>
                            {/if}
                        </div>
                        <h3 class="mt-3 text-xl font-bold text-center">
                            {developer.name}
                        </h3>
                        <p
                            class="text-center mt-1 text-sm font-semibold text-indigo-300"
                        >
                            {developer.role}
                        </p>
                        <p class="mt-4 text-sm leading-6 text-slate-400">
                            {developer.description}
                        </p>
                    </article>
                {/each}
            </div>
        </section>

        <section
            id="tech-stack"
            class="scroll-reveal border-t border-indigo-500/30 px-6 py-12 md:px-16"
            aria-labelledby="tech-stack-title"
        >
            <div class="mb-8 text-center">
                <h2
                    id="tech-stack-title"
                    class="text-4xl font-extrabold tracking-tight text-indigo-400"
                >
                    Tech Stack
                </h2>
                <p class="mt-2 text-sm text-slate-400">
                    The layers behind HulagwAI, revealed one at a time.
                </p>
            </div>
            <TechStackCarousel />
        </section>
    </main>
    {#if loginOpen}<LoginModal onClose={closeLogin} />{/if}
</Layout>

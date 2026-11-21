<script>
    import { inertia } from "@inertiajs/svelte";
    import Layout from "./Components/Layout.svelte";
    import LoginGate from "./Components/LoginGate.svelte";
    import Icon from "./Components/Icon.svelte";

    const steps = [
        {
            n: "01",
            icon: "download",
            title: "Download and Extract",
            text: "Download the ZIP above and extract it to a folder you will keep. Do not select the ZIP itself when loading the extension.",
        },
        {
            n: "02",
            icon: "plug",
            title: "Load It in Your Browser",
            text: "Open brave://extensions, chrome://extensions, or edge://extensions. Turn on Developer mode, choose Load unpacked, then select the extracted folder containing manifest.json.",
        },
        {
            n: "03",
            icon: "link",
            title: "Pair Your HulagwAI Account",
            text: "Click the extension icon to open its settings popup. Enter the HulagwAI site address and choose Open secure pairing page. Sign in if asked, copy the short-lived code, then paste it into the settings popup.",
        },
        {
            n: "04",
            icon: "mouse-pointer-click",
            title: "Right-Click Any Image",
            text: "Choose Scan image with HulagwAI from the context menu. Grant access to that image host if prompted, then explicitly confirm the upload.",
        },
    ];

    const flow = [
        {
            n: "1",
            title: "You Choose",
            text: "Right-click the specific image and select Scan image with HulagwAI. No webpage scan buttons are injected.",
        },
        {
            n: "2",
            title: "You Confirm",
            text: "The HulagwAI toolbar popup opens with a confirmation that previews the selected image. Grant access to its host, then choose Send image for analysis.",
        },
        {
            n: "3",
            title: "HulagwAI Analyzes",
            text: "The existing analysis service processes the image; the extension shows the result and logs the analysis ID.",
        },
    ];

    const help = [
        {
            title: "No Context-Menu Item?",
            text: "Click the extension icon to open its settings popup and turn on Enable right-click scanning. Reload the extension if you just updated it.",
        },
        {
            title: "Pairing Code Rejected?",
            text: "Make sure the extension settings popup and signed-in HulagwAI page use the same site address. Codes expire after three minutes; generate a fresh one.",
        },
        {
            title: "Still processing?",
            text: "Check the analysis ID in HulagwAI History. Results depend on the HulagwAI queue and model service being online.",
        },
    ];
</script>

<svelte:head>
    <title>HulagwAI · Browser Extension</title>
    <meta
        name="description"
        content="Install and pair the HulagwAI web image scanner beta."
    />
</svelte:head>

<Layout active="extension">
    <LoginGate>
        <main class="extension-page mx-auto min-h-[calc(100vh-80px)] max-w-6xl px-5 pb-16 sm:px-8">
            <section
                class="extension-hero relative mt-7 overflow-hidden rounded-3xl border border-indigo-500/40 bg-linear-to-br from-indigo-950 via-slate-950 to-slate-900 p-6 shadow-2xl shadow-indigo-950/30 sm:mt-10 sm:p-10"
            >
                <div
                    class="hero-glow pointer-events-none absolute -right-10 -top-16 hidden size-72 rounded-full bg-indigo-500/15 blur-3xl sm:block"
                ></div>
                <div class="relative z-10 max-w-3xl">
                    <span
                        class="inline-flex items-center gap-2 rounded-full border border-indigo-300/30 bg-indigo-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[.16em] text-indigo-200"
                    >
                        <i
                            class="size-2 rounded-full bg-amber-300"
                            aria-hidden="true"
                        ></i> Beta · Manual install
                    </span>
                    <h1
                        class="mt-5 text-3xl font-extrabold leading-tight tracking-tight text-white sm:text-5xl"
                    >
                        Check Images Anywhere on the Web.
                    </h1>
                    <p
                        class="mt-4 max-w-2xl text-sm leading-6 text-slate-300 sm:text-base sm:leading-7"
                    >
                        Scan an image from the browser's right-click menu on
                        almost any website. No scan buttons clutter the page:
                        choose an image, review the confirmation, then approve
                        its upload to HulagwAI.
                    </p>
                    <ul
                        class="mt-5 flex flex-wrap gap-2 text-xs font-semibold text-slate-200"
                    >
                        <li
                            class="rounded-full border border-slate-600/70 bg-slate-900/60 px-3 py-1.5"
                        >
                            Right-click menu
                        </li>
                        <li
                            class="rounded-full border border-slate-600/70 bg-slate-900/60 px-3 py-1.5"
                        >
                            Confirm before upload
                        </li>
                        <li
                            class="rounded-full border border-slate-600/70 bg-slate-900/60 px-3 py-1.5"
                        >
                            Saved to your history
                        </li>
                    </ul>
                    <div class="mt-7 flex flex-col gap-3 sm:flex-row">
                        <a
                            class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-950/40 transition hover:bg-indigo-500"
                            href="/downloads/hulagwai-image-scanner-v0.4.5.zip"
                            download
                        >
                            <Icon name="download" /> Download for Brave
                            / Chrome / Edge
                        </a>
                        <a
                            use:inertia
                            class="inline-flex min-h-12 items-center justify-center rounded-xl border border-slate-600 bg-slate-900/70 px-5 py-3 text-sm font-semibold text-slate-100 transition hover:border-indigo-300"
                            href="/extension/connect"
                            >Pair an Installed Extension</a
                        >
                    </div>
                    <p class="mt-3 text-xs leading-5 text-slate-400">
                        Version 0.4.5 · Desktop Chromium browsers · Not yet
                        listed in an extension store. Manual installation
                        requires Developer mode.
                    </p>
                </div>
            </section>

            <section class="mt-12" aria-labelledby="install-heading">
                <div
                    class="mb-6 flex flex-wrap items-end justify-between gap-3"
                >
                    <div>
                        <p
                            class="text-xs font-bold uppercase tracking-[.15em] text-indigo-400"
                        >
                            Setup Guide
                        </p>
                        <h2
                            id="install-heading"
                            class="mt-2 text-2xl font-extrabold text-white sm:text-3xl"
                        >
                            Install and Connect in a Few Minutes
                        </h2>
                    </div>
                    <span
                        class="rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-slate-400"
                        >You only pair once per browser</span
                    >
                </div>
                <div class="grid gap-4 md:grid-cols-2">
                    {#each steps as step (step.n)}
                        <article
                            class="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-5 transition duration-300 hover:-translate-y-0.5 hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-950/30 sm:p-6"
                        >
                            <span
                                class="pointer-events-none absolute right-5 top-3 select-none text-5xl font-extrabold text-indigo-500/10"
                                aria-hidden="true">{step.n}</span
                            >
                            <div class="flex gap-4">
                                <span
                                    class="grid size-11 shrink-0 place-items-center rounded-xl border border-indigo-400/30 bg-indigo-500/10 text-xl text-indigo-200"
                                    aria-hidden="true"><Icon name={step.icon} /></span
                                >
                                <div class="pr-10">
                                    <span
                                        class="text-[10px] font-bold tracking-[.14em] text-indigo-400"
                                        >STEP {step.n}</span
                                    >
                                    <h3
                                        class="mt-1 text-base font-bold text-white"
                                    >
                                        {step.title}
                                    </h3>
                                    <p
                                        class="mt-2 text-sm leading-6 text-slate-400"
                                    >
                                        {step.text}
                                    </p>
                                </div>
                            </div>
                        </article>
                    {/each}
                </div>
            </section>

            <section class="mt-12 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
                <article
                    class="rounded-2xl border border-indigo-500/35 bg-indigo-950/20 p-5 sm:p-7"
                >
                    <h2 class="text-xl font-extrabold text-white">
                        What Happens When You Scan?
                    </h2>
                    <ol
                        class="mt-6 flex flex-col gap-3 sm:flex-row sm:items-stretch"
                    >
                        {#each flow as step, index (step.n)}
                            <li
                                class="flex-1 rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                            >
                                <span
                                    class="grid size-8 place-items-center rounded-full bg-indigo-500/20 text-xs font-bold text-indigo-200"
                                    >{step.n}</span
                                >
                                <h3 class="mt-3 text-sm font-bold text-white">
                                    {step.title}
                                </h3>
                                <p
                                    class="mt-2 text-xs leading-5 text-slate-400"
                                >
                                    {step.text}
                                </p>
                            </li>
                            {#if index < flow.length - 1}
                                <li
                                    class="hidden items-center text-lg text-indigo-400 sm:flex"
                                    aria-hidden="true"
                                >
                                    <Icon name="arrow-right" />
                                </li>
                            {/if}
                        {/each}
                    </ol>
                </article>
                <aside
                    class="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-7"
                >
                    <h2 class="text-xl font-extrabold text-white">
                        Before You Install
                    </h2>
                    <ul class="mt-5 space-y-4 text-sm leading-6 text-slate-400">
                        <li class="flex gap-3">
                            <span
                                class="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-indigo-500/15 text-xs text-indigo-300"
                                aria-hidden="true"><Icon name="check" strokeWidth={3} /></span
                            ><span
                                ><b class="text-slate-200">Supported:</b> Brave,
                                Chrome, and Edge on desktop; ordinary web images
                                on most sites.</span
                            >
                        </li>
                        <li class="flex gap-3">
                            <span
                                class="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-indigo-500/15 text-xs text-indigo-300"
                                aria-hidden="true"><Icon name="check" strokeWidth={3} /></span
                            ><span
                                ><b class="text-slate-200">Account:</b> A HulagwAI
                                account is required to pair this beta.</span
                            >
                        </li>
                        <li class="flex gap-3">
                            <span
                                class="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-indigo-500/15 text-xs text-indigo-300"
                                aria-hidden="true"><Icon name="check" strokeWidth={3} /></span
                            ><span
                                ><b class="text-slate-200">Image limits:</b> JPG,
                                PNG, or WEBP up to 5 MB. Protected, logged-in, or
                                browser-only images may not be accessible.</span
                            >
                        </li>
                        <li class="flex gap-3">
                            <span
                                class="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-indigo-500/15 text-xs text-indigo-300"
                                aria-hidden="true"><Icon name="check" strokeWidth={3} /></span
                            ><span
                                ><b class="text-slate-200">Privacy:</b> Only the
                                chosen image is uploaded after confirmation. Host
                                permission is requested for that image's origin;
                                page URLs and cookies are not sent.</span
                            >
                        </li>
                    </ul>
                    <p
                        class="mt-6 rounded-xl border border-amber-800/60 bg-amber-950/25 p-4 text-xs leading-5 text-amber-100/80"
                    >
                        This beta is installed manually and has not yet been
                        reviewed or published in the Chrome Web Store or Edge
                        Add-ons. Only install extension files from HulagwAI's
                        official download.
                    </p>
                </aside>
            </section>

            <section
                class="mt-12 rounded-2xl border border-slate-800 bg-slate-900/50 p-5 sm:p-7"
                aria-labelledby="help-heading"
            >
                <h2 id="help-heading" class="text-xl font-extrabold text-white">
                    Quick Troubleshooting
                </h2>
                <div class="mt-6 grid gap-4 md:grid-cols-3">
                    {#each help as item (item.title)}
                        <div
                            class="rounded-xl border border-slate-800 bg-slate-950/50 p-5"
                        >
                            <h3 class="text-sm font-bold text-slate-200">
                                {item.title}
                            </h3>
                            <p class="mt-2 text-xs leading-5 text-slate-400">
                                {item.text}
                            </p>
                        </div>
                    {/each}
                </div>
            </section>
        </main>
    </LoginGate>
</Layout>

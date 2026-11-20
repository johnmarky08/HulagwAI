<script module>
    // Shared by every group on the page: automatic changes keep at least this gap apart,
    // so no two groups ever flip together.
    const MIN_AUTO_GAP_MS = 1500;
    let lastAutoChangeAt = 0;
</script>

<script>
    import { onMount } from "svelte";
    import { cubicOut } from "svelte/easing";

    // One independent carousel: its own timer (period/offset), wheel, arrows, hover tip, and details.
    let { title, items, period = 6000, offset = 0 } = $props();

    const WHEEL_THRESHOLD = 60;
    const WHEEL_COOLDOWN_MS = 450;

    let activeIndex = $state(0);
    // "down" reveals top to bottom; "up" reveals bottom to top.
    let direction = $state("down");
    let autoplay = $state(true);
    let detailsOpen = $state(false);
    // Until the first automatic change, the border timer starts `offset` late, like the autoplay timer.
    let started = $state(false);
    let cardEl = $state(null);
    let dialogEl = $state(null);
    // Where the details overlay sits: exactly over the card it was opened from.
    let overlayBox = $state({ top: 0, left: 0, width: 0, height: 0 });
    let triggerEl = null;
    const titleId = `tech-title-${Math.random().toString(36).slice(2, 8)}`;
    let autoDirection = "down";
    let firstRun = true;
    let pendingTimer = null;
    let wheelAccumulator = 0;
    let lastWheelAt = 0;

    const total = $derived(items.length);
    const active = $derived(items[activeIndex]);
    const counter = $derived(`${String(activeIndex + 1).padStart(2, "0")} / ${String(total).padStart(2, "0")}`);

    onMount(() => {
        // Respect the system's reduced-motion setting: no automatic changes.
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) autoplay = false;
    });

    function go(index, dir) {
        started = true;
        const target = ((index % total) + total) % total;
        direction = dir ?? (target >= activeIndex ? "down" : "up");
        activeIndex = target;
    }

    function next() {
        go(activeIndex + 1, "down");
    }

    function previous() {
        go(activeIndex - 1, "up");
    }

    // Automatic steps alternate the sweep direction: top to bottom, then bottom to top.
    function autoStep() {
        const wait = lastAutoChangeAt + MIN_AUTO_GAP_MS - Date.now();
        if (wait > 0) {
            pendingTimer = setTimeout(autoStep, wait);
            return;
        }
        lastAutoChangeAt = Date.now();
        const dir = autoDirection;
        autoDirection = dir === "down" ? "up" : "down";
        go(activeIndex + 1, dir);
    }

    function handleWheel(event) {
        // Only this card takes over the wheel; the rest of the page keeps scrolling.
        if (event.ctrlKey) return;
        event.preventDefault();
        wheelAccumulator += event.deltaY;
        if (Math.abs(wheelAccumulator) < WHEEL_THRESHOLD) return;
        const now = performance.now();
        const step = wheelAccumulator > 0 ? next : previous;
        wheelAccumulator = 0;
        if (now - lastWheelAt < WHEEL_COOLDOWN_MS) return;
        lastWheelAt = now;
        step();
    }

    function openDetails() {
        triggerEl = document.activeElement;
        const box = cardEl?.getBoundingClientRect();
        if (box) {
            if (window.innerWidth < 640) {
                // Phones: use most of the screen width so the details have room; still centred.
                const width = Math.min(window.innerWidth * 0.92, 416);
                overlayBox = { top: box.top, left: (window.innerWidth - width) / 2, width, height: box.height };
            } else {
                overlayBox = { top: box.top, left: box.left, width: box.width, height: box.height };
            }
        }
        detailsOpen = true;
    }

    // Keeps the panel fully inside the viewport: it starts at the card's top, but moves up if it would run off the bottom.
    function fitToViewport(node) {
        const fit = () => {
            const maxTop = window.innerHeight - node.offsetHeight - 12;
            node.style.top = `${Math.max(12, Math.min(overlayBox.top, maxTop))}px`;
        };
        fit();
        window.addEventListener("resize", fit);
        return {
            destroy() {
                window.removeEventListener("resize", fit);
            },
        };
    }

    // The overlay is placed by viewport coordinates, so close it if the layout changes.
    function handleResize() {
        if (detailsOpen) closeDetails();
    }

    function closeDetails() {
        detailsOpen = false;
        triggerEl?.focus?.({ preventScroll: true });
    }

    function handleKey(event) {
        if (event.key === "ArrowRight") {
            event.preventDefault();
            next();
        } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            previous();
        }
    }

    // While the overlay is open: Escape closes it, and Tab stays inside the dialog.
    function handleWindowKey(event) {
        if (!detailsOpen) return;
        if (event.key === "Escape") {
            event.preventDefault();
            closeDetails();
            return;
        }
        if (event.key !== "Tab" || !dialogEl) return;
        const focusable = [...dialogEl.querySelectorAll("button, a[href]")];
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const inside = dialogEl.contains(document.activeElement);
        if (!inside) {
            event.preventDefault();
            first.focus();
        } else if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    // Moves the overlay to <body> so no ancestor transform or overflow can clip it.
    function portal(node) {
        document.body.append(node);
        return {
            destroy() {
                node.remove();
            },
        };
    }

    // Lift the card: it fades in and settles from a slightly smaller scale to its exact size.
    // Respects reduced motion.
    function lift(node, { duration = 320 } = {}) {
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        return {
            duration: reduced ? 0 : duration,
            easing: cubicOut,
            // Ends at the identity transform, so nothing lingers on the element; the elevation shadow lives in CSS.
            css: (t) => `opacity: ${t}; transform: scale(${0.97 + 0.03 * t});`,
        };
    }

    $effect(() => {
        if (!detailsOpen) return;
        // Lock page scroll behind the overlay and move focus into the dialog.
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        dialogEl?.focus({ preventScroll: true });
        return () => {
            document.body.style.overflow = previousOverflow;
        };
    });

    $effect(() => {
        const element = cardEl;
        if (!element) return;
        element.addEventListener("wheel", handleWheel, { passive: false });
        return () => element.removeEventListener("wheel", handleWheel);
    });

    // Each group starts later by `offset` so the three never change at the same moment.
    // Reading the details state pauses the timer while someone is reading.
    $effect(() => {
        void activeIndex;
        if (!autoplay || detailsOpen) return;
        const delay = firstRun ? period + offset : period;
        firstRun = false;
        pendingTimer = setTimeout(autoStep, delay);
        return () => clearTimeout(pendingTimer);
    });
</script>

<svelte:window onkeydown={handleWindowKey} onresize={handleResize} />

<div class="tech-group flex flex-col">
    <div class="mb-3 flex items-baseline justify-between gap-3">
        <h3 class="text-sm font-bold uppercase tracking-[.16em] text-indigo-300">{title}</h3>
    </div>

    <div
        bind:this={cardEl}
        class="tech-card relative isolate min-h-72 overflow-hidden rounded-2xl border border-indigo-500/50 bg-slate-900 px-12 py-8 text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
        role="region"
        aria-roledescription="carousel"
        aria-label={`${title} carousel`}
        tabindex="0"
        onkeydown={handleKey}
    >
        <span class="absolute left-3 top-3 text-xs font-semibold tabular-nums tracking-wide text-slate-400">{counter}</span>

        {#key `${activeIndex}-${detailsOpen}`}
            <!-- Loading bar along the card border: it sweeps for one period; downward changes go clockwise, upward counter-clockwise. -->
            <svg
                class="border-run pointer-events-none absolute inset-0 z-[6] size-full overflow-visible"
                class:paused={detailsOpen}
                class:border-rev={direction === "up"}
                style:--period="{period}ms"
                style:--delay={started ? "0ms" : `${offset}ms`}
                aria-hidden="true"
            >
                <rect x="1" y="1" rx="15" pathLength="100" style="width: calc(100% - 2px); height: calc(100% - 2px)" />
            </svg>
        {/key}
        {#key activeIndex}
            <span
                class="tech-beam pointer-events-none absolute inset-x-0 top-0 z-10 h-1"
                class:beam-down={direction === "down"}
                class:beam-up={direction === "up"}
                aria-hidden="true"
            ></span>
            <button
                type="button"
                class="tech-slide block w-full rounded-xl px-2 py-2"
                class:reveal-down={direction === "down"}
                class:reveal-up={direction === "up"}
                onclick={openDetails}
                aria-haspopup="dialog"
                aria-label={`${active.name}. Show details`}
            >
                <span
                    class="mx-auto grid size-16 place-items-center rounded-2xl bg-white p-3 shadow-lg shadow-indigo-500/20"
                    aria-hidden="true"
                >
                    {#if active.path}
                        <svg viewBox="0 0 24 24" class="size-full" fill={active.color}><path d={active.path} /></svg>
                    {:else}
                        <svg viewBox="0 0 24 24" class="size-full" fill="none" stroke={active.color} stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={active.iconPath} /></svg>
                    {/if}
                </span>
                <span class="mt-4 block text-xs font-bold uppercase tracking-[.14em] text-indigo-300">{active.category}</span>
                <span class="mt-1 block text-xl font-extrabold tracking-tight text-white">{active.name}</span>
                <span class="mt-2 block text-[11px] text-slate-500">Hover for purpose · click for details</span>
            </button>
            <span class="tech-tip" role="tooltip">{active.purpose}</span>
        {/key}

        <button
            type="button"
            class="tech-arrow absolute left-2 top-1/2 z-20 -translate-y-1/2"
            onclick={previous}
            aria-label={`Previous in ${title}`}
        >
            <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <button
            type="button"
            class="tech-arrow absolute right-2 top-1/2 z-20 -translate-y-1/2"
            onclick={next}
            aria-label={`Next in ${title}`}
        >
            <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
        </button>

    </div>

    <div class="tech-overlay-root" use:portal>
        {#if detailsOpen}
            <div class="tech-overlay-backdrop" onclick={closeDetails} aria-hidden="true"></div>
            <div
                bind:this={dialogEl}
                class="tech-overlay"
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                tabindex="-1"
                style:left="{overlayBox.left}px"
                style:width="{overlayBox.width}px"
                style:min-height="{overlayBox.height}px"
                use:fitToViewport
                transition:lift={{ duration: 320 }}
            >
                <button type="button" class="tech-close absolute right-3 top-3" onclick={closeDetails} aria-label="Close details">×</button>
                <span
                    class="mx-auto grid size-16 place-items-center rounded-2xl bg-white p-3 shadow-lg shadow-indigo-500/20"
                    aria-hidden="true"
                >
                    {#if active.path}
                        <svg viewBox="0 0 24 24" class="size-full" fill={active.color}><path d={active.path} /></svg>
                    {:else}
                        <svg viewBox="0 0 24 24" class="size-full" fill="none" stroke={active.color} stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={active.iconPath} /></svg>
                    {/if}
                </span>
                <p class="mt-4 text-xs font-bold uppercase tracking-[.14em] text-indigo-300">{active.category}</p>
                <h4 id={titleId} class="mt-1 text-2xl font-extrabold tracking-tight text-white">{active.name}</h4>
                <p class="mt-3 text-sm font-semibold text-indigo-100">{active.purpose}</p>
                <p class="mt-3 text-sm leading-6 text-slate-300">{active.details}</p>
                <a
                    class="mt-5 inline-flex min-h-10 items-center rounded-xl border border-indigo-500/50 bg-indigo-950/35 px-4 text-sm font-semibold text-indigo-200 transition hover:border-indigo-400 hover:bg-indigo-900/50 hover:text-white"
                    href={active.link}
                    target="_blank"
                    rel="noopener noreferrer">Official site ↗</a
                >
            </div>
        {/if}
    </div>
</div>

<style>
    .tech-slide {
        appearance: none;
        background: none;
        border: 0;
        color: inherit;
        cursor: pointer;
        font: inherit;
    }
    .tech-slide:focus-visible {
        outline: 2px solid #a5b4fc;
        outline-offset: 3px;
    }

    /* Purpose tooltip, shown while the item is hovered or focused. */
    .tech-tip {
        position: absolute;
        left: 0.75rem;
        right: 0.75rem;
        bottom: 0.9rem;
        z-index: 15;
        border: 1px solid rgb(129 140 248 / 40%);
        border-radius: 0.75rem;
        background: rgb(2 6 23 / 94%);
        padding: 0.55rem 0.75rem;
        color: #cbd5e1;
        font-size: 0.78rem;
        line-height: 1.4;
        text-align: center;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
    }
    .tech-slide:hover + .tech-tip,
    .tech-slide:focus-visible + .tech-tip {
        opacity: 1;
    }

    .tech-arrow,
    .tech-close {
        display: grid;
        width: 2.25rem;
        height: 2.25rem;
        place-items: center;
        border: 1px solid rgb(129 140 248 / 55%);
        border-radius: 999px;
        background: rgb(49 46 129 / 45%);
        color: #e0e7ff;
        cursor: pointer;
        transition: background-color 0.15s ease;
    }
    .tech-arrow:hover,
    .tech-close:hover {
        background: rgb(67 56 202 / 70%);
    }
    .tech-arrow:focus-visible,
    .tech-close:focus-visible {
        outline: 2px solid #a5b4fc;
        outline-offset: 3px;
    }

    /* Details overlay: a transparent click-away layer, plus a panel placed exactly over the card. */
    .tech-overlay-backdrop {
        position: fixed;
        inset: 0;
        z-index: 1000;
    }
    .tech-overlay {
        position: fixed;
        z-index: 1001;
        box-sizing: border-box;
        max-height: 90vh;
        overflow-y: auto;
        border: 1px solid rgb(165 180 252 / 55%);
        border-radius: 1rem;
        background: #0f172a;
        padding: 1.5rem 1.25rem 1.25rem;
        text-align: center;
        transform-origin: center;
        /* Persistent elevation: a deep drop shadow plus a faint top highlight, so the panel reads as lifted off the card. */
        box-shadow:
            0 28px 64px -16px rgb(0 0 0 / 75%),
            0 10px 24px -10px rgb(0 0 0 / 50%),
            0 0 0 1px rgb(99 102 241 / 25%),
            inset 0 1px 0 rgb(255 255 255 / 7%);
    }
    @media (min-width: 640px) {
        .tech-overlay {
            padding: 2.25rem 3rem 2rem;
        }
    }
    .tech-overlay:focus {
        outline: none;
    }
    .tech-overlay:focus-visible {
        outline: 2px solid #a5b4fc;
        outline-offset: 4px;
    }

    /* Auto-advance loading bar: a stroke that runs along the card border. */
    .border-run rect {
        fill: none;
        stroke: #a5b4fc;
        stroke-width: 2;
        stroke-dasharray: 100 100;
        stroke-dashoffset: 100;
        filter: drop-shadow(0 0 4px rgb(103 232 249 / 80%));
        animation: border-run var(--period, 6000ms) linear var(--delay, 0ms) both;
    }
    /* Upward changes sweep the border counter-clockwise, matching the content's direction. */
    .border-run.border-rev {
        transform: scaleX(-1);
    }
    .border-run.paused rect {
        animation-play-state: paused;
    }
    @keyframes border-run {
        from {
            stroke-dashoffset: 100;
        }
        to {
            stroke-dashoffset: 0;
        }
    }

    /* Scanner: content is uncovered by a beam that sweeps through the card. */
    .reveal-down {
        animation: reveal-down 0.7s ease-out both;
    }
    .reveal-up {
        animation: reveal-up 0.7s ease-out both;
    }
    .tech-beam {
        height: 3px;
        background: linear-gradient(90deg, transparent 0%, #a5b4fc 12%, #67e8f9 50%, #a5b4fc 88%, transparent 100%);
        box-shadow: 0 0 12px 4px rgb(103 232 249 / 80%), 0 0 36px 10px rgb(99 102 241 / 50%);
        opacity: 0;
    }
    .beam-down {
        animation: beam-down 0.7s ease-in-out both;
    }
    .beam-up {
        animation: beam-up 0.7s ease-in-out both;
    }

    @keyframes reveal-down {
        from {
            clip-path: inset(0 0 100% 0);
        }
        to {
            clip-path: inset(0 0 0 0);
        }
    }
    @keyframes reveal-up {
        from {
            clip-path: inset(100% 0 0 0);
        }
        to {
            clip-path: inset(0 0 0 0);
        }
    }
    @keyframes beam-down {
        0% {
            top: 0;
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            top: calc(100% - 3px);
            opacity: 0;
        }
    }
    @keyframes beam-up {
        0% {
            top: calc(100% - 3px);
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            top: 0;
            opacity: 0;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .border-run {
            display: none;
        }
        .reveal-down,
        .reveal-up,
        .beam-down,
        .beam-up {
            animation: none;
        }
        .beam-down,
        .beam-up {
            display: none;
        }
    }
</style>

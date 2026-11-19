<script>
    import { onMount } from "svelte";
    import Nav from "./Nav.svelte";
    import Footer from "./Footer.svelte";
    import { ui } from "../../official/controller.svelte.js";
    import { initScrollReveal } from "../../official/scrollReveal.js";

    onMount(() => initScrollReveal(document.querySelector(".route-page")));

    let { active = "home", children } = $props();
</script>

<div
    class="app-shell min-h-screen bg-[#0a0c13] text-slate-100"
    class:light-mode={ui.light}
    class:theme-scanning={ui.scanTransitioning}
>
    <Nav {active} />
    <div class="route-page">
        {@render children()}
    </div>
    <Footer />
    {#if ui.scanBarActive}
        <span
            class="theme-scanline"
            style={`transform: translateY(${ui.scanBarAtEnd ? "100vh" : "0"})`}
            aria-hidden="true"
        ></span>
    {/if}
</div>

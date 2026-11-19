<script>
    import { onMount } from "svelte";
    import Nav from "./Nav.svelte";
    import Footer from "./Footer.svelte";
    import { ui } from "../../official/controller.svelte.js";
    import { initScrollReveal } from "../../official/scrollReveal.js";

    onMount(() => initScrollReveal(document.querySelector(".route-page")));

    let { active = "home", children } = $props();
</script>

<div class="app-shell min-h-screen bg-[#0a0c13] text-slate-100" class:light-mode={ui.light}>
    <Nav {active} />
    <div class="route-page">
        {@render children()}
    </div>
    <Footer />
</div>

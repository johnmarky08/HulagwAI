<script>
    import { onMount } from "svelte";
    import { session, refreshSession } from "../../api/session.svelte.js";
    import LoginModal from "./LoginModal.svelte";

    // Wraps signed-in-only content: blurred and inert for guests, with a prompt to log in.
    // Blur applies only once the session is known to be a guest, so signed-in users never see it flash.
    let { children } = $props();
    let loginOpen = $state(false);

    function portal(node) {
        document.body.append(node);
        return {
            destroy() {
                node.remove();
            },
        };
    }
    const known = $derived(session.value !== undefined);
    const signedIn = $derived(session.value?.authenticated === true);
    const locked = $derived(known && !signedIn);

    onMount(() => {
        void refreshSession();
    });
</script>

<div class="login-gate relative">
    <div class="login-gate-content" class:locked inert={!signedIn}>
        {@render children?.()}
    </div>
    <!-- Moved to <body>: page wrappers with transform/filter would otherwise turn "fixed" into "absolute". -->
    <div class="login-gate-layer" use:portal>
        {#if locked}
            <div class="login-gate-overlay">
                <div
                    class="login-gate-card"
                    role="region"
                    aria-labelledby="login-gate-title"
                >
                    <span class="login-gate-icon" aria-hidden="true">
                        <svg
                            viewBox="0 0 24 24"
                            class="size-6"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            ><rect
                                x="4"
                                y="11"
                                width="16"
                                height="10"
                                rx="2"
                            /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg
                        >
                    </span>
                    <h2 id="login-gate-title">Log in to use</h2>
                    <p>Don't worry, you can still use the other features.</p>
                    <button
                        type="button"
                        class="login-gate-primary"
                        onclick={() => (loginOpen = true)}>Log in</button
                    >
                </div>
            </div>
        {/if}
        {#if loginOpen}
            <LoginModal onClose={() => (loginOpen = false)} />
        {/if}
    </div>
</div>

<style>
    .login-gate-content.locked {
        filter: blur(7px);
        user-select: none;
        pointer-events: none;
    }
    /* Fixed to the viewport so the prompt stays in view wherever the user has scrolled.
       Above the nav (z-50) but below the login modal (z-100). */
    .login-gate-overlay {
        position: fixed;
        inset: 0;
        z-index: 60;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1.5rem;
        pointer-events: none;
    }
    .login-gate-card {
        width: min(92%, 28rem);
        border: 1px solid rgb(129 140 248 / 45%);
        border-radius: 1.25rem;
        background: rgb(15 23 42 / 96%);
        padding: 1.75rem;
        text-align: center;
        box-shadow: 0 30px 70px -24px rgb(0 0 0 / 75%);
        pointer-events: auto;
    }
    .login-gate-card h2 {
        font-size: 1.25rem;
        font-weight: 800;
        color: #fff;
    }
    .login-gate-card p {
        margin-top: 0.5rem;
        font-size: 0.875rem;
        line-height: 1.5;
        color: #cbd5e1;
    }
    .login-gate-icon {
        display: grid;
        place-items: center;
        width: 3rem;
        height: 3rem;
        margin: 0 auto 1rem;
        border: 1px solid rgb(129 140 248 / 40%);
        border-radius: 999px;
        background: rgb(99 102 241 / 18%);
        color: #c7d2fe;
    }
    .login-gate-primary {
        margin-top: 1.25rem;
        min-height: 2.75rem;
        padding: 0 1.75rem;
        border-radius: 0.75rem;
        background: #4f46e5;
        color: #fff;
        font-size: 0.875rem;
        font-weight: 700;
        transition: background-color 0.15s ease;
    }
    .login-gate-primary:hover {
        background: #6366f1;
    }
    .login-gate-primary:focus-visible {
        outline: 2px solid #a5b4fc;
        outline-offset: 3px;
    }

    :global(.app-shell.light-mode) .login-gate-card {
        border-color: #c7d2fe;
        background: #fffdf8;
        box-shadow: 0 30px 70px -28px rgb(67 56 202 / 35%);
    }
    :global(.app-shell.light-mode) .login-gate-card h2 {
        color: #29251f;
    }
    :global(.app-shell.light-mode) .login-gate-card p {
        color: #4a453d;
    }
    :global(.app-shell.light-mode) .login-gate-icon {
        background: #e0e7ff;
        color: #4338ca;
        border-color: #c7d2fe;
    }
</style>

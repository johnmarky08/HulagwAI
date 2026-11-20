<script>
    import { onMount } from "svelte";
    import { session, refreshSession } from "../../api/session.svelte.js";

    // Full-page link (not Inertia): the server redirects to Google and back to /auth/google/callback.
    let { label = "Continue with Google" } = $props();
    const enabled = $derived(session.value?.auth?.google === true);
    const known = $derived(session.value !== undefined);

    onMount(() => {
        if (!known) void refreshSession();
    });

    const classes =
        "flex w-full items-center justify-center gap-3 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm font-medium text-slate-100 transition";
</script>

{#if enabled}
    <a href="/auth/google/redirect" class={`${classes} hover:bg-slate-800`}>
        <svg class="size-5 shrink-0" viewBox="0 0 48 48" aria-hidden="true">
            <path
                fill="#FFC107"
                d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
            />
            <path
                fill="#FF3D00"
                d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
            />
            <path
                fill="#4CAF50"
                d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
            />
            <path
                fill="#1976D2"
                d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.022 35.483 44 30.027 44 24c0-1.341-.138-2.65-.389-3.917z"
            />
        </svg>
        <span>{label}</span>
    </a>
{:else}
    <button
        type="button"
        disabled
        title={known
            ? "Google sign-in is not configured on this server"
            : "Checking sign-in options…"}
        class={`${classes} opacity-60`}
    >
        <svg class="size-5 shrink-0" viewBox="0 0 48 48" aria-hidden="true">
            <path
                fill="#FFC107"
                d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
            />
            <path
                fill="#FF3D00"
                d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
            />
            <path
                fill="#4CAF50"
                d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
            />
            <path
                fill="#1976D2"
                d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.022 35.483 44 30.027 44 24c0-1.341-.138-2.65-.389-3.917z"
            />
        </svg>
        <span>{label}</span>
    </button>
{/if}

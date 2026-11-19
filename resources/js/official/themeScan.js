import { tick } from "svelte";

const SCAN_DURATION = 680;

export async function scanThemeChange(state, applyThemeChange) {
    if (state.scanTransitioning) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) {
        applyThemeChange();
        return;
    }

    if (typeof document.startViewTransition !== "function") {
        state.scanBarActive = true;
        state.scanBarAtEnd = false;
        await tick();
        applyThemeChange();
        state.scanBarAtEnd = true;
        window.setTimeout(() => {
            state.scanBarActive = false;
            state.scanBarAtEnd = false;
        }, SCAN_DURATION);
        return;
    }

    state.scanTransitioning = true;
    state.scanBarActive = true;
    state.scanBarAtEnd = false;
    await tick();

    let themeApplied = false;
    const applyTheme = () => {
        if (themeApplied) return;
        themeApplied = true;
        applyThemeChange();
        state.scanBarAtEnd = true;
    };

    try {
        const transition = document.startViewTransition(async () => {
            applyTheme();
            await tick();
        });
        await transition.finished;
    } catch {
        // If the transition is interrupted, still apply the requested theme.
        applyTheme();
    } finally {
        state.scanBarActive = false;
        state.scanBarAtEnd = false;
        state.scanTransitioning = false;
    }
}

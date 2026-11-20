import { auth } from "./auth";

// Shared signed-in state. Kept in module memory so Inertia page changes (which remount
// components but keep this module alive) render the last known state immediately,
// instead of blurring signed-in users while /me is pending.
// `value` is undefined until the first /me response is known.
export const session = $state({ value: undefined });

let inFlight = null;

export function refreshSession() {
    if (!inFlight) {
        inFlight = auth
            .me()
            .then((result) => {
                session.value = result;
            })
            .catch(() => {
                // Unknown on a cold load: treat as guest. Keep a known value if one exists.
                if (session.value === undefined) session.value = { authenticated: false, user: null };
            })
            .finally(() => {
                inFlight = null;
            });
    }
    return inFlight;
}

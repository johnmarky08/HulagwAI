const SCAN_DURATION = 980;

export function scanThemeChange() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const app = document.querySelector(".app-shell");
    if (!app) return;

    document.querySelectorAll(".mode-scan-overlay").forEach((overlay) => overlay.remove());

    const bounds = app.getBoundingClientRect();
    const overlay = document.createElement("div");
    overlay.className = "mode-scan-overlay";
    overlay.setAttribute("aria-hidden", "true");
    overlay.style.setProperty("--scan-duration", `${SCAN_DURATION}ms`);

    const snapshot = app.cloneNode(true);
    snapshot.classList.add("mode-scan-snapshot");
    snapshot.querySelector(".route-page")?.classList.remove("route-page");
    snapshot.style.left = `${bounds.left}px`;
    snapshot.style.top = `${bounds.top}px`;
    snapshot.style.width = `${bounds.width}px`;
    overlay.append(snapshot);
    document.body.append(overlay);

    overlay.addEventListener("animationend", () => overlay.remove(), { once: true });
    window.setTimeout(() => overlay.remove(), SCAN_DURATION + 120);
}

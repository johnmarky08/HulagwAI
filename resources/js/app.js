import "./bootstrap";
import { createInertiaApp, router } from "@inertiajs/svelte";
import { mount } from "svelte";
import { selectFile, syncPage, ui } from "./official/controller.svelte.js";

// Follow the Laravel/Inertia route table without forcing full document reloads.
router.on("navigate", syncPage);
window.addEventListener("paste", (event) => {
    if (ui.page !== "detect" || ui.phase !== "upload") return;
    const image = [...(event.clipboardData?.items ?? [])]
        .find((item) => item.type.startsWith("image/"))
        ?.getAsFile();
    if (!image) return;
    // The server checks that the extension matches the real content, so name the file after its type.
    const extension = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" }[image.type];
    if (!extension) {
        selectFile(new File([image], "pasted-image.unsupported", { type: image.type })); // shows the format error
        return;
    }
    selectFile(new File([image], `pasted-image.${extension}`, { type: image.type }));
});

createInertiaApp({
    resolve: (name) => {
        const pages = import.meta.glob("./Pages/**/*.svelte", { eager: true });
        return pages[`./Pages/${name}.svelte`];
    },
    setup({ el, App, props }) {
        mount(App, { target: el, props });
    },
});

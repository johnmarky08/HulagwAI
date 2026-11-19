import { router } from "@inertiajs/svelte";
import { ui, selectFile } from "./controller.svelte.js";

export function openQuickDetection(event) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    selectFile(file);
    if (!ui.error) router.visit("/detect");
    input.value = "";
}

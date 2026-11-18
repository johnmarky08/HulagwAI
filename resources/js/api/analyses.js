import { http } from "./client";

export const analyses = {
    /** @returns {Promise<{id:string,status:string,progress:number,steps:Array}>} */
    async upload(file, onProgress) {
        const body = new FormData();
        body.append("image", file);
        const { data } = await http.post("/analyses", body, {
            onUploadProgress: (e) => onProgress?.(e.total ? Math.round((e.loaded / e.total) * 100) : 0),
        });
        return data;
    },
    async get(id) {
        return (await http.get(`/analyses/${id}`)).data;
    },
    async remove(id) {
        return (await http.delete(`/analyses/${id}`)).data; // cancels if running, deletes if finished
    },
    imageUrl: (id, variant = "preview") => `/api/v1/analyses/${id}/image?variant=${variant}`,
    reportUrl: (id) => `/api/v1/analyses/${id}/report`,

    /** Polls until done/failed. Returns the final payload. Call `signal.cancelled = true` to stop. */
    async waitFor(id, onUpdate, signal = { cancelled: false }) {
        for (;;) {
            const s = await this.get(id);
            onUpdate?.(s);
            if (s.status === "done" || s.status === "failed") return s;
            if (signal.cancelled) return s;
            await new Promise((r) => setTimeout(r, 700));
        }
    },
};

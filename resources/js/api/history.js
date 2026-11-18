import { http } from "./client";

export const history = {
    /** params: {search,result:'all|real|ai_generated|inconclusive',range:'all|7d|30d|90d',sort,page} */
    async list(params = {}) {
        return (await http.get("/history", { params })).data; // {data:[...],meta:{...},stats:{...}}
    },
    async clear() {
        return (await http.delete("/history")).data;
    },
    exportUrl: (format = "csv") => `/api/v1/history/export?format=${format}`,
};

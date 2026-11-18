// ─────────────────────────────────────────────────────────────────────────────
// API layer: the ONLY place that knows URLs. The real frontend can keep these
// files and just replace Pages/, Layouts/ and Components/. See docs/API.md.
// Cookies + CSRF are handled automatically (Laravel sets XSRF-TOKEN, axios echoes it).
// ─────────────────────────────────────────────────────────────────────────────
import axios from "axios";

export const http = axios.create({
    baseURL: "/api/v1",
    withCredentials: true,
    headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
});

/** Root-level (non /api) JSON calls: /login, /register, /logout */
export const web = axios.create({
    baseURL: "/",
    withCredentials: true,
    headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
});

export function errorMessage(e) {
    const d = e?.response?.data;
    return d?.errors ? Object.values(d.errors).flat().join(" ") : d?.message || e?.message || "Something went wrong.";
}

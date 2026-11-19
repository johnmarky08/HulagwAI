import sampleArt from "../../images/sample-art.jpg";
import { analyses } from "../api/analyses";
import { errorMessage } from "../api/client";
import { history } from "../api/history";
import { scanThemeChange } from "./themeScan.js";

const maxBytes = 5 * 1024 * 1024;
const verdicts = {
    "All results": "all",
    Real: "real",
    "AI-generated": "ai_generated",
    Inconclusive: "inconclusive",
};
const ranges = {
    "All time": "all",
    "Last 7 days": "7d",
    "Last 30 days": "30d",
    "Last 90 days": "90d",
};

function getPage() {
    return (
        {
            "/": "home",
            "/dashboard": "dashboard",
            "/detect": "detect",
            "/history": "history",
            "/about": "about",
        }[location.pathname] ?? "home"
    );
}

export const ui = $state({
    page: getPage(),
    phase: "upload",
    file: null,
    preview: "",
    resultPreview: "",
    analysis: null,
    result: null,
    error: "",
    errorTitle: "Invalid file format",
    historyError: "",
    loadingHistory: false,
    loadingResult: false,
    progress: 0,
    steps: [],
    light: false,
    search: "",
    verdictFilter: "All results",
    dateFilter: "All time",
    historyPage: 1,
    rows: [],
    stats: { total: 0, likely_real: 0, ai_generated: 0, inconclusive: 0 },
    meta: { page: 1, per_page: 6, total: 0, last_page: 1, from: 0, to: 0 },
    displayTitle: "",
    displayFormat: "",
    displaySize: "",
    analyzedDate: "",
    verdictLabel: "",
    verdictClass: "ai",
    aiPercent: 0,
    realPercent: 0,
    explanation: "",
    howToRead: "",
    persisted: false,
    reportUrl: "",
});

export const sampleImage = sampleArt;
let activeSignal = null;
let searchTimer = null;
let historyRequest = 0;

function setFinalAnalysis(payload) {
    const file = payload.file ?? {};
    const result = payload.result ?? {};
    const verdict = result.verdict ?? "inconclusive";
    ui.analysis = payload;
    ui.result = result;
    ui.displayTitle =
        file.name ??
        (file.filename ?? ui.file?.name ?? "Uploaded image").replace(
            /\.[^.]+$/,
            "",
        );
    ui.displayFormat =
        file.format ??
        ui.file?.type?.split("/").at(-1)?.toUpperCase() ??
        "Image";
    ui.displaySize = Number(
        file.size_mb ?? (file.size_bytes ?? ui.file?.size ?? 0) / 1048576,
    ).toFixed(2);
    ui.analyzedDate = payload.analyzed_at
        ? new Date(payload.analyzed_at).toLocaleDateString()
        : new Date().toLocaleDateString();
    ui.verdictLabel =
        result.label ??
        (verdict === "ai_generated"
            ? "Likely AI-generated"
            : verdict === "real"
              ? "Likely real"
              : "Inconclusive");
    ui.verdictClass =
        verdict === "real"
            ? "real"
            : verdict === "inconclusive"
              ? "inconclusive"
              : "ai";
    ui.aiPercent = Math.round(
        result.ai_percent ?? (result.ai_probability ?? 0) * 100,
    );
    ui.realPercent = Math.round(
        result.real_percent ??
            (result.real_probability ?? 1 - ui.aiPercent / 100) * 100,
    );
    ui.explanation = result.explanation ?? "The analysis is complete.";
    ui.howToRead =
        result.how_to_read ??
        "Confidence describes how strongly the model favors its prediction. It is not proof of authenticity.";
    ui.persisted = Boolean(payload.persisted);
    ui.resultPreview = payload.id
        ? analyses.imageUrl(payload.id, "thumb")
        : ui.preview;
    ui.reportUrl = payload.id ? analyses.reportUrl(payload.id) : "";
}

export function toggleTheme() {
    scanThemeChange();
    ui.light = !ui.light;
}

export function selectFile(file) {
    if (!file) return;
    ui.error = "";
    ui.errorTitle = "Invalid file format";
    if (!/\.(jpe?g|png|webp)$/i.test(file.name)) {
        ui.file = null;
        ui.preview = "";
        ui.error = `“${file.name}” is not supported. Please use JPG, JPEG, PNG, WEBP`;
        return;
    }
    if (file.size > maxBytes) {
        ui.file = null;
        ui.preview = "";
        ui.error =
            "This image is larger than 5 MB. Please choose a smaller file.";
        return;
    }
    if (ui.preview.startsWith("blob:")) URL.revokeObjectURL(ui.preview);
    ui.file = file;
    ui.preview = URL.createObjectURL(file);
    ui.result = null;
    ui.analysis = null;
}

export function removeFile() {
    if (ui.preview.startsWith("blob:")) URL.revokeObjectURL(ui.preview);
    ui.file = null;
    ui.preview = "";
    ui.resultPreview = "";
    ui.analysis = null;
    ui.result = null;
    ui.error = "";
    ui.phase = "upload";
    ui.progress = 0;
}

export async function startAnalysis() {
    if (!ui.file || ui.phase === "analyzing") return;
    ui.phase = "analyzing";
    ui.progress = 0;
    ui.error = "";
    const signal = { cancelled: false };
    activeSignal = signal;
    try {
        const queued = await analyses.upload(ui.file, (percent) => {
            ui.progress = Math.max(ui.progress, Math.round(percent * 0.2));
        });
        if (signal.cancelled) {
            await analyses.remove(queued.id).catch(() => {});
            return;
        }
        ui.analysis = queued;
        ui.steps = queued.steps ?? [];
        const final =
            queued.status === "done"
                ? queued
                : await analyses.waitFor(
                      queued.id,
                      (status) => {
                          if (signal.cancelled) return;
                          ui.analysis = status;
                          ui.progress = status.progress ?? ui.progress;
                          ui.steps = status.steps ?? ui.steps;
                      },
                      signal,
                  );
        if (signal.cancelled) return;
        if (final.status === "failed") {
            ui.errorTitle = "Analysis failed";
            ui.error =
                final.error?.message ??
                "Analysis failed. Please try another image.";
            ui.phase = "upload";
            return;
        }
        setFinalAnalysis(final);
        ui.phase = "results";
    } catch (error) {
        if (!signal.cancelled) {
            ui.errorTitle = "Unable to analyze image";
            ui.error = errorMessage(error);
            ui.phase = "upload";
        }
    } finally {
        if (activeSignal === signal) activeSignal = null;
    }
}

export async function cancelAnalysis() {
    if (activeSignal) activeSignal.cancelled = true;
    const id = ui.analysis?.id;
    if (id) await analyses.remove(id).catch(() => {});
    activeSignal = null;
    ui.phase = "upload";
    ui.analysis = null;
    ui.progress = 0;
}

export function setHistorySearch(value) {
    ui.search = value;
    ui.historyPage = 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => void loadHistory(), 250);
}

export function setHistoryFilter(kind, value) {
    if (kind === "result") ui.verdictFilter = value;
    if (kind === "range") ui.dateFilter = value;
    ui.historyPage = 1;
    void loadHistory();
}

export async function loadHistory() {
    const request = ++historyRequest;
    ui.loadingHistory = true;
    ui.historyError = "";
    try {
        const response = await history.list({
            search: ui.search,
            result: verdicts[ui.verdictFilter] ?? "all",
            range: ranges[ui.dateFilter] ?? "all",
            sort: "newest",
            page: ui.historyPage,
            per_page: 6,
        });
        if (request !== historyRequest) return;
        ui.rows = response.data ?? [];
        ui.stats = response.stats ?? ui.stats;
        ui.meta = response.meta ?? ui.meta;
    } catch (error) {
        if (request === historyRequest) {
            ui.historyError = errorMessage(error);
            ui.rows = [];
        }
    } finally {
        if (request === historyRequest) ui.loadingHistory = false;
    }
}

export async function loadAnalysisById(id) {
    ui.loadingResult = true;
    ui.phase = "analyzing";
    ui.error = "";
    try {
        let payload = await analyses.get(id);
        const file = payload.file ?? {};
        ui.file = {
            name: file.filename ?? file.name ?? "Analyzed image",
            type: `image/${file.format?.toLowerCase() ?? "jpeg"}`,
            size: file.size_bytes ?? 0,
        };
        ui.resultPreview = analyses.imageUrl(id, "thumb");
        if (payload.status !== "done" && payload.status !== "failed") {
            const signal = { cancelled: false };
            activeSignal = signal;
            ui.analysis = payload;
            ui.phase = "analyzing";
            ui.progress = payload.progress ?? 0;
            ui.steps = payload.steps ?? [];
            payload = await analyses.waitFor(
                id,
                (status) => {
                    if (signal.cancelled) return;
                    ui.analysis = status;
                    ui.progress = status.progress ?? ui.progress;
                    ui.steps = status.steps ?? ui.steps;
                },
                signal,
            );
            if (signal.cancelled) return;
            if (activeSignal === signal) activeSignal = null;
        }
        if (payload.status === "failed")
            throw new Error(payload.error?.message ?? "This analysis failed.");
        setFinalAnalysis(payload);
        ui.phase = "results";
    } catch (error) {
        ui.errorTitle = "Unable to load analysis";
        ui.error = errorMessage(error);
        ui.phase = "upload";
    } finally {
        ui.loadingResult = false;
    }
}

export function exportHistory() {
    window.location.assign(history.exportUrl("csv"));
}
export function formatDate(value) {
    return value ? new Date(value).toLocaleDateString() : "—";
}

let currentAnalysisId = null;
export function syncPage() {
    ui.page = getPage();
    const analysisId = new URLSearchParams(location.search).get("analysis");

    if (ui.page === "history") void loadHistory();
    if (
        ui.page === "detect" &&
        analysisId &&
        analysisId !== currentAnalysisId
    ) {
        currentAnalysisId = analysisId;
        void loadAnalysisById(analysisId);
    } else if (!analysisId) {
        currentAnalysisId = null;
    }
}
export function clearError() {
    ui.error = "";
}
export function allowDrop(event) {
    event.preventDefault();
}
export function handleFileInput(event) {
    selectFile(event.currentTarget.files?.[0]);
}
export function handleFileDrop(event) {
    event.preventDefault();
    selectFile(event.dataTransfer.files?.[0]);
}
export function handleHistorySearch(event) {
    setHistorySearch(event.currentTarget.value);
}
export function handleResultFilter(event) {
    setHistoryFilter("result", event.currentTarget.value);
}
export function handleRangeFilter(event) {
    setHistoryFilter("range", event.currentTarget.value);
}
export function handleHistoryPage(event) {
    ui.historyPage = Number(event.currentTarget.dataset.page);
    void loadHistory();
}
export function previousHistoryPage() {
    ui.historyPage = Math.max(1, ui.historyPage - 1);
    void loadHistory();
}
export function nextHistoryPage() {
    ui.historyPage = Math.min(ui.meta.last_page, ui.historyPage + 1);
    void loadHistory();
}

if (ui.page === "history") void loadHistory();
const analysisId = new URLSearchParams(location.search).get("analysis");
if (ui.page === "detect" && analysisId) {
    currentAnalysisId = analysisId;
    void loadAnalysisById(analysisId);
}

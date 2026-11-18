// Starts the Python ML service (used by `composer run dev` via `npm run ml`).
// Looks for ml-service/.venv first; falls back to `python` on PATH. Binds to 127.0.0.1 only.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const cwd = join(dirname(fileURLToPath(import.meta.url)), "..", "ml-service");
const win = process.platform === "win32";
const venvPy = join(cwd, ".venv", win ? "Scripts" : "bin", win ? "python.exe" : "python");
const py = existsSync(venvPy) ? venvPy : win ? "python" : "python3";

if (!existsSync(join(cwd, ".env"))) {
    console.error("[ml] ml-service/.env is missing. Copy ml-service/.env.example to ml-service/.env and set ML_SERVICE_TOKEN (see README).");
    process.exit(1);
}
const port = process.env.ML_PORT || "8001";
const child = spawn(py, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port], { cwd, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));

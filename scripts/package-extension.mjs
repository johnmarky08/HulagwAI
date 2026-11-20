import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { zipSync } from "fflate";

const root = resolve("browser-extension");
const manifest = JSON.parse(readFileSync(join(root, "manifest.json"), "utf8"));
const files = {};

function addDirectory(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
        const absolute = join(directory, entry.name);
        if (entry.isDirectory()) {
            addDirectory(absolute);
            continue;
        }
        const archivePath = relative(root, absolute).split(sep).join("/");
        files[archivePath] = new Uint8Array(readFileSync(absolute));
    }
}

addDirectory(root);
const archive = zipSync(files, { level: 9 });
const output = resolve(
    "public/downloads",
    `hulagwai-image-scanner-v${manifest.version}.zip`,
);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, archive);
console.log(`Packaged ${Object.keys(files).length} extension files: ${output}`);

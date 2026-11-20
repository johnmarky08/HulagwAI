"""Provenance / metadata forensics.

Looks for *declared* AI origin inside the file: C2PA / JUMBF containers, IPTC "DigitalSourceType",
generator signatures in EXIF/XMP/PNG text chunks (Stable Diffusion WebUI "parameters", ComfyUI
"prompt"/"workflow", NovelAI, Midjourney, DALL-E, Firefly ...).

Security: the file is attacker-controlled, so nothing here is parsed with an XML/JSON parser (no XXE,
no billion-laughs, no deserialisation). Only bounded byte/regex searches and Pillow's own header
readers are used, and every evidence string is cleaned and truncated before it leaves this module.

Absence of metadata proves nothing (platforms strip it); presence of camera EXIF is reported but never
used to *lower* the AI score, because it can be copied onto a synthetic image in seconds.
"""
from __future__ import annotations

import re
from typing import Any

from PIL import Image

AI_TOOLS = re.compile(
    r"(midjourney|stable[ _-]?diffusion|\bsdxl\b|dall[ ._·•-]?e|adobe firefly|\bfirefly\b|comfyui|automatic1111|"
    r"invoke ?ai|novel ?ai|leonardo\.ai|ideogram|\bflux[ .-]?[0-9a-z]*|imagen|runwayml|dreamstudio|"
    r"playground ?ai|bing image creator|nightcafe|craiyon|openai|gpt-?image|sora|\bgrok\b|nano ?banana|"
    r"\bgemini\b|\bkandinsky\b|\bwombo\b|\bdeepai\b)",
    re.I,
)
C2PA_GENERATOR = re.compile(r"(midjourney|openai|dall[-·. ]?e[ -]?[0-9]?|adobe firefly|firefly|imagen|gemini|stable diffusion|flux|ideogram|gpt-?image|sora|grok)", re.I)
DIGITAL_SOURCE_AI = (b"trainedAlgorithmicMedia", b"compositeWithTrainedAlgorithmicMedia", b"algorithmicMedia")
XMP_MAX = 1_000_000

_CTRL = re.compile(r"[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]")


def _clean(value: Any, limit: int = 160) -> str:
    s = value.decode("utf-8", "replace") if isinstance(value, (bytes, bytearray)) else str(value)
    return _CTRL.sub(" ", s).strip()[:limit]


def _finding(fid: str, severity: str, title: str, evidence: str = "", generator: str | None = None) -> dict[str, str]:
    f = {"id": fid, "severity": severity, "title": title, "evidence": _clean(evidence)}
    if generator:
        f["generator"] = _clean(generator, 60)   # name the file itself declares (feeds the attribution)
    return f


def extract(raw: bytes, img: Image.Image) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    out: dict[str, Any] = {"findings": findings, "c2pa": {"present": False, "ai_claim": False}, "exif": {}, "strong_ai": False}

    # --- C2PA / JUMBF (Content Credentials) -----------------------------------------------------
    jumbf = b"jumb" in raw and b"c2pa" in raw
    ai_source = next((m for m in DIGITAL_SOURCE_AI if m in raw), None)
    out["c2pa"] = {"present": jumbf, "ai_claim": bool(jumbf and ai_source)}
    if jumbf:
        j = raw.find(b"jumb")
        gen = C2PA_GENERATOR.search(raw[j:j + 65536].decode("latin-1"))
        if gen:
            findings.append(_finding("c2pa_generator", "strong_ai", "C2PA manifest names an AI generator", gen.group(0), gen.group(0)))
        findings.append(_finding("c2pa_present", "info", "C2PA / Content Credentials container present",
                                 "signature not cryptographically verified by HulagwAI"))
    if ai_source:
        findings.append(_finding("digital_source_ai", "strong_ai",
                                 "File declares synthetic origin (IPTC/C2PA DigitalSourceType)", ai_source.decode()))

    # --- XMP packet -----------------------------------------------------------------------------
    start = raw.find(b"<x:xmpmeta")
    if start != -1:
        end = raw.find(b"</x:xmpmeta>", start, start + XMP_MAX)
        xmp = raw[start: (end + 12 if end != -1 else start + 65536)]
        out["xmp_present"] = True
        m = re.search(rb'CreatorTool(?:=|>)\s*"?([^"<]{1,200})', xmp)
        if m and AI_TOOLS.search(m.group(1).decode("utf-8", "ignore")):
            findings.append(_finding("xmp_creator_tool_ai", "strong_ai", "XMP CreatorTool names an AI generator", m.group(1), m.group(1).decode("utf-8", "ignore")))
        elif m:
            out["exif"]["xmp_creator_tool"] = _clean(m.group(1), 80)

    # --- EXIF (JPEG / WEBP / PNG eXIf) ----------------------------------------------------------
    try:
        exif = img.getexif()
    except Exception:  # corrupt EXIF must never break the analysis
        exif = {}
    if exif:
        make, model, software = (_clean(exif.get(t, ""), 80) for t in (271, 272, 305))
        out["exif"].update({"make": make or None, "model": model or None, "software": software or None})
        try:
            ifd = exif.get_ifd(0x8769)
            out["exif"]["has_exposure_data"] = any(t in ifd for t in (33434, 33437, 34855))
            comment = ifd.get(37510)
        except Exception:
            comment = None
        try:
            out["exif"]["has_gps"] = bool(exif.get_ifd(0x8825))  # presence only - coordinates are never read out
        except Exception:
            pass
        for label, val in (("Software", software), ("ImageDescription", _clean(exif.get(270, ""), 200)),
                           ("UserComment", _clean(comment or "", 200))):
            if val and AI_TOOLS.search(val):
                findings.append(_finding("exif_ai_signature", "strong_ai", f"EXIF {label} names an AI generator", val, val))
        if make or model:
            findings.append(_finding("camera_exif", "info", "Camera make/model present in EXIF",
                                     f"{make} {model}".strip() + " (can be forged; not used to adjust the score)"))

    # --- PNG text chunks / generic Pillow info -----------------------------------------------------
    info = dict(getattr(img, "info", {}) or {})
    text = dict(getattr(img, "text", {}) or {}) if hasattr(img, "text") else {}
    chunks = {**{str(k): v for k, v in info.items() if isinstance(v, (str, bytes))}, **{str(k): v for k, v in text.items()}}
    out["text_keys"] = sorted({_clean(k, 40) for k in chunks})[:30]
    for key, val in chunks.items():
        sval = _clean(val, 4000)
        lk = key.lower()
        if lk == "parameters" and re.search(r"\bSteps:\s*\d+", sval) and re.search(r"(Sampler|CFG scale|Seed):", sval):
            mdl = re.search(r"Model:\s*([^,\n]{1,60})", sval)
            findings.append(_finding("sd_webui_parameters", "strong_ai", "Stable Diffusion WebUI generation parameters embedded", sval[:120],
                                     mdl.group(1) if mdl else "Stable Diffusion WebUI"))
        elif lk in {"prompt", "workflow"} and '"class_type"' in sval:
            findings.append(_finding("comfyui_graph", "strong_ai", "ComfyUI workflow embedded", key))
        elif lk in {"invokeai_metadata", "sd-metadata", "dream", "generation_time"}:
            findings.append(_finding("sd_tool_metadata", "strong_ai", "Generator-specific metadata chunk", key))
        elif lk in {"software", "comment", "description", "title", "author", "source", "creator"} and AI_TOOLS.search(sval):
            findings.append(_finding("text_chunk_ai", "strong_ai", f"'{_clean(key, 30)}' field names an AI generator", sval, sval))

    # de-duplicate by (id, evidence)
    seen, uniq = set(), []
    for f in findings:
        k = (f["id"], f["evidence"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    out["findings"] = uniq[:20]
    out["strong_ai"] = any(f["severity"] == "strong_ai" for f in uniq)
    return out

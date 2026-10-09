#!/usr/bin/env python3
"""
Dukaan Bench - image generation harness.

Design goal: MODULAR. The eval must run whether you have API keys or not.

Three ways to use this file:

  1. FULL API MODE - generate everything via API
       python generate.py --all

  2. PARTIAL API MODE - generate only the models you have keys for
       python generate.py --models gemini_2_5_flash_image,gemini_3_1_flash_image_preview

  3. MANUAL MODE - you generated images by hand in ChatGPT / AI Studio.
     Drop them in images/<model_key>/ and run:
       python generate.py --register-manual
     This hashes each file, writes the same manifest rows the API path writes,
     and tells you which (model, prompt) cells are still missing.

Whichever path you use, the output contract is IDENTICAL:

  images/<model_key>/<prompt_id>__<model_key>__run<N>.png
  evidence/manifest.csv      <- one row per image, the provenance record
  evidence/raw/<...>.json    <- raw API response metadata (API mode only)

manifest.csv is the file the analysis and the rating tool both read, so the
rest of the pipeline does not know or care how the images were made.

Install:  pip install -r requirements.txt
Keys:     copy .env.example to .env and fill in what you have
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT_SET = ROOT / "prompts" / "prompt_set_v1.json"
IMAGES_DIR = ROOT / "images"
EVIDENCE_DIR = ROOT / "evidence"
MANIFEST = EVIDENCE_DIR / "manifest.csv"
RAW_DIR = EVIDENCE_DIR / "raw"

MANIFEST_FIELDS = [
    "image_id",          # P01__gpt_image_1__run1
    "prompt_id",
    "model_key",
    "company",           # exact company name  (required by the brief)
    "model_name",        # exact model name    (required by the brief)
    "api_model_id",
    "run_index",
    "script",
    "language",
    "target_text",       # pipe-separated ground-truth strings
    "prompt_text",       # the exact prompt sent
    "generated_via",     # api | web_ui
    "generation_surface",# e.g. "OpenAI Images API" / "Google AI Studio (web)"
    "settings_json",     # all settings used, as JSON
    "aspect_requested",
    "output_path",
    "sha256",
    "bytes",
    "generated_at_utc",
    "deviation_notes",   # <- document any per-model workflow difference HERE
    "error",
]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def load_prompt_set() -> dict:
    with open(PROMPT_SET, encoding="utf-8") as f:
        return json.load(f)


def load_dotenv() -> None:
    """Minimal .env loader so we don't add a dependency for three lines."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_manifest(rows: list[dict]) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def upsert_manifest(row: dict) -> None:
    rows = read_manifest()
    rows = [r for r in rows if r.get("image_id") != row["image_id"]]
    rows.append(row)
    rows.sort(key=lambda r: (r.get("prompt_id", ""), r.get("model_key", ""), r.get("run_index", "")))
    write_manifest(rows)


def image_id_for(prompt_id: str, model_key: str, run_index: int) -> str:
    return f"{prompt_id}__{model_key}__run{run_index}"


def base_row(prompt: dict, model: dict, run_index: int) -> dict:
    return {
        "image_id": image_id_for(prompt["id"], model["key"], run_index),
        "prompt_id": prompt["id"],
        "model_key": model["key"],
        "company": model["company"],
        "model_name": model["model_name"],
        "api_model_id": model.get("api_model_id", ""),
        "run_index": run_index,
        "script": prompt["script"],
        "language": prompt["language"],
        "target_text": "|".join(prompt["target_text"]),
        "prompt_text": prompt["full_prompt"],
        "aspect_requested": prompt.get("aspect", "portrait"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "deviation_notes": "",
        "error": "",
    }


def save_raw(image_id: str, payload: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{image_id}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------
# model adapters
#
# Each adapter has the same signature and returns (image_bytes, settings_dict,
# raw_metadata_dict, deviation_note). Adding a 4th model = adding one function
# and one dict entry. That is the whole point of this structure.
# ----------------------------------------------------------------------------

def gen_openai(prompt: dict, model: dict) -> tuple[bytes, dict, dict, str]:
    """OpenAI GPT Image 1 via the Images API."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    settings = {
        "model": model["api_model_id"],
        "size": "1024x1536",       # portrait
        "quality": "high",
        "n": 1,
    }
    resp = client.images.generate(prompt=prompt["full_prompt"], **settings)
    b64 = resp.data[0].b64_json
    if b64 is None:
        raise RuntimeError("OpenAI returned no b64_json payload")
    raw = {
        "created": getattr(resp, "created", None),
        "usage": getattr(resp, "usage", None).model_dump() if getattr(resp, "usage", None) else None,
        "revised_prompt": getattr(resp.data[0], "revised_prompt", None),
    }
    deviation = ""
    if raw.get("revised_prompt") and raw["revised_prompt"] != prompt["full_prompt"]:
        deviation = ("MODEL REWROTE THE PROMPT. OpenAI returned a revised_prompt that differs from "
                     "the prompt we sent. See evidence/raw/ for the exact revised text. This is a "
                     "real fairness caveat and must be reported, not hidden.")
    return base64.b64decode(b64), settings, raw, deviation


def gen_gemini(prompt: dict, model: dict) -> tuple[bytes, dict, dict, str]:
    """Google Gemini image models via google-genai."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    deviation = ""
    cfg_kwargs: dict = {"response_modalities": ["IMAGE"]}
    # Aspect-ratio control has moved around across Gemini image releases.
    # Try to request portrait; if the installed SDK rejects it, fall back to
    # the default and RECORD that, rather than silently changing the setup.
    try:
        cfg = types.GenerateContentConfig(
            **cfg_kwargs,
            image_config=types.ImageConfig(aspect_ratio="3:4"),
        )
        settings = {"model": model["api_model_id"], "aspect_ratio": "3:4",
                    "response_modalities": ["IMAGE"]}
    except (TypeError, AttributeError):
        cfg = types.GenerateContentConfig(**cfg_kwargs)
        settings = {"model": model["api_model_id"], "aspect_ratio": "SDK_DEFAULT",
                    "response_modalities": ["IMAGE"]}
        deviation = ("Installed google-genai SDK did not accept image_config.aspect_ratio; used the "
                     "model default aspect ratio instead. Documented per the brief's requirement to "
                     "record any per-model workflow difference.")

    resp = client.models.generate_content(
        model=model["api_model_id"],
        contents=prompt["full_prompt"],
        config=cfg,
    )

    img_bytes = None
    for cand in (resp.candidates or []):
        for part in (cand.content.parts or []):
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                img_bytes = data if isinstance(data, bytes) else base64.b64decode(data)
                break
        if img_bytes:
            break
    if img_bytes is None:
        fr = None
        try:
            fr = resp.candidates[0].finish_reason
        except Exception:
            pass
        raise RuntimeError(f"Gemini returned no image part (finish_reason={fr})")

    raw = {"model_version": getattr(resp, "model_version", None)}
    try:
        raw["usage"] = resp.usage_metadata.model_dump()
    except Exception:
        pass
    try:
        raw["finish_reason"] = str(resp.candidates[0].finish_reason)
    except Exception:
        pass
    return img_bytes, settings, raw, deviation


ADAPTERS = {
    "gpt_image_1": (gen_openai, "OPENAI_API_KEY", "OpenAI Images API"),
    "gemini_2_5_flash_image": (gen_gemini, "GEMINI_API_KEY", "Google Gemini API"),
    "gemini_3_1_flash_image_preview": (gen_gemini, "GEMINI_API_KEY", "Google Gemini API"),
}


# ----------------------------------------------------------------------------
# API mode
# ----------------------------------------------------------------------------

def run_api(model_keys: list[str], prompt_ids: list[str] | None,
            runs: int, overwrite: bool) -> None:
    spec = load_prompt_set()
    models = {m["key"]: m for m in spec["models"]}
    prompts = {p["id"]: p for p in spec["prompts"]}

    targets = prompt_ids or [p["id"] for p in spec["prompts"]]
    existing = {r["image_id"] for r in read_manifest() if not r.get("error")}

    for mk in model_keys:
        if mk not in models:
            print(f"  !! unknown model key '{mk}', skipping", file=sys.stderr)
            continue
        if mk not in ADAPTERS:
            print(f"  !! no API adapter for '{mk}'. Generate it manually and use "
                  f"--register-manual.", file=sys.stderr)
            continue

        fn, env_key, surface = ADAPTERS[mk]
        if not os.environ.get(env_key):
            print(f"\n[{mk}] SKIPPED - {env_key} not set.")
            print(f"         Generate these by hand instead (see MANUAL_WORKFLOW.md), "
                  f"then run --register-manual.")
            continue

        model = models[mk]
        (IMAGES_DIR / mk).mkdir(parents=True, exist_ok=True)
        print(f"\n[{mk}] {model['company']} - {model['model_name']}")

        for pid in targets:
            prompt = prompts[pid]
            for run_index in range(1, runs + 1):
                iid = image_id_for(pid, mk, run_index)
                out_path = IMAGES_DIR / mk / f"{iid}.png"
                if iid in existing and out_path.exists() and not overwrite:
                    print(f"  = {iid} (exists, skipping)")
                    continue

                row = base_row(prompt, model, run_index)
                row["generated_via"] = "api"
                row["generation_surface"] = surface
                try:
                    img, settings, raw, deviation = fn(prompt, model)
                    out_path.write_bytes(img)
                    row.update({
                        "settings_json": json.dumps(settings, ensure_ascii=False),
                        "output_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                        "sha256": sha256_of(out_path),
                        "bytes": out_path.stat().st_size,
                        "deviation_notes": deviation,
                    })
                    save_raw(iid, {"settings": settings, "raw": raw,
                                   "prompt": prompt["full_prompt"]})
                    print(f"  + {iid}  ({out_path.stat().st_size // 1024} KB)"
                          + ("  [DEVIATION LOGGED]" if deviation else ""))
                except Exception as e:  # noqa: BLE001 - we want to log and continue
                    row["error"] = f"{type(e).__name__}: {e}"
                    print(f"  x {iid}  FAILED: {row['error']}", file=sys.stderr)
                upsert_manifest(row)
                time.sleep(1.0)  # be polite to the APIs


# ----------------------------------------------------------------------------
# manual registration mode
# ----------------------------------------------------------------------------

def run_register_manual(surface_overrides: dict[str, str]) -> None:
    """
    Scan images/<model_key>/ for hand-generated files and write manifest rows.

    Expected filename: <prompt_id>__<model_key>__run<N>.<ext>
    e.g. P01__gpt_image_1__run1.png

    Anything that does not match that pattern is reported and skipped, so a
    typo in a filename can never silently become a mislabelled manifest row.
    """
    spec = load_prompt_set()
    models = {m["key"]: m for m in spec["models"]}
    for extra in spec.get("optional_additional_models", []):
        models.setdefault(extra["key"], {**extra, "api_model_id": ""})
    prompts = {p["id"]: p for p in spec["prompts"]}

    found, skipped = 0, []
    if not IMAGES_DIR.exists():
        print(f"No images/ directory yet. Create images/<model_key>/ and drop files in.")
        return

    for model_dir in sorted(p for p in IMAGES_DIR.iterdir() if p.is_dir()):
        mk = model_dir.name
        if mk not in models:
            skipped.append(f"{model_dir.name}/ - not a known model key in prompt_set_v1.json")
            continue
        model = models[mk]
        default_surface = {
            "gpt_image_1": "ChatGPT web UI (chatgpt.com)",
            "gemini_2_5_flash_image": "Google AI Studio (aistudio.google.com)",
            "gemini_3_1_flash_image_preview": "Google AI Studio (aistudio.google.com)",
        }.get(mk, "web UI")
        surface = surface_overrides.get(mk, default_surface)

        for f in sorted(model_dir.iterdir()):
            if f.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            stem = f.stem
            parts = stem.split("__")
            if len(parts) != 3 or not parts[2].startswith("run"):
                skipped.append(f"{f.name} - filename must be <prompt_id>__<model_key>__run<N>")
                continue
            pid, fmk, run_s = parts
            if pid not in prompts:
                skipped.append(f"{f.name} - unknown prompt_id '{pid}'")
                continue
            if fmk != mk:
                skipped.append(f"{f.name} - model key in filename ('{fmk}') != folder ('{mk}')")
                continue
            try:
                run_index = int(run_s[3:])
            except ValueError:
                skipped.append(f"{f.name} - run index not an integer")
                continue

            row = base_row(prompts[pid], model, run_index)
            row.update({
                "generated_via": "web_ui",
                "generation_surface": surface,
                "settings_json": json.dumps({"note": "recorded manually - see MANUAL_WORKFLOW.md"}),
                "output_path": str(f.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_of(f),
                "bytes": f.stat().st_size,
                "generated_at_utc": datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
            })
            upsert_manifest(row)
            found += 1
            print(f"  + registered {row['image_id']}")

    print(f"\nRegistered {found} manually-generated image(s).")
    if skipped:
        print(f"\nSkipped {len(skipped)} file(s) - fix these:")
        for s in skipped:
            print(f"  - {s}")
    print("\nIMPORTANT: --register-manual cannot know your web-UI settings. Open "
          "evidence/manifest.csv and fill in settings_json and deviation_notes for "
          "these rows by hand. The brief explicitly requires recorded settings.")


# ----------------------------------------------------------------------------
# coverage check
# ----------------------------------------------------------------------------

def run_status() -> None:
    spec = load_prompt_set()
    rows = read_manifest()
    ok = {(r["prompt_id"], r["model_key"]) for r in rows
          if not r.get("error") and r.get("output_path")}

    required_models = [m["key"] for m in spec["models"]]
    prompt_ids = [p["id"] for p in spec["prompts"]]

    print("\nDukaan Bench coverage - required 3 models x 10 prompts\n")
    header = "prompt  " + "  ".join(f"{mk[:22]:>22}" for mk in required_models)
    print(header)
    print("-" * len(header))
    missing = []
    for pid in prompt_ids:
        cells = []
        for mk in required_models:
            if (pid, mk) in ok:
                cells.append(f"{'OK':>22}")
            else:
                cells.append(f"{'MISSING':>22}")
                missing.append((pid, mk))
        print(f"{pid:<8}" + "  ".join(cells))

    total = len(prompt_ids) * len(required_models)
    print(f"\n{total - len(missing)}/{total} required cells present.")

    errs = [r for r in rows if r.get("error")]
    if errs:
        print(f"\n{len(errs)} recorded failure(s):")
        for r in errs:
            print(f"  - {r['image_id']}: {r['error']}")

    extra = {r["model_key"] for r in rows} - set(required_models)
    if extra:
        print(f"\nAdditional (optional) models present: {', '.join(sorted(extra))}")

    blanks = [r["image_id"] for r in rows
              if r.get("generated_via") == "web_ui"
              and "recorded manually" in (r.get("settings_json") or "")]
    if blanks:
        print(f"\n{len(blanks)} manually-registered row(s) still need settings_json filled in.")


# ----------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Dukaan Bench generation harness (API and/or manual).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--all", action="store_true",
                    help="generate all 3 required models via API (needs keys)")
    ap.add_argument("--models", type=str, default="",
                    help="comma-separated model keys to generate via API")
    ap.add_argument("--prompts", type=str, default="",
                    help="comma-separated prompt ids (default: all)")
    ap.add_argument("--runs", type=int, default=1,
                    help="generations per (model, prompt). Use 1 for the primary run; "
                         "use --runs 4 --prompts P01,P05 for the variance sub-study.")
    ap.add_argument("--overwrite", action="store_true",
                    help="regenerate cells that already exist")
    ap.add_argument("--register-manual", action="store_true",
                    help="register hand-generated images from images/<model_key>/")
    ap.add_argument("--status", action="store_true",
                    help="show the 3x10 coverage grid and what is still missing")
    args = ap.parse_args()

    load_dotenv()
    ensure_dirs()

    if args.status:
        run_status()
        return
    if args.register_manual:
        run_register_manual({})
        run_status()
        return

    spec = load_prompt_set()
    if args.all:
        model_keys = [m["key"] for m in spec["models"]]
    elif args.models:
        model_keys = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        ap.print_help()
        return

    prompt_ids = [p.strip() for p in args.prompts.split(",") if p.strip()] or None
    run_api(model_keys, prompt_ids, args.runs, args.overwrite)
    run_status()


if __name__ == "__main__":
    main()

import re
import time

import streamlit as st
from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash"


@st.cache_resource
def get_gemini_client(api_key: str) -> genai.Client:
    """Cached Gemini client — one instance per unique API key.
    The api_key argument is part of the cache key, so a new client
    is automatically created whenever the key changes.
    """
    return genai.Client(api_key=api_key.strip())


def _safe_str(text: str) -> str:
    """Normalize unicode to avoid ASCII-codec errors downstream."""
    replacements = {
        "\u2014": "--", "\u2013": "-",
        "\u2018": "'",  "\u2019": "'",
        "\u201c": '"',  "\u201d": '"',
        "\u2026": "...", "\u00a0": " ", "\u2022": "-",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _gemini_generate(client: genai.Client, contents: list, retries: int = 4) -> str:
    """Call Gemini with exponential backoff on 429 / quota errors."""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
            )
            return _safe_str(response.text or "")
        except Exception as exc:
            err = str(exc)
            delay_match = re.search(r"retry[^\d]*(\d+)s", err, re.I)
            suggested = int(delay_match.group(1)) if delay_match else 0
            wait = max(suggested, 2 ** attempt)
            is_quota = "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()
            if is_quota and attempt < retries - 1:
                time.sleep(wait)
                continue
            raise


def workspace_image_parts(workspace: dict) -> list[types.Part]:
    """Extracts and validates image bytes to prepare multi-modal payloads."""
    from utils.files import validate_image
    parts = []
    for file_item in workspace.get("files", []):
        for image in file_item.get("images", []):
            try:
                image_bytes, mime_type = validate_image(image["bytes"], image["mime_type"])
                parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            except ValueError:
                workspace.setdefault("visual_warnings", []).append(
                    "Visual analysis failed for this slide, but text was processed successfully."
                )
    return parts


def call_gemini(api_key: str, prompt: str, workspace: dict, metric_label: str = "gemini_call", include_images: bool = False) -> str:
    """Call Gemini and log TTV + token-efficiency metrics.
    
    Optimized: include_images is False by default to prevent large visual payloads 
    from causing high network latency during text-only generation workflows (like Quizzes).
    """
    from utils.metrics import log_metric, _count_tokens, _estimate_cost
    prompt = _safe_str(prompt)
    
    # Only load heavy visual assets if explicitly requested by the calling workflow
    image_parts = workspace_image_parts(workspace) if include_images else []
    
    t0 = time.perf_counter()
    client = get_gemini_client(api_key)

    try:
        output = _gemini_generate(client, [prompt, *image_parts])
    except Exception as exc:
        # If visual analysis failed and we had images, fallback gracefully to text-only evaluation
        if image_parts:
            workspace.setdefault("visual_warnings", []).append(
                "Visual analysis failed for this slide, but text was processed successfully."
            )
            output = _gemini_generate(client, [prompt])
        else:
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

    elapsed = round(time.perf_counter() - t0, 3)
    log_metric(metric_label, {
        "ttv_seconds": elapsed,
        "input_tokens": _count_tokens(prompt),
        "output_tokens": _count_tokens(output),
        "cost_usd": _estimate_cost(_count_tokens(prompt), _count_tokens(output)),
    })
    return output

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    """Build Gemini Part objects from already-optimised image bytes stored in the workspace.

    Images are validated and compressed to JPEG/PNG exactly once at ingestion time
    (parse_uploaded_file / extract_pptx).  Re-encoding on every API call is wasteful,
    so we pass the cached bytes through directly.
    """
    parts = []
    for file_item in workspace.get("files", []):
        for image in file_item.get("images", []):
            raw = image.get("bytes")
            if raw:
                parts.append(types.Part.from_bytes(data=raw, mime_type=image["mime_type"]))
    return parts


def _parse_skeleton(raw: str) -> list[str]:
    """Extract JSON topic list from the skeleton response, with graceful fallbacks."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()
    try:
        topics = json.loads(raw)
        if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
            return [t.strip() for t in topics if t.strip()]
    except json.JSONDecodeError:
        pass
    # Fallback: pull every quoted string
    matches = re.findall(r'"([^"]+)"', raw)
    if matches:
        return matches
    # Last resort: split on newlines and strip list markers
    lines = [re.sub(r"^[\d\-\*\.\s]+", "", l).strip() for l in raw.splitlines()]
    return [l for l in lines if l and len(l) > 3][:8]


def generate_study_guide_sot(
    api_key: str,
    subject: str,
    workspace: dict,
    mode: str,
    progress_callback=None,
    username: str | None = None,
) -> str:
    """
    Skeleton-of-Thought parallel study guide generation.

    Stage 1 — one API call returns a JSON list of N section topics (the skeleton).
    Stage 2 — N parallel API calls each write one full section (the flesh).
    Results are assembled in topic order into a single Markdown document.
    """
    from utils.guide import skeleton_prompt, section_prompt
    from utils.metrics import log_metric, _count_tokens, _estimate_cost, report_generation_metrics

    client = get_gemini_client(api_key)
    t0 = time.perf_counter()
    total_input_tokens = 0
    total_output_tokens = 0

    # ------------------------------------------------------------------ Stage 1
    skel_text = _safe_str(skeleton_prompt(subject, workspace, mode))
    skeleton_raw = _gemini_generate(client, [skel_text])
    topics = _parse_skeleton(skeleton_raw)
    total_input_tokens += _count_tokens(skel_text)
    total_output_tokens += _count_tokens(skeleton_raw)

    if progress_callback:
        progress_callback("skeleton_done", len(topics))

    # ------------------------------------------------------------------ Stage 2
    completed = [0]
    completed_lock = threading.Lock()
    sections: dict[int, str] = {}
    failed_topics: list[str] = []
    failed_lock = threading.Lock()

    def _write_section(idx: int, topic: str) -> tuple[int, str, int, int]:
        prompt_text = _safe_str(section_prompt(topic, subject, workspace, mode))
        try:
            text = _gemini_generate(client, [prompt_text])
            return idx, text, _count_tokens(prompt_text), _count_tokens(text)
        except Exception as exc:
            log_metric("generation_failed", {
                "subject": subject,
                "topic": topic,
                "error_message": str(exc)[:300],
            }, username=username)
            with failed_lock:
                failed_topics.append(topic)
            fallback = f"## {topic}\n\n_This section could not be generated ({exc})._\n"
            return idx, fallback, _count_tokens(prompt_text), 0

    max_workers = min(len(topics), 6)  # cap to stay within Gemini RPM limits
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_write_section, i, topic): i
            for i, topic in enumerate(topics)
        }
        for future in as_completed(futures):
            idx, text, in_tok, out_tok = future.result()
            sections[idx] = text
            total_input_tokens += in_tok
            total_output_tokens += out_tok
            with completed_lock:
                completed[0] += 1
                done = completed[0]
            if progress_callback:
                progress_callback("section_done", done, len(topics))

    assembled = "\n\n".join(sections[i] for i in sorted(sections))
    elapsed = round(time.perf_counter() - t0, 3)
    cost = _estimate_cost(total_input_tokens, total_output_tokens)

    log_metric("study_guide_sot", {
        "ttv_seconds": elapsed,
        "sections": len(topics),
        "parallelism": max_workers,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "cost_usd": cost,
        "failed_sections": len(failed_topics),
    }, username=username)

    report_generation_metrics(
        label=f"Study Guide ({mode}) [SoT x{len(topics)}]",
        subject=subject,
        mode=mode,
        prompt_text=skel_text,
        output_text=assembled,
        elapsed_s=elapsed,
        username=username,
    )

    # Surface partial failures to the UI layer. The caller (app.py / tabs/study.py)
    # should check st.session_state["last_guide_failed_sections"] after calling this
    # function and render a warning banner if it's non-empty.
    st.session_state["last_guide_failed_sections"] = failed_topics
    st.session_state["last_guide_total_sections"] = len(topics)

    return assembled


_REMEDIATION_BATCH_SIZE = 3  # topics per Gemini call; tune down to 2 on free-tier RPM limits


def generate_remediation_pooled(
    api_key: str,
    subject: str,
    workspace: dict,
    missed_questions: list[dict],
    batch_size: int = _REMEDIATION_BATCH_SIZE,
    username: str | None = None,
) -> str:
    """
    Dynamic Remediation Pooling.

    Groups weak topics into batches of `batch_size` and fires one Gemini call per
    batch.  When there are multiple batches they run in parallel via
    ThreadPoolExecutor, then results are stitched together in topic order.

    Call reduction vs. naive per-topic approach:
        N topics  →  ceil(N / batch_size) calls  (e.g. 6 topics → 2 calls, not 6)
    """
    from utils.guide import batched_remediation_prompt
    from utils.metrics import log_metric, _count_tokens, _estimate_cost, report_generation_metrics

    if not missed_questions:
        return ""

    # --- Deduplicate topics while preserving first-seen order ----------------
    missed_per_topic: dict[str, list[str]] = {}
    for q in missed_questions:
        topic = q.get("topic", "General")
        missed_per_topic.setdefault(topic, []).append(q.get("question", "?"))

    unique_topics = list(dict.fromkeys(
        q.get("topic", "General") for q in missed_questions
    ))

    batches: list[list[str]] = [
        unique_topics[i: i + batch_size]
        for i in range(0, len(unique_topics), batch_size)
    ]

    client = get_gemini_client(api_key)
    t0 = time.perf_counter()
    total_input_tokens = 0
    total_output_tokens = 0
    batch_results: dict[int, str] = {}
    collected_prompts: list[str] = []
    collect_lock = threading.Lock()
    failed_batches: list[list[str]] = []
    failed_lock = threading.Lock()

    def _call_batch(batch_idx: int, topics_batch: list[str]) -> tuple[int, str, str, int, int]:
        prompt_text = _safe_str(
            batched_remediation_prompt(topics_batch, missed_per_topic, subject, workspace)
        )
        with collect_lock:
            collected_prompts.append(prompt_text)
        try:
            text = _gemini_generate(client, [prompt_text])
            return batch_idx, text, prompt_text, _count_tokens(prompt_text), _count_tokens(text)
        except Exception as exc:
            log_metric("generation_failed", {
                "subject": subject,
                "topics": topics_batch,
                "error_message": str(exc)[:300],
            }, username=username)
            with failed_lock:
                failed_batches.append(topics_batch)
            fallback = "\n\n".join(
                f"## {t}\n\n_Section could not be generated ({exc})._" for t in topics_batch
            )
            return batch_idx, fallback, prompt_text, _count_tokens(prompt_text), 0

    if len(batches) == 1:
        # Fast path: skip thread overhead entirely for the common case
        idx, text, prompt_text, in_tok, out_tok = _call_batch(0, batches[0])
        batch_results[0] = text
        total_input_tokens += in_tok
        total_output_tokens += out_tok
    else:
        max_workers = min(len(batches), 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_call_batch, i, batch): i
                for i, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                idx, text, prompt_text, in_tok, out_tok = future.result()
                batch_results[idx] = text
                total_input_tokens += in_tok
                total_output_tokens += out_tok

    assembled = "\n\n".join(batch_results[i] for i in sorted(batch_results))
    elapsed = round(time.perf_counter() - t0, 3)
    cost = _estimate_cost(total_input_tokens, total_output_tokens)

    log_metric("remediation_pooled", {
        "ttv_seconds": elapsed,
        "topics": len(unique_topics),
        "batches": len(batches),
        "batch_size": batch_size,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "cost_usd": cost,
        "failed_batches": len(failed_batches),
    }, username=username)

    combined_prompt = "\n\n--- BATCH SEPARATOR ---\n\n".join(collected_prompts)
    report_generation_metrics(
        label=f"Remediation Guide [Pooled {len(unique_topics)}T/{len(batches)}B]",
        subject=subject,
        mode=f"{len(unique_topics)} topic(s) in {len(batches)} batch(es) of ≤{batch_size}",
        prompt_text=combined_prompt,
        output_text=assembled,
        elapsed_s=elapsed,
        username=username,
    )

    # Surface partial failures to the UI layer, same pattern as generate_study_guide_sot.
    st.session_state["last_remediation_failed_batches"] = failed_batches
    st.session_state["last_remediation_total_batches"] = len(batches)

    return assembled


def call_gemini(api_key: str, prompt: str, workspace: dict, metric_label: str = "gemini_call", include_images: bool = False, username: str | None = None) -> str:
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
            try:
                output = _gemini_generate(client, [prompt])
            except Exception as exc2:
                log_metric("generation_failed", {
                    "metric_label": metric_label,
                    "error_message": str(exc2)[:300],
                }, username=username)
                raise RuntimeError(f"Gemini request failed: {exc2}") from exc2
        else:
            log_metric("generation_failed", {
                "metric_label": metric_label,
                "error_message": str(exc)[:300],
            }, username=username)
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

    elapsed = round(time.perf_counter() - t0, 3)
    log_metric(metric_label, {
        "ttv_seconds": elapsed,
        "input_tokens": _count_tokens(prompt),
        "output_tokens": _count_tokens(output),
        "cost_usd": _estimate_cost(_count_tokens(prompt), _count_tokens(output)),
    }, username=username)
    return output

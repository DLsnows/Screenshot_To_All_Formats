import os
import base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from openai import OpenAI

from Screenshot_To_All_Formats.PROMPTS_LIB import prompts_library
import Screenshot_To_All_Formats.prompt_setting as prompt_setting  # noqa: F401 — registers all prompts


# ---------------------------------------------------------------------------
# Supported image extensions (lowercase with dot)
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

# MIME type lookup for the API request
MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}

# Format → file extension mapping
FORMAT_EXT_MAP = {
    "markdown": ".md",
    "html": ".html",
    "csv": ".csv",
    "json": ".json",
    "latex": ".tex",
    "text": ".txt",
    "code": ".txt",
}


# ---------------------------------------------------------------------------
# Low-level OCR call
# ---------------------------------------------------------------------------

def ocr(client: OpenAI, image_path: str, model: str, prompt: str, max_token: int) -> str:
    """Send a single image to the vision model and return the response text."""
    ext = Path(image_path).suffix.lower()
    mime_type = MIME_MAP.get(ext, "image/png")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_token,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    }
                ],
            },
        ],
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Batch processing with progress callbacks
# ---------------------------------------------------------------------------

def process_all_images(
    input_path: str,
    output_path: str,
    language: str,
    format: str,
    model_config: dict,
    progress_callback: Callable[[int, int], None] | None = None,
    max_workers: int = 50,
) -> tuple[list[str], str]:
    """Process every supported image in *input_path* concurrently.

    Parameters
    ----------
    input_path:
        Directory containing source images.
    output_path:
        Directory where per-image result files are written.
    language:
        Content language key (``"cn" | "en" | "fr"``).
    format:
        Output format key (see ``FORMAT_EXT_MAP``).
    model_config:
        Dict with keys ``api_key``, ``base_url``, ``model_name``, ``max_tokens``.
    progress_callback:
        Optional two-arg callable ``fn(completed, total)`` invoked each time
        an image finishes (success or error).
    max_workers:
        Maximum concurrent API calls (default 50).

    Returns
    -------
    (individual_results, combined_result)
        ``individual_results`` is a list of strings (one per image, in the same
        order as the input file listing).  ``combined_result`` is the per-image
        results joined by ``\\n\\n\\n``.
    """
    client = OpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"],
    )

    prompt = prompts_library.get_prompt_from_manager(language, format)
    file_ext = FORMAT_EXT_MAP.get(format, ".txt")

    # ---- collect image files ----
    if not os.path.isdir(input_path):
        return [], ""

    image_files = sorted(
        fname
        for fname in os.listdir(input_path)
        if Path(fname).suffix.lower() in IMAGE_EXTENSIONS
    )
    total = len(image_files)

    if total == 0:
        return [], ""

    # ---- prepare output directory ----
    os.makedirs(output_path, exist_ok=True)

    # ---- parallel processing ----
    results: list[str | None] = [None] * total  # pre-alloc to preserve order
    concurrency = min(total, max_workers)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {}

        for idx, fname in enumerate(image_files):
            img_path = os.path.join(input_path, fname)
            future = executor.submit(
                ocr, client, img_path, model_config["model_name"], prompt, model_config["max_tokens"]
            )
            future_map[future] = (idx, fname)

        for future in as_completed(future_map):
            idx, fname = future_map[future]
            try:
                content = future.result()
            except Exception as exc:
                content = f"[OCR ERROR: {exc}]"

            results[idx] = content

            # write individual result file immediately
            out_path = os.path.join(output_path, f"{fname}{file_ext}")
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass

            if progress_callback:
                completed = sum(1 for r in results if r is not None)
                progress_callback(completed, total)

    # ---- write combined file ----
    combined = "\n\n\n".join(results)

    all_in_one_path = os.path.join(output_path, f"all_in_one{file_ext}")
    try:
        with open(all_in_one_path, "w", encoding="utf-8") as f:
            f.write(combined)
    except OSError:
        pass

    return results, combined

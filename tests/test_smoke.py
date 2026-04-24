"""
Smoke test — verifies that the FastAPI application starts and all core
endpoints respond correctly.

Usage:
    # Start the server in one terminal:
    python main.py

    # In another terminal, run this script:
    python test_smoke.py

    # Or use the helper that starts and stops the server automatically:
    python test_smoke.py --auto
"""

import os
import sys
import time
import json
import subprocess
import argparse
from pathlib import Path

import httpx
from httpx import ASGITransport

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://127.0.0.1:8000"
API = f"{BASE_URL}/api"

PASSED = 0
FAILED = 0


def check(description: str, condition: bool, detail: str = ""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [OK] {description}")
    else:
        FAILED += 1
        print(f"  [FAIL] {description}")
        if detail:
            print(f"      {detail}")


# ---------------------------------------------------------------------------
# Tests against a running server (HTTP)
# ---------------------------------------------------------------------------

def test_live_server():
    """Run all smoke tests against a live FastAPI server."""
    client = httpx.Client(timeout=15)

    print("\n--- 1. Settings API ---\n")

    # GET /api/settings
    r = client.get(f"{API}/settings")
    check("GET /api/settings returns 200", r.status_code == 200)
    data = r.json()
    check("  response has 'model' section", "model" in data)
    check("  response has 'ui' section", "ui" in data)
    check("  response has 'hotkey' section", "hotkey" in data)
    check("  response has 'defaults' section", "defaults" in data)

    # PUT /api/settings
    test_settings = {
        "model": {
            "base_url": "https://test.example.com/v1",
            "api_key": "sk-test-key",
            "model_name": "test-model",
            "max_tokens": 16384,
        },
        "ui": {"language": "en", "format": "markdown", "copy_to_clipboard": False},
    }
    r = client.put(f"{API}/settings", json=test_settings)
    check("PUT /api/settings returns 200", r.status_code == 200)
    saved = r.json()
    check("  model.base_url is updated", saved["model"]["base_url"] == "https://test.example.com/v1")
    check("  model.api_key is persisted", saved["model"]["api_key"] == "sk-test-key")
    check("  model.max_tokens is clamped", 1024 <= saved["model"]["max_tokens"] <= 200000)

    # Restore settings
    restore = {
        "model": {"base_url": "https://api.openai.com/v1", "api_key": "", "model_name": "gpt-4o", "max_tokens": 30000},
        "ui": {"language": "en", "format": "markdown", "copy_to_clipboard": True},
    }
    client.put(f"{API}/settings", json=restore)

    # GET /api/languages
    r = client.get(f"{API}/languages")
    check("GET /api/languages returns 200", r.status_code == 200)
    langs = r.json()
    check("  contains cn/en/fr", set(langs) == {"cn", "en", "fr"})

    # GET /api/ui-languages
    r = client.get(f"{API}/ui-languages")
    check("GET /api/ui-languages returns 200", r.status_code == 200)
    check("  contains en/zh", set(r.json()) == {"en", "zh"})

    # GET /api/formats
    r = client.get(f"{API}/formats")
    check("GET /api/formats returns 200", r.status_code == 200)
    expected_formats = {"markdown", "html", "csv", "json", "latex", "text", "code"}
    check("  contains 7 formats", set(r.json()) == expected_formats)

    print("\n--- 2. Tasks API (no real OCR) ---\n")

    # Create a dummy input dir with a test image
    test_img_dir = PROJECT_ROOT / "test_input"
    test_img_dir.mkdir(exist_ok=True)

    # Create a minimal valid PNG (1x1 pixel)
    _create_minimal_png(test_img_dir / "test_1x1.png")

    # POST /api/convert (should fail without API key, but we just test validation)
    r = client.post(
        f"{API}/convert",
        json={
            "input_path": str(test_img_dir),
            "output_path": str(PROJECT_ROOT / "test_output"),
            "language": "en",
            "format": "markdown",
            "copy_to_clipboard": False,
            "model": {
                "api_key": "sk-invalid",
                "base_url": "https://api.openai.com/v1",
                "model_name": "gpt-4o",
                "max_tokens": 30000,
            },
        },
    )
    # Should create a task (even though OCR will fail)
    check("POST /api/convert returns 200/201", r.status_code in (200, 201))
    task_data = r.json()
    check("  response has task_id", "task_id" in task_data)
    check("  response has total_images", task_data.get("total_images") == 1)

    task_id = task_data["task_id"]

    # Wait briefly then check task status
    time.sleep(1)
    r = client.get(f"{API}/tasks/{task_id}")
    check("GET /api/tasks/{id} returns 200", r.status_code == 200)
    status_data = r.json()
    check("  has status field", "status" in status_data)
    check("  has percentage field", "percentage" in status_data)
    check("  task id matches", status_data["id"] == task_id)

    # GET /api/tasks (list)
    r = client.get(f"{API}/tasks?limit=10")
    check("GET /api/tasks returns 200", r.status_code == 200)
    tasks = r.json()
    check("  returns a list", isinstance(tasks, list))
    if tasks:
        check("  newest task is ours", tasks[0]["id"] == task_id)

    # GET /api/tasks/nonexistent
    r = client.get(f"{API}/tasks/nonexistent-id")
    check("GET /api/tasks/nonexistent returns 404", r.status_code == 404)

    print("\n--- 3. Upload API ---\n")

    # POST /api/upload
    files = {"files": ("test.png", _create_minimal_png_bytes(), "image/png")}
    r = client.post(f"{API}/upload", files=files)
    check("POST /api/upload returns 200", r.status_code == 200)
    upload_data = r.json()
    check("  has uploaded list", "uploaded" in upload_data)
    check("  has upload_dir", "upload_dir" in upload_data)
    check("  uploaded contains test.png", "test.png" in upload_data["uploaded"])

    # Cleanup test files
    import shutil
    shutil.rmtree(test_img_dir, ignore_errors=True)
    shutil.rmtree(PROJECT_ROOT / "test_output", ignore_errors=True)

    client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_minimal_png_bytes():
    """Return bytes of a minimal valid 1x1 red PNG."""
    # Minimal PNG: signature + IHDR + IDAT + IEND
    import struct
    import zlib

    def make_chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = make_chunk(b'IHDR', struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))

    # Raw pixel data (filter byte 0 + RGB)
    raw = b'\x00\xff\x00\x00'
    compressed = zlib.compress(raw)
    idat = make_chunk(b'IDAT', compressed)

    iend = make_chunk(b'IEND', b'')

    return sig + ihdr + idat + iend


def _create_minimal_png(path: Path):
    path.write_bytes(_create_minimal_png_bytes())


def start_server():
    """Start the FastAPI server as a subprocess."""
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "Screenshot_To_All_Formats.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_for_server(timeout=15):
    """Wait until the server responds at /api/settings."""
    client = httpx.Client(timeout=2)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = client.get(f"{API}/settings")
            if r.status_code == 200:
                client.close()
                return True
        except (httpx.ConnectError, httpx.RemoteProtocolError):
            pass
        time.sleep(0.5)
    client.close()
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Smoke test for Img2Text API")
    parser.add_argument("--auto", action="store_true", help="Auto-start and stop the server")
    args = parser.parse_args()

    print("=" * 56)
    print("  Img2Text - Smoke Test Suite")
    print("=" * 56)

    if args.auto:
        print("\nStarting server...")
        proc = start_server()
        if not wait_for_server():
            print("FAILED: Server did not start within 15 seconds")
            proc.kill()
            sys.exit(1)
        print("Server is ready.\n")
    else:
        print(f"\nMake sure the server is running at {BASE_URL}")
        print("  python main.py\n")

    try:
        test_live_server()
    finally:
        if args.auto:
            print("\nShutting down server...")
            proc.terminate()
            proc.wait()

    # Summary
    total = PASSED + FAILED
    print(f"\n{'=' * 56}")
    print(f"  Results: {PASSED}/{total} passed", end="")
    if FAILED:
        print(f", {FAILED} FAILED", end="")
    print()
    print(f"{'=' * 56}")

    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

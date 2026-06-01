"""HiDream-O1 캐릭터 생성 테스트.

기존 워크플로(ai/workflows/character_generate.json)를 그대로 사용.
프롬프트 텍스트(노드 171)와 시드(노드 108)만 교체해서 제출한다.

실행:
    python ai/character_ctrl/test_generate.py
"""

import json
import os
import random
import time
import urllib.request
import urllib.parse
from pathlib import Path

# ai/.env 로드 (python-dotenv 없이 직접 파싱)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

COMFY_URL    = os.environ.get("COMFYUI_CHARACTER_URL", "https://comfy1.mtvs2026.work")
OUTPUT_DIR   = Path("backend/app/storage/characters")
WORKFLOW_PATH = Path(__file__).parent.parent / "workflows" / "character_generate.json"

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

# ── 수정할 노드 ID (워크플로 JSON 기준) ───────────────────────────────────────
NODE_USER_PROMPT   = "171"  # PrimitiveStringMultiline — 사용자 프롬프트
NODE_ENABLE_REFINE = "177"  # PrimitiveBoolean — Gemma 프롬프트 정제 ON/OFF
NODE_SAMPLER       = "108"  # SamplerCustom — noise_seed


# ── ComfyUI HTTP 헬퍼 ─────────────────────────────────────────────────────────

def post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{COMFY_URL}{path}", data=body, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"\n❌ ComfyUI 오류 ({e.code}):\n{e.read().decode()}")
        raise


def get(path: str, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{COMFY_URL}{path}", headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (ConnectionResetError, urllib.error.URLError):
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise


# ── 워크플로 빌드 ─────────────────────────────────────────────────────────────

def build_workflow(prompt: str, seed: int) -> dict:
    """기존 워크플로 JSON 로드 → 프롬프트·시드만 교체."""
    wf = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))

    # 1. 프롬프트 주입 (한국어 또는 영어 모두 가능)
    wf[NODE_USER_PROMPT]["inputs"]["value"] = prompt

    # 2. Gemma 정제 끄기 — 영어 프롬프트는 그대로 사용
    #    한국어로 입력하고 싶으면 True로 바꾸면 Gemma가 영어로 변환해줌
    wf[NODE_ENABLE_REFINE]["inputs"]["value"] = False

    # 3. 시드 설정 (매번 다른 이미지)
    wf[NODE_SAMPLER]["inputs"]["noise_seed"] = seed

    return wf


# ── 큐 등록 / 폴링 / 저장 ─────────────────────────────────────────────────────

def queue_prompt(workflow: dict) -> str:
    result = post("/prompt", {"prompt": workflow})
    prompt_id = result["prompt_id"]
    print(f"📤 큐 등록 완료. prompt_id: {prompt_id}")
    return prompt_id


def wait_for_result(prompt_id: str, timeout: int = 300) -> list:
    print("⏳ 생성 중", end="", flush=True)
    start = time.time()

    while time.time() - start < timeout:
        history = get(f"/history/{prompt_id}")
        if prompt_id in history:
            entry  = history[prompt_id]
            status = entry.get("status", {})
            outputs = entry.get("outputs", {})

            # 에러 감지
            if status.get("status_str") == "error":
                for msg_type, msg_data in status.get("messages", []):
                    if msg_type == "execution_error":
                        err  = msg_data.get("exception_message", "알 수 없는 오류")
                        node = msg_data.get("node_type", "?")
                        print(f" ❌ 오류!\n   노드: {node}\n   오류: {err.strip()}")
                        raise RuntimeError(f"ComfyUI 실행 오류 [{node}]: {err.strip()}")

            print(" ✅ 완료!")
            images = []
            for node_output in outputs.values():
                if "images" in node_output:
                    images.extend(node_output["images"])
            return images

        print(".", end="", flush=True)
        time.sleep(5)

    raise TimeoutError("생성 시간 초과 (300초)")


def save_image(image_info: dict, save_path: Path):
    filename  = image_info["filename"]
    subfolder = image_info.get("subfolder", "")
    url = (
        f"{COMFY_URL}/view"
        f"?filename={urllib.parse.quote(filename)}"
        f"&subfolder={subfolder}&type=output"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(r.read())
    print(f"💾 저장 완료: {save_path}")


# ── 테스트 실행 ───────────────────────────────────────────────────────────────

def test_character_generation():
    name       = "어린왕자"
    appearance = "blonde hair, small boy, blue coat, curious eyes, full body, white background"
    seed       = random.randint(0, 2**32 - 1)

    print(f"\n🎨 캐릭터 생성 테스트 (HiDream-O1 @ {COMFY_URL})")
    print(f"   이름  : {name}")
    print(f"   외형  : {appearance}")
    print(f"   seed  : {seed}\n")

    workflow  = build_workflow(appearance, seed)
    prompt_id = queue_prompt(workflow)
    images    = wait_for_result(prompt_id)

    if not images:
        print("⚠️  이미지 없음 — ComfyUI UI에서 확인하세요.")
        return

    output_path = OUTPUT_DIR / f"test_{name}.png"
    save_image(images[0], output_path)
    print(f"\n✅ 테스트 성공! 이미지: {output_path}")


if __name__ == "__main__":
    test_character_generation()

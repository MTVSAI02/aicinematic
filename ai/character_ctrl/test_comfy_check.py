"""ComfyUI 연결 확인 + 사용 가능한 모델 목록 출력.

실행:
    python ai/character_ctrl/test_comfy_check.py
"""

import json
import os
import urllib.request
from pathlib import Path

# ai/.env 로드 (python-dotenv 없이 직접 파싱)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

COMFY_URL = os.environ.get("COMFYUI_CHARACTER_URL", "https://comfy1.mtvs2026.work")


HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

def get(path: str):
    req = urllib.request.Request(f"{COMFY_URL}{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    # 1. 연결 확인
    try:
        stats = get("/system_stats")
        print("✅ ComfyUI 연결 성공")
        print(f"   버전: {stats.get('system', {}).get('comfyui_version', '?')}")
        print(f"   VRAM: {stats.get('devices', [{}])[0].get('vram_total', '?')} bytes\n")
    except Exception as e:
        print(f"❌ ComfyUI 연결 실패: {e}")
        print(f"   접속 시도 URL: {COMFY_URL}")
        print("   403이면 서버 인증(API 키 등) 필요 여부 확인하세요.")
        return

    # 2. 체크포인트 목록
    info = get("/object_info/CheckpointLoaderSimple")
    checkpoints = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    print("📦 체크포인트 (checkpoints/):")
    for c in checkpoints:
        print(f"   {c}")

    # 3. UNET 목록 (Flux 스타일)
    try:
        info2 = get("/object_info/UNETLoader")
        unets = info2["UNETLoader"]["input"]["required"]["unet_name"][0]
        print("\n📦 UNET 모델 (models/unet/ or diffusion_models/):")
        for u in unets:
            print(f"   {u}")
    except Exception:
        print("\n📦 UNET 목록 없음 (UNETLoader 노드 미설치)")

    # 4. VAE 목록
    info3 = get("/object_info/VAELoader")
    vaes = info3["VAELoader"]["input"]["required"]["vae_name"][0]
    print("\n📦 VAE 모델:")
    for v in vaes:
        print(f"   {v}")

    # 5. CLIP 목록
    try:
        info4 = get("/object_info/DualCLIPLoader")
        clips = info4["DualCLIPLoader"]["input"]["required"]["clip_name1"][0]
        print("\n📦 CLIP / 텍스트 인코더:")
        for c in clips:
            print(f"   {c}")
    except Exception:
        print("\n📦 DualCLIPLoader 없음")

    # 6. CLIPLoader 지원 type 목록
    clip_info = get("/object_info/CLIPLoader")
    clip_types = clip_info["CLIPLoader"]["input"]["required"]["type"][0]
    print("\n📦 CLIPLoader 지원 type 목록:")
    for t in clip_types:
        print(f"   {t}")

    # 7. DualCLIPLoader 지원 type 목록
    try:
        dual_info = get("/object_info/DualCLIPLoader")
        dual_types = dual_info["DualCLIPLoader"]["input"]["required"]["type"][0]
        print("\n📦 DualCLIPLoader 지원 type 목록:")
        for t in dual_types:
            print(f"   {t}")
    except Exception:
        print("\n📦 DualCLIPLoader 정보 없음")

    # 7. HiDream 전용 노드 탐색
    print("\n🔍 HiDream 관련 노드:")
    try:
        all_nodes = get("/object_info")
        hidream_nodes = [k for k in all_nodes.keys() if "hidream" in k.lower() or "HiDream" in k]
        if hidream_nodes:
            for n in hidream_nodes:
                print(f"   {n}")
        else:
            print("   (없음)")
    except Exception as e:
        print(f"   탐색 실패: {e}")

    print("\n위 목록을 혜원씨가 Claude에 붙여넣으면 맞는 워크플로 만들어드릴게요!")


if __name__ == "__main__":
    main()

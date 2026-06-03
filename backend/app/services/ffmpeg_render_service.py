"""무음 mp4 렌더링 (Pillow 프레임 합성 → ffmpeg 인코딩).

- 입력은 render plan(timeline_service.build_render_plan) 결과만 사용한다. story/scene/character 를 직접 다시 조회하지 않는다.
- 레이어 순서: background → characters(zIndex 오름차순) → textOverlays(현재 시간 cue만).
- 자막은 cueTimings 기준으로 현재 프레임 시간(sceneLocalTime)에 해당하는 cueOrder 만 표시한다.
- 오디오/TTS 없음(무음). ffmpeg 경로는 config.resolve_ffmpeg_bin(env→PATH→번들)로 찾는다.
"""

import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageStat

from ..core.config import (
    RENDER_FPS,
    RENDER_HEIGHT,
    RENDER_STORAGE_DIR,
    RENDER_TMP_DIR,
    RENDER_WIDTH,
    resolve_ffmpeg_bin,
    storage_path,
    storage_url,
)
from ..core.exceptions import (
    FFmpegNotInstalledError,
    FFmpegRenderFailedError,
    RenderPlanInvalidError,
)

# 자막 스타일: 배경 박스 없음 + 배경 밝기로 글자색 자동(흰/검) + 아주 약한 그림자(동화 톤).
# (외곽선 stroke 미사용 — 유튜브식으로 보이지 않게)
_SUBTITLE_LUMA_THRESHOLD = 128                    # luma < 128 → 어두운 배경 → 흰 글자
_TEXT_ON_DARK = (255, 255, 255, 255)              # 어두운 배경: 흰 글자
_TEXT_ON_LIGHT = (0, 0, 0, 255)                   # 밝은 배경: 검은 글자
_SHADOW_ON_DARK = (0, 0, 0, 110)                  # 흰 글자용 약한 검정 그림자
_SHADOW_ON_LIGHT = (255, 255, 255, 120)           # 검은 글자용 약한 흰 그림자
_PLACEHOLDER_BG = (28, 28, 38, 255)               # 배경 이미지 없을 때

# 한글 가능한 기본 폰트 후보 (서버에 설치된 것을 찾아 사용 — 사용자에게 폰트 공유 안 함)
_FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",          # macOS
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # macOS
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",       # Linux Noto
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",              # Linux Nanum
    "C:/Windows/Fonts/malgun.ttf",                                 # Windows
]
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}


def _font(px: int) -> ImageFont.FreeTypeFont:
    if px in _FONT_CACHE:
        return _FONT_CACHE[px]
    for path in _FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(path, px)
            _FONT_CACHE[px] = f
            return f
        except Exception:  # noqa: BLE001 (없는 폰트는 다음 후보로)
            continue
    f = ImageFont.load_default()  # 최후: 기본 폰트(한글은 깨질 수 있음)
    _FONT_CACHE[px] = f
    return f


def _parse_color(value):
    """'#fff' / '#ffffff' / 'rgb(...)' / 'rgba(...)' → (r,g,b,a). 실패 시 None."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    try:
        if s.startswith("#"):
            h = s[1:]
            if len(h) == 3:
                return (*[int(c * 2, 16) for c in h], 255)
            if len(h) == 6:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
            if len(h) == 8:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
        if s.startswith("rgb"):
            nums = s[s.index("(") + 1: s.index(")")].split(",")
            r, g, b = (int(float(nums[i])) for i in range(3))
            a = int(float(nums[3]) * 255) if len(nums) >= 4 else 255
            return (r, g, b, a)
    except Exception:  # noqa: BLE001
        return None
    return None


def _load_rgba(url):
    """/storage URL → RGBA 이미지. 없거나 열기 실패 시 None(placeholder 처리)."""
    p = storage_path(url)
    if p is None or not p.exists():
        return None
    try:
        return Image.open(p).convert("RGBA")
    except Exception:  # noqa: BLE001
        return None


def _cover(img, w, h):
    """비율 유지로 캔버스를 꽉 채우고 넘치는 부분은 중앙 crop."""
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, round(sw * scale)), max(1, round(sh * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _paste(canvas, img, top_left):
    """음수/화면 밖 좌표도 안전하게(자동 clip) 합성."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(img, top_left, img)
    canvas.alpha_composite(layer)


def _paste_character(canvas, ch, w, h):
    img = _load_rgba(ch.get("imageUrl"))
    if img is None:
        return  # 누락 캐릭터는 건너뜀(MVP placeholder 정책)
    layout = ch.get("layout") or {}
    scale = float(layout.get("scale") or 0.3)
    target_w = max(1, round(scale * w))
    ratio = target_w / img.width
    img = img.resize((target_w, max(1, round(img.height * ratio))), Image.Resampling.LANCZOS)
    if layout.get("flipX"):
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    rotation = float(layout.get("rotation") or 0) % 360
    if rotation:  # CSS는 시계방향 +, PIL은 반시계 + → 부호 반전
        img = img.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
    cx, cy = float(layout.get("x", 0.5)) * w, float(layout.get("y", 0.5)) * h
    _paste(canvas, img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def _wrap(text, font, max_w):
    """max_w(px) 안으로 줄바꿈. 공백 우선, 한 단어가 너무 길면 글자 단위(한글 대응)."""
    if max_w <= 0:
        return [text]
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = word if not cur else f"{cur} {word}"
            if font.getlength(trial) <= max_w:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            if font.getlength(word) <= max_w:
                cur = word
            else:  # 단어 자체가 김 → 글자 단위
                chunk = ""
                for chx in word:
                    if font.getlength(chunk + chx) <= max_w:
                        chunk += chx
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = chx
                cur = chunk
        lines.append(cur)
    return lines or [""]


def _region_luma(canvas, left, top, right, bottom):
    """캔버스의 해당 사각형 영역 평균 밝기(luma 0~255). PIL 'L' 변환이 0.299R+0.587G+0.114B 를 쓴다."""
    cw, ch = canvas.size
    left = max(0, min(int(left), cw - 1))
    top = max(0, min(int(top), ch - 1))
    right = max(left + 1, min(int(right), cw))
    bottom = max(top + 1, min(int(bottom), ch))
    region = canvas.crop((left, top, right, bottom)).convert("L")
    return ImageStat.Stat(region).mean[0]


def _draw_subtitle(canvas, ov, w, h):
    text = (ov.get("text") or "").strip()
    if not text:
        return
    layout = ov.get("layout") or {}
    style = ov.get("style") or {}

    box_w = max(1, int(float(layout.get("width", 0.75)) * w))
    font_px = max(10, int(float(layout.get("fontSize", 0.06)) * h))
    font = _font(font_px)
    align = layout.get("align", "center")

    pad_x, pad_y = max(8, font_px // 3), max(6, font_px // 4)
    lines = _wrap(text, font, box_w - 2 * pad_x)
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    line_gap = max(2, font_px // 6)
    text_h = len(lines) * line_h + (len(lines) - 1) * line_gap

    tile_w, tile_h = box_w, text_h + 2 * pad_y
    cx, cy = float(layout.get("x", 0.5)) * w, float(layout.get("y", 0.85)) * h
    left, top = int(cx - tile_w / 2), int(cy - tile_h / 2)

    # 글자색 자동: style.color 명시되면 그대로, 없으면 자막 영역 배경 밝기로 흰/검 선택.
    override = _parse_color(style.get("color"))
    if override is not None:
        text_color, shadow_color = override, _SHADOW_ON_DARK
    elif _region_luma(canvas, left, top, left + tile_w, top + tile_h) < _SUBTITLE_LUMA_THRESHOLD:
        text_color, shadow_color = _TEXT_ON_DARK, _SHADOW_ON_DARK    # 어두운 배경 → 흰 글자
    else:
        text_color, shadow_color = _TEXT_ON_LIGHT, _SHADOW_ON_LIGHT  # 밝은 배경 → 검은 글자

    # 배경 박스 없음(투명 타일). 가독성은 아주 약한 그림자만으로 보완(외곽선 X).
    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    sh = max(1, font_px // 22)  # 은은한 그림자 오프셋
    y = pad_y
    for line in lines:
        lw = font.getlength(line)
        if align == "left":
            x = pad_x
        elif align == "right":
            x = tile_w - pad_x - lw
        else:
            x = (tile_w - lw) / 2
        draw.text((x + sh, y + sh), line, font=font, fill=shadow_color)  # 약한 그림자
        draw.text((x, y), line, font=font, fill=text_color)              # 본문
        y += line_h + line_gap

    rotation = float(layout.get("rotation") or 0) % 360
    if rotation:
        tile = tile.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
    _paste(canvas, tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))


def _compose_base(scene, w, h):
    """배경 + 캐릭터까지 합성한 씬 base(자막 제외). 자막은 프레임별로 덧입힌다."""
    bg = _load_rgba(scene.get("backgroundImageUrl"))
    canvas = _cover(bg, w, h) if bg is not None else Image.new("RGBA", (w, h), _PLACEHOLDER_BG)
    for ch in sorted(scene.get("characters") or [], key=lambda c: (c.get("layout") or {}).get("zIndex", 0)):
        _paste_character(canvas, ch, w, h)
    return canvas


def _active_cue_orders(scene, local_time):
    """sceneLocalTime 기준 표시할 cueOrder 집합. cue.startSec <= local < startSec+durationSec."""
    active = set()
    for c in scene.get("cueTimings") or []:
        start = float(c.get("startSec", 0.0))
        if start <= local_time < start + float(c.get("durationSec", 0.0)):
            active.add(c.get("cueOrder"))
    return active


def _scene_at(starts, durations, t):
    for i in range(len(starts) - 1, -1, -1):
        if t >= starts[i]:
            return i
    return 0


def render_video(render_id: str, plan: dict) -> str:
    """render plan → 무음 mp4 생성, /storage URL 반환. 임시 프레임은 항상 정리한다."""
    ffmpeg_bin = resolve_ffmpeg_bin()
    if not ffmpeg_bin:
        raise FFmpegNotInstalledError()

    scenes = plan.get("scenes") or []
    if not scenes:
        raise RenderPlanInvalidError()

    fps, w, h = RENDER_FPS, RENDER_WIDTH, RENDER_HEIGHT
    durations = [float(s.get("duration") or 0.0) for s in scenes]
    total = sum(durations)
    starts, acc = [], 0.0
    for d in durations:
        starts.append(acc)
        acc += d
    total_frames = max(1, round(total * fps))

    tmp_dir = RENDER_TMP_DIR / render_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    base_cache: dict = {}   # sceneId → 배경+캐릭터 합성(RGBA)
    frame_cache: dict = {}  # (sceneId, frozenset(activeCues)) → 최종 프레임(RGB)
    try:
        for fi in range(total_frames):
            t = fi / fps
            idx = _scene_at(starts, durations, t)
            scene = scenes[idx]
            sid = scene.get("sceneId")
            active = _active_cue_orders(scene, t - starts[idx])
            key = (sid, frozenset(active))
            frame = frame_cache.get(key)
            if frame is None:
                if sid not in base_cache:
                    base_cache[sid] = _compose_base(scene, w, h)
                composed = base_cache[sid].copy()
                for ov in scene.get("textOverlays") or []:
                    if ov.get("cueOrder") in active:
                        _draw_subtitle(composed, ov, w, h)
                frame = composed.convert("RGB")  # yuv420p 인코딩용
                frame_cache[key] = frame
            frame.save(tmp_dir / f"frame_{fi + 1:05d}.png")

        RENDER_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RENDER_STORAGE_DIR / f"{render_id}.mp4"
        cmd = [
            ffmpeg_bin, "-y",
            "-framerate", str(fps),
            "-i", str(tmp_dir / "frame_%05d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not out_path.exists():
            tail = (proc.stderr or "").strip().splitlines()
            raise FFmpegRenderFailedError(f"ffmpeg 실패: {tail[-1] if tail else 'unknown error'}")
        return storage_url("renders", f"{render_id}.mp4")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)  # 성공/실패 모두 임시 프레임 정리

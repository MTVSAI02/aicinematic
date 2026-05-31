"""ai/image — 이미지 생성 연동 패키지.

- `background.py`: 배경 생성 ComfyUI 연동 (현재 "연결 준비 단계"). workflow/mapping 로드 +
  finalPrompt/negativePrompt 주입 payload 구성 + 연결 확인까지만. 실제 이미지 생성은 아직 안 한다.

모델 방향은 SDXL + IPAdapter 에서 HiDream-I1 + IP-Adapter for Flux 로 변경되었고,
실제 ComfyUI workflow는 아직 확정 전(placeholder)이라 SDXL 전제 코드는 작성하지 않는다.
실제 생성 workflow가 확정되면 별도 단계에서 구현한다.
"""

#!/usr/bin/env python3
# status.py — workspace/state.yaml 과 slices.yaml 을 읽어 진행 상태 요약을 출력한다. (/status 가 사용)
#
# 사용법: python tools/status.py
# 의존성: pyyaml

import os
import sys

# Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 고정한다
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    sys.exit("[status] pyyaml 패키지가 필요합니다. 설치: python -m pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _workspace():
    # workspace/<project>/ — 프로젝트명은 config/project.yaml → project.name. 없으면 workspace/ 바로 아래(구 구조).
    cfg = os.path.join(ROOT, "config", "project.yaml")
    try:
        with open(cfg, encoding="utf-8") as f:
            name = yaml.safe_load(f)["project"]["name"]
        return os.path.join(ROOT, "workspace", name)
    except Exception:
        return os.path.join(ROOT, "workspace")


WS = _workspace()
STATE = os.path.join(WS, "state.yaml")
SLICES = os.path.join(WS, "slices", "slices.yaml")
CONFIG = os.path.join(ROOT, "config", "project.yaml")

MARK = {"done": "✅", "in_progress": "🔄", "blocked": "⛔", "pending": "·", "skipped": "－", None: "·", "": "·"}


def load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    cfg = load(CONFIG)
    st = load(STATE)
    sl = load(SLICES)

    if cfg is None:
        print("config/project.yaml 이 없습니다. config/project.yaml.example 을 복사해 만드세요.")
        return
    if st is None:
        print("workspace/state.yaml 이 없습니다. /stage0 를 실행하면 생성됩니다.")
        return

    print(f"# {st.get('project')}  (mode={st.get('mode')}, iteration={st.get('iteration')}, updated={st.get('updated_at')})")
    print(f"target_dir: {cfg.get('project', {}).get('target_dir')}")
    approved = sl.get("approved") if sl else None
    print(f"slices.yaml 승인: {'예' if approved else '아니오 (approved: true 필요)' if sl else '(없음)'}")
    print()

    print("## 공통 단계")
    print("| 단계 | 상태 |")
    print("|---|---|")
    for k, v in (st.get("stages") or {}).items():
        print(f"| {k} | {MARK.get(v, v)} {v} |")
    print()

    slices = st.get("slices") or {}
    if slices:
        print("## slice × 단계")
        print("| slice | stage2 BE | stage4 FE | stage5 통합 | blocked 사유 |")
        print("|---|---|---|---|---|")
        for sid, s in slices.items():
            s = s or {}
            print(f"| {sid} | {MARK.get(s.get('stage2_backend'), '·')} {s.get('stage2_backend', 'pending')} "
                  f"| {MARK.get(s.get('stage4_frontend'), '·')} {s.get('stage4_frontend', 'pending')} "
                  f"| {MARK.get(s.get('stage5_integration'), '·')} {s.get('stage5_integration', 'pending')} "
                  f"| {s.get('blocked_reason') or ''} |")
        print()

    rr = st.get("refactor_requests") or {}
    print(f"## 리팩토링 요구서: open {rr.get('open', 0)} / in_progress {rr.get('in_progress', 0)} "
          f"/ done {rr.get('done', 0)} / rejected {rr.get('rejected', 0)}")
    print()

    log = st.get("log") or []
    if log:
        print("## 최근 기록")
        for e in log[-5:]:
            print(f"- {e.get('at')} [{e.get('stage')}{'/' + str(e.get('slice')) if e.get('slice') else ''}] "
                  f"{e.get('result')} — {e.get('note', '')}")


if __name__ == "__main__":
    main()

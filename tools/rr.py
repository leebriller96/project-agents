#!/usr/bin/env python3
# rr.py — 리팩토링 요구서(RR) 관리 도구
#
# 사용법:
#   python tools/rr.py new                       # 다음 RR id 를 출력하고 템플릿 복사본 생성 (RR-0001.yaml ...)
#   python tools/rr.py new --title "..." --slice order --source 5 --target 2 --layer backend/service --severity high
#   python tools/rr.py list [--status open] [--slice order] [--stage 2]   # 표 출력
#   python tools/rr.py set RR-0001 done [--note "..."]                    # 상태 변경 (open|in_progress|done|rejected)
#   python tools/rr.py stats                     # 상태별 건수 (state.yaml 의 refactor_requests 에 그대로 반영)
#   python tools/rr.py validate                  # 필수 키·값 검사
#
# 의존성: pyyaml

import argparse
import datetime
import glob
import os
import re
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
    sys.exit("[rr] pyyaml 패키지가 필요합니다. 설치: python -m pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RR_DIR = os.path.join(ROOT, "workspace", "refactor-requests")
TEMPLATE = os.path.join(ROOT, "templates", "refactor-request.yaml")
STATE = os.path.join(ROOT, "workspace", "state.yaml")

KST = datetime.timezone(datetime.timedelta(hours=9), name="KST")
STATUSES = ("open", "in_progress", "done", "rejected")
SEVERITIES = ("blocker", "high", "medium", "low")
SEV_ORDER = {s: i for i, s in enumerate(SEVERITIES)}
REQUIRED = ("id", "title", "source_stage", "slice", "target_stage", "target_layer",
            "severity", "evidence", "description", "status", "iteration")


def now_kst() -> str:
    return datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def rr_files():
    return sorted(glob.glob(os.path.join(RR_DIR, "RR-*.yaml")))


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def next_id() -> str:
    nums = []
    for p in rr_files():
        m = re.search(r"RR-(\d{4})\.yaml$", p)
        if m:
            nums.append(int(m.group(1)))
    return f"RR-{(max(nums) + 1 if nums else 1):04d}"


def current_iteration() -> int:
    if os.path.exists(STATE):
        try:
            return int(load(STATE).get("iteration", 1))
        except Exception:
            pass
    return 1


def cmd_new(args):
    os.makedirs(RR_DIR, exist_ok=True)
    rid = next_id()
    data = load(TEMPLATE)
    data.update({
        "id": rid,
        "title": args.title or "",
        "source_stage": args.source if args.source is not None else "",
        "found_at": now_kst(),
        "slice": args.slice or "",
        "target_stage": args.target if args.target is not None else "",
        "target_layer": args.layer or "",
        "severity": args.severity or "",
        "evidence": [],
        "description": "",
        "suggested_fix": "",
        "status": "open",
        "iteration": current_iteration(),
        "resolved_at": None,
        "resolution_note": None,
    })
    path = os.path.join(RR_DIR, f"{rid}.yaml")
    dump(path, data)
    print(rid)
    print(path)


def matches(d, args) -> bool:
    if args.status and d.get("status") != args.status:
        return False
    if args.slice and d.get("slice") != args.slice:
        return False
    if args.stage is not None and str(d.get("target_stage")) != str(args.stage):
        return False
    return True


def cmd_list(args):
    rows = []
    for p in rr_files():
        d = load(p)
        if matches(d, args):
            rows.append(d)
    rows.sort(key=lambda d: (SEV_ORDER.get(d.get("severity"), 99), d.get("id", "")))
    if not rows:
        print("(해당하는 RR 없음)")
        return
    print("| id | severity | status | slice | src→tgt | layer | title |")
    print("|---|---|---|---|---|---|---|")
    for d in rows:
        print(f"| {d.get('id')} | {d.get('severity')} | {d.get('status')} | {d.get('slice')} | "
              f"{d.get('source_stage')}→{d.get('target_stage')} | {d.get('target_layer')} | {d.get('title')} |")


def cmd_set(args):
    if args.new_status not in STATUSES:
        sys.exit(f"[rr] 상태는 {STATUSES} 중 하나여야 합니다.")
    path = os.path.join(RR_DIR, f"{args.id}.yaml")
    if not os.path.exists(path):
        sys.exit(f"[rr] {path} 없음")
    d = load(path)
    d["status"] = args.new_status
    if args.new_status in ("done", "rejected"):
        d["resolved_at"] = now_kst()
    if args.note:
        d["resolution_note"] = args.note
    dump(path, d)
    print(f"{args.id} → {args.new_status}")


def cmd_stats(args):
    counts = {s: 0 for s in STATUSES}
    for p in rr_files():
        s = load(p).get("status", "open")
        counts[s if s in counts else "open"] += 1
    print(yaml.safe_dump({"refactor_requests": counts}, allow_unicode=True, sort_keys=False).strip())
    if args.write and os.path.exists(STATE):
        st = load(STATE)
        st["refactor_requests"] = counts
        st["updated_at"] = now_kst()
        dump(STATE, st)
        print(f"(state.yaml 반영: {STATE})")


def cmd_validate(args):
    bad = 0
    for p in rr_files():
        d = load(p)
        errs = [k for k in REQUIRED if k not in d or d[k] in (None, "", [])]
        if d.get("status") not in STATUSES:
            errs.append(f"status={d.get('status')}")
        if d.get("severity") not in SEVERITIES:
            errs.append(f"severity={d.get('severity')}")
        if os.path.basename(p) != f"{d.get('id')}.yaml":
            errs.append("id≠파일명")
        if errs:
            bad += 1
            print(f"{os.path.basename(p)}: {', '.join(errs)}")
    print(f"검사 완료: {len(rr_files())}건 중 문제 {bad}건")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description="리팩토링 요구서(RR) 관리")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new")
    p.add_argument("--title"); p.add_argument("--slice"); p.add_argument("--layer")
    p.add_argument("--source", type=int); p.add_argument("--target", type=int)
    p.add_argument("--severity", choices=SEVERITIES)
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("list")
    p.add_argument("--status", choices=STATUSES); p.add_argument("--slice"); p.add_argument("--stage", type=int)
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("set")
    p.add_argument("id"); p.add_argument("new_status"); p.add_argument("--note")
    p.set_defaults(fn=cmd_set)

    p = sub.add_parser("stats")
    p.add_argument("--write", action="store_true", help="state.yaml 의 refactor_requests 갱신")
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("validate")
    p.set_defaults(fn=cmd_validate)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

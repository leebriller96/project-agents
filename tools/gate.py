#!/usr/bin/env python3
# gate.py — 단계 레포트의 게이트 메타(pa-meta 블록)를 기계적으로 검증한다.
#
# 목적: "빌드·테스트 통과", "확인 필요 있음" 같은 문장을 사람이 읽고 믿는 대신
#       (1) 실행 증거(명령·종료코드·테스트 개수)가 실제로 있는지
#       (2) target_dir 의 git 실측(HEAD/브랜치/dirty/변경파일)이 레포트 기재와 같은지
#       (3) slice 의 traits 가 요구하는 검증 축이 닫히거나 예약됐는지
#       (4) 요구사항 ID 가 테스트까지 이어지는지
#       (5) 미해결 항목(open item)이 RR 이나 승인 없이 조용히 사라지지 않는지
#       (6) 레포트에 자격증명·개인정보가 섞이지 않았는지
#       를 도구가 대조한다. (착안: ing-people/sk-secu-agent 의 slice_agent_hooks.py)
#
# 사용법:
#   python tools/gate.py check --report workspace/<p>/reports/2609221130_stage2_notice_....md
#   python tools/gate.py check --stage 2 --slice notice          # 최신 레포트 자동 탐색
#   python tools/gate.py check --stage 5 --slice notice --format json
#   python tools/gate.py template --stage 2 --slice notice        # 메타 블록 골격 출력
#   python tools/gate.py plan [--to 5] [--max 4]                  # /run 진행 계획(웨이브·축·멈춤 조건)
#   python tools/gate.py trace [--slice notice] [--strict]        # 요구사항 → 계약 → 테스트 추적 대조
#   python tools/gate.py secrets <파일|디렉토리> ...              # 비밀정보 스캔만
#   python tools/gate.py oi new --stage 2 --slice notice --kind unverified --severity high \
#          --summary "..." --evidence "파일:라인" --target 5
#   python tools/gate.py oi import --report <레포트> --write     # pa-meta 의 open_items 일괄 채번
#   python tools/gate.py oi list [--status open] [--slice notice]
#   python tools/gate.py oi set OI-0003 converted --rr RR-0041 [--note "..."]
#   python tools/gate.py oi set OI-0004 accepted --approved-by 사용자 --expiry 2026-10-31 --note "..."
#
# 종료 코드: 0 통과(WARN 포함) · 1 차단(FAIL) · 2 입력/실행 오류
# 의존성: pyyaml

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    sys.exit("[gate] pyyaml 패키지가 필요합니다. 설치: python -m pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = datetime.timezone(datetime.timedelta(hours=9), name="KST")

META_START = "<!-- pa-meta:start"
META_END = "pa-meta:end -->"

RESULTS = ("done", "done_with_gaps", "blocked", "failed")
OI_KINDS = ("evidence_gap", "decision", "unverified", "risk", "deferred")

# 검증 축 — "앞 단계가 보지 못하는 축" 에서만 새 결함이 나온다는 실측(채점표 7건)에서 나온 분류
AXES = ("unit", "module", "real-db", "real-server", "browser", "concurrency", "security-static")
# 모든 slice 가 공통으로 요구하는 축. module 이상은 slice 특성(traits)이 요구할 때만 본다 —
# 기본 요구를 넓히면 axis 를 적지 않은 기존 관행이 곧바로 차단돼 도구가 무시당한다.
BASE_AXES = ("unit",)
# slice 특성(traits) → 반드시 닫아야 하는 축. config 의 verification.trait_axes 로 덮어쓸 수 있다.
TRAIT_AXES = {
    "file-upload": ["real-server"],       # 서블릿/파서 단계가 서비스보다 먼저 갈린다 (multipart NUL·413 실측)
    "transaction": ["real-db"],           # H2 로는 못 보는 방언·캐스트 (Timestamp·H2 override 실측)
    "batch": ["real-db"],
    "counter": ["concurrency"],           # 조회수·시퀀스 (REQUIRES_NEW 커넥션 2중 점유 실측)
    "concurrency-sensitive": ["concurrency"],
    "rich-text": ["browser"],             # jsdom 이 못 잡는 로드 크래시 (Tiptap 실측)
    "dom-heavy": ["browser"],
    "auth": ["real-server"],              # 필터·프록시 경로 (XFF 위조 실측)
    "proxy-header": ["real-server"],
    "external-io": ["real-server"],
    "sanitizer": ["security-static"],
}
# 각 축을 닫는 것이 자연스러운 단계 (안내용)
AXIS_STAGE = {"unit": 2, "module": 2, "real-db": 5, "real-server": 5,
              "browser": 4, "concurrency": 7, "security-static": 6}
# 포함 관계 — 바깥 축을 닫으면 안쪽 축도 닫힌 것으로 본다 (실 서버 테스트는 컨텍스트·로직을 이미 지난다)
AXIS_IMPLIES = {
    "module": ["unit"],
    "real-db": ["unit", "module"],
    "real-server": ["unit", "module"],
    "browser": ["unit"],
}


def expand_axes(axes):
    out = set()
    for a in axes:
        if not a:
            continue
        out.add(a)
        out.update(AXIS_IMPLIES.get(a, []))
    return out


def gate_axes(g):
    """gates[].axis 는 문자열 또는 배열."""
    a = g.get("axis")
    if isinstance(a, str):
        return [a]
    if isinstance(a, list):
        return [x for x in a if isinstance(x, str)]
    return []
SEVERITIES = ("blocker", "high", "medium", "low")
OI_STATUSES = ("open", "resolved", "converted", "accepted")
BLOCKING_SEV = ("blocker", "high")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

# 개발 단계(빌드·테스트 게이트가 완료 조건인 단계)
DEV_STAGES = (2, 3, 4)

# 자격증명·개인정보 패턴. 값이 플레이스홀더면 건너뛴다.
SECRET_PATTERNS = {
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}\b"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "bearer": re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[A-Za-z0-9._~+/-]{12,}"),
    "password": re.compile(r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*(\S+)"),
    "cookie": re.compile(r"(?i)(?:set-cookie|jsessionid|session(?:id|token))\s*[:=]\s*(\S+)"),
    "phone": re.compile(r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)"),
    "rrn": re.compile(r"(?<!\d)\d{6}[- ]\d{7}(?!\d)"),
}
# 플레이스홀더로 간주해 넘기는 값
PLACEHOLDER_RE = re.compile(
    r"^[\"'`]?(?:\*+|x{3,}|<[^>]*>|\{\{?[^}]*\}?\}|\$\{[^}]*\}|redacted|masked|dummy|sample|example|changeme|"
    r"password|secret|token|test|none|null|nil|생략|마스킹|비공개)[\"'`,.]?$",
    re.IGNORECASE,
)


def now_kst(full=True) -> str:
    n = datetime.datetime.now(KST)
    return n.strftime("%Y-%m-%d %H:%M") if full else n.strftime("%y%m%d%H%M")


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def config():
    try:
        return load_yaml(os.path.join(ROOT, "config", "project.yaml"))
    except Exception:
        return {}


def workspace():
    cfg = config()
    name = (cfg.get("project") or {}).get("name")
    return os.path.join(ROOT, "workspace", name) if name else os.path.join(ROOT, "workspace")


def target_dir():
    cfg = config()
    td = (cfg.get("project") or {}).get("target_dir")
    if not td:
        return None
    return td if os.path.isabs(td) else os.path.normpath(os.path.join(ROOT, td))


WS = workspace()
REPORTS = os.path.join(WS, "reports")
OI_FILE = os.path.join(WS, "open-items.yaml")
RR_DIR = os.path.join(WS, "refactor-requests")
STATE = os.path.join(WS, "state.yaml")


# ---------------------------------------------------------------- 결과 형식

def finding(severity, field, message, action=""):
    return {"severity": severity, "field": field, "message": message, "action": action}


def result_of(hook, findings, evidence, skipped=False):
    blocking = any(f["severity"] in ("FAIL", "CRITICAL") for f in findings)
    if skipped:
        res = "SKIPPED"
    elif blocking:
        res = "FAIL"
    elif findings:
        res = "WARN"
    else:
        res = "PASS"
    return {"hook": hook, "result": res, "findings": findings, "evidence": evidence}


def fail(field, message, action=""):
    return finding("FAIL", field, message, action)


def warn(field, message, action=""):
    return finding("WARN", field, message, action)


# ---------------------------------------------------------------- 메타 파싱

def extract_meta(path):
    """레포트에서 pa-meta 블록의 JSON 을 꺼낸다. (meta, error)"""
    if not os.path.exists(path):
        return None, f"레포트가 없다: {path}"
    with open(path, encoding="utf-8") as f:
        text = f.read()
    s, e = text.find(META_START), text.find(META_END)
    if s < 0 or e < 0 or e <= s:
        return None, "pa-meta 블록이 없다 (templates/report-meta.json 형식으로 레포트 끝에 넣는다)"
    block = text[s + len(META_START):e]
    l, r = block.find("{"), block.rfind("}")
    if l < 0 or r < l:
        return None, "pa-meta 블록에 JSON 객체가 없다"
    try:
        meta = json.loads(block[l:r + 1])
    except json.JSONDecodeError as ex:
        return None, f"pa-meta JSON 파싱 실패: {ex.msg} (line {ex.lineno})"
    if not isinstance(meta, dict):
        return None, "pa-meta 는 객체여야 한다"
    return meta, None


def find_report(stage, slice_id):
    """최신 레포트 자동 탐색: yymmddhhmm_stage<N>_<slice|all>_*.md"""
    if not os.path.isdir(REPORTS):
        return None
    pats = [f"*_stage{stage}_{slice_id}_*.md"] if slice_id else [f"*_stage{stage}_*.md"]
    hits = []
    for p in pats:
        hits.extend(glob.glob(os.path.join(REPORTS, p)))
    return sorted(hits)[-1] if hits else None


# ---------------------------------------------------------------- 훅

def hook_report_meta(ctx):
    meta, err = ctx["meta"], ctx["meta_error"]
    ev = [ctx["report"]]
    if err:
        return result_of("report-meta", [fail("meta", err, "레포트 끝에 pa-meta 블록을 넣는다")], ev)
    f = []
    if meta.get("schema") != 1:
        f.append(fail("schema", "schema 는 1 이어야 한다"))
    for key in ("stage", "result", "agent"):
        if not meta.get(key) and meta.get(key) != 0:
            f.append(fail(key, f"{key} 가 비었다"))
    if meta.get("result") not in RESULTS:
        f.append(fail("result", f"result 는 {'|'.join(RESULTS)} 중 하나여야 한다 (현재: {meta.get('result')})"))
    try:
        stage = int(meta.get("stage"))
    except (TypeError, ValueError):
        stage = None
        f.append(fail("stage", "stage 는 정수여야 한다"))
    if stage is not None and ctx["stage"] is not None and stage != ctx["stage"]:
        f.append(fail("stage", f"레포트 메타의 stage({stage}) 가 검사 대상 stage({ctx['stage']}) 와 다르다"))
    if ctx["slice"] and meta.get("slice") and meta.get("slice") != ctx["slice"]:
        f.append(fail("slice", f"메타 slice({meta.get('slice')}) 가 검사 대상({ctx['slice']}) 과 다르다"))
    if not meta.get("finished_at"):
        f.append(warn("finished_at", "종료 시각이 없다"))
    return result_of("report-meta", f, ev)


def hook_gate_proof(ctx):
    """빌드·테스트 실행 증거 검사. '조용한 0건 매칭'(EXIT 0 · 0 tests)을 차단한다."""
    meta = ctx["meta"]
    ev = [ctx["report"]]
    if not meta:
        return result_of("gate-proof", [], ev, skipped=True)
    f = []
    stage = meta.get("stage")
    gates = meta.get("gates")
    if not isinstance(gates, list):
        return result_of("gate-proof", [fail("gates", "gates 배열이 없다")], ev)
    kinds = set()
    for i, g in enumerate(gates):
        fld = f"gates[{i}]"
        if not isinstance(g, dict):
            f.append(fail(fld, "게이트 항목은 객체여야 한다"))
            continue
        kind = g.get("kind")
        kinds.add(kind)
        if kind not in ("build", "test", "lint", "typecheck", "smoke", "scan", "other"):
            f.append(fail(f"{fld}.kind", f"알 수 없는 kind: {kind}"))
        if kind in ("test", "smoke", "scan"):
            axes = gate_axes(g)
            if g.get("axis") is None:
                f.append(warn(f"{fld}.axis", f"검증 축이 없다 ({'|'.join(AXES)})", "어느 축을 닫은 실행인지 적는다"))
            elif not axes:
                f.append(fail(f"{fld}.axis", "axis 는 문자열 또는 문자열 배열이어야 한다"))
            for a in axes:
                if a not in AXES:
                    f.append(fail(f"{fld}.axis", f"알 수 없는 axis: {a}"))
        if not str(g.get("command", "")).strip():
            f.append(fail(f"{fld}.command", "실행한 명령을 그대로 적는다"))
        if not isinstance(g.get("exit_code"), int):
            f.append(fail(f"{fld}.exit_code", "종료 코드(정수)를 적는다"))
        elif g["exit_code"] != 0 and meta.get("result") in ("done", "done_with_gaps"):
            f.append(fail(f"{fld}.exit_code",
                          f"종료 코드 {g['exit_code']} 인데 result={meta.get('result')} 다",
                          "게이트를 통과시키거나 result 를 blocked/failed 로 내린다"))
        if not g.get("executed_at"):
            f.append(warn(f"{fld}.executed_at", "실행 시각이 없다"))
        if kind in ("test", "smoke"):
            tc = g.get("test_count")
            if not isinstance(tc, int):
                f.append(fail(f"{fld}.test_count", "테스트 개수를 적는다 (집계 명령 근거 포함)"))
            elif tc <= 0:
                f.append(fail(f"{fld}.test_count",
                              "테스트가 0건인데 통과로 기록됐다 (필터가 아무것도 매칭하지 않은 경우)",
                              "필터 패턴을 고쳐 실제 실행 개수를 확인한다"))
            if isinstance(g.get("failures"), int) and g["failures"] > 0 and meta.get("result") == "done":
                f.append(fail(f"{fld}.failures", f"실패 {g['failures']}건인데 result=done 이다"))
    if isinstance(stage, int) and stage in DEV_STAGES and meta.get("result") in ("done", "done_with_gaps"):
        for need in ("build", "test"):
            if need not in kinds:
                f.append(fail("gates", f"{stage}단계 완료에는 {need} 게이트 기록이 필요하다"))
    return result_of("gate-proof", f, ev)


def git(cwd, *args):
    try:
        p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False,
                           encoding="utf-8", errors="replace")
    except OSError as ex:
        return None, str(ex)
    if p.returncode != 0:
        return None, (p.stderr or "").strip() or f"git exit {p.returncode}"
    return p.stdout.strip(), None


def hook_repo_consistency(ctx):
    """레포트가 적은 브랜치/HEAD/dirty/변경파일을 target_dir 의 git 으로 실측 대조."""
    meta = ctx["meta"]
    ev = [ctx["report"]]
    if not meta:
        return result_of("repo-consistency", [], ev, skipped=True)
    repo = meta.get("repo")
    stage = meta.get("stage")
    if repo is None:
        sev = fail if (isinstance(stage, int) and stage in DEV_STAGES) else warn
        return result_of("repo-consistency", [sev("repo", "repo(브랜치·HEAD·변경파일) 기록이 없다")], ev)
    if not isinstance(repo, dict):
        return result_of("repo-consistency", [fail("repo", "repo 는 객체여야 한다")], ev)
    f = []
    head = repo.get("head")
    if head != "NOT_CHANGED" and not (isinstance(head, str) and SHA_RE.match(head or "")):
        f.append(fail("repo.head", "head 는 커밋 SHA 또는 NOT_CHANGED 여야 한다"))
    if head == "NOT_CHANGED" and repo.get("changed_files"):
        f.append(fail("repo.changed_files", "head=NOT_CHANGED 인데 변경 파일이 있다"))
    td = ctx["target_dir"]
    if not td or not os.path.isdir(os.path.join(td, ".git")):
        f.append(warn("repo.actual", f"target_dir git 을 찾지 못해 메타 내부 검사만 했다: {td}"))
        return result_of("repo-consistency", f, ev)
    ev.append(td)
    actual_head, e1 = git(td, "rev-parse", "HEAD")
    actual_branch, e2 = git(td, "branch", "--show-current")
    status, e3 = git(td, "status", "--porcelain")
    if e1 or e2 or e3:
        f.append(warn("repo.actual", f"git 실행 실패: {e1 or e2 or e3}"))
        return result_of("repo-consistency", f, ev)
    if head and head != "NOT_CHANGED" and actual_head and not actual_head.startswith(head):
        f.append(fail("repo.head", f"기재 HEAD({head}) 와 실제 HEAD({actual_head[:12]}) 가 다르다",
                      "레포트를 현재 HEAD 로 갱신하거나 커밋 후 다시 기록한다"))
    if repo.get("branch") and actual_branch and repo["branch"] != actual_branch:
        f.append(fail("repo.branch", f"기재 브랜치({repo['branch']}) ≠ 실제({actual_branch})"))
    if isinstance(repo.get("dirty"), bool) and repo["dirty"] != bool(status):
        f.append(fail("repo.dirty", f"기재 dirty={repo['dirty']} ≠ 실제 {bool(status)}",
                      "커밋하지 않은 변경이 있으면 dirty=true 로 적는다"))
    declared = repo.get("changed_files")
    base = repo.get("base")
    if isinstance(declared, list) and declared:
        for p in declared:
            if not isinstance(p, str) or os.path.isabs(p) or ".." in p.replace("\\", "/").split("/"):
                f.append(fail("repo.changed_files", f"repo 기준 상대경로여야 한다: {p}"))
        if base:
            diff, e4 = git(td, "diff", "--name-only", f"{base}...HEAD")
            if e4:
                f.append(warn("repo.changed_files", f"base({base}) 대조 불가: {e4}"))
            else:
                actual = {l.strip() for l in (diff or "").splitlines() if l.strip()}
                decl = {p.replace("\\", "/").strip() for p in declared if isinstance(p, str)}
                missing = sorted(actual - decl)
                extra = sorted(decl - actual)
                if missing or extra:
                    detail = []
                    if missing:
                        detail.append("누락: " + ", ".join(missing[:8]) + (" …" if len(missing) > 8 else ""))
                    if extra:
                        detail.append("초과: " + ", ".join(extra[:8]) + (" …" if len(extra) > 8 else ""))
                    f.append(fail("repo.changed_files", "기재 변경 파일이 git diff 와 다르다 (" + "; ".join(detail) + ")",
                                  "git diff --name-only base...HEAD 결과로 갱신한다"))
        else:
            f.append(warn("repo.base", "base 가 없어 변경 파일 대조를 건너뛰었다"))
    return result_of("repo-consistency", f, ev)


def load_open_items():
    if not os.path.exists(OI_FILE):
        return {"items": []}
    data = load_yaml(OI_FILE)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return {"items": []}
    return data


def rr_exists(rid):
    return bool(rid) and os.path.exists(os.path.join(RR_DIR, f"{rid}.yaml"))


def hook_open_items(ctx):
    """미해결 항목이 RR·승인 없이 사라지지 않는지. (레포트 메타 ↔ open-items.yaml 대조)"""
    meta = ctx["meta"]
    ev = [ctx["report"], OI_FILE]
    if not meta:
        return result_of("open-items", [], ev, skipped=True)
    f = []
    store = {i.get("id"): i for i in load_open_items()["items"] if isinstance(i, dict)}
    items = meta.get("open_items")
    if items is None:
        return result_of("open-items", [warn("open_items", "open_items 키가 없다 (없으면 빈 배열로 적는다)")], ev)
    if not isinstance(items, list):
        return result_of("open-items", [fail("open_items", "open_items 는 배열이어야 한다")], ev)
    for i, it in enumerate(items):
        fld = f"open_items[{i}]"
        if not isinstance(it, dict):
            f.append(fail(fld, "항목은 객체여야 한다"))
            continue
        oid = it.get("id")
        if not oid:
            f.append(fail(f"{fld}.id", "OI-NNNN id 가 필요하다 (python tools/gate.py oi new …)"))
        elif oid not in store:
            f.append(fail(f"{fld}.id", f"{oid} 가 open-items.yaml 에 없다", "gate.py oi new 로 먼저 채번한다"))
        if it.get("kind") not in OI_KINDS:
            f.append(fail(f"{fld}.kind", f"kind 는 {'|'.join(OI_KINDS)} 중 하나여야 한다"))
        sev = it.get("severity")
        if sev not in SEVERITIES:
            f.append(fail(f"{fld}.severity", f"severity 는 {'|'.join(SEVERITIES)} 중 하나여야 한다"))
        if not str(it.get("evidence", "")).strip():
            f.append(fail(f"{fld}.evidence", "근거(파일:라인·명령·레포트 절)가 없다"))
        target = it.get("target_stage")
        if target is None or target == "":
            f.append(fail(f"{fld}.target_stage", "어느 단계가 닫을 항목인지 적는다 (사람 결정 대기는 0)"))
        status = (store.get(oid) or it).get("status", "open")
        rid = (store.get(oid) or it).get("rr_id") or it.get("rr_id")
        # RR(리팩토링 요구서)은 "이미 있는 코드의 결함" 을 고치라는 요구다. 그래서 RR 전환을 요구할 수 있는 것은
        # 코드가 존재하는 단계(2~7)에서 나온 unverified·risk 뿐이다.
        # decision·evidence_gap·deferred 는 다음 단계가 자기 일로 받아 닫는 정상 경로이므로 예약(target_stage)만 있으면 된다.
        stage_num = meta.get("stage") if isinstance(meta.get("stage"), int) else None
        code_exists = stage_num is not None and stage_num >= 2
        rr_applicable = it.get("kind") in ("unverified", "risk") and code_exists
        if sev in BLOCKING_SEV and meta.get("result") in ("done", "done_with_gaps"):
            if not rr_applicable and status == "open":
                where = "사람 결정 대기" if str(target) == "0" else f"stage{target} 가 닫을 항목으로 예약"
                f.append(warn(f"{fld}", f"{sev} 항목이 열린 채 넘어간다 ({where})",
                              "사용자 보고에 포함하고, 그 단계 착수 시 oi list --target 으로 받아 처리한다"))
            elif status == "open" and not rid:
                f.append(fail(f"{fld}", f"{sev} 항목이 RR 연결·사람 승인 없이 열린 채로 완료 처리됐다",
                              "RR 로 변환(gate.py oi set <id> converted --rr RR-xxxx)하거나 accepted 승인을 받는다"))
            if rid and not rr_exists(rid):
                f.append(fail(f"{fld}.rr_id", f"{rid} 파일이 없다"))
            if status == "accepted":
                rec = store.get(oid, {})
                if not rec.get("approved_by"):
                    f.append(fail(f"{fld}", "accepted 는 approved_by(사람) 기록이 필요하다"))
                exp = str(rec.get("expiry") or "")
                try:
                    ok = datetime.date.fromisoformat(exp) >= datetime.datetime.now(KST).date()
                except ValueError:
                    ok = False
                if not ok:
                    f.append(fail(f"{fld}", f"accepted 의 expiry({exp or '없음'}) 가 없거나 지났다"))
    # 이번 단계·slice 가 닫기로 한 항목이 레포트에서 언급되지 않은 경우.
    # 같은 단계라도 레포트는 slice 마다 나뉘므로, 이름이 정확히 일치하는 항목만 누락으로 본다.
    # slice 가 특정되지 않은 항목(all·공란)은 어느 레포트가 닫을지 알 수 없어 건수만 알린다.
    stage, sl = meta.get("stage"), meta.get("slice")
    listed = {it.get("id") for it in items if isinstance(it, dict)}
    pending_other = 0
    for oid, rec in store.items():
        if rec.get("status") != "open" or str(rec.get("target_stage")) != str(stage) or oid in listed:
            continue
        if sl and rec.get("slice") == sl:
            f.append(warn("open_items", f"{oid} 는 이 단계·이 slice 가 닫기로 한 항목인데 레포트에 없다",
                          "처리했으면 resolved 로, 남았으면 메타에 싣는다"))
        else:
            pending_other += 1
    if pending_other:
        f.append(warn("open_items",
                      f"이 단계가 닫기로 한 항목 {pending_other}건이 아직 열려 있다(다른 slice 몫이거나 미배정)",
                      f"python tools/gate.py oi list --status open --target {stage} 로 확인한다"))
    if not isinstance(meta.get("rr_ids"), list):
        f.append(warn("rr_ids", "rr_ids 배열이 없다"))
    else:
        for rid in meta["rr_ids"]:
            if not rr_exists(rid):
                f.append(fail("rr_ids", f"{rid} 파일이 없다"))
    return result_of("open-items", f, ev)


def hook_state_consistency(ctx):
    """state.yaml 의 상태와 레포트 result 가 모순되지 않는지."""
    meta = ctx["meta"]
    ev = [ctx["report"], STATE]
    if not meta or not os.path.exists(STATE):
        return result_of("state-consistency", [], ev, skipped=True)
    try:
        st = load_yaml(STATE)
    except Exception as ex:
        return result_of("state-consistency", [warn("state", f"state.yaml 읽기 실패: {ex}")], ev)
    f = []
    stage, sl = meta.get("stage"), meta.get("slice")
    expect = {"done": "done", "done_with_gaps": "done", "blocked": "blocked", "failed": "blocked"}.get(meta.get("result"))
    key_by_stage = {0: "stage0_ingest", 1: "stage1_slicing", 3: "stage3_common", 5: "stage5_integration",
                    6: "stage6_security", 7: "stage7_qa", 8: "stage8_deliverables"}
    if sl in ("scaffold", "scaffold-fe"):   # 골격 레포트는 slices 가 아니라 stages 를 본다
        key_by_stage.update({2: "stage2_scaffold", 4: "stage4_scaffold"})
        sl = None
    actual = None
    if sl and isinstance(st.get("slices"), dict) and sl in st["slices"]:
        node = st["slices"][sl] or {}
        actual = node.get({2: "stage2_backend", 4: "stage4_frontend", 5: "stage5_integration"}.get(stage, ""), None)
    if actual is None and stage in key_by_stage:
        actual = (st.get("stages") or {}).get(key_by_stage[stage])
    if actual is None:
        f.append(warn("state", "state.yaml 에서 해당 항목을 찾지 못했다"))
    elif expect and actual not in (expect, "in_progress"):
        f.append(fail("state", f"레포트 result={meta.get('result')} 인데 state.yaml 은 {actual} 이다",
                      "웨이브 종료 시 state.yaml 을 갱신한다"))
    return result_of("state-consistency", f, ev)


def load_slices():
    path = os.path.join(WS, "slices", "slices.yaml")
    if not os.path.exists(path):
        return None, path
    try:
        return load_yaml(path), path
    except Exception:
        return None, path


def slice_entry(slice_id):
    data, path = load_slices()
    if not data or not slice_id:
        return None, path
    for s in (data.get("slices") or []):
        if isinstance(s, dict) and s.get("id") == slice_id:
            return s, path
    return None, path


def trait_axis_map():
    cfg = (config().get("verification") or {})
    custom = cfg.get("trait_axes")
    if isinstance(custom, dict):
        merged = dict(TRAIT_AXES)
        merged.update({k: list(v) for k, v in custom.items() if isinstance(v, list)})
        return merged
    return TRAIT_AXES


def hook_coverage_axis(ctx):
    """slice 의 특성(traits)이 요구하는 검증 축이 닫혔거나, 닫을 단계가 예약돼 있는지.

    실측 근거: 파이프라인이 스스로 만든 결함 7건은 전부 '앞 단계가 보지 못한 축'에서만 잡혔다.
    """
    meta = ctx["meta"]
    if not meta:
        return result_of("coverage-axis", [], [ctx["report"]], skipped=True)
    slice_id = meta.get("slice")
    entry, spath = slice_entry(slice_id)
    ev = [ctx["report"], spath]
    if not slice_id or slice_id == "all" or entry is None:
        return result_of("coverage-axis", [], ev, skipped=True)
    traits = entry.get("traits")
    if not isinstance(traits, list) or not traits:
        return result_of("coverage-axis",
                         [warn("traits", f"slices.yaml 의 {slice_id} 에 traits 가 없어 축 검사를 건너뛴다",
                               "stage1 에서 traits(file-upload·transaction·counter·rich-text·auth 등)를 채운다")], ev)
    amap = trait_axis_map()
    required = set(BASE_AXES)
    unknown = []
    for t in traits:
        if t in amap:
            required.update(amap[t])
        else:
            unknown.append(t)
    declared = []
    for g in (meta.get("gates") or []):
        if not isinstance(g, dict) or g.get("exit_code") != 0:
            continue
        axes = gate_axes(g)
        if axes:
            declared.extend(axes)
        elif g.get("kind") in ("test", "smoke"):
            declared.append("unit")   # 축 미기재 테스트는 가장 약한 축만 닫은 것으로 본다
    covered = expand_axes(declared)
    deferred = {i.get("axis") for i in (meta.get("open_items") or [])
                if isinstance(i, dict) and i.get("axis")}
    f = []
    for t in unknown:
        f.append(warn("traits", f"알 수 없는 trait: {t}", "config 의 verification.trait_axes 에 매핑을 추가한다"))
    missing = sorted(required - covered - deferred)
    stage = meta.get("stage")
    for axis in missing:
        owner = AXIS_STAGE.get(axis, 5)
        blocking = isinstance(stage, int) and stage >= owner
        msg = f"{slice_id}({','.join(traits)}) 가 요구하는 '{axis}' 축이 닫히지도, 예약되지도 않았다"
        act = (f"그 축으로 실행해 gates[].axis={axis} 로 남기거나, "
               f"python tools/gate.py oi new --stage {stage} --slice {slice_id} --kind unverified "
               f"--axis {axis} --target {owner} … 로 넘긴다")
        f.append(finding("FAIL" if blocking else "WARN", f"axis.{axis}", msg, act))
    return result_of("coverage-axis", f, ev)


TEST_GLOBS = ("**/src/test/**/*.java", "**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx")


def collect_test_text(td, cache={}):
    if td in cache:
        return cache[td]
    chunks = []
    for pat in TEST_GLOBS:
        for p in glob.glob(os.path.join(td, pat), recursive=True):
            if "node_modules" in p or os.sep + "target" + os.sep in p or os.sep + "dist" + os.sep in p:
                continue
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    chunks.append(fh.read())
            except OSError:
                continue
    cache[td] = "\n".join(chunks)
    return cache[td]


def trace_slice(td, entry):
    """slice 의 요구사항 ID 가 테스트까지 살아 있는지. (found, missing, contract_ok)"""
    reqs = [str(r) for r in (entry.get("requirements") or [])]
    text = collect_test_text(td) if td else ""
    found, missing = [], []
    for r in reqs:
        (found if r and r in text else missing).append(r)
    contract = os.path.join(td, "docs", "api", f"{entry.get('id')}.yaml") if td else ""
    contract_ok = (not entry.get("apis")) or (contract and os.path.exists(contract))
    return found, missing, contract_ok, contract


def hook_traceability(ctx):
    """요구사항 ID 가 slices → 테스트까지 이어지는지. 8단계에서 '끊긴 추적' 으로 드러나던 것을 앞당긴다."""
    meta = ctx["meta"]
    if not meta:
        return result_of("traceability", [], [ctx["report"]], skipped=True)
    slice_id = meta.get("slice")
    entry, spath = slice_entry(slice_id)
    ev = [ctx["report"], spath]
    td = ctx["target_dir"]
    if entry is None or not td or not os.path.isdir(td):
        return result_of("traceability", [], ev, skipped=True)
    found, missing, contract_ok, contract = trace_slice(td, entry)
    stage = meta.get("stage")
    blocking = isinstance(stage, int) and stage == 8
    f = []
    if not found and not missing:
        return result_of("traceability", [warn("requirements", f"{slice_id} 에 requirements 가 없다")], ev)
    for r in missing:
        f.append(finding("FAIL" if blocking else "WARN", f"trace.{r}",
                         f"{r} 을 인용한 테스트를 찾지 못했다 (8단계 추적표에서 끊긴 연결이 된다)",
                         "요구사항을 다루는 테스트의 @DisplayName·describe 에 요구사항 ID 를 적는다"))
    if not contract_ok:
        f.append(finding("FAIL" if blocking else "WARN", "trace.contract",
                         f"API 가 있는 slice 인데 계약 파일이 없다: {contract}", "2단계에서 계약을 산출한다"))
    return result_of("traceability", f, ev)


def hook_cost_record(ctx):
    """단계 비용(소요·tool call) 기록. 회차 간 비교 근거이며 누락은 경고만 한다."""
    meta = ctx["meta"]
    if not meta:
        return result_of("cost-record", [], [ctx["report"]], skipped=True)
    cost = meta.get("cost")
    f = []
    if cost is None:
        f.append(warn("cost", "cost(소요 시간·tool call·토큰) 기록이 없다",
                      "cost: {duration_min, tool_calls, tokens_k} 를 남기면 회차 간 비용 비교가 된다"))
    elif not isinstance(cost, dict):
        f.append(fail("cost", "cost 는 객체여야 한다"))
    else:
        for k in ("duration_min", "tool_calls"):
            v = cost.get(k)
            if v is not None and not isinstance(v, (int, float)):
                f.append(fail(f"cost.{k}", f"{k} 는 숫자여야 한다"))
        if cost.get("duration_min") is None:
            f.append(warn("cost.duration_min", "소요 시간이 없다"))
    # 판별력 실측(mutation·수정 전 재현) 기록 — 산문에만 남으면 기계 추적이 안 된다(실측: 범위를 한 클래스로 좁혀
    # 보고한 것을 reviewer 가 잡았다). gates[] 에 실으면 gate-proof 가 "실패를 통과로 기재" 로 읽으므로 별도 칸이다.
    disc = meta.get("discrimination")
    if disc is not None:
        if not isinstance(disc, list):
            f.append(fail("discrimination", "discrimination 은 배열이어야 한다"))
        else:
            for i, d in enumerate(disc):
                fld = f"discrimination[{i}]"
                if not isinstance(d, dict):
                    f.append(fail(fld, "항목은 객체여야 한다"))
                    continue
                if not str(d.get("target", "")).strip():
                    f.append(fail(f"{fld}.target", "무엇의 판별력을 증명했는지(테스트·지적 id) 적는다"))
                method = d.get("method")
                if method not in ("mutation", "pre_fix_repro", "absent_pre_fix", "other"):
                    f.append(fail(f"{fld}.method", "method 는 mutation | pre_fix_repro | absent_pre_fix | other"))
                if not str(d.get("scope", "")).strip():
                    f.append(fail(f"{fld}.scope", "실행 범위(모듈·클래스)를 적는다 — 범위를 좁혀 일반화한 오보가 실측됐다",
                                  "모듈 전체(-pl <모듈> test)로 1회 실행하는 것이 기준이다"))
                # absent_pre_fix = 수정 전에는 판별 수단(메서드·오류코드)이 없어 재현 단언을 쓸 수조차 없던 경우.
                # 이때만 failures 0 을 허용하되, 해악의 실재 증거와 mutation 을 둘 다 요구한다 —
                # "재현 불가" 가 판별력 면제로 쓰이면 규격이 자리끼움 숫자를 부른다(실측: failures:1 로 적고 통과).
                if method == "absent_pre_fix":
                    if d.get("failures") not in (0, None):
                        f.append(warn(f"{fld}.failures", "absent_pre_fix 는 failures 0 이 정상이다"))
                    if not str(d.get("harm_evidence", "")).strip():
                        f.append(fail(f"{fld}.harm_evidence",
                                      "결함의 해악이 실재함을 증명하는 통과 단언(예: FK 위반 재현)을 적는다"))
                    if not str(d.get("mutation", "")).strip():
                        f.append(fail(f"{fld}.mutation",
                                      "수정 후 구현에 결함을 주입해 새 테스트가 잡는지 확인한 기록을 적는다",
                                      "absent_pre_fix 는 mutation 을 면제하지 않는다 — 재현이 불가능하면 mutation 이 의무다"))
                elif not isinstance(d.get("failures"), int) or d["failures"] <= 0:
                    f.append(fail(f"{fld}.failures", "재현 실패 건수(1 이상)를 적는다 — 0 이면 판별력을 증명하지 못했다"))
                if not str(d.get("evidence", "")).strip():
                    f.append(warn(f"{fld}.evidence", "실패 실행의 surefire XML 사본 경로를 남긴다",
                                  "최종 실행이 XML 을 덮어써 독립 검증이 불가능했다(실측)"))
                if not str(d.get("restored", "")).strip():
                    f.append(warn(f"{fld}.restored", "되돌림 확인 방법(grep·재통과 건수)을 적는다"))
    risks = meta.get("risk_surface")
    if risks is not None:
        if not isinstance(risks, list):
            f.append(fail("risk_surface", "risk_surface 는 배열이어야 한다"))
        else:
            for i, r in enumerate(risks):
                if not isinstance(r, dict):
                    f.append(fail(f"risk_surface[{i}]", "항목은 객체여야 한다"))
                    continue
                if not str(r.get("what", "")).strip():
                    f.append(fail(f"risk_surface[{i}].what", "이 변경이 무엇을 깨뜨릴 수 있는지 적는다"))
                if r.get("axis") and r["axis"] not in AXES:
                    f.append(fail(f"risk_surface[{i}].axis", f"알 수 없는 axis: {r['axis']}"))
                if not str(r.get("covered_by", "")).strip():
                    f.append(fail(f"risk_surface[{i}].covered_by",
                                  "무엇으로 덮었는지(테스트명) 또는 '미검증' 을 적는다",
                                  "미검증이면 확인 필요 항목으로 남긴다"))
    return result_of("cost-record", f, [ctx["report"]])


def scan_secrets_text(text, label):
    f = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for name, pat in SECRET_PATTERNS.items():
            m = pat.search(line)
            if not m:
                continue
            value = m.group(1) if m.groups() else m.group(0)
            if PLACEHOLDER_RE.match(value.strip()):
                continue
            if name == "password" and re.search(r"(?i)(?:password|token|secret|api[_-]?key)\s*[:=]\s*[\"'`]?\$?\{", line):
                continue
            snippet = line.strip()[:110]
            f.append(finding("FAIL", f"{label}:{line_no}", f"{name} 로 보이는 값이 있다: {snippet}",
                             "값을 마스킹(***)하거나 참조 경로만 남긴다"))
    return f


def hook_secret_scan(ctx):
    ev = [ctx["report"]]
    if not os.path.exists(ctx["report"]):
        return result_of("secret-scan", [], ev, skipped=True)
    with open(ctx["report"], encoding="utf-8") as fp:
        text = fp.read()
    return result_of("secret-scan", scan_secrets_text(text, os.path.basename(ctx["report"])), ev)


HOOKS = {
    "report-meta": hook_report_meta,
    "gate-proof": hook_gate_proof,
    "repo-consistency": hook_repo_consistency,
    "coverage-axis": hook_coverage_axis,
    "traceability": hook_traceability,
    "open-items": hook_open_items,
    "state-consistency": hook_state_consistency,
    "cost-record": hook_cost_record,
    "secret-scan": hook_secret_scan,
}
PROFILES = {
    # 2·3·4단계: 빌드·테스트 증거와 git 실측까지
    "dev": ["report-meta", "gate-proof", "repo-consistency", "coverage-axis", "traceability",
            "open-items", "state-consistency", "cost-record", "secret-scan"],
    # 5·6·7단계: 검증 단계 — 결함은 RR, 미확인은 open item 으로 나갔는지
    "verify": ["report-meta", "gate-proof", "coverage-axis", "open-items", "state-consistency",
               "cost-record", "secret-scan"],
    # 0·1단계
    "doc": ["report-meta", "open-items", "state-consistency", "cost-record", "secret-scan"],
    # 8단계: 추적 체인이 끊기면 산출물이 비어 나온다 → 여기서는 차단
    "deliver": ["report-meta", "traceability", "open-items", "state-consistency", "cost-record", "secret-scan"],
    "all": list(HOOKS),
}
STAGE_PROFILE = {0: "doc", 1: "doc", 2: "dev", 3: "dev", 4: "dev", 5: "verify", 6: "verify", 7: "verify", 8: "deliver"}


# ---------------------------------------------------------------- 명령

def cmd_check(args):
    report = args.report
    stage = args.stage
    if report and not os.path.isabs(report):
        report = os.path.normpath(os.path.join(ROOT, report))
    if not report:
        if stage is None:
            sys.exit("[gate] --report 또는 --stage 가 필요하다")
        report = find_report(stage, args.slice)
        if not report:
            sys.exit(f"[gate] stage{stage} {args.slice or ''} 레포트를 찾지 못했다: {REPORTS}")
    meta, meta_error = extract_meta(report)
    if stage is None and meta and isinstance(meta.get("stage"), int):
        stage = meta["stage"]
    profile = args.profile or STAGE_PROFILE.get(stage, "all")
    ctx = {"report": report, "meta": meta, "meta_error": meta_error, "stage": args.stage,
           "slice": args.slice, "target_dir": target_dir()}
    results = [HOOKS[h](ctx) for h in PROFILES[profile]]
    blocked = any(r["result"] == "FAIL" for r in results)
    if args.format == "json":
        print(json.dumps({"schema": 1, "report": report, "stage": stage, "slice": args.slice,
                          "profile": profile, "blocked": blocked, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print(f"레포트: {report}")
        print(f"프로파일: {profile} (stage {stage})")
        for r in results:
            print(f"[{r['result']}] {r['hook']}")
            for it in r["findings"]:
                print(f"    - {it['severity']} {it['field']}: {it['message']}")
                if it["action"]:
                    print(f"      → {it['action']}")
        print("결과: " + ("차단(FAIL)" if blocked else "통과"))
    return 1 if blocked else 0


def cmd_template(args):
    meta = {
        "schema": 1,
        "stage": args.stage,
        "slice": args.slice or "",
        "iteration": 1,
        "agent": args.agent or "",
        "result": "done",
        "started_at": now_kst(),
        "finished_at": now_kst(),
        "repo": {"dir": target_dir() or "", "branch": "", "head": "", "base": "", "dirty": False,
                 "changed_files": []},
        "gates": [
            {"kind": "build", "command": "", "exit_code": 0, "executed_at": now_kst()},
            {"kind": "test", "command": "", "exit_code": 0, "executed_at": now_kst(),
             "axis": "unit", "test_count": 0, "failures": 0, "skipped": 0},
        ],
        "open_items": [],
        "rr_ids": [],
        "common_candidates": [],
        "not_executed": [],
        "risk_surface": [],
        "cost": {"duration_min": 0, "tool_calls": 0, "tokens_k": 0},
    }
    print(META_START)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(META_END)
    return 0


def cmd_secrets(args):
    findings = []
    for target in args.paths:
        p = target if os.path.isabs(target) else os.path.normpath(os.path.join(ROOT, target))
        files = []
        if os.path.isdir(p):
            for ext in ("*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.log", "*.html"):
                files.extend(glob.glob(os.path.join(p, "**", ext), recursive=True))
        else:
            files.append(p)
        for fp in files:
            try:
                with open(fp, encoding="utf-8", errors="replace") as fh:
                    findings.extend(scan_secrets_text(fh.read(), os.path.relpath(fp, ROOT)))
            except OSError as ex:
                print(f"[gate] 읽기 실패 {fp}: {ex}", file=sys.stderr)
    if args.format == "json":
        print(json.dumps({"findings": findings}, ensure_ascii=False, indent=2))
    else:
        for it in findings:
            print(f"- {it['field']}: {it['message']}")
        print(f"총 {len(findings)}건")
    return 1 if findings else 0


# ---------------------------------------------------------------- open item

def next_oi_id(items):
    nums = [int(m.group(1)) for i in items
            for m in [re.match(r"OI-(\d{4})$", str(i.get("id", "")))] if m]
    return f"OI-{(max(nums) + 1 if nums else 1):04d}"


def cmd_oi(args):
    os.makedirs(WS, exist_ok=True)
    data = load_open_items()
    items = data["items"]
    if args.oi_cmd == "import":
        return cmd_oi_import(args)
    if args.oi_cmd == "new":
        if args.kind not in OI_KINDS:
            sys.exit(f"[gate] kind 는 {'|'.join(OI_KINDS)}")
        if args.severity not in SEVERITIES:
            sys.exit(f"[gate] severity 는 {'|'.join(SEVERITIES)}")
        if args.axis and args.axis not in AXES:
            sys.exit(f"[gate] axis 는 {'|'.join(AXES)}")
        oid = next_oi_id(items)
        rec = {"id": oid, "found_at": now_kst(), "stage": args.stage, "slice": args.slice or "",
               "kind": args.kind, "severity": args.severity, "summary": args.summary,
               "evidence": args.evidence, "target_stage": args.target, "axis": args.axis or "",
               "owner": args.owner or "", "rr_id": "", "status": "open",
               "approved_by": "", "expiry": "", "note": ""}
        items.append(rec)
        dump_yaml(OI_FILE, data)
        print(oid)
        print(OI_FILE)
        return 0
    if args.oi_cmd == "list":
        rows = [i for i in items
                if (not args.status or i.get("status") == args.status)
                and (not args.slice or i.get("slice") == args.slice)
                and (args.target is None or str(i.get("target_stage")) == str(args.target))]
        if not rows:
            print("해당 항목 없음")
            return 0
        print(f"{'ID':<8} {'sev':<7} {'kind':<12} {'→단계':<6} {'상태':<10} slice / 요약")
        for i in rows:
            print(f"{i.get('id',''):<8} {i.get('severity',''):<7} {i.get('kind',''):<12} "
                  f"{str(i.get('target_stage','')):<6} {i.get('status',''):<10} "
                  f"{i.get('slice','')} / {str(i.get('summary',''))[:60]}")
        print(f"총 {len(rows)}건")
        return 0
    if args.oi_cmd == "set":
        if args.status not in OI_STATUSES:
            sys.exit(f"[gate] status 는 {'|'.join(OI_STATUSES)}")
        for i in items:
            if i.get("id") == args.id:
                i["status"] = args.status
                if args.rr:
                    i["rr_id"] = args.rr
                if args.note:
                    i["note"] = args.note
                if args.approved_by:
                    i["approved_by"] = args.approved_by
                if args.expiry:
                    i["expiry"] = args.expiry
                i["updated_at"] = now_kst()
                if args.status == "converted" and not i.get("rr_id"):
                    sys.exit("[gate] converted 는 --rr RR-xxxx 가 필요하다")
                if args.status == "accepted" and not (i.get("approved_by") and i.get("expiry")):
                    sys.exit("[gate] accepted 는 --approved-by 와 --expiry(YYYY-MM-DD) 가 필요하다")
                dump_yaml(OI_FILE, data)
                print(f"{args.id} → {args.status}")
                return 0
        sys.exit(f"[gate] {args.id} 를 찾지 못했다")
    return 2


def cmd_plan(args):
    """/run 의 진행 계획을 계산한다 — 선행조건·웨이브·축 요구·멈춤 조건.

    /run 이 이 계산을 매번 산문으로 재구현하면 어긋난다. 계획은 도구가 한 곳에서 만든다.
    """
    cfg = config()
    if not os.path.exists(STATE):
        sys.exit(f"[gate] state.yaml 이 없다: {STATE}")
    st = load_yaml(STATE)
    sl_data, spath = load_slices()
    if not sl_data:
        sys.exit(f"[gate] slices.yaml 을 읽지 못했다: {spath}")
    slices = {s["id"]: s for s in (sl_data.get("slices") or []) if isinstance(s, dict)}
    maxp = int(((cfg.get("pipeline") or {}).get("max_parallel") or 1))
    amap = trait_axis_map()

    # 웨이브 편성 (depends_on 위상 정렬)
    waves, done, remaining, cyc = [], set(), dict(slices), []
    while remaining:
        ready = sorted([i for i, s in remaining.items()
                        if all(d in done for d in (s.get("depends_on") or []))],
                       key=lambda i: slices[i].get("priority", 99))
        if not ready:
            cyc = sorted(remaining)
            break
        waves.append(ready)
        done |= set(ready)
        for i in ready:
            remaining.pop(i)

    # 열린 확인 필요 항목 / RR
    items = [i for i in load_open_items()["items"] if isinstance(i, dict) and i.get("status") == "open"]
    blocking = [i for i in items if i.get("severity") in BLOCKING_SEV]
    unreserved = [i for i in blocking if i.get("target_stage") in (None, "")]
    rr_open = int((st.get("refactor_requests") or {}).get("open") or 0)

    # 멈춤 조건 (run.md 의 표를 그대로 검사)
    stops = []
    if not sl_data.get("approved"):
        stops.append("slices.yaml approved=false — 1단계 승인은 사람 몫 (pipeline-core §10)")
    if unreserved:
        stops.append(f"blocker/high 확인 필요 항목 {len(unreserved)}건이 닫을 단계 예약 없이 열려 있다")
    if cyc:
        stops.append(f"depends_on 순환: {', '.join(cyc)}")

    # 실행 가능한 단계 계산 (pipeline-core §4)
    stages = st.get("stages") or {}
    sstate = st.get("slices") or {}
    steps = []
    if rr_open and (blocking or rr_open >= 5):
        steps.append(("/refactor", f"열린 RR {rr_open}건 — 다음 단계 전에 먼저 반영"))
    if stages.get("stage2_scaffold") != "done":
        steps.append(("/stage2 scaffold", "골격 1회 — 환경 점검 후 빌드·테스트 게이트"))
    todo2 = [i for i in slices if (sstate.get(i) or {}).get("stage2_backend") != "done"]
    if todo2:
        steps.append(("/stage2 all", f"웨이브 {len(waves)}단 × 동시 {maxp}개, 대상 {len(todo2)} slice"))
    if any((sstate.get(i) or {}).get("stage2_backend") == "done" for i in slices) or todo2:
        steps.append(("/stage3", "공통화 — 공통 후보 흡수"))
    todo4 = [i for i in slices if (sstate.get(i) or {}).get("stage4_frontend") != "done"]
    if todo4:
        steps.append(("/stage4 all", f"프론트 골격 + 웨이브, 대상 {len(todo4)} slice"))
    todo5 = [i for i in slices if (sstate.get(i) or {}).get("stage5_integration") != "done"]
    if todo5 and args.to >= 5:
        steps.append(("/stage5 all", f"통합 테스트, 대상 {len(todo5)} slice"))
    if args.to >= 6 and stages.get("stage6_security") != "done":
        steps.append(("/stage6", "보안 점검"))
    if args.to >= 7 and stages.get("stage7_qa") != "done":
        steps.append(("/stage7", "QA 자동화"))
    if args.to >= 8 and stages.get("stage8_deliverables") != "done":
        steps.append(("/stage8", "산출물"))
    planned, deferred_steps = steps[:args.max], steps[args.max:]

    # 축 요구 집계
    axis_slices = {}
    for i, s in slices.items():
        for t in (s.get("traits") or []):
            for a in amap.get(t, []):
                axis_slices.setdefault(a, []).append(i)
    for a in axis_slices:
        axis_slices[a] = sorted(set(axis_slices[a]))

    batches = sum(-(-len(w) // maxp) for w in waves)
    plan = {
        "project": (cfg.get("project") or {}).get("name"),
        "to": args.to, "max": args.max, "max_parallel": maxp,
        "slices": len(slices), "waves": waves, "batches": batches,
        "serial_waves": [w[0] for w in waves if len(w) == 1],
        "open_items": {"open": len(items), "blocking": len(blocking), "unreserved": len(unreserved)},
        "rr_open": rr_open,
        "axis_requirements": {a: {"slices": len(v), "closed_by": f"stage{AXIS_STAGE.get(a, 5)}"}
                              for a, v in sorted(axis_slices.items())},
        "steps": [{"command": c, "note": n} for c, n in planned],
        "deferred": [{"command": c, "note": n} for c, n in deferred_steps],
        "stops": stops,
        "runnable": not stops,
    }
    if args.format == "json":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    print(f"/run --to {args.to} --max {args.max} --dry   (project={plan['project']}, max_parallel={maxp})")
    print(f"\n[선행 확인]")
    print(f"  slices.yaml approved : {sl_data.get('approved')}")
    print(f"  열린 확인 필요 항목  : {len(items)}건 (blocker/high {len(blocking)}, 예약 없음 {len(unreserved)})")
    print(f"  열린 RR              : {rr_open}건")
    print(f"  stage2 골격          : {stages.get('stage2_scaffold')}")
    print(f"\n[웨이브] slice {len(slices)} / 동시 {maxp} → 배치 {batches}회")
    for n, w in enumerate(waves, 1):
        mark = "  <- slice 1개, 병렬 손실" if len(w) == 1 else ""
        print(f"  w{n} ({len(w)}) {', '.join(w)}{mark}")
    print(f"\n[진행 계획] 최대 {args.max}단계")
    for n, (c, note) in enumerate(planned, 1):
        print(f"  {n}. {c:<18} {note}")
    for c, note in deferred_steps:
        print(f"  -  {c:<18} {note}  (--max 초과 → 다음 /run)")
    print(f"\n[검증 축 요구]")
    for a, v in plan["axis_requirements"].items():
        print(f"  {a:<16} {v['slices']:>2} slice   닫을 단계 {v['closed_by']}")
    print(f"\n[판정] {'실행 가능' if plan['runnable'] else '멈춤'}")
    for s in stops:
        print(f"  x {s}")
    if stops:
        print(f"\n  사람이 할 일: {stops[0]}")
        print(f"  이어갈 명령 : /run --to {args.to}")
    return 0


def write_meta_back(report, meta):
    """레포트의 pa-meta 블록을 갱신한 meta 로 교체한다."""
    with open(report, encoding="utf-8") as fh:
        text = fh.read()
    s, e = text.find(META_START), text.find(META_END)
    if s < 0 or e < 0:
        return False
    body = json.dumps(meta, ensure_ascii=False, indent=2)
    new = text[:s] + META_START + "\n" + body + "\n" + text[e:]
    with open(report, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    return True


def cmd_oi_import(args):
    """레포트 pa-meta 의 open_items 를 일괄 채번하고 레포트에 id 를 써넣는다.

    규모가 커지면 항목이 수십 건이 되므로 한 건씩 oi new 를 부르는 것은 현실적이지 않다.
    """
    report = args.report if os.path.isabs(args.report) else os.path.normpath(os.path.join(ROOT, args.report))
    meta, err = extract_meta(report)
    if err:
        sys.exit(f"[gate] {err}")
    items = meta.get("open_items")
    if not isinstance(items, list):
        sys.exit("[gate] pa-meta.open_items 가 배열이 아니다")
    os.makedirs(WS, exist_ok=True)
    data = load_open_items()
    store = data["items"]
    known = {i.get("id") for i in store if isinstance(i, dict)}
    added, skipped = [], 0
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("id") and it["id"] in known:
            skipped += 1
            continue
        if it.get("kind") not in OI_KINDS or it.get("severity") not in SEVERITIES:
            sys.exit(f"[gate] kind/severity 가 유효하지 않다: {it.get('summary', '')[:40]}")
        oid = next_oi_id(store)
        rec = {"id": oid, "found_at": now_kst(), "stage": meta.get("stage"),
               "slice": it.get("slice") or meta.get("slice") or "",
               "kind": it["kind"], "severity": it["severity"],
               "summary": it.get("summary", ""), "evidence": it.get("evidence", ""),
               "target_stage": it.get("target_stage"), "axis": it.get("axis") or "",
               "owner": it.get("owner") or "", "rr_id": "", "status": "open",
               "approved_by": "", "expiry": "", "note": ""}
        store.append(rec)
        known.add(oid)
        it["id"] = oid
        added.append(rec)
    dump_yaml(OI_FILE, data)
    if args.write:
        write_meta_back(report, meta)
    print(f"채번 {len(added)}건 (기존 {skipped}건 건너뜀) → {OI_FILE}")
    for rec in added:
        print(f"  {rec['id']} {rec['severity']:<7} {rec['kind']:<12} →stage{rec['target_stage']}  {str(rec['summary'])[:56]}")
    if args.write:
        print(f"레포트 pa-meta 갱신: {report}")
    else:
        print("레포트에 id 를 써넣으려면 --write 를 붙인다")
    return 0


def cmd_trace(args):
    """요구사항 ID → 계약 → 테스트 추적 체인을 slice 별로 전수 대조."""
    data, spath = load_slices()
    if not data:
        sys.exit(f"[gate] slices.yaml 을 읽지 못했다: {spath}")
    td = target_dir()
    if not td or not os.path.isdir(td):
        sys.exit(f"[gate] target_dir 이 없다: {td}")
    rows, broken = [], 0
    for entry in (data.get("slices") or []):
        if not isinstance(entry, dict):
            continue
        if args.slice and entry.get("id") != args.slice:
            continue
        found, missing, contract_ok, contract = trace_slice(td, entry)
        broken += len(missing) + (0 if contract_ok else 1)
        rows.append((entry.get("id"), len(found), missing, contract_ok))
    if args.format == "json":
        print(json.dumps({"slices": [{"id": i, "traced": t, "missing": m, "contract": c}
                                     for i, t, m, c in rows], "broken": broken},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{'slice':<18} {'추적됨':<7} {'계약':<6} 끊긴 요구사항")
        for i, t, m, c in rows:
            print(f"{i:<18} {t:<7} {'OK' if c else '없음':<6} {', '.join(m) if m else '-'}")
        print(f"끊긴 연결 총 {broken}건")
    return 1 if broken and args.strict else 0


def build_parser():
    p = argparse.ArgumentParser(description="단계 레포트 게이트 메타 검증")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="레포트 게이트 검사")
    c.add_argument("--report")
    c.add_argument("--stage", type=int)
    c.add_argument("--slice")
    c.add_argument("--profile", choices=sorted(PROFILES))
    c.add_argument("--format", choices=["human", "json"], default="human")
    c.set_defaults(fn=cmd_check)

    t = sub.add_parser("template", help="pa-meta 블록 골격 출력")
    t.add_argument("--stage", type=int, required=True)
    t.add_argument("--slice")
    t.add_argument("--agent")
    t.set_defaults(fn=cmd_template)

    pl = sub.add_parser("plan", help="/run 의 진행 계획 계산 (선행조건·웨이브·축·멈춤 조건)")
    pl.add_argument("--to", type=int, default=5, help="여기까지 진행 (기본 5)")
    pl.add_argument("--max", type=int, default=4, help="한 번에 실행할 최대 단계 수 (기본 4)")
    pl.add_argument("--format", choices=["human", "json"], default="human")
    pl.set_defaults(fn=cmd_plan)

    tr = sub.add_parser("trace", help="요구사항 → 계약 → 테스트 추적 체인 대조")
    tr.add_argument("--slice")
    tr.add_argument("--format", choices=["human", "json"], default="human")
    tr.add_argument("--strict", action="store_true", help="끊긴 연결이 있으면 종료 코드 1")
    tr.set_defaults(fn=cmd_trace)

    s = sub.add_parser("secrets", help="자격증명·개인정보 스캔")
    s.add_argument("paths", nargs="+")
    s.add_argument("--format", choices=["human", "json"], default="human")
    s.set_defaults(fn=cmd_secrets)

    o = sub.add_parser("oi", help="확인 필요 항목(open item) 관리")
    osub = o.add_subparsers(dest="oi_cmd", required=True)
    on = osub.add_parser("new")
    on.add_argument("--stage", type=int, required=True)
    on.add_argument("--slice")
    on.add_argument("--kind", required=True, choices=OI_KINDS)
    on.add_argument("--severity", required=True, choices=SEVERITIES)
    on.add_argument("--summary", required=True)
    on.add_argument("--evidence", required=True)
    on.add_argument("--target", type=int, required=True, help="닫을 단계")
    on.add_argument("--axis", choices=AXES, help="이 항목이 기다리는 검증 축")
    on.add_argument("--owner")
    oim = osub.add_parser("import", help="레포트 pa-meta 의 open_items 를 일괄 채번")
    oim.add_argument("--report", required=True)
    oim.add_argument("--write", action="store_true", help="레포트 pa-meta 에 채번한 id 를 써넣는다")
    ol = osub.add_parser("list")
    ol.add_argument("--status", choices=OI_STATUSES)
    ol.add_argument("--slice")
    ol.add_argument("--target", type=int)
    os_ = osub.add_parser("set")
    os_.add_argument("id")
    os_.add_argument("status", choices=OI_STATUSES)
    os_.add_argument("--rr")
    os_.add_argument("--note")
    os_.add_argument("--approved-by", dest="approved_by")
    os_.add_argument("--expiry")
    o.set_defaults(fn=cmd_oi)
    return p


def main():
    args = build_parser().parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

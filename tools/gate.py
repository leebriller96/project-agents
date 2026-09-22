#!/usr/bin/env python3
# gate.py — 단계 레포트의 게이트 메타(pa-meta 블록)를 기계적으로 검증한다.
#
# 목적: "빌드·테스트 통과", "확인 필요 있음" 같은 문장을 사람이 읽고 믿는 대신
#       (1) 실행 증거(명령·종료코드·테스트 개수)가 실제로 있는지
#       (2) target_dir 의 git 실측(HEAD/브랜치/dirty/변경파일)이 레포트 기재와 같은지
#       (3) 미해결 항목(open item)이 RR 이나 승인 없이 조용히 사라지지 않는지
#       (4) 레포트에 자격증명·개인정보가 섞이지 않았는지
#       를 도구가 대조한다. (착안: ing-people/sk-secu-agent 의 slice_agent_hooks.py)
#
# 사용법:
#   python tools/gate.py check --report workspace/<p>/reports/2609221130_stage2_notice_....md
#   python tools/gate.py check --stage 2 --slice notice          # 최신 레포트 자동 탐색
#   python tools/gate.py check --stage 5 --slice notice --format json
#   python tools/gate.py template --stage 2 --slice notice        # 메타 블록 골격 출력
#   python tools/gate.py secrets <파일|디렉토리> ...              # 비밀정보 스캔만
#   python tools/gate.py oi new --stage 2 --slice notice --kind unverified --severity high \
#          --summary "..." --evidence "파일:라인" --target 5
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
        if not it.get("target_stage"):
            f.append(fail(f"{fld}.target_stage", "어느 단계가 닫을 항목인지 적는다"))
        status = (store.get(oid) or it).get("status", "open")
        rid = (store.get(oid) or it).get("rr_id") or it.get("rr_id")
        if sev in BLOCKING_SEV and meta.get("result") in ("done", "done_with_gaps"):
            if status == "open" and not rid:
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
    # 이번 단계·slice 가 닫기로 한 항목이 레포트에서 언급되지 않은 경우
    stage, sl = meta.get("stage"), meta.get("slice")
    listed = {it.get("id") for it in items if isinstance(it, dict)}
    for oid, rec in store.items():
        if rec.get("status") != "open":
            continue
        if str(rec.get("target_stage")) == str(stage) and (not sl or rec.get("slice") in (sl, None, "", "all")):
            if oid not in listed:
                f.append(warn("open_items", f"{oid} 는 이 단계가 닫기로 한 항목인데 레포트에 없다",
                              "처리했으면 resolved 로, 남았으면 메타에 싣는다"))
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
    "open-items": hook_open_items,
    "state-consistency": hook_state_consistency,
    "secret-scan": hook_secret_scan,
}
PROFILES = {
    # 2·3·4단계: 빌드·테스트 증거와 git 실측까지
    "dev": ["report-meta", "gate-proof", "repo-consistency", "open-items", "state-consistency", "secret-scan"],
    # 5·6·7단계: 검증 단계 — 결함은 RR, 미확인은 open item 으로 나갔는지
    "verify": ["report-meta", "gate-proof", "open-items", "state-consistency", "secret-scan"],
    # 0·1·8단계
    "doc": ["report-meta", "open-items", "state-consistency", "secret-scan"],
    "all": list(HOOKS),
}
STAGE_PROFILE = {0: "doc", 1: "doc", 2: "dev", 3: "dev", 4: "dev", 5: "verify", 6: "verify", 7: "verify", 8: "doc"}


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
             "test_count": 0, "failures": 0, "skipped": 0},
        ],
        "open_items": [],
        "rr_ids": [],
        "common_candidates": [],
        "not_executed": [],
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
    if args.oi_cmd == "new":
        if args.kind not in OI_KINDS:
            sys.exit(f"[gate] kind 는 {'|'.join(OI_KINDS)}")
        if args.severity not in SEVERITIES:
            sys.exit(f"[gate] severity 는 {'|'.join(SEVERITIES)}")
        oid = next_oi_id(items)
        rec = {"id": oid, "found_at": now_kst(), "stage": args.stage, "slice": args.slice or "",
               "kind": args.kind, "severity": args.severity, "summary": args.summary,
               "evidence": args.evidence, "target_stage": args.target, "owner": args.owner or "",
               "rr_id": "", "status": "open", "approved_by": "", "expiry": "", "note": ""}
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
    on.add_argument("--owner")
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

---
description: 6단계 보안 점검 — code-security-auditor 의 방법론으로 target_dir 을 점검하고 취약점을 리팩토링 요구서로 만듭니다.
argument-hint: "[all|<slice-id>] [hybrid|claude-only] (기본 all hybrid)"
---

# /stage6 — 보안 점검

인자: `$ARGUMENTS` (대상, 모드)

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§8. 선행: `stage5_integration: done` 인 slice 1개 이상. `config/tools.yaml → security_auditor.path` 존재 확인 (없으면 안내 후 종료).
2. 모드 결정: 인자 없으면 hybrid. semgrep 등 미설치면 claude-only 로 폴백하고 알린다.
3. `stages.stage6_security: in_progress` → `security-auditor` 호출. 전달: 대상, target_dir 절대경로, 모드, 외부 스킬 경로.
4. 보고를 받아 `state.yaml` 갱신 (`done`), RR 집계 갱신(`python tools/rr.py stats`). blocker/high 가 있으면 log 에 "재점검 필요".
5. 사용자에게: 모드, 심각도별 건수, **RR 표**, 중복 제외 건수, 레포트(md/html) 경로.
6. 안내: RR 이 있으면 `/refactor` 후 `/stage6` 재실행, 없으면 `/stage7`.

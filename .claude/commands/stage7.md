---
description: 7단계 QA 자동화 — qa-automation 의 방법론으로 target_dir 의 통합 테스트를 자동 생성·실행하고 결함/위험을 리팩토링 요구서로 만듭니다.
argument-hint: "[full|generate-only|run-only] (기본 full)"
---

# /stage7 — QA 자동화

인자: `$ARGUMENTS` (모드)

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§8. 선행: `stage5_integration: done` 인 slice 1개 이상. `config/tools.yaml → qa_automation.path` 존재 확인.
2. `stages.stage7_qa: in_progress` → `qa-runner` 호출. 전달: target_dir 절대경로, 모드, 프로필들, 외부 스킬 경로(`config/tools.yaml → qa_automation`), 5단계 시나리오 경로.
3. 보고를 받아 `state.yaml` 갱신 (`done`), RR 집계 갱신.
4. 사용자에게: 모드(폴백 여부), 생성/실행/통과/실패/에러 수(summary.json 기준), 확정 결함 수(+미확정 수), **RR 표**, 중복 제외 건수, Top 3 우선 조치, 커버리지 공백 요약, 레포트 경로.
5. 안내: RR 이 있으면 `/refactor` 후 `/stage5`→`/stage7` 재확인, 없으면 `/stage8`.

---
description: 0단계 준비 — workspace/<project>/00_inputs/ 의 문서·AS-IS 소스를 읽어 PROJECT_BRIEF.md 등 요약 지식을 만듭니다.
argument-hint: "(인자 없음)"
---

# /stage0 — 준비 (Ingest)

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1 시작 절차를 수행한다 (config·state 확인, 선행 조건: `workspace/<project>/00_inputs/` 에 파일 1개 이상).
2. `state.yaml → stages.stage0_ingest: in_progress` 기록.
3. `ingest-analyst` 서브에이전트를 호출한다. 전달: `config/project.yaml` 요약(mode, stack, asis 경로), 이미 brief 가 있으면 "갱신 모드" 임을 알린다.
4. 보고를 받아 `state.yaml` 갱신: `stage0_ingest: done`, `updated_at`, `log` 추가.
5. 사용자에게 보여준다: 입력 인벤토리 요약, 엔티티/화면/API/요구사항 수, **§11 근거 부족·모순 표 전체**, brief 경로.
6. 안내: "brief 를 확인·수정한 뒤 `/stage1` 을 실행하세요."

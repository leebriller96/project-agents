---
description: 8단계 산출물 — 파이프라인 결과물을 재가공해 config 에 지정된 SI 산출물(요구사항 추적표, 아키텍처·테이블·API·화면 정의서, 테스트/보안/QA 결과서 등)을 생성합니다.
argument-hint: "[all|<산출물 키>[,<키>...]] (기본 all)"
---

# /stage8 — 산출물 작성

인자: `$ARGUMENTS`

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1. 선행: `stage5_integration: done`. 6·7 미완료면 경고만 하고 진행(해당 결과서는 "미수행" 표시).
2. `config/project.yaml → deliverables` 에서 대상 목록 결정 (인자로 키를 주면 그것만).
3. `stages.stage8_deliverables: in_progress` → `deliverable-writer` 호출. 전달: target_dir 절대경로, 대상 목록, 형식, iteration.
4. 보고를 받아 `state.yaml` 갱신 (`done`).
5. 사용자에게: 생성 산출물 표(번호·이름·경로), 원천 없음 목록(어느 단계를 돌려야 하는지), 끊긴 추적 항목 수, open RR 수.
6. 안내: open RR 이 남아 있으면 `/refactor` 후 `/stage8` 재생성 권장.

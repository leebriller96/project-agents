---
description: 3단계 공통화 리팩토링 — 완료된 slice 들에서 공통 코드를 common 모듈로 추출하고 컨벤션을 정렬합니다. 동작(테스트 결과)은 보존합니다.
argument-hint: "(인자 없음)"
---

# /stage3 — 공통화 리팩토링

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§7 (선행: `stage2_backend: done` 인 slice 1개 이상).
2. `stages.stage3_common: in_progress`, log 에 회차(iteration) 기록.
3. `common-refactorer` 호출. 전달: target_dir, 프로필, `done` slice 목록, `workspace/<project>/reports/common-candidates.md` 경로.
4. 보고 후 `backend-reviewer` 를 `common` 대상으로 호출. FAIL 이면 `common-refactorer` 재호출 (최대 2회) → 잔여 시 `blocked`.
5. `state.yaml` 갱신 (`done`|`blocked`). 보류된 후보 중 향후 필요한 것은 RR(`source_stage: 3`) 로 남긴다.
6. 사용자에게: 추출 목록, 보류 목록과 사유, 기준선 대비 테스트 결과, `common-module-spec.md` 경로.
7. 안내: `/stage4 <slice>` 또는 새 slice 가 있으면 `/stage2 <slice>`.

---
description: 열린 리팩토링 요구서(RR)를 target_stage·slice 별로 묶어 해당 단계 에이전트에 반영시키고, 게이트를 다시 통과시킵니다.
argument-hint: "[RR-0001,RR-0002 | slice:<id> | stage:<n> | all] (기본 all)"
---

# /refactor — 리팩토링 요구서 반영

인자: `$ARGUMENTS`

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§6·§7·§8.
2. 대상 RR 결정: `python tools/rr.py list --status open` 결과에 인자 필터 적용 (RR id 목록 / `slice:<id>` / `stage:<n>` / all). 0건이면 안내 후 종료.
3. 대상 RR 을 사용자에게 표로 보여준다 (id·severity·slice·target_stage/layer·제목). **blocker/high 가 없고 medium/low 만 있으면 진행 여부를 한 번 확인**한다.
4. `iteration` 을 +1 하고 log 에 기록.
5. RR 을 `(target_stage, slice)` 로 묶는다. 처리 순서: target_stage 1 → 2 → 3 → 4. 단, **`blocked` 상태인 단계의 원인 RR**(예: 기준선 실패 테스트)이 있으면 그 묶음을 가장 먼저 처리하고, 끝나면 해당 단계 게이트를 재확인해 `done` 으로 되돌린다. 같은 stage 안에서 slice 가 다르면 §6 규칙대로 **병렬** 가능(target_stage 3 은 항상 단독).
   - `target_stage: 1` → 사용자에게 `/stage1 reslice` 를 권하고 이 묶음은 건너뛴다 (자동 재분류하지 않음).
   - `target_stage: 2` → `backend-developer` 를 `refactor <RR-id 목록>` 작업으로 호출 → `backend-reviewer` → FAIL 시 재호출 최대 2회.
   - `target_stage: 3` → `common-refactorer` → `backend-reviewer`(common).
   - `target_stage: 4` → `frontend-developer` 를 `refactor <RR-id 목록>` 으로 호출 → `frontend-reviewer`.
   각 호출 전 해당 RR 을 `in_progress` 로 바꾼다(`python tools/rr.py set <id> in_progress`).
6. 결과 반영: developer 가 `done` 으로 바꾼 RR 을 확인. reviewer FAIL 잔여 지적은 새 RR 로 남기고 원 RR 은 그대로 `in_progress` 유지 + 사용자 보고.
7. 영향받은 slice 의 후속 단계 상태를 되돌린다: target_stage 2 반영 → 그 slice 의 `stage5_integration: pending` (stage4 는 계약이 바뀐 경우에만 pending). target_stage 4 반영 → `stage5_integration: pending`. target_stage 3 → 전 slice `stage5_integration: pending`. `stage6_security`·`stage7_qa` 는 어떤 반영이든 `pending`.
8. `state.yaml` 갱신, RR 집계(`python tools/rr.py stats`).
9. 사용자에게: 처리된 RR 표(상태), 남은 RR, 되돌린 단계 목록, 다음 안내(`/stage5 <slice>` 등).

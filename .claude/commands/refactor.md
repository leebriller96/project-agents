---
description: 열린 리팩토링 요구서(RR)를 target_stage·slice 별로 묶어 해당 단계 에이전트에 반영시키고, 게이트를 다시 통과시킵니다.
argument-hint: "[RR-0001,RR-0002 | slice:<id> | stage:<n> | layer:<backend/mapper 등> | all] (기본 all, 필터 조합 가능)"
---

# /refactor — 리팩토링 요구서 반영

인자: `$ARGUMENTS`

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§6·§7·§8.
2. 대상 RR 결정: `python tools/rr.py list --status open` 결과에 인자 필터 적용 (RR id 목록 / `slice:<id>` / `stage:<n>` / `layer:<target_layer 접두어, 예 backend/mapper·frontend·common>` / all — 필터는 조합 가능, 예 `slice:book-loan layer:backend/mapper`). 0건이면 안내 후 종료.
   **부분 재작업 원칙**: 전수 변환이 아니라 필터에 걸린 RR 의 slice·계층만 돌린다. 그 밖의 slice 는 건드리지 않는다.
3. 대상 RR 을 사용자에게 표로 보여준다 (id·severity·slice·target_stage/layer·제목). **blocker/high 가 없고 medium/low 만 있으면 진행 여부를 한 번 확인**한다.
4. `iteration` 을 +1 하고 log 에 기록.
5. RR 을 `(target_stage, slice)` 로 묶는다. 처리 순서: target_stage 1 → 2 → 3 → 4. 예외: stage 2 RR 의 `suggested_fix` 가 공용 기반(`common/`, 골격 설정, 유틸)을 필요로 하면 **stage 3 묶음을 먼저** 돌려 기반을 만든 뒤 stage 2 를 돌린다 (common-refactorer 프롬프트에 후속 slice RR 을 함께 알려 준비하게 한다). 단, **`blocked` 상태인 단계의 원인 RR**(예: 기준선 실패 테스트)이 있으면 그 묶음을 가장 먼저 처리하고, 끝나면 해당 단계 게이트를 재확인해 `done` 으로 되돌린다. 같은 stage 안에서 slice 가 다르면 §6 규칙대로 **병렬** 가능(target_stage 3 은 항상 단독).
   - `target_stage: 1` → 사용자에게 `/stage1 reslice` 를 권하고 이 묶음은 건너뛴다 (자동 재분류하지 않음).
   - `target_stage: 2` → `backend-developer` 를 `refactor <RR-id 목록>` 작업으로 호출 → `backend-reviewer` → FAIL 시 재호출 최대 2회.
   - `target_stage: 3` → `common-refactorer` → `backend-reviewer`(common).
   - `target_stage: 4` → `frontend-developer` 를 `refactor <RR-id 목록>` 으로 호출 → `frontend-reviewer`.
   병렬 호출 프롬프트에는 **C-번호 대역(공통 후보)·F-번호 대역** 을 반드시 적는다(빠뜨려 충돌 2회).
   각 호출 전 해당 RR 을 `in_progress` 로 바꾼다(`python tools/rr.py set <id> in_progress`).
   - slice 소유 문서만 고치는 RR(예 매핑표 근거 부족 보강)은 공용 묶음이 아니라 **그 slice 묶음**에 배정한다(경계 원칙 — 문서라도).
   - 여러 slice·공용 파일에 걸친 **문서 RR**(추적표·4분류표 정합 묶음)은 항목을 소유 slice 별로 쪼개 각 developer/common-refactorer 프롬프트에 배정하고, 전부 끝난 뒤 오케스트레이터가 RR 을 닫는다(한 파일을 두 에이전트가 만지지 않게).
   - developer 에게 라이브러리 동작(정제기·파서 등)을 단정해 지시하지 말고 기대 결과("정제 후 비면 400")만 준다 — 실측이 다르면 developer 가 규약 우선으로 바로잡는다.
6. 결과 반영: developer 가 `done` 으로 바꾼 RR 을 확인. stage 3 공용 기반이 후속 stage 2 RR 을 자동 해결했다고 보고하면(evidence 경로의 동작을 테스트로 증명한 경우) 그 RR 은 developer 호출 없이 `done` 으로 인정하고 note 에 "공용 기반으로 해결" 을 남긴다. reviewer FAIL 잔여 지적은 새 RR 로 남기고 원 RR 은 그대로 `in_progress` 유지 + 사용자 보고.
6-1. target_stage 2 반영으로 `docs/api/<slice>.yaml` 이 재생성됐으면 **같은 회차에** `frontend-developer` 에게 `gen:api` 재생성(+ 타입 변화에 따른 FE 수정) 작업을 자동으로 추가한다. 계약 설명(`@Operation`·`@Tag`)도 §12 정책 변경 시 stale 여부를 grep 한다.
7. 영향받은 slice 의 후속 단계 상태를 되돌린다: target_stage 2 반영 → 그 slice 의 `stage5_integration: pending` (stage4 는 계약이 바뀐 경우에만 pending). target_stage 4 반영 → `stage5_integration: pending`. target_stage 3 → 전 slice `stage5_integration: pending`. `stage6_security`·`stage7_qa` 는 어떤 반영이든 `pending`.
8. `state.yaml` 갱신, RR 집계(`python tools/rr.py stats`).
9. 사용자에게: 처리된 RR 표(상태), 남은 RR, 되돌린 단계 목록, 다음 안내(`/stage5 <slice>` 등).

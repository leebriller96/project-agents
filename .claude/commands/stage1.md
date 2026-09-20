---
description: 1단계 업무 분류 — PROJECT_BRIEF 를 바탕으로 업무 slice 를 나누어 slices.yaml 을 만들고 사람 승인을 요청합니다.
argument-hint: "[reslice] (재분류 시)"
---

# /stage1 — 업무 분류 (Slicing)

인자: `$ARGUMENTS` (`reslice` 면 기존 slices.yaml 을 재분류)

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1 시작 절차 (선행: stage0 `done`).
2. 기존 `workspace/slices/slices.yaml` 이 있고 인자가 `reslice` 가 아니면: 현재 slice 목록과 approved 상태를 보여주고 "재분류하려면 `/stage1 reslice`" 안내 후 종료.
3. `state.yaml → stages.stage1_slicing: in_progress`.
4. `slice-planner` 서브에이전트 호출. 전달: mode, 재분류 여부, 이미 `done` 인 slice id 목록(있으면).
5. 보고를 받아 `state.yaml` 갱신: `stage1_slicing: done`, `slices` 에 새 slice 들을 `pending` 으로 추가(기존 항목 유지), log.
6. 사용자에게 보여준다: slice 표(id·이름·priority·depends_on·엔티티/화면/API 수), 의존 그래프(텍스트), unassigned 목록, 애매했던 판단.
7. **승인 요청**: "`workspace/slices/slices.yaml` 을 검토하고 `approved: true` 로 바꿔 주세요. 승인 전에는 `/stage2` 가 진행되지 않습니다."

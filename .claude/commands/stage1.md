---
description: 1단계 업무 분류 — PROJECT_BRIEF 를 바탕으로 업무 slice 를 나누어 slices.yaml 을 만들고 사람 승인을 요청합니다.
argument-hint: "[reslice] (재분류 시)"
---

# /stage1 — 업무 분류 (Slicing)

인자: `$ARGUMENTS` (`reslice` 면 기존 slices.yaml 을 재분류)

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1 시작 절차 (선행: stage0 `done`).
2. 기존 `workspace/<project>/slices/slices.yaml` 이 있고 인자가 `reslice` 가 아니면: 현재 slice 목록과 approved 상태를 보여주고 "재분류하려면 `/stage1 reslice`" 안내 후 종료.
3. `state.yaml → stages.stage1_slicing: in_progress`.
4. `slice-planner` 서브에이전트 호출. 전달: mode, 재분류 여부, 이미 `done` 인 slice id 목록(있으면).
5. 보고를 받아 `state.yaml` 갱신: `stage1_slicing: done`, `slices` 에 새 slice 들을 `pending` 으로 추가(기존 항목 유지), log.
6. 사용자에게 보여준다: slice 표(id·이름·priority·depends_on·엔티티/화면/API 수), 의존 그래프(텍스트), unassigned 목록, 애매했던 판단.
7. **승인 요청**: "`workspace/<project>/slices/slices.yaml` 을 검토하고 `approved: true` 로 바꿔 주세요. 승인 전에는 `/stage2` 가 진행되지 않습니다."
8. brief §11 중 **골격·마이그레이션·인증에 영향을 주는 항목**(인증 토큰 전달 방식, 공통코드 seed, 초기 계정, 삭제 방식, FK 정의 등)과 **보안 사양 항목**(초기 비밀번호 정책·변경 기능, 토큰 폐기·세션 무효화, TLS/쿠키 Secure, 레이트 리밋)을 골라 "2단계 전 결정 필요" 로 함께 제시하고, 기본값 제안을 붙인다.
   사용자가 결정(또는 "기본값")하면 `PROJECT_BRIEF.md` **§12 결정 사항** 표에 기록한 뒤 `/stage2` 로 넘어간다.

## 완료 처리 (공통 · pipeline-core §9·§11·§12)

1. 서브에이전트 보고의 `pa-agent-result` 블록에서 게이트·변경 파일·확인 필요 항목을 그대로 가져온다.
   `changed_files` 에 소유 밖 파일이 있으면 되돌리고 공통 후보로 돌린다.
2. 확인 필요 항목은 `python tools/gate.py oi new --stage 1 --slice <id> --kind <kind> --severity <sev> --summary "…" --evidence "…" --target <닫을 단계>` 로 채번한다.
   `blocker`·`high` 는 RR 전환(`oi set <id> converted --rr RR-xxxx`) 또는 사람 승인(`accepted`) 없이 남기지 않는다.
3. 레포트 끝에 `pa-meta` 블록을 붙인다 (`python tools/gate.py template --stage 1 --slice <id> --agent orchestrator` 로 골격 생성 후 실제 값으로 채움).
4. `python tools/gate.py check --stage 1 [--slice <id>]` 를 실행한다. **FAIL 이면 그 단계를 `done` 으로 기록하지 않는다.**
   검사 결과(통과 / FAIL 항목)를 사용자 보고에 한 줄로 포함한다.

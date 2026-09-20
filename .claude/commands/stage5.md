---
description: 5단계 통합 테스트 — slice 별 통합 테스트 시나리오(없으면 작성)를 근거로 FE↔BE↔DB 연동을 실행·검증하고 결함을 리팩토링 요구서로 만듭니다.
argument-hint: "<slice-id>[,<slice-id>...] | all"
---

# /stage5 — 통합 테스트

인자: `$ARGUMENTS`

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§4·§5·§8. 선행: 대상 slice 의 `stage2_backend`·`stage4_frontend` 모두 `done`.
2. 대상 slice 결정 (§5). 미충족 slice 는 제외·안내.
3. slice 마다 `stage5_integration: in_progress` → `integration-tester` 호출 (환경 충돌을 피하기 위해 **순차** 실행; 포트·DB 를 공유하므로 병렬 금지). 전달: slice id, target_dir 절대경로, 프로필들.
4. 보고를 받아 `state.yaml` 갱신 (`done`|`blocked`), `refactor_requests` 집계를 `python tools/rr.py stats` 로 다시 계산해 기록.
5. 모든 대상이 끝나면 `stages.stage5_integration` 을 갱신 (전 slice done 이면 done).
6. 사용자에게: slice 별 통과/실패/미실행 수, 실행 환경, 정적 검증 불일치, **생성된 RR 표(id·severity·target_stage/layer·제목)**, 레포트 경로.
7. 안내: RR 이 있으면 `/refactor`, 없으면 `/stage6`.

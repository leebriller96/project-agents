---
description: 4단계 Frontend 개발 — (최초 1회 골격 생성 후) slice 별로 디자인 근거와 OpenAPI 계약만으로 화면·컴포넌트·단위테스트를 개발합니다. 의존 없는 slice 는 병렬 실행.
argument-hint: "<slice-id>[,<slice-id>...] | all | scaffold"
---

# /stage4 — Frontend 개발

인자: `$ARGUMENTS`

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§4·§5·§6·§7.
   선행: 대상 slice 의 `stage2_backend: done` 이고 `<target_dir>/docs/api/<slice>.yaml` 존재.
2. **골격**: `stages.stage4_scaffold` 가 없거나 `done` 이 아니거나 인자가 `scaffold` 면
   `frontend-developer` 를 `scaffold` 작업으로 호출 → 빌드·린트·샘플 테스트 통과 시 `stage4_scaffold: done` (state.yaml 에 키 추가). 인자가 `scaffold` 였으면 종료.
3. **대상 slice 결정** (§5): 선행 조건 미충족 slice 는 제외하고 사유 안내. `depends_on` slice 의 `stage4_frontend` 가 `done` 이어야 한다.
4. **웨이브 구성** (§6): stage2 와 동일.
5. 웨이브마다:
   a. `stage4_frontend: in_progress`.
   b. `frontend-developer` 를 slice 마다 호출 (병렬 가능). 전달: `slice <id>`, target_dir 절대경로, 프로필, 계약 경로, 화면 근거 파일 경로(brief §6 에서 추출).
   c. `frontend-reviewer` 호출 (병렬 가능). FAIL 이면 developer 재호출 최대 2회 → 잔여 시 `blocked`.
   d. `state.yaml` 갱신. developer 가 만든 RR(계약 부족)은 그대로 두고 사용자에게 알린다.
5-1. 웨이브 종료 후 reviewer 지적 중 "규칙 부재·규칙 신설로 인한 것"(예: URL 파라미터 정규화, 검증 규칙 테스트 누락)은 같은 웨이브의 **다른 slice 에도 해당하는지** 오케스트레이터가 grep 으로 확인하고, 해당하면 slice 별 RR 을 함께 만든다. 프로필 규칙을 갱신했다면 다음 웨이브 developer 프롬프트에 명시한다.
6. 사용자에게: slice 별 결과 표(상태·화면 수·테스트 수·reviewer 결과), 계약 부족 RR 목록, blocked 사유, 레포트 경로.
7. 안내: 계약 부족 RR 이 있으면 `/refactor` 로 BE 보강 후 재실행, 없으면 `/stage5 <slice>`.

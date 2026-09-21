---
name: stage5-integration-test
description: 5단계 통합 테스트 — slice별 통합 테스트 시나리오(없으면 작성)를 근거로 FE↔BE↔DB 연동을 실행·검증하고, 결함을 리팩토링 요구서(RR)로 도출하는 방법론. /stage5 수행 시 사용.
---

# 5단계 통합 테스트 방법론

목표: FE 와 BE 가 **계약대로 실제로 연결되는지**를 시나리오 기반으로 검증하고, 결함을 RR 로 남긴다. 이 단계는 코드를 고치지 않는다.

## 1. 시나리오 문서

`<target_dir>/docs/test/<slice>-scenario.md` 가 없으면 `templates/test-scenario.md` 형식으로 **먼저 작성**한다. 근거:
- `slices.yaml` 의 requirements → 요구사항마다 정상 1 + 예외/경계 1 이상
- `docs/screens/<slice>.md` 의 버튼→API 매핑 → 화면 조작 경로
- `docs/api/<slice>.yaml` 의 에러 응답 → 에러 노출 시나리오
- depends_on slice 와의 연동(예: 인증 후 주문) → 교차 slice 시나리오 (`ITS-<slice>-x<3자리>`)

이미 있으면 새 요구사항·API 가 반영됐는지 확인해 보강한다. 사람이 쓴 시나리오는 지우지 않는다.

## 2. 실행 환경

우선순위: (1) testcontainers/도커로 MySQL 기동 + BE 기동 + FE 빌드 → E2E, (2) 도커 없음 → BE 는 H2 MySQL 모드로 기동, FE 는 실제 BE 를 바라보게, (3) 기동 불가 → 계약 기반 정적 검증만 (아래 §4) 하고 미실행 사유 기록.

- BE: 테스트 프로파일로 기동, 시나리오 사전조건은 SQL 픽스처(`docs/test/fixtures/<slice>.sql`)로 세팅.
- FE: Playwright(설치돼 있거나 설치 가능하면) 로 화면 조작. 불가하면 API 레벨(REST 호출)로 시나리오를 실행하고 FE 는 정적 검증.
- 테스트 코드는 `<target_dir>/tests/integration/<slice>/` 에 저장 (재실행 가능해야 함).
- **첫 slice 가 환경을 만든다**: `tests/integration/env-up.sh [--with-fe] [--skip-build]` / `env-down.sh` / `env.sh`(포트·계정) + `docs/test/README.md`. 이후 slice 는 README 대로 재사용. Playwright 는 `tests/integration/package.json` 에 격리 설치(프론트 `package.json` 은 공용 파일).
- 포트는 개발 PC 의 8080/5173 이 점유될 수 있으므로 18080/5174 같은 대체값을 기본으로. Windows Git Bash 에서 기동 스크립트를 파이프(`| tee`)에 물리면 백그라운드 java 가 핸들을 물어 끝나지 않는다 — 파일 리다이렉트 + health 폴링.
- 5단계는 open RR 중 "환경에서 확인 후 처리" 로 미룬 것(예: MySQL 한정 잠금 문제)을 **실측**해 severity 를 조정하고 evidence 를 보강한다.

## 3. 검증 항목 (시나리오별)
- HTTP 상태·응답 스키마가 계약과 일치
- DB 상태 변화가 기대 결과와 일치
- FE 가 응답을 올바르게 표시(성공 메시지/에러 메시지/목록 갱신)
- 인증·권한: 미인증·권한 없음 시나리오

## 4. 정적 검증 (항상 수행)
- FE 의 API 호출 목록(`features/<slice>/api/`) ↔ 계약 ↔ BE 컨트롤러 경로·메서드·필드명 3자 대조. 불일치는 즉시 RR.
- 계약 드리프트: 기동한 BE 의 `/v3/api-docs.yaml/<slice>` 를 정규화(키 순서 무시)해 `docs/api/<slice>.yaml` 과 diff, FE `gen:api` 재생성 diff 도 확인. 둘 중 하나라도 다르면 RR.
- slice 간 규약 일관성(생성 상태코드, 에러 포맷, 페이징) 도 대조한다 — 단일 slice 안에서는 일치해도 slice 간에 다를 수 있다.
- FE 폼 검증 규칙 ↔ BE DTO 검증 규칙 대조 (FE 가 더 느슨하면 medium, BE 가 더 느슨하면 high).

- 시각 의존 결함(월 경계·자정·UTC/KST 창)은 "재현 창(시각 범위)" 을 시나리오·README 에 명시한다. 자동 실행이 창 밖이면 통과해도 결함이 없는 게 아니다.
- 과거 이력처럼 API 로 만들 수 없는 fixture 는 타 slice 소유 테이블에 SQL INSERT 를 허용하되 fixture 파일·시나리오에 사유를 적는다.

- **재실행(rN)**: 시나리오 문서에 이전 결과를 병기하고, 기대값이 바뀐 건수·신규 건수를 레포트에 명시한다. 이전 RR 의 resolution_note 를 근거로 기대값을 갱신하며, 갱신 없이 통과한 항목은 회귀 확인으로 기록.
- 시각 의존 시나리오가 재현 창 밖이면 간접 증거(커넥션 세션 TZ, seed 컬럼 값, 세션 TZ 지정 SQL 결과)로 대체하고 "창 안 재확인 필요" 를 남긴다.

## 5. RR 도출
- 실패 시나리오·불일치마다 RR 1개. `source_stage: 5`, `evidence` 에 시나리오 ID + 실패 로그/파일:라인.
- `target_stage`/`target_layer` 판단: 응답·DB 문제 → 2/backend/*, 표시·검증 문제 → 4/frontend/*, 공통 포맷 문제 → 3/common, 계약 자체 문제 → 2/backend/api.
- 환경 문제(기동 실패 등)는 RR 이 아니라 레포트 "실행 불가" 항목.

## 6. 산출물 및 상태
- 시나리오 문서(결과 열 채움), `tests/integration/<slice>/`, RR 파일들
- 레포트 `workspace/reports/<ts>_stage5_<slice>_integration.md`: 실행 환경, 시나리오 통과/실패/미실행 수, RR 목록, 정적 검증 결과
- `state.yaml → slices.<slice>.stage5_integration: done` (실패 시나리오가 있어도 RR 로 남겼으면 done; 환경 부재로 아무것도 못 돌렸으면 blocked)
- 사용자에게 RR 요약을 보여주고 `/refactor` 안내

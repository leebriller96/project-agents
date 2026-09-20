---
name: stage7-qa
description: 7단계 QA 자동화 — 외부 repo qa-automation 의 test-automation 스킬 방법론으로 target_dir 의 통합 테스트를 자동 생성·실행하고 결함/위험을 리팩토링 요구서(RR)로 변환하는 방법론. /stage7 수행 시 사용.
---

# 7단계 QA 자동화 방법론

목표: `qa-automation` 의 방법론으로 **도구가 스스로 도출한** 통합 테스트를 생성·실행하고 결함·잠재 위험을 RR 로 넘긴다. 5단계(우리가 쓴 시나리오)와 보완 관계다. 코드는 고치지 않는다.

## 1. 외부 스킬 로드
1. `config/tools.yaml → qa_automation.path` 를 읽는다. 없으면 안내 후 중단.
2. `<path>/<skill>` (SKILL.md), `<path>/CLAUDE.md`, `<path>/templates/report_template.md` 를 읽고 **그 방법론(서비스 인벤토리 → 환경 준비 → 생성 → 실행 → 결함/위험 분석, 모드, 등급 기준)** 을 따른다.
3. 모드: 인자 `full|generate-only|run-only`. 기본 full. 실행 환경이 없으면 원 스킬 규칙대로 generate-only 폴백 + 사유 기록.

## 2. 대상과 차이점
- 대상은 `<target_dir>` 전체 (원 도구의 `input/` 대신). 복사하지 않는다.
- 생성한 테스트는 `<target_dir>/tests/qa/<서비스>/` 에 둔다 (5단계의 `tests/integration/` 과 분리).
- 5단계 시나리오·결과(`docs/test/*-scenario.md`)와 open RR 을 먼저 읽어 **이미 알려진 결함은 중복 RR 을 만들지 않는다** (레포트에 "기존 RR-xxxx 와 동일" 표시).
- 이 프로젝트에 특히 볼 것: slice 간 호출 경계, 트랜잭션 경계(부분 실패), 페이징·정렬 경계값, 동시성(재고 차감 등), 마이그레이션 재실행.

## 3. 레포트 → RR 변환
1. 원 도구 형식 레포트를 `workspace/reports/<ts>_stage7_all_qa.md` (+html) 로 쓴다.
2. 결함(실패 테스트)은 RR 필수. 잠재 위험은 등급 Major 이상만 RR, 그 이하는 레포트에만.
   등급 매핑: Blocker→blocker, Critical/Major→high, Minor→medium, Trivial→low.
3. `source_stage: 7`, `evidence` 에 실패 테스트명 + 파일:라인. `target_stage/layer` 는 원인 위치로.

## 4. 산출물 및 상태
- 레포트(md+html), `tests/qa/`, RR 파일들
- `state.yaml → stages.stage7_qa: done`
- 사용자에게 결함/위험 건수·RR 목록·커버리지 공백을 보여주고 `/refactor` 안내

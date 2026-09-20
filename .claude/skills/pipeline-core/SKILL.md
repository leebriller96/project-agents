---
name: pipeline-core
description: project-agents 파이프라인의 공통 규칙 — 설정·상태·slice·리팩토링 요구서 파일 형식, 게이트, 병렬 실행, 레포트 규칙. 모든 /stageN·/refactor·/status 명령이 가장 먼저 읽는다.
---

# 파이프라인 공통 규칙 (pipeline-core)

모든 단계 명령과 에이전트는 이 문서를 먼저 읽고 따른다.

## 1. 시작 절차 (모든 명령 공통)

1. `config/project.yaml` 을 읽는다. 없으면 "config/project.yaml.example 을 복사해 config/project.yaml 을 만들어 주세요" 안내 후 **중단**.
2. `config/tools.yaml` 을 읽는다 (6·7단계만 필수).
3. `workspace/state.yaml` 을 읽는다. 없으면 `templates/state.yaml` 을 복사해 project·mode 를 채우고 slices 는 비워 둔다.
4. 선행 단계 조건을 확인한다 (아래 §4). 미충족이면 무엇을 먼저 실행해야 하는지 안내 후 중단.
5. 시작 시 `state.yaml` 의 해당 항목을 `in_progress` 로 바꾸고 `log` 에 한 줄 남긴다.
6. 끝나면 결과(`done` | `blocked`)와 `updated_at` 을 갱신하고, 레포트를 `workspace/reports/` 에 남긴다.

## 2. 경로

- `target_dir`: `config/project.yaml → project.target_dir`. 이 repo 기준 상대경로면 절대경로로 바꿔 쓴다.
  없으면 만든다. **생성되는 서비스 소스는 반드시 target_dir 안에만 쓴다.** 이 repo 안에는 소스를 두지 않는다.
- target_dir 안의 표준 배치:
  ```
  <target_dir>/
  ├── backend/            # 2·3단계
  ├── frontend/           # 4단계
  ├── db/migration/       # Flyway 등 마이그레이션 (2단계)
  ├── docs/api/<slice>.yaml   # OpenAPI 계약 (2단계 산출, 4단계 소비)
  ├── docs/test/<slice>-scenario.md   # 통합 테스트 시나리오 (5단계)
  └── docs/deliverables/  # 8단계 산출물
  ```
- 파이프라인 메타(brief, slices, 요구서, 레포트, 상태)는 항상 이 repo 의 `workspace/` 에 둔다.

## 3. 파일 형식

| 파일 | 형식 | 템플릿 |
|---|---|---|
| `workspace/state.yaml` | 파이프라인 상태 | `templates/state.yaml` |
| `workspace/knowledge/PROJECT_BRIEF.md` | 프로젝트 요약 지식 | `templates/PROJECT_BRIEF.md` |
| `workspace/slices/slices.yaml` | 업무 분류 | `templates/slices.yaml` |
| `workspace/refactor-requests/RR-NNNN.yaml` | 리팩토링 요구서 | `templates/refactor-request.yaml` |
| `<target_dir>/docs/test/<slice>-scenario.md` | 통합 테스트 시나리오 | `templates/test-scenario.md` |

템플릿의 키를 빼거나 이름을 바꾸지 않는다. 값이 없으면 빈 값으로 둔다.

## 4. 선행 조건 (게이트)

| 명령 | 선행 조건 |
|---|---|
| /stage0 | `workspace/00_inputs/` 에 파일이 1개 이상 |
| /stage1 | stage0 `done` |
| /stage2 `<slice>` | stage1 `done` **and** `slices.yaml → approved: true`; 골격(stage2_scaffold) 미완료면 먼저 골격 수행; `depends_on` slice 의 stage2 가 `done` |
| /stage3 | stage2 가 `done` 인 slice 가 1개 이상 |
| /stage4 `<slice>` | 해당 slice 의 stage2 `done` (OpenAPI 계약 존재); `depends_on` slice 의 stage4 `done` |
| /stage5 | 해당 slice 의 stage2·stage4 `done` |
| /stage6, /stage7 | stage5 가 `done` 인 slice 가 1개 이상 (전체 완료 권장) |
| /stage8 | stage5 `done`; 6·7은 권장 |
| /refactor | open 요구서 1개 이상 |

**완료 조건 (2·3·4단계)**: `pipeline.gate` 설정에 따라 빌드·단위테스트가 통과해야 `done`. 실패하면 `blocked` + `blocked_reason` 기록.
통과시키려고 테스트를 지우거나 `@Disabled`/`skip` 하지 않는다.

## 5. slice 인자 해석

- `/stage2 order` → 해당 slice 하나.
- `/stage2 order,member` → 나열된 slice.
- `/stage2 all` 또는 인자 없음 → `slices.yaml` 의 모든 slice 중 아직 `done` 이 아닌 것.
- 존재하지 않는 id 면 slices.yaml 의 id 목록을 보여주고 중단.

## 6. 병렬 실행

`pipeline.parallel: true` 일 때 2·4단계에서 여러 slice 를 처리하면:

1. `depends_on` 으로 위상 정렬하여 **웨이브(wave)** 를 만든다. 같은 웨이브의 slice 는 서로 의존이 없다.
2. 웨이브 안에서 `max_parallel` 개까지 developer 서브에이전트를 **동시에** 실행한다 (Agent 도구를 한 메시지에서 여러 개 호출).
3. 웨이브가 끝나면 각 slice 에 reviewer 를 돌린 뒤 다음 웨이브로 간다.
4. **충돌 방지 규칙** — 병렬 중인 developer 는:
   - 자기 slice 패키지/디렉토리(`backend/.../<slice>/`, `frontend/src/features/<slice>/`, `db/migration/V<n>__<slice>_*.sql`)와
     자기 계약 파일(`docs/api/<slice>.yaml`)만 쓴다.
   - 공용 파일(빌드 설정, common 패키지, 라우터 루트, 공용 타입)은 **수정하지 않는다.**
     필요한 공용 변경은 `workspace/reports/common-candidates.md` 에 "무엇이·왜 필요한지" 를 적고 slice 안에 임시 구현한다. 3단계가 이를 흡수한다.
   - 마이그레이션 버전 번호는 충돌을 피하기 위해 `V<yyMMddHHmm>__<slice>_<설명>.sql` 형식을 쓴다.
5. `state.yaml` 갱신은 오케스트레이터(명령 본문)가 웨이브 종료 시점에 한 번에 한다. 서브에이전트는 state.yaml 을 직접 쓰지 않고 결과를 보고한다.

`parallel: false` 면 priority → depends_on 순으로 순차 실행한다.

## 7. developer → reviewer

2·3·4단계는 developer 서브에이전트가 만든 뒤 reviewer 서브에이전트가 검토한다.
- reviewer 는 코드를 고치지 않고 지적 목록(파일:라인, 심각도, 이유, 수정안)을 돌려준다.
- 오케스트레이터는 `blocker`·`high` 지적을 developer 에게 다시 넘겨 같은 단계 안에서 고친다 (최대 2회).
- 2회 후에도 남으면 `blocked` 로 기록하고 사람에게 보고한다.

## 8. 리팩토링 요구서 (RR)

- 5·6·7단계와 reviewer 가 다음 단계로 넘길 결함은 **반드시** RR 파일로 남긴다.
- ID 채번: `python tools/rr.py new` (기존 최대 번호 +1). 목록: `python tools/rr.py list [--status open]`.
- `evidence` 는 필수. 근거 없는 요구서는 만들지 않는다.
- 한 요구서에는 한 가지 결함만 담는다. `target_stage`·`target_layer`·`slice` 를 반드시 채운다.
- 상태 전이: `open → in_progress → done | rejected`. `rejected` 는 사람만 지정한다.

## 9. 레포트

- 위치: `workspace/reports/`, 파일명 `yymmddhhmm_stage<N>_<slice|all>_<설명>.md` (KST).
- HTML 변환: `python tools/build_report.py <md파일>`.
- 레포트에는 항상 포함: 대상·입력 근거·수행 내용·게이트 결과(빌드/테스트 명령과 출력 요약)·미완료/근거 부족 항목·다음 단계 안내.
- 실행하지 못한 것은 "실행하지 못함 + 이유" 로 쓴다. 통과한 것처럼 쓰지 않는다.

## 10. 사람 확인 지점

| 시점 | 내용 |
|---|---|
| stage0 종료 | PROJECT_BRIEF.md 의 "근거 부족·모순" 표를 사용자에게 보여주고 확인 요청 (차단 아님) |
| stage1 종료 | `slices.yaml` 을 보여주고 **`approved: true` 로 바꿔 달라고 요청**. 승인 전 stage2 진행 불가 |
| stage2 골격 종료 | 골격 구조·컨벤션 요약을 보여주고 확인 요청 (차단 아님) |
| reviewer 2회 후 잔여 지적 | 사람에게 보고, `blocked` |
| RR `rejected` | 사람만 가능 |

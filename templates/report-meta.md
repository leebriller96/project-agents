# 레포트 게이트 메타 블록 (pa-meta)

모든 단계 레포트(`workspace/<project>/reports/*.md`)는 **맨 끝**에 아래 블록을 붙인다.
사람이 읽는 본문과 별개로, `python tools/gate.py check` 가 이 블록을 읽어
실행 증거·git 실측·미해결 항목을 기계적으로 대조한다. 블록이 없으면 게이트는 FAIL 이다.

골격 출력: `python tools/gate.py template --stage 2 --slice notice --agent backend-developer`
검사: `python tools/gate.py check --stage 2 --slice notice` (또는 `--report <경로>`)

```markdown
<!-- pa-meta:start
{
  "schema": 1,
  "stage": 2,
  "slice": "notice",
  "iteration": 5,
  "agent": "backend-developer",
  "result": "done",
  "started_at": "2026-09-23 00:00",
  "finished_at": "2026-09-23 00:40",
  "repo": {
    "dir": "C:/secu-sample",
    "branch": "master",
    "head": "592e89253699fd8a0f1b4bacdb0f23b8f0f8662f",
    "base": "3f1ac2d…",
    "dirty": false,
    "changed_files": ["server/domain-notice/src/main/java/.../NoticeService.java"]
  },
  "gates": [
    {"kind": "build", "command": "mvn -q -DskipTests package", "exit_code": 0, "executed_at": "2026-09-23 00:20"},
    {"kind": "test", "command": "mvn test -Dtest='com.example.secu.notice.**'", "exit_code": 0,
     "executed_at": "2026-09-23 00:35", "axis": "module", "test_count": 226, "failures": 0, "skipped": 0},
    {"kind": "test", "command": "mvn verify -Pmysql", "exit_code": 0,
     "executed_at": "2026-09-23 00:38", "axis": "real-db", "test_count": 41, "failures": 0, "skipped": 0}
  ],
  "open_items": [
    {"id": "OI-0003", "kind": "unverified", "severity": "high", "axis": "real-server",
     "summary": "삭제 첨부 연쇄가 notice 계약 문구와 어긋나는지 미확인",
     "evidence": "reports/2609221900_stage2_notice-admin.md#8", "target_stage": 5, "rr_id": ""}
  ],
  "rr_ids": ["RR-0041"],
  "common_candidates": ["C-21"],
  "not_executed": ["-Pmysql 동시성 테스트: Docker 미가동"],
  "risk_surface": [
    {"what": "조회수 갱신을 REQUIRES_NEW 로 분리 — 커넥션을 2개 점유한다",
     "axis": "concurrency", "covered_by": "NoticeViewConcurrencyTest#poolOfOne"}
  ],
  "cost": {"duration_min": 40, "tool_calls": 96, "tokens_k": 210}
}
pa-meta:end -->
```

## 필드

| 필드 | 규칙 |
|---|---|
| `schema` | 항상 `1` |
| `stage` | 단계 번호(정수). `/refactor` 레포트는 반영 대상 단계 |
| `slice` | slice id. 전체 대상이면 `"all"` |
| `iteration` | `state.yaml → iteration` |
| `agent` | 이 레포트를 만든 주체(`backend-developer`, `orchestrator` 등) |
| `result` | `done` \| `done_with_gaps` \| `blocked` \| `failed`. **미확인 항목이 남았는데 게이트는 통과했으면 `done_with_gaps`** |
| `repo` | `target_dir` 의 git 실측값. 도구가 `rev-parse HEAD`·`branch --show-current`·`status --porcelain` 로 대조한다 |
| `repo.head` | 커밋 SHA. 이 단계가 코드를 바꾸지 않았으면 `"NOT_CHANGED"` (이때 `changed_files` 는 비어야 한다) |
| `repo.base` | 변경 파일 대조 기준(웨이브 시작 커밋). 있으면 `git diff --name-only base...HEAD` 와 `changed_files` 를 대조한다 |
| `gates[]` | 실제로 실행한 명령. `kind`: `build\|test\|lint\|typecheck\|smoke\|scan\|other` |
| `gates[].exit_code` | 실제 종료 코드. 0 이 아닌 게이트가 있으면 `result` 는 `done` 일 수 없다 |
| `gates[].axis` | 이 실행이 **어느 축을 닫았는가**: `unit`·`module`·`real-db`·`real-server`·`browser`·`concurrency`·`security-static`. `test`·`smoke`·`scan` 에 필수 |
| `gates[].test_count` | `test`·`smoke` 필수. **0 이면 FAIL** — 필터가 아무것도 매칭하지 않은 채 EXIT 0 이 나오는 함정을 막는다. 집계는 `python tools/surefire_sum.py <target_dir>` 등 근거 있는 방법으로 |
| `open_items[]` | 확인 필요 항목. `id` 는 `gate.py oi new` 로 채번한 뒤 여기 싣는다 (`pipeline-core §11`) |
| `rr_ids[]` | 이 단계에서 만든 RR id. 파일 존재를 도구가 확인한다 |
| `common_candidates[]` | `common-candidates.md` 에 추가한 C-번호 |
| `not_executed[]` | 실행하지 못한 검증과 이유. 여기 적은 것 중 다음 단계가 닫아야 하는 것은 `open_items` 로도 올린다 |
| `risk_surface[]` | **이 변경이 무엇을 깨뜨릴 수 있는가** + 어느 축의 문제인가 + 무엇으로 덮었는가(`covered_by`, 없으면 `"미검증"`). `/refactor` 레포트에 필수 — 리팩토링이 새 결함을 낳은 실측(REQUIRES_NEW) 때문 |
| `cost` | `{duration_min, tool_calls, tokens_k}`. 회차 간 비용 비교 근거. 모르면 아는 것만 적는다 |

## 검사 규칙 요약 (`tools/gate.py`)

| 훅 | 무엇을 막는가 |
|---|---|
| `report-meta` | 메타 누락·필드 누락·stage/slice 불일치 |
| `gate-proof` | 실패한 게이트를 통과로 기록, 테스트 0건 통과, 2·3·4단계에서 build/test 증거 누락 |
| `repo-consistency` | 기재한 HEAD·브랜치·dirty·변경 파일이 실제 git 과 다름 |
| `coverage-axis` | slice 의 `traits` 가 요구하는 검증 축이 닫히지도, 예약(open item)되지도 않은 채 넘어감 |
| `traceability` | 요구사항 ID 가 테스트까지 이어지지 않음(8단계 추적표의 끊긴 연결), 계약 파일 부재 |
| `open-items` | high 이상 미확인 항목이 RR 연결·사람 승인 없이 완료 처리됨, 이 단계가 닫기로 한 항목의 누락 |
| `cost-record` | 비용 기록 누락(경고), `risk_surface` 형식 오류 |
| `state-consistency` | 레포트 result 와 `state.yaml` 상태의 모순 |
| `secret-scan` | 레포트에 비밀번호·토큰·키·개인정보 원문 노출 |

이 규칙은 2026-09-23 이후 생성한 레포트에 적용한다. 그 이전 레포트는 대상이 아니다.

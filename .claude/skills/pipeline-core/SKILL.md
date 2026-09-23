---
name: pipeline-core
description: project-agents 파이프라인의 공통 규칙 — 설정·상태·slice·리팩토링 요구서 파일 형식, 게이트, 병렬 실행, 레포트 규칙. 모든 /stageN·/refactor·/status 명령이 가장 먼저 읽는다.
---

# 파이프라인 공통 규칙 (pipeline-core)

모든 단계 명령과 에이전트는 이 문서를 먼저 읽고 따른다.

## 1. 시작 절차 (모든 명령 공통)

1. `config/project.yaml` 을 읽는다. 없으면 "config/project.yaml.example 을 복사해 config/project.yaml 을 만들어 주세요" 안내 후 **중단**.
2. `config/tools.yaml` 을 읽는다 (6·7단계만 필수).
3. `workspace/<project>/state.yaml` 을 읽는다. 없으면 `templates/state.yaml` 을 복사해 project·mode 를 채우고 slices 는 비워 둔다.
4. 선행 단계 조건을 확인한다 (아래 §4). 미충족이면 무엇을 먼저 실행해야 하는지 안내 후 중단.
5. 시작 시 `state.yaml` 의 해당 항목을 `in_progress` 로 바꾸고 `log` 에 한 줄 남긴다.
6. 끝나면 결과(`done` | `blocked`)와 `updated_at` 을 갱신하고, 레포트를 `workspace/<project>/reports/` 에 남긴다.

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
- 파이프라인 메타(brief, slices, 요구서, 레포트, 상태)는 항상 이 repo 의 **`workspace/<project>/`** 에 둔다 (`<project>` = `config/project.yaml → project.name`). 프로젝트가 바뀌면 config 만 바꾸면 되고 이전 프로젝트의 workspace 는 그대로 남는다. `tools/rr.py`·`status.py` 는 config 에서 프로젝트명을 읽어 경로를 정한다. 에이전트에게는 항상 **절대경로**로 전달한다.

## 3. 파일 형식

| 파일 | 형식 | 템플릿 |
|---|---|---|
| `workspace/<project>/state.yaml` | 파이프라인 상태 | `templates/state.yaml` |
| `workspace/<project>/knowledge/PROJECT_BRIEF.md` | 프로젝트 요약 지식 | `templates/PROJECT_BRIEF.md` |
| `workspace/<project>/slices/slices.yaml` | 업무 분류 | `templates/slices.yaml` |
| `workspace/<project>/refactor-requests/RR-NNNN.yaml` | 리팩토링 요구서 | `templates/refactor-request.yaml` |
| `workspace/<project>/open-items.yaml` | 확인 필요 항목(§11) | `templates/open-items.yaml` |
| `workspace/<project>/reports/*.md` 끝의 `pa-meta` 블록 | 레포트 게이트 메타(§9) | `templates/report-meta.md` |
| `<target_dir>/docs/test/<slice>-scenario.md` | 통합 테스트 시나리오 | `templates/test-scenario.md` |

템플릿의 키를 빼거나 이름을 바꾸지 않는다. 값이 없으면 빈 값으로 둔다.

## 4. 선행 조건 (게이트)

| 명령 | 선행 조건 |
|---|---|
| /stage0 | `workspace/<project>/00_inputs/` 에 파일이 1개 이상 |
| /stage1 | stage0 `done` |
| /stage2 `<slice>` | stage1 `done` **and** `slices.yaml → approved: true`; 골격(stage2_scaffold) 미완료면 먼저 골격 수행; `depends_on` slice 의 stage2 가 `done` |
| /stage3 | stage2 가 `done` 인 slice 가 1개 이상 |
| /stage4 `<slice>` | 해당 slice 의 stage2 `done` (OpenAPI 계약 존재); `depends_on` slice 의 stage4 `done` |
| /stage5 | 해당 slice 의 stage2·stage4 `done` |
| /stage6, /stage7 | stage5 가 `done` 인 slice 가 1개 이상 (전체 완료 권장) |
| /stage8 | stage5 `done`; 6·7은 권장 |
| /refactor | open 요구서 1개 이상 |

**완료 조건 (2·3·4단계)**: `pipeline.gate` 설정에 따라 빌드·단위테스트가 통과해야 `done`. 실패하면 `blocked` + `blocked_reason` 기록.
게이트 통과 여부는 **말이 아니라 증거로 남긴다** — 레포트 `pa-meta` 의 `gates[]` 에 명령·종료 코드·테스트 개수를 적고
`python tools/gate.py check --stage <N> [--slice <id>]` 가 통과해야 단계를 `done` 으로 기록한다 (§9).
테스트 개수 0 은 통과가 아니다 — 필터가 아무것도 매칭하지 않아도 종료 코드는 0 이 나온다(실측 2회).
통과시키려고 테스트를 지우거나 `@Disabled`/`skip` 하지 않는다.
예외: 환경 조건부 실행(예: Docker 필요한 동시성 테스트 `@EnabledIfSystemProperty`)은 조건·사유가 어노테이션에 있고, 해당 환경(`-Pmysql` 등)에서 실제 실행·통과한 기록이 레포트에 있으면 허용한다.
이런 테스트가 어떤 RR 의 유일한 회귀 근거라면 **그 환경에서의 1회 실행이 게이트에 포함**된다 — 오케스트레이터가 웨이브 종료 시 `-Pmysql` 등으로 실행하고 state log 에 남긴다. 5단계 시나리오에도 같은 조건을 적는다.

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
     필요한 공용 변경은 `workspace/<project>/reports/common-candidates.md` 에 "무엇이·왜 필요한지" 를 적고 slice 안에 임시 구현한다. 3단계가 이를 흡수한다.
     병렬 에이전트는 **스크래치패드를 공유**하므로 임시 스크립트·파일명에 slice 접두어를 붙인다(`<slice>_patch.py`) — 다른 developer 의 패치가 덮어써진 실측.
     에이전트가 API 서버 오류(5xx)로 중단되면 새 에이전트를 띄우지 말고 같은 에이전트를 **재개**(`SendMessage`)한다 — "작업 트리 상태(`git status`·파일 목록)를 먼저 확인하고 중단 지점부터" 를 지시. 컨텍스트가 보존돼 산출물 손실 없이 이어진다(실측 2회).
     오케스트레이터는 developer 프롬프트에 포트·라이브러리 동작·정제 결과 같은 **사실을 단정해 적지 않는다** — "실측할 파일 경로" 와 기대 결과만 준다(틀린 단정 3회 실측: 포트·jsoup·swagger-core).
     병렬 웨이브에서는 오케스트레이터가 slice 마다 C-번호 대역(예 A: C-10~19, B: C-20~29)을 프롬프트로 배정해 번호 충돌을 막는다.
     빌드 의존성 추가도 공용 변경이다 — slice 는 대안 구현(예: xlsx 대신 CSV) 또는 인터페이스만 만들고 후보로 남긴다.
   - **마이그레이션 버전에 slice 고유 번호를 넣는다**: `V<대역><slice번호2자리>_<yyMMddHHmmss>__<slice>_<설명>.sql`
     (대역 규약이 없으면 `V<slice번호2자리>_<yyMMddHHmmss>__…`). slice 번호는 오케스트레이터가 웨이브 프롬프트로 배정한다.
     **분 단위 타임스탬프만으로는 충돌을 막지 못한다** — 동시 3개 웨이브에서 두 slice 가 같은 분에 파일을 만들어
     `Found more than one migration with version …` 로 **무관한 모듈까지 컨텍스트 생성이 실패했다**(실측, 3개 slice 게이트가 동시에 멈춤).
     `db/migration` 은 모든 모듈이 공유하므로 한 slice 의 버전 충돌이 웨이브 전체를 막는다.
   - 웨이브 착수 전과 종료 후 오케스트레이터가 **버전 중복을 검사한다**:
     `ls <target_dir>/db/migration/*/ | grep -oE '^V[0-9_]+' | sort | uniq -d` 가 비어 있어야 한다.
   - 파일명을 고친 뒤에도 **빌드 산출물의 옛 복사본이 충돌을 남긴다**(`copy-resources` 는 삭제를 전파하지 않는다).
     이름을 바꿨는데 같은 오류가 계속되면 `target/*/test-classes/db/migration` 의 잔존 파일을 지운다(골격이 정리 스크립트를 제공하는 것이 낫다).
5. `state.yaml` 갱신은 오케스트레이터(명령 본문)가 웨이브 종료 시점에 한 번에 한다. 서브에이전트는 state.yaml 을 직접 쓰지 않고 결과를 보고한다.
6. 병렬 developer 는 앱 기동이 필요할 때(계약 생성 등) **서로 다른 포트**를 쓴다 (오케스트레이터가 slice 마다 지정, 예: 18081/18082). 같은 `build/` 디렉토리를 공유하므로 전체 테스트(`gradlew test`)는 **웨이브 종료 후 오케스트레이터(또는 reviewer)가 1회만** 실행한다. developer 는 자기 slice 테스트(`--tests "<pkg>.<slice>.*"`)까지만 게이트로 삼는다.
   웨이브가 끝나면 **오케스트레이터가 전체 테스트를 1회 직접 실행**해 실패가 있으면 reviewer 를 부르기 전에 developer 재작업으로 돌린다 (reviewer 의 시간을 게이트 실패 확인에 쓰지 않는다).
   프론트도 같다: `node_modules`·`dist` 공유 → `build` 는 마지막 1회(실패 시 30초 후 재시도), vitest 는 파일 단위(`npm run test --run src/features/<slice>`)로 먼저, 전체는 마지막 1회.
7. **target repo 커밋**: 골격 완료 시 오케스트레이터가 `git init` + 첫 커밋, 이후 웨이브가 `done` 될 때마다 `stage2(<slice>): ...` 형식으로 커밋한다. reviewer 가 `git status/diff` 로 공용 파일 변경을 판별할 수 있어야 한다. 서브에이전트는 커밋하지 않는다.

`parallel: false` 면 priority → depends_on 순으로 순차 실행한다.

## 7. developer → reviewer

2·3·4단계는 developer 서브에이전트가 만든 뒤 reviewer 서브에이전트가 검토한다.
- reviewer 는 코드를 고치지 않고 지적 목록을 돌려준다. 지적 한 건의 고정 형식:

  | 필드 | 규칙 |
  |---|---|
  | `id` | `<축약어>-<번호>` (예: `BR-03`) |
  | `severity` | `blocker` \| `high` \| `medium` \| `low` |
  | `confidence` | `confirmed`(실행·대조로 증명) \| `high` \| `medium` \| `low`(정황) — **근거 없이 severity 만 높이지 않는다** |
  | `evidence` | `파일:라인` 또는 실행한 명령·출력. 없으면 지적으로 만들지 않는다 |
  | `impact` | 사용자·데이터·운영에 실제로 무엇이 잘못되는가 |
  | `fix` | 구체적 수정안 |
  | `test_hint` | 이 지적을 닫으려면 **5단계가 무엇을 실측해야 하는가**. `medium`·`low` 로 넘기는 지적에는 필수 |

  `confidence: low` 인데 `severity: blocker` 면 오케스트레이터는 재작업 대신 확인 필요 항목(§11)으로 돌린다.
  `test_hint` 는 5단계 시나리오·7단계 인벤토리의 입력이다 — 여기서 끊기면 "확인 필요" 가 증발한다(실측: notice-admin §8 미인계).
- 오케스트레이터는 `blocker`·`high` 지적을 developer 에게 다시 넘겨 같은 단계 안에서 고친다 (최대 2회).
- 2회 후에도 남으면 `blocked` 로 기록하고 사람에게 보고한다.
- `medium`·`low` 지적 처리: 코드 수정이 필요한 것은 RR(`source_stage` = 현재 단계)로 남기고, 공용 파일·컨벤션 문서 변경은 `common-candidates.md` 로 넘긴다. 같은 단계에서 바로 고치지 않는다 (병렬 slice 와의 충돌·회귀 방지).
- 뒤따르는 slice 에 적용할 교훈(예: `@Pattern` 앵커)은 오케스트레이터가 다음 developer 호출 프롬프트에 명시한다.
- 우선순위: **brief §12 결정 > 골격 `CONVENTIONS.md` > 프로필 > 오케스트레이터 프롬프트의 구현 세부**. 프롬프트가 규약과 충돌하면 developer 는 규약을 따르고 보고에 "지시와 다른 결정" 으로 명시한다.

## 8. 리팩토링 요구서 (RR)

- 5·6·7단계와 reviewer 가 다음 단계로 넘길 결함은 **반드시** RR 파일로 남긴다.
- ID 채번: `python tools/rr.py new --title … --slice … --layer … --source N --target N --severity … --evidence "파일:라인" [--evidence …] --description "…" --fix "…"` (기존 최대 번호 +1, 본문까지 한 번에 — 생성 후 YAML 을 정규식·문자열 치환으로 고치지 말 것: 백틱·콜론이 YAML 을 깨뜨림. 고쳐야 하면 yaml 로드→수정→dump). 목록: `python tools/rr.py list [--status open]`.
- `evidence` 는 필수. 근거 없는 요구서는 만들지 않는다.
- 한 요구서에는 한 가지 결함만 담는다. `target_stage`·`target_layer`·`slice` 를 반드시 채운다.
- 상태 전이: `open → in_progress → done | rejected`. `rejected` 는 사람만 지정한다.

## 9. 레포트

- 위치: `workspace/<project>/reports/`, 파일명 `yymmddhhmm_stage<N>_<slice|all>_<설명>.md` (KST).
- HTML 변환: `python tools/build_report.py <md파일>`.
- 타임스탬프는 항상 `python tools/kst_now.py` (파일명용 `yyMMddHHmm`; `--full` 은 본문용 `YYYY-MM-DD HH:MM`). bash `TZ=... date` 는 Windows Git Bash 에서 틀린다.
- 레포트에는 항상 포함: 대상·입력 근거·수행 내용·게이트 결과(빌드/테스트 명령과 출력 요약)·미완료/근거 부족 항목·다음 단계 안내.
- 실행하지 못한 것은 "실행하지 못함 + 이유" 로 쓴다. 통과한 것처럼 쓰지 않는다.
- **레포트 끝에 `pa-meta` 블록을 붙인다** (형식·필드: `templates/report-meta.md`).
  골격: `python tools/gate.py template --stage <N> --slice <id> --agent <이름>`.
  본문의 서술과 별개로 이 블록이 기계 대조 대상이다 — `gates[]`(명령·종료 코드·테스트 개수),
  `repo`(git HEAD·브랜치·dirty·변경 파일), `open_items[]`, `rr_ids[]`, `not_executed[]`.
- **레포트를 쓴 직후 `python tools/gate.py check --stage <N> [--slice <id>]` 를 실행하고 결과를 본문에 남긴다.**
  FAIL 이면 그 단계를 `done` 으로 기록하지 않는다. 검사 항목:
  실패한 게이트를 통과로 적기 · 테스트 0건 통과 · git 실측과 다른 기재 ·
  high 이상 확인 필요 항목의 무단 종료 · state.yaml 과의 모순 · 레포트의 자격증명/개인정보 노출.
  (도구가 잡아낸 것은 사람이 다시 읽어 확인하지 않아도 되고, 도구가 못 보는 것만 사람이 본다.)
- 레포트·산출물에 비밀번호·토큰·키·주민번호·연락처 **원문을 적지 않는다.** 값은 `***` 로 가리고 경로·변수명만 남긴다.
  별도 스캔: `python tools/gate.py secrets workspace/<project>/reports`.

## 10. 사람 확인 지점

| 시점 | 내용 |
|---|---|
| stage0 종료 | PROJECT_BRIEF.md 의 "근거 부족·모순" 표를 사용자에게 보여주고 확인 요청 (차단 아님) |
| stage1 종료 | `slices.yaml` 을 보여주고 **`approved: true` 로 바꿔 달라고 요청**. 승인 전 stage2 진행 불가 |
| stage2 골격 종료 | 골격 구조·컨벤션 요약을 보여주고 확인 요청 (차단 아님) |
| reviewer 2회 후 잔여 지적 | 사람에게 보고, `blocked` |
| RR `rejected` | 사람만 가능 |
| 확인 필요 항목 `accepted` (§11) | 사람만 가능 — 승인자·만료일 기록 |

## 11. 확인 필요 항목 (open item)

RR 은 "고쳐야 할 결함"이고, open item 은 **"아직 확인·결정되지 않은 것"** 이다.
레포트 산문에만 적힌 "확인 필요" 는 다음 단계로 넘어가면서 사라진다(실측: notice-admin §8, F-306).
그래서 다음 다섯 가지는 반드시 `workspace/<project>/open-items.yaml` 에 채번해 남긴다.

| kind | 예 |
|---|---|
| `evidence_gap` | brief §11 근거 부족이 그 단계에서 결정을 막은 것 |
| `decision` | 사람 결정이 필요한 것 (brief §12 후보) |
| `unverified` | 구현은 했으나 그 단계의 테스트로는 도달·증명 불가 (MockMvc 로는 못 보는 서블릿 경로 등) |
| `risk` | 지금은 괜찮지만 조건이 바뀌면 깨지는 것 |
| `deferred` | 뒤 단계로 의도적으로 미룬 것 |

- 채번: `python tools/gate.py oi new --stage <N> --slice <id> --kind <kind> --severity <sev> --summary "…" --evidence "파일:라인" --target <닫을 단계> [--axis <축>] [--owner <에이전트>]`
- **항목이 여러 건이면** 서브에이전트 보고를 레포트 `pa-meta.open_items` 에 그대로 옮긴 뒤
  `python tools/gate.py oi import --report <레포트> --write` 로 **일괄 채번**한다 (레포트의 id 까지 도구가 채운다).
  0단계에서 51건이 나온 실측 — 한 건씩 부르는 것은 규모에서 불가능하다.
- 레포트 `pa-meta.open_items[]` 에 같은 id 로 싣는다. 도구가 파일과 대조한다.
- **RR 전환을 요구하는 것은 `unverified`·`risk` 이고 단계가 2 이상일 때뿐이다.** RR 은 "이미 있는 코드의 결함" 을 고치라는 요구이므로
  0·1단계에는 만들 대상이 없다. `blocker`·`high` 라도 `decision`·`evidence_gap`·`deferred` 는
  **`target_stage` 로 예약**되어 있으면 열린 채 넘어갈 수 있다(도구가 WARN 으로 추적한다).
  2단계 이후의 `unverified`·`risk` 가 `blocker`·`high` 면 RR 전환(`oi set <id> converted --rr RR-xxxx`) 또는
  사람 승인(`accepted`) 없이 그 단계를 `done` 으로 끝낼 수 없다.
  게이트는 통과했지만 미확인이 남았으면 레포트 `result` 는 `done_with_gaps` 다.
- `target_stage` 가 자기 단계인 항목은 착수 시 `oi list --target <N>` 으로 확인하고, 처리하면 `resolved`,
  못 했으면 레포트에 다시 싣는다 (도구가 누락을 WARN 으로 알린다).
- `accepted` 는 사람만 지정하고 `approved_by`·`expiry`(YYYY-MM-DD)가 필요하다. 만료된 승인은 FAIL 이다.

## 12. 에이전트 결과 계약 (Agent Result)

서브에이전트의 보고가 산문뿐이면 오케스트레이터가 집계·인계에서 항목을 흘린다(실측: RR-0023 admin 몫 증발).
**모든 서브에이전트는 보고의 마지막을 아래 블록으로 끝낸다.** 오케스트레이터는 이 블록만으로
state 갱신·다음 호출 프롬프트·레포트 `pa-meta` 를 만들 수 있어야 한다.

````markdown
```json pa-agent-result
{
  "schema": 1,
  "agent": "backend-developer",
  "stage": 2,
  "slice": "notice",
  "attempt": 1,
  "result": "done",
  "gates": [
    {"kind": "build", "command": "…", "exit_code": 0, "executed_at": "2026-09-23 00:20"},
    {"kind": "test", "command": "…", "exit_code": 0, "executed_at": "2026-09-23 00:35",
     "test_count": 226, "failures": 0, "skipped": 0}
  ],
  "changed_files": ["server/domain-notice/src/main/java/…"],
  "open_items": [{"kind": "unverified", "severity": "high", "axis": "real-server",
                  "summary": "…", "evidence": "…", "target_stage": 5}],
  "rr_ids": [],
  "common_candidates": ["C-21"],
  "not_executed": ["…"],
  "risk_surface": [{"what": "이 변경이 깨뜨릴 수 있는 것", "axis": "concurrency",
                    "covered_by": "테스트명 또는 '미검증'"}],
  "cost": {"duration_min": 40, "tool_calls": 96},
  "deviations": ["오케스트레이터 지시와 다르게 결정한 것 + 근거"],
  "next_action": "reviewer 검토 요청"
}
```
````

- `result`: `done` | `done_with_gaps` | `blocked` | `failed`.
- `open_items` 는 id 없이 보고해도 된다 — 채번은 오케스트레이터가 `gate.py oi new` 로 한다.
- `changed_files` 는 실제로 고친 파일 전부. 오케스트레이터가 `git status`·`diff` 로 대조하고,
  **자기 소유 밖의 파일(공용 설정·common·다른 slice)** 이 있으면 되돌린 뒤 공통 후보로 돌린다(§6-4).
- 실행하지 못한 검증은 `not_executed` 에 이유와 함께 적는다. 비워 두고 통과로 보고하지 않는다.
- `risk_surface` 는 **이 변경이 무엇을 깨뜨릴 수 있는가**를 스스로 선언하는 칸이다(§14). `covered_by` 가 "미검증" 이면 확인 필요 항목으로 올린다.
  RR 을 반영하는 작업에서는 비워 둘 수 없다 — 리팩토링이 더 큰 결함을 낳은 실측(RR-0041: 락 축소 목적의 `REQUIRES_NEW` 가 커넥션 2중 점유를 만듦) 때문이다.
- reviewer 는 같은 블록에 `findings[]`(§7 형식)를 함께 싣는다.

## 13. 모델 배정

`.claude/agents/*.md` 는 `model: inherit` 이다. 오케스트레이터가 Agent 호출 시 아래 기준으로 상위/중급을 고른다.
전부 최상위는 낭비이고, 전부 중급은 공용·경계에서 사고가 난다.

| 상위 모델을 쓰는 곳 | 이유 |
|---|---|
| 골격(scaffold)·3단계 공통화·계약 설계 | 실수가 모든 slice 로 전파된다 |
| 분기·상태 조합이 많은 slice (권한·결재·파일·외부연동) | 경우의 수를 놓치면 5·6단계에서 크게 돌아온다 |
| 5·6·7단계 검증과 reviewer | 결함의 원인 계층을 정확히 지목해야 재작업이 라우팅된다 |
| AS-IS 추적(sql-migrator·ingest) | 근거 해석이 틀리면 뒤 단계가 전부 틀린다 |

계약이 정해진 CRUD slice, 확정 스키마의 기계적 작성, 산출물 재가공(8단계)은 중급으로 충분하다.
**상향 규칙**: 같은 문제로 developer 가 2회 이상 막히면(reviewer 재작업 2회 소진 직전) 그 에이전트만 상위 모델로 재실행하고,
사유를 레포트에 남긴다.

## 14. 검증 축 (axis)

단계를 늘려도 **같은 축**에서만 검증하면 새 결함은 나오지 않는다.
secu-sample 최종 채점에서 파이프라인이 스스로 만든 결함 7건은 전부 앞 단계가 **보지 못하는 축**에서만 잡혔다.

| 축 | 무엇을 볼 수 있나 | 실측으로 여기서만 잡힌 것 |
|---|---|---|
| `unit` | 로직 분기 | — |
| `module` | 스프링 컨텍스트·H2 | — |
| `real-db` | 실제 DB 방언·타입·인덱스 | H2 URL override, `Timestamp` 캐스트 |
| `real-server` | 서블릿·필터·파서·프록시 (`RANDOM_PORT`) | multipart NUL 500, 413 순서, XFF 위조 허용 |
| `browser` | 실제 렌더·타이머·번들 | Tiptap 로드 즉시 크래시 (jsdom 122 tests 통과) |
| `concurrency` | 경합·풀·교착 | `REQUIRES_NEW` 커넥션 2중 점유 |
| `security-static` | 소스 전역 sink 추적 | 정제기 우회, 로그 인젝션 |

운영 규칙:

1. 1단계가 slice 마다 `traits` 를 정하고, 그것이 **요구 축**을 결정한다(`stage1-slicing §4-1`). 모든 slice 는 기본으로 `unit` 을 요구하고, 그 위의 축은 traits 가 요구할 때만 본다.
   축에는 포함 관계가 있다 — `real-server`·`real-db` 는 `module`·`unit` 을, `module` 은 `unit` 을 이미 지난다. 같은 실행을 여러 축으로 중복해 적지 않는다.
2. 게이트를 실행할 때마다 `pa-meta.gates[].axis` 에 어느 축을 닫았는지 적는다.
3. 이번 단계가 닫을 수 없는 축은 **확인 필요 항목으로 예약**한다: `gate.py oi new … --axis <축> --target <닫을 단계>`.
4. `gate.py` 의 `coverage-axis` 훅이 대조한다 — 요구 축 중 닫히지도 예약되지도 않은 것이 있으면
   2·4단계에서는 WARN, 그 축을 닫아야 할 단계(5·6·7)에서는 FAIL.
5. **판별력 없는 테스트는 축을 닫지 않는다.** 그 축에서 결함을 재현하지 못하는 테스트(수정 전에도 통과하는 테스트)는
   축 충족으로 세지 말고, 재현→수정→통과를 레포트에 남긴다(실측: jsdom 프로브로 재현 불가를 먼저 증명한 뒤 Chromium 스모크 채택).
   증명 방법은 두 가지다 — **수정 전 재현**(테스트를 먼저 넣고 실패를 확인) 또는 **mutation**(구현에 결함을 주입해 테스트가 잡는지 확인).
6. **판별력 증거는 `pa-meta.discrimination[]` 에 기록한다**(형식: `templates/report-meta.md`).
   `target`·`method`·**`scope`**·`failures`·`evidence`(실패 실행의 surefire XML 사본)·`restored`.
   - **실행 범위를 반드시 적는다.** 한 클래스만 돌린 결과를 모듈 전체로 일반화한 오보가 실측됐다
     (mutation 을 한 클래스에서 돌려 "기존 테스트 전부 통과" 로 보고했으나, 같은 모듈의 통합 테스트는 그 변이를 이미 잡고 있었다).
     **기준은 모듈 전체 1회 실행**이다.
   - 실패 실행을 `gates[]` 에 싣지 않는다 — `gate-proof` 가 "실패한 게이트를 통과로 기재" 로 읽는다. 그래서 별도 칸이다.
   - 최종 실행이 surefire XML 을 덮어쓰므로 **실패 실행의 XML 사본**을 `reports/discrimination/<slice>_<회차>/` 에 남긴다.
     사본이 없으면 판별력 증거가 산문뿐이어서 검증할 수 없다(실측).
   - **수정 전에는 판별 수단(메서드·오류 코드)이 없어 단언을 쓸 수조차 없는 경우**가 있다(`method: absent_pre_fix`).
     이때는 `failures: 0` 이 정상이지만 **면제가 아니라 의무가 바뀐다** — 해악이 실재함을 증명하는 통과 단언(`harm_evidence`)과
     수정 후 결함을 주입해 새 테스트가 잡는지 확인한 기록(`mutation`)을 **둘 다** 남긴다.
     (실측: "컴파일이 안 돼 재현 불가" 를 `failures: 1` 로 적어 규격의 정수 검사를 통과시킨 사례가 reviewer 에게 적발됐다.)

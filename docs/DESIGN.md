# 설계 문서 (DESIGN)

> 최초 구상(사용자)과 그에 대한 제안을 함께 기록한다. "제안" 표시가 붙은 항목은 아직 확정되지 않았다.

## 1. 최초 구상

| 단계 | 내용 |
|---|---|
| 0 | 정적 문서 투입 — 환경, AS-IS 소스, 요구사항, RFP, 설계/분석 산출물 |
| 1 | 업무별 분류 (초기에 애매하면 건너뛰고 나중에 나눠도 됨) |
| 2 | Backend 개발 — 0단계 문서 근거, slice별 진행 |
| 3 | 공통 소스 추출·리팩토링 (1~3 반복) |
| 4 | Frontend 개발 — 피그마/스토리보드 근거, slice별 진행 |
| 5 | 단위테스트 (시나리오 없으면 먼저 작성) → FE·BE 연결 확인 → 리팩토링 요구서 |
| 6 | 보안취약점 검사 (code-security-auditor) → 리팩토링 요구서 |
| 7 | QA 자동 테스트 (qa-automation) → 리팩토링 요구서 |
| 8 | 산출물 작성 |

## 2. 제안 사항

### 2-1. 단계 간 계약(contract)을 파일로 고정 — **가장 중요**
각 단계의 출력이 다음 단계의 입력이 되므로, 출력을 사람이 읽는 문서가 아니라 **기계가 읽을 수 있는 고정 형식**으로 둔다.

| 산출물 | 위치 | 생산 | 소비 |
|---|---|---|---|
| `PROJECT_BRIEF.md` | workspace/knowledge/ | 0 | 전 단계 |
| `slices.yaml` | workspace/slices/ | 1 | 2·4·5, /refactor |
| OpenAPI 계약 (slice별) | target_dir/docs/api/<slice>.yaml | 2 | 4·5·8 |
| `RR-xxxx.yaml` 리팩토링 요구서 | workspace/refactor-requests/ | 5·6·7 | /refactor → 1~4 |
| `state.yaml` | workspace/ | 전 단계 | /status, 재개 |

특히 **리팩토링 요구서를 단일 스키마**(`templates/refactor-request.yaml`)로 통일하면 5·6·7단계가 같은 형식을 뱉고,
`/refactor`가 `target_stage`·`slice` 기준으로 묶어 정확한 곳만 다시 돌릴 수 있다.

### 2-2. 0단계에 "요약(Ingest)" 에이전트 추가
문서를 넣어두는 것만으로는 이후 단계에서 컨텍스트가 넘친다. 0단계에서 문서 전체를 읽어
`PROJECT_BRIEF.md`(기술스택·컨벤션·용어집·엔티티 목록·화면 목록·API 후보·비기능 요구)로 압축하고,
이후 단계 에이전트는 brief + 자기 slice 관련 원문만 읽는다. 원문 참조는 `문서명#절` 형태로 남겨 추적 가능하게 한다.

### 2-3. 1단계 승인 게이트
슬라이스 분류는 이후 모든 단계의 축이므로 사람이 `slices.yaml`을 확인·수정한 뒤 진행한다.
차세대라면 AS-IS 패키지/화면/테이블 → slice 매핑표를 함께 만든다.

### 2-4. 2단계 안에 "골격(scaffold) 1회" + 계층 순서 고정
- 최초 1회: 빌드 설정, 공통 응답/에러/로깅/인증 뼈대, 코드 컨벤션을 먼저 만든다.
  → 첫 slice부터 공통 뼈대 위에서 작업하므로 3단계 공통화 부담이 크게 준다.
- slice별 순서: **Migration(DDL) → Mapper/Repository → Service → API → OpenAPI 계약 → 단위테스트**.
  구상의 계층 목록(Mapper·Migration)이 여기 들어간다.
- 차세대일 때 Migration 단계는 AS-IS→TO-BE 테이블·컬럼 매핑표를 산출한다.

### 2-5. 5단계 이름: 단위테스트 → **통합 테스트**
FE·BE 연결 확인은 통합/E2E 성격이다. 단위테스트는 2·4단계의 완료 조건(Definition of Done)으로 넣고,
5단계는 시나리오 기반 통합 테스트에 집중한다. (7단계 qa-automation도 통합 테스트 중심이므로
5단계는 "우리가 쓴 시나리오", 7단계는 "도구가 자동 도출한 시나리오"로 역할을 구분한다.)

### 2-6. developer / reviewer 분리 + 게이트
각 단계에 생성 에이전트와 검토 에이전트를 따로 둔다. 검토는 brief·slices·계약과의 정합성, 컨벤션, 테스트 존재 여부를 본다.
2·3·4단계는 빌드+단위테스트 통과가 완료 조건이며, 실패 시 `state.yaml`에 `blocked`로 기록한다.

### 2-7. 되먹임 경로를 "1단계로 복귀"가 아니라 "target_stage로 라우팅"
요구서마다 `target_stage`·`target_layer`·`slice`가 있으므로 `/refactor`가 그 단계·slice만 다시 실행한다.
slice 재분류가 필요한 경우만 1단계로 간다. 반복 회차(`iteration`)를 올려 같은 요구서가 재적용되지 않게 한다.

### 2-8. 외부 도구 연동 방식
`code-security-auditor`, `qa-automation`은 별도 repo이고 슬래시 명령은 repo 밖에서 호출할 수 없다.
→ `config/tools.yaml`에 경로를 두고, 6·7단계 에이전트가 해당 repo의 `SKILL.md`를 읽어 방법론대로 수행한 뒤,
레포트를 `workspace/reports/`로 가져와 `tools/report_to_rr.py`(예정)로 요구서로 변환한다.
(대안: 두 repo를 Claude Code 플러그인으로 묶기 — 추후 검토)

## 3. 결정 사항 (2026-09-20)

| 항목 | 결정 |
|---|---|
| 구현 형태 | Claude Code repo — `.claude/commands`(오케스트레이터) + `.claude/agents`(서브에이전트) + `.claude/skills`(방법론). 상태는 파일이므로 나중에 Agent SDK 오케스트레이터를 얹을 수 있다 |
| 생성 소스 위치 | `config/project.yaml → project.target_dir` (별도 repo). 이 repo 의 `workspace/` 에는 메타(brief·slices·RR·레포트·state)만 |
| 병렬 실행 | 허용. `pipeline.parallel`·`max_parallel`. depends_on 위상 정렬로 웨이브를 만들고 웨이브 안에서 동시 실행. 충돌 방지 규칙은 `pipeline-core` §6. 5단계(통합 테스트)는 포트·DB 공유 때문에 순차 |
| 기술 스택 | 제한 없음. config 의 `stack.*.profile` 이 프로필 파일을 고른다. 기본 프로필 `spring-mybatis-mysql`(Java 17/Spring Boot 3/MyBatis/MySQL 8/Flyway) + `react-ts`(React 18/TS/Vite). 프로필이 없으면 범용 규칙 |
| 산출물 | SI 관례 기준 13종 (`stage8-deliverables` 원천 표). config `deliverables.items` 로 선택. md+html 기본, docx 선택 |
| 사람 개입 | stage0 brief 확인(비차단), stage1 slices 승인(차단), stage2 골격 확인(비차단), reviewer 2회 후 잔여 지적(blocked), RR rejected 는 사람만 |

## 4. 남은 과제

- 실제 프로젝트로 stage0→stage2 를 한 번 돌려 스킬 문구·게이트 명령이 현실과 맞는지 검증 (첫 실전 후 프로필 보정)
- `tools/report_to_rr.py`: 6·7단계 외부 도구 레포트를 RR 로 자동 변환 (지금은 에이전트가 직접 `rr.py new` 로 생성)
- 다른 스택 프로필 추가 (예: `spring-jpa-postgres`, `node-nest`, `vue-ts`)
- 두 외부 도구를 Claude Code 플러그인으로 묶어 경로 설정 없이 쓰는 방안

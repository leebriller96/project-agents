---
name: stage2-backend
description: 2단계 Backend 개발 — 최초 1회 프로젝트 골격(scaffold) 후 slice별로 Migration→Mapper→Service→API→OpenAPI 계약→단위테스트 순으로 개발하는 방법론. /stage2 수행 시 사용. 스택별 규칙은 profiles/ 참조.
---

# 2단계 Backend 방법론

목표: slice 하나를 **근거 문서대로, 계약(OpenAPI)과 단위테스트를 갖춘 상태로** 완성한다.
스택별 구체 규칙은 `profiles/<stack.backend.profile>.md` 를 읽고 따른다. 프로필 파일이 없으면 이 문서의 범용 규칙만 적용하고 레포트에 "프로필 없음" 을 남긴다.

## A. 골격 (scaffold) — 최초 1회

`state.yaml → stages.stage2_scaffold` 가 `done` 이 아니면 slice 작업 전에 수행한다. 골격은 **slice 코드가 하나도 없는 상태**에서 만든다.

0. **환경 점검 (골격 전 필수)**: 설치된 JDK 버전(`java -version`), 빌드 도구(`gradle`/`mvn` CLI 또는 `~/.gradle/wrapper/dists` 의 캐시된 배포본), Docker 데몬(`docker info`), DB CLI, Node, 그리고 6단계용 SAST(semgrep/gitleaks/osv-scanner — 없으면 사용자에게 미리 알림)를 확인해
   `config/project.yaml → stack` 과 대조한다. 불일치(예: config 17 vs 설치 21)는 **config 를 설치본에 맞추거나 사용자에게 알린 뒤** 진행하고 레포트 "환경" 절에 기록한다.
   빌드 도구가 없으면 wrapper 캐시의 배포본으로 `gradle wrapper` 를 만들고, 그것도 없으면 `blocked` (게이트를 통과할 수 없으므로).
   Docker 가 없으면 Mapper 테스트는 H2 `MODE=MySQL` 로 폴백하고 명시한다.
1. 빌드 설정 (`<target_dir>/backend/`): 언어·프레임워크 버전은 `config/project.yaml → stack` 대로. 의존성은 프로필의 기본 목록
   **+ brief §7·§8 을 훑어 slice 가 필요로 할 기능성 의존성(엑셀 POI, PDF, 메일, 파일 저장, 캐시 등)을 미리 추가**한다. slice 는 `build.gradle` 을 수정할 수 없으므로 여기서 빠지면 3단계까지 대안 구현으로 버텨야 한다.
2. 패키지 구조: `<base_package>/` 아래 `common/`(응답·예외·로깅·보안·설정) 과 slice 별 패키지 자리.
3. 공통 뼈대 — 프로필이 정하는 것들: 공통 응답 포맷, 에러 코드 체계·전역 예외 처리, 요청/응답 로깅, 인증/인가 골격, 페이징 규약, 감사 컬럼 처리, MyBatis(또는 ORM) 설정, 프로파일별 설정(local/dev/prod).
4. DB: `db/migration/V0001__baseline.sql` 에 공통 테이블(공통코드·감사 등 brief 에 근거가 있는 것만).
5. 테스트 기반: 단위테스트 프레임워크 설정, 테스트용 DB(H2 MySQL 모드 또는 testcontainers) 설정, 샘플 테스트 1개.
6. `<target_dir>/backend/CONVENTIONS.md`: 패키지 규칙, 네이밍, 응답/에러 규약, 트랜잭션 경계, 테스트 규약. 이후 모든 slice 와 reviewer 가 이 문서를 기준으로 삼는다.
7. 게이트: 빌드 + 샘플 테스트 통과. 통과하면 `stage2_scaffold: done`, 사용자에게 구조 요약을 보여준다.
8. 골격 테스트는 slice 가 채워도 깨지지 않게 쓴다 — "핸들러 없어 404" 같은 빈 상태 전제 대신 "401 아님 + 응답 봉투" 수준. 모듈에 `@SpringBootTest` 가 둘 이상이면 DB 상태를 공유하므로 골격이 `src/test/resources/cleanup.sql` + `@Sql(executionPhase=AFTER_TEST_METHOD)` 패턴을 제공한다. **`@SpringBootTest(properties="spring.datasource.url=jdbc:h2:mem:…")` 로 DB 를 분리하지 말 것** — 테스트 속성이 `-Pmysql` 프로파일보다 우선해 MySQL 게이트에서 컨텍스트가 깨진다.

brief §3 컨벤션과 프로필 기본값이 다르면 brief 를 우선한다.

## B. slice 개발 — 계층 순서

입력: `PROJECT_BRIEF.md`, `slices.yaml` 의 해당 slice 항목, brief 가 가리키는 원문 절, (migration) 해당 slice 의 AS-IS 프로그램·테이블, `CONVENTIONS.md`, `depends_on` slice 의 OpenAPI 계약.

### B-1. Migration (DDL)
- slice 의 엔티티를 테이블로 설계한다. 근거: 테이블정의서/ERD > 요구사항 > AS-IS DDL.
- 파일: `db/migration/V<yyMMddHHmm>__<slice>_<설명>.sql`. 골격 baseline 은 수정하지 않는다.
- migration 모드: `docs/deliverables/mapping/<slice>-table-mapping.md` 에 AS-IS 테이블·컬럼 → TO-BE 매핑표를 쓴다 (유지/변경/폐기/신규 표시, 변환 규칙). 표준 컬럼(M-38 등) 도입 시 AS-IS 감사 컬럼 → 표준 컬럼 이름·값 변환 규칙, 업무 구분 숫자 코드 → 코드마스터 대응을 포함. 데이터 이관 SQL 은 Flyway 800 대역(또는 별도 스크립트)으로 분리.
- 다른 slice 소유 테이블은 참조(FK)만 하고 만들지 않는다.

### B-2. Mapper / Repository
- 테이블당 Mapper 1개를 기본으로. 쿼리는 slice 가 필요로 하는 것만 만든다.
- 동적 SQL 은 프로필 규칙대로. 문자열 결합 SQL 금지(6단계에서 잡힌다).
- AS-IS 에 SQL 이 있으면 의미를 유지하되 TO-BE 스키마에 맞춰 다시 쓴다. 저장 프로시저는 서비스 로직으로 옮기고 매핑표에 기록.
- **migration + Oracle 방언**: `sql-migrator` 를 `convert <slice>` 로 먼저 호출해 Mapper 인터페이스·XML·DTO·매핑표(`<slice>-sql-mapping.md`)·Mapper 테스트를 받은 뒤, backend-developer 는 그 시그니처로 서비스를 만든다(`migration-sql` 스킬). `sqlSession` 직접 호출 잔존 0.

### B-2-1. 기능 추적표 (migration 게이트)
- `docs/deliverables/mapping/<slice>-function-mapping.md`: `ASIS_FUNCTION_CONTRACTS.md` 의 이 slice 행마다 → TO-BE 구현(컨트롤러 메서드·서비스·Mapper)·동작 차이(없음 | §12 결정 근거 | RR)·특성화 테스트 ID. **모든 행이 채워져야 slice done** — "미이관" 은 §12 폐기 결정 근거 없이는 허용하지 않는다(조용한 기능 누락 차단).
- 동작이 AS-IS 와 달라지는 곳은 요구사항/§12 근거가 있을 때만 허용. 근거 없으면 AS-IS 동작을 유지하고 개선 제안은 RR(low).
- "근거 부족" 으로 올리기 전에 brief **§12-A R행(상태 "확인 요청" 포함)과 §12-B/C 전부**를 grep 으로 대조한다. 이미 결정된 항목을 근거 부족으로 올리면 3단계에 불필요한 결정 요청이 생긴다.
- AS-IS 와 다른 **비기능 세부**(다운로드 `Content-Length` 산출원, 정렬 오류 처리, 오류 코드)도 동작 차이 열에 적는다 — "기능이 같다" 로 넘기지 않는다.

### B-3. Service
- 트랜잭션 경계는 서비스 메서드. 비즈니스 규칙은 요구사항 ID 를 주석으로 단다 (`// REQ-011: 재고 부족 시 주문 불가`).
- 다른 slice 기능은 그 slice 의 서비스 인터페이스(또는 API)로만 호출한다. 남의 Mapper 를 직접 쓰지 않는다.
- 근거가 없는 규칙은 구현하지 말고 레포트 "근거 부족" 에 적는다.

### B-4. API (Controller)
- 경로: `<api_prefix>/<slice>/...`. 응답·에러는 공통 포맷.
- 입력 검증은 DTO 레벨에서. 인증/인가는 골격의 방식대로 어노테이션/필터로.

### B-5. OpenAPI 계약
- `<target_dir>/docs/api/<slice>.yaml` (OpenAPI 3.x). 코드에서 생성하든 손으로 쓰든, **실제 컨트롤러와 일치**해야 한다.
- 스키마·예시·에러 응답·인증 요구를 포함한다. 4단계는 이 파일만 보고 개발하므로 설명은 한글로 충분히.
- `depends_on` slice 계약과 타입이 겹치면 그 정의를 `$ref` 로 참조한다.

### B-6. 단위테스트
- Service: 비즈니스 규칙마다 최소 1개 (정상 + 경계/예외). Mapper: 주요 쿼리 실제 DB(테스트 DB)로. Controller: 요청 검증·응답 포맷.
- 테스트 이름은 한글 설명 허용(`@DisplayName`). 요구사항 ID 를 테스트에 연결한다.
- 외부 연동은 테스트 더블. 실서버·실데이터 금지. "파일 없음" 더블은 플랫폼 경로 리터럴(`Z:/no/such`) 이 아니라 `Resource` 목(`exists()=false`).
- 파일 다운로드 특성화 테스트는 **실물 바이트 수 == `Content-Length`** 를 단언한다(DB 크기 컬럼은 표시용, 헤더는 `Resource.contentLength()`).

## C. 게이트 및 산출물

- 빌드 + 단위테스트 실행. 명령과 출력 요약을 레포트에 싣는다. 실패하면 고치고 다시 돌린다. 못 고치면 `blocked`.
- 공용 파일 변경이 필요했던 것은 `workspace/<project>/reports/common-candidates.md` 에 누적 기록 (3단계 입력).
- 레포트 `workspace/<project>/reports/<ts>_stage2_<slice>_backend.md`: 만든 파일 목록, 테이블, API 표, 테스트 수/결과, 근거 부족, 공통 후보.
- `state.yaml → slices.<slice>.stage2_backend: done|blocked`.

## D. reviewer 체크리스트 (backend-reviewer 가 사용)

1. 계약 일치: `docs/api/<slice>.yaml` 의 경로·스키마·에러가 컨트롤러와 같은가.
2. 근거 일치: 구현된 규칙마다 REQ ID 또는 문서 근거가 있는가. 근거 없는 기능이 있는가.
3. 경계 준수: 남의 slice Mapper 직접 사용, 공용 파일 수정, 골격 규약 위반.
4. 데이터: 마이그레이션이 재실행 가능하고 baseline 을 건드리지 않는가. 매핑표(migration)가 있는가 — 테이블·SQL·기능 매핑표 3종의 행이 100% 채워졌는가, ⚠ 판정에 근거가 있는가, `sqlSession`·`${}`·Oracle 대문자 별칭 잔존 0 인가. XML 주석 ↔ 매핑표 ⚠ 결론 상충 없는가. 테스트 `@DisplayName` REQ 번호 ↔ brief §8 제목 대조. 옵션 포함 행(예 `includeDeleted`)을 구분할 컬럼이 행 DTO 에 있는가. API 없는 공유 도메인 slice 도 기능 추적표(배정 FB 행)가 있는가.
5. 테스트: 규칙마다 테스트가 있는가. 비활성화된 테스트가 있는가. 요구사항을 다루는 테스트의 `@DisplayName` 에 REQ ID 가 있는가(8단계 추적표의 원천 — 없으면 끊긴 연결로 표시된다). 고정 시각(`Clock.fixed`, 상수 Instant)과 시스템 시계를 쓰는 검증기가 한 테스트에 섞여 있지 않은가(시간 폭탄).
6. 기본 보안: SQL 문자열 결합, 입력 미검증, 인증 누락 엔드포인트, 민감정보 로깅.
7. 컨벤션: `CONVENTIONS.md` 위반.

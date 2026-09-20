# 실행 이력·교훈 로그 (LESSONS)

실제 프로젝트를 돌리며 드러난 문제와 파이프라인에 반영한 조치를 누적한다. 형식: 날짜 · 단계 · 현상 → 조치(반영 파일).

## 2026-09-20 — library-sample (샘플 검증, greenfield)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage0 | 문서 5개(요구 22·화면 8·테이블 4)에서 §11 근거 부족 20건 도출. 의도적으로 심은 모순 4건 전부 탐지 + 실제 설계 결함(복합 PK FK 불가, 논리 삭제 필요, 동시성) 추가 발견 | 방법론 유효. 변경 없음 |
| stage0→1 | §11 항목 중 골격·마이그레이션에 필요한 결정(JWT 전달 방식, 코드 seed, 초기 계정)이 승인 없이는 2단계를 막음 | brief 에 **§12 결정 사항** 절을 두고 사용자 승인 결정을 기록하는 관례 도입 → `templates/PROJECT_BRIEF.md`·`stage1` 명령에 반영 예정 |
| stage1 | slice-planner 가 Book+Loan 을 한 slice 로 묶음(순환 의존 회피). 방법론 §2.5 "공통코드는 common-* slice" 와 달리 분리하지 않음 — 소비자 1개뿐이라 타당 | `stage1-slicing` §2.5 에 "소비자가 1개면 분리하지 않는다" 예외 추가 예정 |
| stage2 준비 | config `stack.backend.version: "17"` 이나 설치 JDK 는 21뿐. gradle CLI 없음(wrapper 캐시 8.10.2 만 존재). `mysql` CLI 없음, Docker 데몬은 실행 중 | config 를 21 로 갱신. **골격 전 환경 점검 절차**(JDK·빌드 도구·Docker·Node 확인 후 config 와 불일치 시 보고) 를 `stage2-backend` §A 와 `/stage2` 명령에 추가 예정 |
| 도구 | `tools/*.py` 출력이 Windows 콘솔(cp949)에서 깨짐; slices 템플릿의 `{id}` 가 YAML flow 시퀀스 파싱 오류 | `sys.stdout.reconfigure(utf-8)`, 템플릿 값 따옴표 처리 (반영 완료) |
| 도구 | Bash 도구로 10KB 넘는 다중 heredoc 명령이 통째로 실패 | 긴 파일은 Write 도구로 작성 (메모리 기록) |
| stage2 골격 | testcontainers 1.19.8(Boot 3.3 BOM) 이 Docker Desktop 29.7(API 1.55) 을 못 붙음(`Npipe ... Status 400`). DOCKER_HOST/API_VERSION 변경 무효 → **1.21.4 상향**으로 해결 | 프로필에 버전 요구 명시 |
| stage2 골격 | `@MybatisTest` 임베디드 DB 교체 → `spring.test.database.replace: none`; `@WebMvcTest` 가 SecurityConfig 미스캔 → `@Import` + `JwtTestSupport`; JWT 필터 @Component 시 중복 등록 | 프로필 단위테스트 규약에 추가 |
| stage2 골격 | 에이전트도 Bash heredoc 다중 파일 작성 실패 겪음 | 프로필·에이전트 지시에 "소스는 Write 도구" 명시 |
| stage2 골격 | 에이전트가 `ErrorCode` 를 인터페이스 + slice 별 enum 으로 설계 (공용 enum 병렬 수정 충돌 회피) — 프로필 기본(단일 enum)보다 나음 | 프로필 "골격 설계 메모" 로 채택 |
| stage2 골격 | 게이트 4개 명령 전부 실제 실행·통과(25 tests, H2 + testcontainers). 소요 약 24분, 84 tool call | 정상. 골격은 1회성이라 허용 |
| stage2 common-auth | 계약(OpenAPI) 생성에 앱 기동이 필요해 임시 MySQL 컨테이너(33061)+포트 18080 을 썼고 `servers.url` 이 18080 으로 찍힘 | 프로필에 "계약 생성은 test 프로파일(H2)로 기동하거나 springdoc 의 `servers` 를 상대경로로 고정" 추가 예정 |
| stage2 common-auth | 골격에 `Clock` 빈이 없어 시간 의존 로직(잠금 30분) 테스트가 어려움 → 에이전트가 생성자 주입으로 우회, common-candidates C-1 기록 | 프로필 골격 항목에 `Clock` 빈 추가 예정 |
| stage2 common-auth | 실패 횟수 UPDATE 가 BusinessException 롤백에 묻힘 → `noRollbackFor` | 프로필 규약에 "카운터성 갱신은 noRollbackFor 또는 REQUIRES_NEW" 메모 |
| stage2 common-auth | jjwt 가 키 길이로 알고리즘 자동 선택(HS384) → 명시 고정 필요 | 프로필 JWT 항목에 명시 |
| stage2 common-auth | developer 가 게이트 외에 실제 MySQL 기동 + curl 시나리오까지 자체 검증 (약 17분, 69 tool call) | 좋은 관행이나 5단계 통합테스트와 중복. "smoke 검증은 선택, 레포트에 구분 표기" 로 정리 예정 |
| stage2 common-auth 검토 | reviewer PASS, medium 1(실패 횟수 읽기-덮어쓰기 경합)·low 4. 게이트 재실행으로 보고 일치 확인. target repo 에 커밋이 없어 `git status` 로 공용 파일 변경 판별 불가 → 수정시각으로 대체 | pipeline-core §6-7 **target repo 커밋 규칙** 신설(골격·웨이브마다 오케스트레이터가 커밋). §7 에 medium/low → RR 또는 common-candidates 규칙 명문화 |
| stage2 common-auth 검토 | `@Pattern` 앵커 누락 → OpenAPI pattern 부분 일치 (FE/BE 검증 불일치 위험) | 프로필 검증 규칙에 앵커 필수. W2 developer 프롬프트에 교훈 전달 |
| stage2 W2 | 병렬 developer 2개가 계약 생성 기동 시 포트 충돌 가능, 전체 `gradlew test` 가 상대 컴파일 중 실패 가능 | pipeline-core §6-6: 포트 분리·자기 slice 테스트 우선·전체는 마지막 1회 |
| stage2 member | 병렬 실행 성공: member 가 전체 115 tests 통과(상대 slice 의 진행 중 테스트 9개 포함), 공용 파일 충돌 없음. 계약 생성 포트 분리(18082) 유효 | 정상 |
| stage2 member | H2 가 `testRuntimeOnly` 라 `bootRun` 으로 test 프로파일 기동 불가 → 프로젝트 밖 Gradle init 스크립트로 우회 (C-9) | 프로필 골격 항목에 **계약 생성용 `openApiDump` 태스크**(test 클래스패스 JavaExec 로 기동 → `/v3/api-docs.yaml/<group>` 저장 → `servers` 후처리) 추가 예정. 골격이 만들면 slice 마다 우회 불필요 |
| stage2 member | springdoc: 검색 조건 객체는 `@ParameterObject` 필요, boolean 파라미터는 `@Schema` 아닌 `@Parameter` 로 문서화해야 타입 유지. common-auth 와 다른 slice 의 Mapper 빈 이름 충돌(`MemberMapper`) → `MemberAdminMapper` | 프로필에 springdoc 메모·Mapper 명명 규칙(`<Slice><Entity>Mapper` 또는 slice 접두어) 추가 |
| stage2 book-loan | 가장 큰 slice(API 11, 테스트 88). 274k 토큰·83 tool call·24분. 병렬 member 와 Gradle 동시 실행 충돌 없음, 전체 194 tests 통과 | slice 크기 상한(API 5~20) 안이지만 상단. `stage1-slicing` 크기 기준에 "테스트 포함 예상 파일 30개 초과면 하위 slice 분할 고려" 메모 예정 |
| stage2 book-loan | member 와 동일하게 `bootRun` 계약 생성 우회(init 스크립트) 반복, `operationId` 자동 번호(`search_1`) 발생 → 11개 전부 명시 | 프로필: `@Operation(operationId=...)` 명시 규칙 추가. openApiDump 태스크는 골격 항목으로 이미 반영 |
| stage2 book-loan | 타 slice 테이블(tb_member) 테스트 데이터를 각 slice 가 JDBC fixture 로 따로 삽입 (C-17) | 프로필 테스트 규약에 "골격이 `src/test/resources/fixtures/<table>.sql` 공용 fixture 제공" 추가 예정 (3단계 C-17) |
| stage2 book-loan 검토 | reviewer PASS, medium 1(회원 단위 직렬화 없어 동시 대여 시 3권 초과 가능)·low 3. §12 결정(도서 행 잠금)만으로는 REQ-020 이 안 지켜짐 — 결정 사항이 요구를 완전히 덮는지 reviewer 가 잡아냄 | 프로필 동시성 규칙에 "한도(N권·N회) 검증은 한도의 주체(회원) 행을 잠근다" 추가 |
| stage2 W3 준비 | 의존성 추가(POI)가 필요한 기능이 slice 에 있으면 `build.gradle` 수정 금지 규칙과 충돌 | pipeline-core §6 충돌 방지에 "의존성 추가는 common-candidates 로 요청하고 slice 는 대안 구현 또는 인터페이스만" 명문화. 골격 단계에서 brief 를 훑어 **예상 의존성(엑셀·PDF·메일 등)을 미리 build.gradle 에 넣는** 절차 추가 |
| stage2 stats | `GlobalExceptionHandler` 가 `HttpMediaTypeNotAcceptableException`(406) 을 500 으로 변환 → 파일 다운로드 엔드포인트가 `produces=ALL_VALUE` 로 우회 (C-19). Clock 시간대가 slice 마다 다름(systemDefault vs Asia/Seoul, C-20) | 프로필 골격 항목: GlobalExceptionHandler 에 406/415 핸들러 포함, `ClockConfig` 는 config 의 시간대(환경정보)로 고정 |
| stage2 전체 | 4 slice 모두 reviewer PASS(blocker/high 0), medium 2·low 9 → RR 7건 + common-candidates 24건. 총 225 tests. 전체 소요 약 2시간 20분, 에이전트 9회 호출 | 정상. common-candidates 가 24건이면 3단계 부담이 큼 → 골격 체크리스트에 이번 회차 C-1/C-9/C-19/C-20 을 기본 포함시켜 다음 프로젝트에서 재발 방지 |
| stage2 stats 검토 | reviewer 가 `./gradlew test` 만 돌리면 Gradle 캐시로 `UP-TO-DATE/FROM-CACHE` 가 되어 실제 실행이 안 됨 → `cleanTest test --no-build-cache` 필요. developer 보고의 테스트 내역(Service 10/Controller 11)이 실제(9/12)와 달랐음(합계는 일치) | 프로필 명령 표에 reviewer 용 `cleanTest --no-build-cache` 추가, backend-reviewer 에이전트 지시에 명시. developer 는 테스트 수를 XML 결과에서 읽도록 |
| stage2 stats 검토 | operationId 프로필 규칙(`<slice>_<동작>`)이 실제 관행(`getBook`)과 어긋남 — 문서가 코드보다 늦게 쓰였고 검증 안 됨 | 프로필 규칙을 실제 관행(`<동사><명사>`, 그룹 내 유일)으로 수정 (C-26) |

## 2026-09-21 — library-sample (계속)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage3 기준선 | **시간 폭탄 테스트**: common-auth 테스트 3건이 "고정 시각(17:00)으로 발급한 1시간 토큰을 시스템 시계 파서로 검증" → 18시 이후 항상 실패. stage2 검토 시점(17시대)엔 통과했으므로 developer·reviewer 모두 놓침. 3단계 refactorer 가 원칙대로 테스트를 안 고치고 RR-0008(high)로 남김 → stage3 `blocked` | 프로필 테스트 규약: "시각 고정 테스트는 발급·검증 양쪽이 같은 Clock 을 본다. 시스템 시계를 쓰는 파서/검증기는 고정 시각과 섞지 않는다". reviewer 체크리스트 §D-5 에 "고정 시각 + 시스템 시계 조합" 항목 추가. 골격 `JwtTokenParser` 에 Clock 주입 |
| stage3 | 27건 중 24건 처리, 3건 보류(추상화 과잉·요구 근거 없음·배포 항목). xlsx 전환은 §12 결정에 따른 동작 변경으로 §3 원칙 예외 명시. 계약 4개 재생성 diff 가 의도한 변경만인지 검증함 | 정상. `stage3-common` §3 에 "brief §12 결정에 따른 기능 전환은 동작 변경 예외로 허용하되 레포트에 명시" 추가 |
| stage3 | `-Pgroup` 이 Gradle 내장 `project.group` 과 충돌 → `startParameter.projectProperties` 로 읽음 | 프로필 openApiDump 설명에 `-PapiGroup=` 으로 이름 변경 권장 |
| /refactor | stage3 가 blocked 인 채로 /refactor 를 먼저 돌림(RR-0008 이 게이트를 막으므로). 순서: stage3 변경 커밋 → refactor 병렬(common-auth 4건 ‖ book-loan 3건) → member 1건 → stage3 게이트 재확인 | `/refactor` 명령에 "blocked 단계의 원인 RR 이 있으면 그것을 첫 묶음으로" 규칙 추가 |
| /refactor book-loan | RR-0005 동시성 결함이 testcontainers 로 **실제 재현**(잠금 제거 시 2건 성공) 후 수정 검증. `-Pmysql` 전용 테스트는 H2 에서 `@EnabledIfSystemProperty` 로 skip — "skip 금지" 규칙의 환경 조건부 예외 | pipeline-core §4 에 "환경 조건부 skip(도커 필요 등)은 조건과 사유가 어노테이션에 명시되고 해당 환경에서 실제 실행된 기록이 레포트에 있으면 허용" 예외 명문화 |
| /refactor | Docker Desktop 이 꺼져 있어 에이전트가 직접 기동. bash `TZ=Asia/Seoul date` 가 Windows Git Bash 에서 시스템(KST) 을 UTC 로 오인해 타임스탬프 오류 | 모든 스킬의 타임스탬프 명령을 **python 한 줄**(`tools/kst_now.py` 신설) 로 통일. 환경 점검에 `docker info` 결과가 "실행 중" 이 아니면 기동 시도 |
| /refactor common-auth | RR-0008 B안(파서 Clock 주입)은 골격에 생성자가 없어 불가 — 프로필 문서(내가 방금 추가)와 실제 골격 코드가 불일치 | 교훈 반영 시 "다음 프로젝트 골격" 과 "현재 프로젝트 후보(C-31)" 를 구분해 적어야 함. 프로필 변경은 현재 target 에 소급되지 않음 |
| /refactor | 병렬 developer 2개가 같은 `build/test-results` 를 써서 `cleanTest` 잠금 충돌 2회 → 폴링 후 성공 | pipeline-core §6-6 에 "Gradle 은 `--project-cache-dir`/별도 `build` 디렉토리를 쓰거나, 전체 테스트는 웨이브 종료 후 오케스트레이터가 1회만" 으로 조정 |
| /refactor book-loan 검토 | reviewer **FAIL(high)**: 새로 만든 동시성 테스트가 또 시간 폭탄(seed 고정 날짜 + 시스템 Clock 빈) — 방금 추가한 §D-5 체크리스트 항목이 잡아냄. 12일 뒤 LOAN_002 대신 LOAN_003 으로 오진될 결함. developer 재작업(1회차) 지시 | 체크리스트 되먹임이 작동. 추가로 프로필 테스트 규약에 "`@SpringBootTest` 통합 테스트는 `@TestConfiguration` 으로 `Clock.fixed` 를 override 하고 seed 날짜는 그 Clock 기준 상대값" 명문화 |
| /refactor book-loan 검토 | `-Pmysql` 전용 테스트가 RR-0005 의 유일한 회귀 근거인데 기본 게이트(H2)에서는 skip → 회귀가 조용히 재발 가능 | 5단계 시나리오와 stage state 에 "`-Pmysql` 동시성 테스트 1회 실행" 조건 명시. pipeline-core §4 게이트에 "환경 조건부 테스트는 그 환경에서 1회 실행이 게이트에 포함" 추가 |
| /refactor member | **InnoDB REPEATABLE READ 스냅숏**: "행 잠금 → 일반 COUNT" 는 잠금 전 스냅숏을 읽어 상대 커밋을 못 봄 → MySQL 에서 여전히 2건 성공(실측). 판정은 잠금 조회(current read)가 돌려준 결과로 해야 함. 내가 RR 수정안에 쓴 "잠금 후 count" 도 이 함정에 걸림 | 프로필 동시성 규칙: "잠금 뒤 판정은 `FOR UPDATE` 조회가 반환한 행/집계로만. 잠금 전에 읽은 값·잠금 없는 COUNT 는 스냅숏이라 쓰지 않는다". RR-0001(common-auth) 도 같은 패턴인지 5단계에서 확인 |
| /refactor member | 집합 불변식(활성 ADMIN ≥ 1)은 집합 전체를 PK 순 잠금. `(role, active)` 인덱스 없어 전체 스캔 잠금 (C-34) | 프로필: "집합 불변식은 집합 전체 PK 순 잠금 + 그 조건의 인덱스 필수" |
| stage4 골격 | 68 파일, 게이트 4개 통과(36 tests). 26분·106 tool call. 에이전트가 프로필보다 나은 설계: **라우트 자동 등록**(`import.meta.glob` 으로 `features/*/routes.tsx` 수집 → slice 가 router.tsx 를 안 건드림), `ApiError.fieldErrorMap()`, `api.download()` | 프로필 `react-ts.md` 에 자동 등록 패턴·`registerLogoutHandler` 훅 패턴 채택 |
| stage4 골격 | vitest jsdom + react-router 데이터 라우터의 `AbortSignal` 충돌(jsdom vs undici) → 커스텀 환경 파일. jsdom `Blob.text()` 없음 → 폴백. `vitest/config` 가 `loadEnv` 미재export | 프로필 "알려진 문제" 절 신설 |
| stage4 골격 | 생성 타입이 응답 스키마 `required` 부재로 전부 optional (F-4) — backend 계약 품질 문제 | stage2 프로필 OpenAPI 항목에 "응답 DTO 는 `@Schema(requiredMode=REQUIRED)` 또는 Java record + `@NotNull` 로 required 명시" 추가. 현재 프로젝트는 common-candidates |
| stage4 common-auth | reviewer PASS, low 4. developer 가 오케스트레이터 지시("/me 재호출")보다 골격 CONVENTIONS(login 응답으로 setUser)를 우선함 — reviewer 도 타당 판정 | pipeline-core §7 에 "골격 CONVENTIONS > 오케스트레이터 프롬프트. 충돌 시 developer 는 규약을 따르고 보고에 명시" 명문화 |
| stage4 common-auth | react-query mutation variables 에 비밀번호가 gcTime(5분) 동안 잔존 (RR-0010) | `react-ts.md` 규약: "자격증명을 보내는 mutation 은 `gcTime: 0`" |
| stage4 W2 | 프론트 병렬 developer 는 `node_modules`·`dist` 공유 → build 는 마지막 1회. vitest 는 파일 단위라 동시 실행 가능 | pipeline-core §6-6 에 프론트 버전 추가 |

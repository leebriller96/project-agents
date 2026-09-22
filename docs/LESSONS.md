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
| stage4 member 검토 | reviewer medium: zod 스키마 max 길이 규칙에 테스트 없음 — "검증 규칙마다 테스트 1건" 을 developer 가 일부만 지킴. URL 복원 파라미터 길이 미검증 | `react-ts.md` 테스트 규약에 "zod 스키마의 모든 규칙(required/min/max/pattern/format)을 표로 뽑아 각 1건, 붙여넣기 경로(maxlength 제거)로 검증" + "URL 에서 복원한 검색 조건도 스키마로 정규화" 추가 |
| stage4 book-loan 검토 | reviewer PASS, medium 2 — member 와 **같은 종류**(URL 검색 조건 미정규화, zod max 규칙 1건 테스트 누락). 프로필 규칙은 member 검토 후 추가됐으나 book-loan developer 는 그 전에 시작해 못 봄(병렬 웨이브) | 같은 웨이브에서 발견된 교훈은 다음 웨이브부터 적용됨을 인정. `/stage4`·`/stage2` 명령: 웨이브 종료 후 reviewer 지적 중 "규칙 부재로 인한 것" 은 **같은 웨이브의 다른 slice 에도 해당하는지 오케스트레이터가 grep 으로 확인**해 RR 을 묶어 만든다 |
| stage4 book-loan | 화면 5개·API 11개·테스트 77, 290k 토큰·23분. RR 없이 계약만으로 완결 — 2단계 계약 우선 원칙의 효과 | 정상 |
| stage4 stats | 최신 규칙(URL 정규화·zod 전수 테스트)을 프롬프트에 명시하니 developer 가 선반영 — 같은 종류 지적 재발 없음(reviewer 확인 예정). recharts 는 jsdom 에서 `ResponsiveContainer initialDimension` 으로 목 없이 렌더 검증 가능 | `react-ts.md` 알려진 문제에 recharts 항목 추가. 번들 1.1MB(recharts) → 골격 항목에 "차트/에디터 등 무거운 라이브러리는 라우트 lazy + manualChunks 기본" 추가 |
| stage4 stats | `vi.stubGlobal('URL', {...})` 이 `new URL()` 을 깨뜨림 → `defineProperty` 로 메서드만 추가. 골격 queryClient 의 5xx 재시도가 실패 토스트 테스트를 4초 지연 | 프로필: 테스트 QueryClient 는 `retry: false`(골격 `createTestQueryClient` 가 보장) |
| /refactor FE | react-query `gcTime: 0` 은 observer 분리 후에만 작동 — 로그인 실패 시 폼이 남아 비밀번호 variables 잔존. developer 가 소스를 읽고 `reset()` 추가 + 역검증(gcTime 제거 시 테스트 실패 확인) | 프로필 규약 보강 |
| /refactor FE | 3 slice 가 URL 정규화를 "필드 단위 safeParse, 실패 필드만 기본값" 으로 일관 구현 — stats 선반영 패턴을 참고 지시한 효과 | 3단계 2회차에서 `shared/` 헬퍼로 승격(F 후보) |

## 2026-09-21 (오전) — stage5 통합 테스트

| 단계 | 현상 | 조치 |
|---|---|---|
| stage5 common-auth | 첫 slice 가 환경(MySQL 컨테이너·BE jar·vite preview·Playwright 격리)을 구성하고 `env-up.sh/env-down.sh` + `docs/test/README.md` 로 남김 → 이후 slice 재사용. 29분 소요 | `stage5-integration-test` §2 에 "첫 slice 가 환경 스크립트를 만들고 README 로 남긴다, Playwright 는 `tests/integration/package.json` 격리" 명문화 |
| stage5 common-auth | 개발 PC 의 8080·5173 이 다른 프로세스에 점유 → 18080/5174 기본값. Git Bash 에서 `env-up.sh | tee` 하면 백그라운드 java 가 파이프 핸들을 물어 안 끝남 | 스킬 §2 에 포트 회피·파이프 금지 주의 추가 |
| stage5 common-auth | **RR-0009 갭 잠금 실측**: 미존재 사번 로그인 워커 8개 부하 중 회원 등록 INSERT 가 1538ms(단독 68ms, 22.6배), 3s 부하면 기아. `performance_schema.data_locks` 로 X,GAP 459건 관측 → severity low→medium | 5단계가 "RR 의 실제 심각도 측정" 역할을 함을 확인. 프로필 동시성 규칙에 "미존재 키 `FOR UPDATE` 는 갭 잠금 → 존재 확인 후 잠금" 추가 |
| stage5 common-auth | 정적 검증에서 FE zod `min(1)` 이 공백만 통과, BE `@NotBlank` 400 → FE 느슨(RR-0014). JDBC 세션 TZ 미고정으로 seed `NOW()` 와 앱 Clock 9시간 차(RR-0015, C-4 재확인) | `react-ts.md`: 문자열 필수 검증은 `.trim().min(1)`; 프로필 골격: JDBC URL 에 `serverTimezone=Asia/Seoul`(또는 `connectionTimeZone`) 고정 + Flyway seed 는 `CURRENT_TIMESTAMP` 대신 앱 시간대 명시 |
| stage5 book-loan | API 43 + UI 5 전부 통과, 동시성 2종 5라운드 회귀 없음. RR 3건 모두 low — 2·4단계 계약 우선·reviewer 게이트의 효과. 발견: 생성 상태코드 slice 간 불일치(200 vs 201), LIKE `%`/`_` 미이스케이프, 역직렬화 실패 시 fieldErrors 비어 있음 | 프로필: "생성은 201 통일" 을 골격 CONVENTIONS 규약에, MyBatis LIKE 는 `ESCAPE` + 이스케이프 유틸(골격 common/util), GlobalExceptionHandler 가 `HttpMessageNotReadableException` 의 경로를 fieldErrors 로 변환 |
| stage5 book-loan | 정적 검증에서 기동 BE 의 `/v3/api-docs` 와 계약 파일 diff, `gen:api` 재생성 diff 를 함께 확인 — 계약 드리프트 0 | `stage5-integration-test` §4 에 "기동 BE 의 api-docs ↔ 계약 파일 diff" 항목 추가 |
| stage5 member | API 22 + UI 5 통과, RR-0004 동시성 5라운드 회귀 없음. RR-0017 LIKE 횡전개 **재현**(새 RR 대신 evidence 보강 — 횡전개 규칙 작동). 신규 low 2: 검색 DTO trim 불일치(book-loan 은 trim, member 는 미trim), 검증 실패 메시지가 Spring 영문 내부 메시지 노출 | 프로필: 검색 DTO 문자열은 골격 `@TrimmedString`(또는 setter trim) 으로 통일; GlobalExceptionHandler 가 타입 변환 실패(`MethodArgumentTypeMismatch`) 메시지를 한글 규격 문구로 변환 |
| stage5 member | C-3(비활성 계정의 기존 토큰이 만료까지 유효) 현 동작 기록 — 요구 근거 없어 RR 아님. 6단계 보안 점검에서 판단될 항목 | 정상. stage6 프롬프트에 "C-3 현 동작" 을 점검 포인트로 전달 |
| stage5 stats | API 18/19(Content-Type charset 1건 실패 → RR-0021), UI 5/5. xlsx 를 의존성 없이 zip+XML 로 직접 파싱해 검증. **RR-0015 월 경계 실측**: 실행이 KST 08:55(UTC 전날) 창에 걸려 같은 분에 API 대여는 09-21, SQL `CURDATE()` 대여는 09-20 으로 기록됨 — 앱 경로는 정확, 영향은 SQL `NOW()` 로 만든 행(seed·이관·배치)에 한정 | 시각 의존 결함은 "재현 창" 을 시나리오에 명시. 골격 규칙(JDBC TZ 고정) 유지, 이관 계획 시 medium 상향 조건 기록 |
| stage5 전체 | 4 slice API 101/102 + UI 19/19. RR 9건 중 medium 2·low 7 — **blocker/high 0**. 2·4단계 reviewer 게이트 + 계약 우선이 통합 단계 결함을 낮은 등급으로 눌렀음. 소요 약 1시간 40분 | 정상. `/refactor` 순서를 3(common 기반) → 2(slice) → 4(FE) 로 조정: LIKE 유틸·trim 등 공용 기반이 먼저 있어야 slice RR 이 깔끔 |
| /refactor 순서 | 규칙은 target_stage 1→2→3→4 이지만, 이번엔 stage 2 RR(LIKE·trim)이 stage 3 공용 유틸에 의존 → 3 을 먼저 | `/refactor` 명령: "stage 2 RR 이 공용 기반을 필요로 하면(suggested_fix 에 common/ 언급) stage 3 묶음을 먼저" 규칙 추가 |
| /refactor iter4 common | RR 4건 + 공용 기반 처리, **RR-0019 가 공용 trim advice 로 자동 해결**(slice 코드 무변경). LIKE 이스케이프 문자 `\` 는 H2/MySQL 에서 서로 다르게 동작해 `!` 로 결정(실측) — 내가 프로필에 쓴 `\` 규칙이 틀림 | 프로필 LIKE 규칙 `!` 로 정정. "공용 기반이 slice RR 을 자동 해결하면 developer 호출 없이 done 처리(테스트로 증명)" 를 `/refactor` 에 명시 |
| /refactor iter4 common | 명명 TZ 강제(`connectionTimeZone=Asia/Seoul`)는 시간대 테이블 없으면 접속 실패 — 조용한 드리프트 대신 즉시 실패가 낫다는 판단 | 배포 가이드 항목으로 8단계에 전달 |
| /refactor iter4 common-auth | RR-0009 갭 잠금: 존재 확인 후 잠금으로 부하 중 INSERT **1540ms → 82ms(1.1배)**. 수정 전 코드로 되돌려 같은 테스트가 실패함을 확인(5단계 실측 1538ms 와 일치) — 결함 재현·수정·회귀 테스트가 한 사이클로 닫힘 | 정상. 테스트 JVM stdout cp949 로 한글 로그 깨짐 → C-37(`stdout.encoding=UTF-8`), 프로필 골격 build.gradle 항목에 추가 |
| /refactor iter4 FE | RR-0014: 내 지시 `.trim().min(1)` 은 비밀번호 값을 변환해 전송하는 문제 — developer 가 RR evidence("BE 는 trim 없이 BCrypt")를 근거로 `refine` 선택. 규약 우선순위(evidence·근거 > 프롬프트 세부)가 작동 | 프로필: 비밀번호류는 `refine` |
| /refactor iter4 FE | 201 후속: 통합 테스트 기대값 변경이 지시(2곳)보다 많음(18곳) — developer 가 grep 으로 전수 수정. 통합 테스트 실제 재실행은 안 함 | 6·7단계 전에 5단계 재실행 필요 항목으로 기록. `/refactor` 명령 7항에 "stage 2 반영 → 그 slice 의 stage5 pending" 규칙대로 book-loan·member·common-auth stage5 를 pending 으로 되돌림 |

## 2026-09-21 (오전) — stage6 보안 점검

| 단계 | 현상 | 조치 |
|---|---|---|
| stage6 준비 | SAST 4종(semgrep/bandit/gitleaks/osv-scanner) 전부 미설치 → claude-only 폴백. 소스 284개 > 150 → slice 병렬 scan + merge | 환경 점검 절차에 "6단계 전 SAST 설치 여부 확인·설치 권고(WSL/도커)" 추가. 골격 단계 환경 점검 표에 SAST 항목 포함 |
| stage6 book-loan | 외부 `export_findings.py` 가 `### [F-<숫자>]` 만 인식 → `F-BL-###` 접두어 불가. slice 별 **번호 대역**(F-2xx/F-3xx/F-4xx)으로 대체 | `stage6-security` §2 대규모 절차에 "slice 별 F-번호 대역 배정(오케스트레이터가 지정), merge 시 그대로 유지" 명시 |
| stage6 book-loan | Low 3·Info 2, Critical/High/Medium 0. 발견의 질: ISBN 중복 경합이 500(member 는 409 — slice 간 불일치), 비활성 계정 토큰으로 대여 가능(C-3 연계), 상태 변경 POST 가 SameSite 단일 방어 | 프로필 골격: `DataIntegrityViolationException` 공용 409 변환, 인증 필터에서 비활성 계정 즉시 거부(DB 조회 1회 또는 캐시), 상태 변경 요청에 커스텀 헤더 요구 — 6단계 merge 후 RR 로 |
| stage6 merge | 병렬 4 scan 24건 → 병합 20건(통합 5·신규 1). 같은 근본 원인(초기 비밀번호·비활성 토큰·PageParam)이 3 slice 에서 각각 잡혀 merge 가 하나로 묶음. 경계 흐름 5개 중 확정 3·부분 1·기각 1(잠금 순환 없음) | merge 방식 유효. `stage6-security` §5 merge 규칙에 "통합 시 근본 원인 위치를 대표로, sink 는 evidence 로" 예시 추가 |
| stage6 결과 | High 2건 모두 **0단계 §11 근거 부족(11-08 초기 비밀번호)** 에서 이미 표시됐던 사양 문제. 코드 결함이 아니라 요구사항 결정 부재 → RR 은 만들되 "사업 결정 선행" 표시 | `/stage6` 명령: RR 중 "사양 결정 필요" 는 brief §12 결정 요청으로 사용자에게 올리고 `/refactor` 에서 결정 전 착수 금지. `/stage1` 8항(2단계 전 결정 필요 항목)에 "보안 관련 §11 항목(초기 비밀번호·토큰 폐기·TLS)은 반드시 포함" 추가 — 6단계까지 미루지 않도록 |
| stage6 | 6단계 실행 시간 약 1시간 10분(scan 4 병렬 2웨이브 + merge). 토큰 약 900k | 정상. hybrid 였다면 SAST 결과 검증 시간이 더 필요 |

## 2026-09-21 (오후) — refactor iteration 5 (보안 RR)

| 단계 | 현상 | 조치 |
|---|---|---|
| iter5 common | RR 5건 + A안 공용 기반. Boot 3.3.5→**3.4.13** 상향 성공(springdoc 2.8 동반, `@MockBean→@MockitoBean`), lockfile 도입. 306 tests(+39), `-Pmysql` 전체 통과. 31분·114 tool call | 프로필: 골격 기본 버전을 Boot 3.4.x + springdoc 2.8 + `springdoc.api-docs.version=openapi_3_0` 고정(2.8 기본 3.1 이 계약 형식을 흔듦), `dependencyLocking` 기본 |
| iter5 common | 인메모리 rate limit 이 통합 테스트(한 IP 수백 회 로그인)를 막음 → env-up.sh 에 `..._ENABLED=false` | 프로필: "보안 필터는 설정으로 끌 수 있게, 통합 테스트 환경은 rate limit 비활성" |
| iter5 common | OriginCheck 는 nginx `proxy_set_header Host $host` 없으면 전부 403 — 배포 가이드 필수 항목 | 8단계 배포 가이드 체크리스트에 추가 |
| iter5 BE 검토 | reviewer **FAIL(high 2)**: ① `@Primary` provider 가 MyBatis 세션이라 `@Transactional` 테스트 안에서 **1차 캐시** 로 stale 상태 반환 → 공용 회귀 테스트 실패(developer 는 slice 부분 실행만 해서 못 봄, 오케스트레이터가 고친 C-47 단언도 이 실패는 못 잡음). ② rate limit 이 `X-Forwarded-For` **첫 값**을 키로 — nginx 표준은 클라이언트 값 뒤에 실 IP 를 덧붙이므로 스푸핑 가능 → 내 프롬프트 지시("첫 값 사용")가 틀렸음 | 프로필: "인증/상태 조회 Mapper 는 `flushCache=true useCache=false`", "XFF 는 신뢰 프록시 홉 수 기준 **마지막 값**". 병렬 웨이브 후 전체 테스트를 reviewer 전에 오케스트레이터가 1회 돌려 먼저 잡는 게 낫다 — pipeline-core §6-6 에 "웨이브 종료 시 오케스트레이터가 전체 테스트 1회, 실패면 reviewer 전에 developer 재작업" 명시 |
| stage6 재점검 | `report_diff`: 해결 10·잔존 10·신규 1. 해결 10건 전부 코드로 실확인, 놓친 것 0. 신규 코드(비밀번호 변경 API·필터 3종·runner)를 새 공격면으로 점검 → Low/추정 1건뿐. 되돌린 RR 0 | 재점검 절차(§5) 유효. 남은 것은 운영 배포 전 확정 항목(TLS·ADMIN_INITIAL_PASSWORD·XFF 신뢰 설정) → 8단계 배포 가이드 체크리스트로 |
| 구조 | 사용자 지시: 외부 도구를 별도 clone 하지 않고 project-agents 하나만 받아 쓰게 → **git subtree** 로 `external/` 편입 (submodule 은 `--recursive` 필요라 제외). 경로는 tools.yaml 상대경로, `tools/sync-external.sh` 로 upstream 갱신 | 도구의 `reports/.sast`·`.tests` 산출물은 gitignore. 도구 안의 `.claude/`·`CLAUDE.md` 는 루트가 아니라 자동 로드되지 않음(의도) |

## 2026-09-21 (오후) — stage5 재실행(r2)·refactor iter7

| 단계 | 현상 | 조치 |
|---|---|---|
| stage5 r2 | 4 slice **API 126/126, UI 24/24**(r1 101/102·19/19). 재실행이 refactor 4·5 의 효과를 전부 실측으로 확인: 갭 잠금 22.6배→1.3배, 비활성 토큰 200→401, Content-Type 통과, ISBN 동시 등록 201+409, export 상한 10k, A안 흐름. 신규 RR 5건 전부 low(문서·타입 stale) | 재실행 = 회귀 게이트로 유효. `stage5-integration-test` 에 "재실행(rN) 은 이전 결과 병기, 기대값 변경 건수 보고" 규칙 추가 |
| stage5 r2 | 첫 slice 가 만든 `provisionChanged()`(A안 초기 상태 해제) 헬퍼를 나머지 3 slice 가 import 로 재사용 — 헬퍼 인계 규칙이 작동 | 정상 |
| stage5 r2 | RR 5건 중 3건이 **계약/타입 stale**(BE 계약 재생성 후 FE `gen:api` 미실행, 계약 설명이 정책 변경 미반영). `/refactor` 가 BE 계약을 바꾸면 FE 타입 재생성을 자동으로 붙여야 함 | `/refactor` 7항에 "target_stage 2 반영으로 `docs/api/*.yaml` 이 바뀌면 같은 회차에 FE `gen:api` 재생성 작업을 자동 추가" 규칙. 계약 설명 문구도 정책 결정(§12) 변경 시 grep 대상 |
| stage5 r2 | TZ 재현 창(00~09 KST) 밖 실행이라 SQL `CURDATE()` 케이스 직접 재확인 불가 → 커넥션 time_zone·seed 값·세션 CURDATE 로 간접 확인 | 시각 의존 시나리오는 "재현 창 밖이면 간접 증거 3종" 패턴을 스킬에 예시로 |

## 2026-09-21 (오후) — stage7 QA

| 단계 | 현상 | 조치 |
|---|---|---|
| stage7 | external/qa-automation 첫 사용(subtree). 1,351건 실행(BE 368·FE 341·통합 153·생성 53). 확정 결함 2 + 플래키 1 — **DB 응답 정지 시 무기한 대기**(JDBC socketTimeout 미설정, 30초 재현), `/error` 디스패치 비-ApiResponse, `Auditable.markUpdated` 가 Clock 빈 미사용 | 프로필 골격: datasource `connectTimeout/socketTimeout` + MyBatis `defaultStatementTimeout`, `ErrorController` 를 ApiResponse 로, `Auditable` 은 Clock 주입. 셋 다 첫 샘플 골격 결함 → 다음 골격 체크리스트 |
| stage7 | **외부 도구 버그**: `run_tests.sh` 가 Windows(cygpath)에서 Gradle 결과 glob `*` 를 제거해 0건 집계, `./gradlew test` UP-TO-DATE 를 ran 으로 기록. 에이전트가 `cleanTest` + runs.tsv 보정으로 우회 | **upstream 수정 후보** → qa-automation repo 이슈로: (1) Windows glob 처리, (2) Gradle 은 `cleanTest test` 강제, (3) `-Pmysql` 같은 프로파일 인자 전달 옵션. 수정되면 `tools/sync-external.sh` 로 가져옴 |
| stage7 | 러너가 `tests/integration` 을 설정 없이 Playwright 로 실행해 에러 5·스킵 19 → 환경 문제로 분류(정상 환경 24/24) | qa-automation 에 "환경 기동 훅(pre-run 스크립트) 지정" 옵션 upstream 후보. 파이프라인: `docs/test/README.md` 의 env-up 을 7단계 프롬프트에 명시(이미 함) |
| stage7 | 소요 48분·421k 토큰·128 tool call — 단일 단계 최대. 1,351건 실행 + 우회 작업 | 대규모면 7단계도 "기존 테스트 실행" 과 "신규 생성·triage" 를 두 에이전트로 분할 검토 |
| refactor iter8 | RR-0041: 내 지시 "URL socketTimeout=30000, 10초 내" 가 실측과 어긋남 — (1) URL 파라미터는 테스트가 URL 을 통째로 바꾸면 무효 → Hikari 프로퍼티, (2) 실패까지 ≈ socketTimeout×2(5회 실측), (3) statement timeout 은 무응답에 무효, (4) MyBatis-Spring 예외 변환기가 첫 예외 때 메타데이터 커넥션을 새로 얻어 +12초 → 선적재. developer 가 전부 실측으로 잡음 | 프로필 정정. "타임아웃 값은 반드시 정지 시나리오로 실측해 결정" 규칙 |
| 외부 도구 | qa-automation `run_tests.sh` 버그 3종을 project-agents 에서 고쳐 **subtree push 로 upstream 반영**(`39f351e`). 이후 upstream 은 `sync-external.sh` 로 | 마스터 repo 워크플로 확립: 도구 버그 → external/ 수정 → `tools/push-external.sh` |

## 2026-09-21 (오후) — stage8·library-sample 완료

| 단계 | 현상 | 조치 |
|---|---|---|
| stage8 | 12종 생성(md 2,688행). 04·05 는 마이그레이션·OpenAPI 를 스크립트 파싱. 08 은 재실행 현재 값. RTM 끊김 6건은 전부 "요구 자체가 범위 밖/비기능"(REQ-025 제외, NFR-001 부하, NFR-005 Edge) — 코드 누락 0 | 정상. `@DisplayName` REQ 표기율 130/378(34%) → 프로필 테스트 규약에 "REQ 를 다루는 테스트는 DisplayName 에 ID 필수" 를 게이트(reviewer §D-5)로 승격 |
| stage8 | `build_report.py` 가 mermaid 미포함 → html 에서 ERD·구성도가 코드로 보임 | `tools/build_report.py` 에 mermaid.js CDN + ```mermaid 블록 변환 추가(아래 반영). 두 subtree 의 build_report.py 도 동일 개선 후보 |
| stage8 | `state.yaml` RR 카운터가 stale(iter7·8 미갱신) — `rr.py stats --write` 를 매 refactor 종료 시 호출하는 걸 빠뜨림 | `/refactor` 8항에 이미 있음 → 오케스트레이터 누락. `rr.py set` 이 done 처리 시 state 카운터를 자동 갱신하도록 도구 개선 |
| 전체 | **library-sample 0~8단계 완료**: iteration 8, RR 42(done 41·rejected 1), BE 375·FE 341·통합 150·QA 53 tests, target 커밋 30개, project-agents 커밋 약 80개, LESSONS 약 90건, 총 에이전트 호출 약 70회 | 두 번째 샘플(차세대) 착수 — `docs/samples/sample2-migration-brief.md` |

## 2026-09-21 (저녁) — secu-sample (차세대 migration) 1차 배치

| 단계 | 현상 | 조치 |
|---|---|---|
| stage0 migration | 요구사항 문서 0 → AS-IS 동작 계약에서 REQ 34 채번. 기능 계약 12+분기 44, 공통 인벤토리 73(사용처 0 = 10), SQL 인벤토리 18(A15/B1/C3/D1). **채점표 18/18 포착**, ⚠ 태그로 2단계 함정까지 사전 포착. §11 30건 | 방법론 유효. 두 에이전트 병렬(ingest ‖ sql-migrator) 후 수치 교차 대조가 자연스럽게 됨 — `/stage0` 명령에 "migration 이면 두 에이전트 병렬, 완료 후 statement 수 대조" 명시 |
| stage0 migration | sql-migrator 가 카탈로그에 없는 구문 9개를 스킬에 직접 추가 — "에이전트가 방법론 파일을 갱신" 하는 첫 사례. 위험: 병렬 에이전트가 같은 파일을 고치면 충돌 | 규칙: 스킬 파일 자기 갱신은 `sql-migrator` 의 카탈로그 §2 표에만 허용, append 만, 오케스트레이터가 커밋 |
| stage0 migration | 입력 소스에 운영 DB 비밀번호 평문(profile/prd1) — 에이전트가 값을 산출물에 복사하지 않고 위치만 기록 | `stage0-ingest` §2 에 "AS-IS 설정의 비밀값은 마스킹, 위치만" 명문화(6단계 규칙을 0단계로 앞당김) |
| stage0 migration | §11 30건 중 slice 구조·접근 통제·인증 범위 결정이 stage1 을 막음 — 첫 샘플의 "2단계 전 결정" 이 migration 에서는 **1단계 전**으로 당겨짐 | `/stage0` 명령: migration 이면 stage0 종료 시 "stage1 전 결정 필요" 목록을 따로 제시 |
| stage2 골격 (secu) | Boot 4.0.8 골격 51분·434k 토큰·180 tool call — 첫 샘플 골격의 2배. 원인: Maven 설치·wrapper 생성, Boot 4 패키지 이동·Jackson 3·Security 7 CSRF·Testcontainers 2 등 호환 이슈 8건을 전부 실측으로 해결 | 프로필 "알려진 주의" 에 실측 조합·패키지·CSRF 테스트 패턴 기록 → 다음엔 재발 없음. 골격은 1회성이라 허용 |
| stage2 골격 (secu) | 에이전트가 permitAll 범위를 내 프롬프트(`GET /notices/**`)가 아니라 brief §12-A R11·기능 계약 FC-12(상세·첨부·분류만 공개, 목록은 인증)대로 결정 — 규약 우선순위 작동 | 정상 |

## 2026-09-22 — secu-sample stage2 W1 (domain-notice: sql-migrator convert → reviewer)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage2 convert | Oracle 18 statement 변환 첫 실전: 매핑표 20행 100%, ⚠ 16건 전부 `파일:라인` 근거(reviewer 무작위 대조 16건 일치), MySQL 실측으로 GROUP_CONCAT 절단(1024B) 실제 재현. **채점표 2단계 함정 8/8**. 카탈로그 +4행 | 방법론 유효. 실측 후 ⚠ 결론이 뒤집힌 곳의 **XML 주석**은 옛 결론 그대로 남음 → sql-migrator 규칙 "실측 후 주석 동기화", reviewer "주석↔매핑표 상충 grep" |
| stage2 convert | API·서비스가 없는 **공유 도메인 slice**(domain-notice) 는 developer 단계가 없어 기능 추적표(FB-07~13) 를 아무도 안 만듦 → reviewer FAIL(high). 산출물 경계가 비면 게이트가 통째로 빠진다 | `sql-migrator` 규칙: 공유 도메인 slice 는 convert 가 function-mapping 까지. reviewer D-4 에 "API 없는 slice 도 추적표" 추가 |
| stage2 convert | `USE_YN` → `use_yn`+`del_yn` 분리 후 옵션(`includeDeleted`) 으로 포함시킨 삭제 행을 목록 DTO 가 구분 못 함(delYn 없음) → 관리자 화면 FB-35/36 재현 불가 | 카탈로그 규칙: 컬럼 분리 변환 시 옵션 포함 행을 구분할 컬럼을 행 DTO 에 함께 반환. reviewer 체크 추가 |
| stage2 convert | `SYSDATE → Clock 바인드` 변환에서 `null → CURRENT_DATE` 폴백을 넣음 → 서비스가 Clock 바인드를 빠뜨려도 조용히 통과(§4 now() 금지 우회 경로). 테스트도 고정 기준일과 DB 시계가 한 메서드에 섞임 | 폴백 제거(fail-fast), 카탈로그 행에 권장 명시. 테스트는 시계 경로별로 분리 |
| stage2 convert | 테스트 `@DisplayName` REQ 번호 오연결 3건(트리→REQ-004 상단고정, 페이징→REQ-002 검색) — 8단계 추적표 원천 오염 | sql-migrator·reviewer 에 "REQ 번호 ↔ brief §8 제목 대조". 후보: `tools/trace_check.py` 기계 대조 |
| stage2 convert | 800 이관 대역 번호가 골격 README(notice→file→class) 와 slice 규칙 문서(class→notice→file, FK 순) 에서 다름. FK 순이 맞음 | 프로필: 800 번호는 FK 참조 순으로 골격이 매김. 골격 README 정정은 C-07(공용 파일) |
| stage2 convert | 근거 부족 S-1(collation) 을 매핑표가 `brief §11 "3"` 으로 인용했으나 brief §11 에 항목 자체가 없었음(실제 출처 SQL 인벤토리 §10) → 사람 확인 누락 위험 | brief §11-31 추가. sql-migrator 규칙: §11 에 없는 근거 부족은 "brief §11 후보" 로 분리 보고, 인용은 실제 출처 |
| stage2 convert | 매핑표 행 수 표기 혼선(보고 19 / 실제 20 = fragment 포함) | 통계 형식 고정 "statement N(정의 n + B m) + fragment k = 행 수" |

## 2026-09-22 — secu-sample stage2 W2 (notice user ‖ notice-admin admin)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage2 notice | 다운로드 `Content-Length` 를 DB `file_size` 로 내보냄(AS-IS 는 `realFile.length()`). 통합 테스트가 실물 5B vs fixture 1024 불일치를 만들면서도 헤더를 단언하지 않아 통과 — **테스트가 결함을 재현하고도 못 잡은 사례** | 프로필: `Resource.contentLength()`, 특성화 테스트 "실물 바이트 == Content-Length" 단언 규칙. 추적표에 비기능 세부도 동작 차이로 기록 |
| stage2 notice | 분류 트리 permitAll 을 "근거 부족(N-1)" 으로 올렸으나 brief §12-A R11 이 이미 결정(상태 "확인 요청"). §12-B 만 보고 판단 → 3단계에 불필요한 C-08 | stage2 §B-2-1: 근거 부족 전 §12-A R행(확인 요청 포함) 전부 grep 대조 |
| stage2 notice | 골격 테스트 `UserApplicationTest` 가 "핸들러 없어 404" 를 전제 → slice 가 골격 테스트를 수정하게 됨(공용 규칙 위반 아님이지만 결합) | 골격 §A-8: 빈 상태 전제 금지, "401 아님 + 봉투" 수준 |
| stage2 notice | 한 모듈의 `@SpringBootTest` 2개가 같은 H2 인메모리 DB(`secu_user`) 를 공유해 fixture 누출 → developer 가 IT 의 datasource url 을 `properties` 로 override. **그 override 가 `-Pmysql` 프로파일보다 우선해 웨이브 MySQL 게이트에서 9건 컨텍스트 실패** — 모듈 단위 게이트(H2)만 보고 통과시킨 결함 | 골격 §A-8: URL override 금지, `cleanup.sql` + `@Sql(AFTER_TEST_METHOD)` 패턴. 프로필 "알려진 주의" 에 명시 |
| stage2 병렬 | 두 developer 가 `common-candidates.md` 에 동시에 C-08/09 를 써서 번호 충돌 → admin 이 C-10~13 으로 재번호 | pipeline-core §6: 병렬 웨이브는 C-번호 대역을 프롬프트로 사전 배정 |
| stage2 병렬 | Maven 멀티모듈에서 두 developer 가 각각 `-pl <자기모듈> -am` 으로 common/domain-notice 를 동시 재컴파일 — 이번엔 충돌 없이 통과했으나 `target/classes` 경합 위험 | 관찰 중. 문제 생기면 웨이브 시작 시 오케스트레이터가 `./mvnw -q -pl server/common,server/domain-* install -DskipTests` 후 developer 는 `-am` 없이 || stage2 notice-admin | 통합 테스트의 `(Timestamp) row.get("mod_dt")` 캐스트가 H2 전용 → `-Pmysql` 에서 3/7 error. developer 는 "MySQL 전용 구문 없음" 을 이유로 `-Pmysql` 을 건너뜀 — **SQL 이식성과 테스트 이식성은 별개 축** | 프로필: `queryForObject(sql, LocalDateTime.class)`; reviewer 가 slice IT 를 `-Pmysql` 로 1회 실행. `/stage2` e 항: 게이트에 걸리는 medium 은 같은 단계에서 수정 |
| stage2 notice-admin | 원자성 REQ-020 의 롤백을 목 예외→보상만으로 "증명" — 실제 DB 롤백은 어노테이션 신뢰뿐 | 프로필: 두 번째 INSERT 실제 실패(컬럼 길이 초과) 케이스로 롤백 증명 |
| stage2 도구 | RR 생성 후 본문을 정규식 치환으로 넣다가 백틱이 YAML 을 깨뜨림(`rr.py stats` 전체 실패) | `rr.py new` 에 `--evidence/--description/--fix` 추가, pipeline-core 에 "YAML 문자열 치환 금지" |

## 2026-09-22 — secu-sample stage3 (공통화 회차 1)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage3 | 모듈 간 fixture 공유를 `test-jar` 로 하려다 `./mvnw test`(package 전) 리액터에서 test-jar 의존이 `target/test-classes` 디렉터리 전체로 해석 → `DomainNoticeTestApplication` 이 user IT 의 `@SpringBootConfiguration` 으로 잡혀 9건 오류 | 프로필: test-jar 금지, `maven-resources-plugin` 복사(`copy-shared-fixtures`) — 골격이 user/admin pom 에 미리 넣음 |
| stage3 | C-04 `connection-init-sql: SET SESSION group_concat_max_len` 을 H2 MODE=MySQL 이 거부 | 프로필: test 프로파일 `""` 덮기 + test-mysql 재설정 |
| stage3 | 2단계 RR(공용 `MailMessage` 다수 수신자)을 3단계가 흡수 — 공용 변경은 3단계만 가능하므로 자연스러움 | stage3 스킬 §3: 2단계 RR 중 공용 변경 필요분은 3단계가 흡수하고 `/refactor` 는 slice 잔여만 |
| stage3 | 4분류표 74행 중 대체·개선 8건은 증명 테스트 없음(Hikari 풀·ShedLock·세션 타임아웃·logback 등 설정성) | 5단계 특성화 시나리오 입력으로 넘김(레포트 §7) || stage3 검토 | MySQL 세션 변수 테스트가 1024 로 내린 뒤 원복 안 함 → 풀 커넥션 오염(순서 의존). 3단계 이전엔 "올리기만" 해서 무해했던 것이 갱신으로 방향이 생김 | 프로필: `finally` 원복 규칙. RR-0006 |
| stage3 검토 | 4분류표 증명 테스트 ID 72건 중 1건 오기 — reviewer 가 스크립트 전수 대조로 검출 | stage3 reviewer 체크 5 추가. 문서 정합 low 6건은 RR-0007 로 묶음 |
## 2026-09-22 — secu-sample /refactor iteration 2 (RR-0002~0007)

| 단계 | 현상 | 조치 |
|---|---|---|
| refactor | 3단계가 공용 `MailMessage` 를 고쳐 RR-0002 는 slice 에서 코드 변경 0(테스트·추적표만) — "공용 변경 RR 은 3단계가 흡수" 규칙이 실제로 동작 | 정상. `/refactor` 6항의 "공용 기반으로 해결" 경로 |
| refactor | 오케스트레이터 지시("`<img src=x>` 만 있는 본문 → 400")가 jsoup 실측(`<img>` 태그는 남음)과 어긋남 → developer 가 지시를 따르지 않고 실측대로 2단 테스트 + C-14 로 보고 | 정상(규약 > 프롬프트). 오케스트레이터는 정제기 동작을 단정하지 말고 "정제 후 빈 본문이면 400" 으로만 지시 |
| refactor | 병렬 3 에이전트(2 developer + common 문서)가 파일 경계를 지켜 충돌 0 — RR-0007 처럼 여러 slice 파일에 걸친 문서 RR 은 오케스트레이터가 **항목을 소유 slice 별로 쪼개 배정** | `/refactor` 5항에 문서 RR 분할 규칙 추가 |
| refactor | reviewer 가 만든 일회성 대조 스크립트를 `tools/check_test_ids.py` 로 편입 — 에이전트가 스크래치에 만든 검증 도구는 재사용 후보 | 규칙: reviewer 보고의 스크립트는 오케스트레이터가 tools/ 편입 여부 판단 || refactor 검토 | RR-0004 처리로 `@Size(min=1)` 을 추가 → `@NotBlank` 와 겹쳐 `title:""` 에 fieldErrors 2건(둘째 문구 오안내) — **계약 강화 목적의 수정이 런타임 동작을 바꿈** | 프로필: 계약 강화는 `@Schema(minLength…)` 문서 수단 먼저; Bean Validation 추가 시 `""`·`"  "`·`null` 세 경계 테스트 필수 |
| refactor 검토 | "GET 3개 401/403 누락" RR 을 처리하면서 같은 계약의 POST/DELETE 401 누락은 그대로 — RR 범위 밖이라도 같은 기준으로 전체를 훑어야 | stage2 §D: 같은 종류 누락은 계약 전체 엔드포인트를 대조 |
| refactor 검토 | `check_test_ids.py` 가 추적표 약어(`SvcT`)·`Test.Nested.method`·`reject*` 를 못 읽어 60건 중 5건만 대조하고 "불일치 0"(공허) | 도구: 범례 2형식 파싱·중첩 경로·접두 와일드카드 지원 → 70/70·87/87. reviewer 는 "인용 토큰 수" 가 문서 인용 수와 비슷한지 먼저 확인 |
| refactor 검토 | RR-0007 을 3 에이전트가 나눠 처리한 뒤 yaml 을 닫지 않음 — 오케스트레이터 누락 | `/refactor` 5항 분할 규칙에 "오케스트레이터가 같은 회차에 닫고 note 기록" 이미 명시. reviewer 체크에 "RR status ↔ 작업 트리" 대조 추가 || refactor 검토 반영 | 지시(`@Size(max)`+`@Schema(minLength=1)`)대로 하니 계약이 `minLength: 0` 으로 회귀 — swagger-core 가 `@Size` 존재 시 `@Schema.minLength` 를 무조건 덮어씀(javap 확인). developer 가 `@Length(max)`(Hibernate) 로 우회 | 프로필에 실측 기록. 오케스트레이터 지시도 라이브러리 동작 단정이었음(재발) |
## 2026-09-22 — secu-sample stage4 골격 (pnpm 워크스페이스)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage4 골격 | 36분·329k 토큰·117 tool call. pnpm 12 의 `minimumReleaseAge`·`allowBuilds` 가 설치를 두 번 막음, 최신 메이저가 전부 지정 버전 초과, corepack EPERM, Windows 대소문자 파일명 충돌 | 프로필 "알려진 주의" 에 실측 조합·pnpm 12 규칙 기록 → 다음 골격에서 재발 없음 |
| stage4 골격 | 내 프롬프트의 서버 포트(18080/81)가 틀렸고 에이전트가 yml 실측(18090/91)으로 바로잡음 — 오케스트레이터가 사실을 단정해 지시한 3번째 사례(정제기·swagger·포트) | 규칙: 프롬프트에는 "실측할 파일 경로" 를 주고 값은 단정하지 않는다(pipeline-core §6 developer 프롬프트 규칙) |
| stage4 골격 | auth 계약에 login/me 의 401 응답·문구 미기술 → FE 가 오류 문구를 추정할 수 없어 RR-0008(4→2) | 정상 경로(계약 부족 → RR) |
## 2026-09-22 — secu-sample stage4 W1 (notice-admin admin 앱)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage4 notice-admin | 36분·372k 토큰. ftl 분기 21 ↔ 테스트 대응표, 122 tests. 계약 부족 1(관리자 상세 첨부 다운로드 API 없음 → RR-0009 medium) — 2단계가 admin 상세의 첨부 다운로드를 빠뜨린 것을 FE 가 잡음(사용자 앱 API 를 admin 이 못 씀) | 정상 경로. 교훈: slices.yaml 의 apis 가 "첨부 목록" 만 있고 다운로드가 없었음 → stage1 slice-planner 는 첨부 표시가 있는 화면에 다운로드 API 를 자동 포함 |
| stage4 notice-admin | 에디터 TextAlign 이 SafeHtml 에서 `style` 제거로 표시 안 됨(실측) → developer 가 제외하고 F-25 | 프로필: 허용 마크 3자 동일 원칙 + 실측 규칙 |
| stage4 notice-admin | RHF 체크박스 `value="Y"`, zod 4 refine 미평가, msw+jsdom FormData, react-hooks 7 이름 규칙, date input — 실측 5건 | 프로필 "알려진 주의" |
| stage4 병렬 | 두 FE developer 가 `common-candidates.md` frontend 섹션에 F-1x/F-2x 대역으로 충돌 없이 기록 — 대역 배정 규칙 효과 확인 | 정상 || stage4 notice-admin 검토 | 분기→테스트 대응표 21행 중 1행이 요청 파라미터만 검증하고 렌더 단언 없음(대응표는 채워짐) | stage4 §D-0: 행마다 렌더 단언 확인 |
| stage4 notice-admin 검토 | 인라인 오류 표시 + 공통 토스트 이중 알림(`meta.silent` 누락) — 테스트로 안 잡힘 | §D-0 대조 항목 |
| stage4 notice-admin 검토 | 계약이 오류 코드만 싣고 문구가 없어 FE/서버 문구 갈림(007) — "계약만 보고 개발" 원칙의 구멍 | stage2 §B-5: 오류 코드별 문구를 계약 description 에. RR-0010 |
| stage4 notice-admin 검토 | 골격 SafeHtml 이 서버가 허용하는 `style` 을 지워 에디터 정렬 기능을 빼야 했음 — 3자 동일을 골격 시점에 맞추지 않은 결과 | stage4 §A-6 |
## 2026-09-22 — secu-sample stage4 W1 (notice user 앱)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage4 notice | developer 가 API 서버 오류(529, 500)로 두 번 중단 → `SendMessage` 재개로 같은 컨텍스트에서 이어 완료(산출물 손실 0). 재개 프롬프트에 "작업 트리 상태를 먼저 확인" 을 넣은 것이 효과 | 규칙(pipeline-core §6): 에이전트가 서버 오류로 끊기면 새 에이전트 대신 **재개**(컨텍스트 보존) + "git status 로 상태 복구 후 이어서" 지시 |
| stage4 notice | 계약 7개로 화면 2개 전부 구현, RR 0 — 2단계 notice 계약이 충분했음(admin 은 다운로드 누락) | — |
| stage4 notice | msw 선등록 우선(`/:id` 가 `/top` 가로챔), user-event 앵커 click 목, 도구의 ` ` 이스케이프 변환 — 실측 3건 | 프로필 "알려진 주의" |
| stage4 notice | 테스트가 실제 결함 1건 발견(react-query `onSuccess` 2번째 인자를 잘못 넘김) | 정상 || stage4 notice 검토 | 분류 change·정렬·페이지 이동이 URL 값만 merge → 입력 중 검색어 유실. AS-IS 는 `form.submit()` 으로 폼 전체 전송 — "스크립트 동작 매핑" 에 **전송 필드 범위**가 빠져 있었음 | 프로필: 매핑표에 전송 필드 범위 열 |
| stage4 notice 검토 | `pnpm test -- --run <경로>` 의 `--` 가 vitest 필터를 무효화(전체 실행) — 프로필·pipeline-core 예시가 틀렸음(F-17 실측 재현) | 모든 pnpm 예시에서 `--` 제거, 프로필에 금지 명시 |
| stage4 notice 검토 | 운영 QueryClient `retry: 1` 이 404 도 재시도 → AS-IS 즉시 오류 화면과 1초 차이 | 프로필: 단건 조회 404 재시도 제외 |
| stage4 notice 검토 | `meta.silent` 누락이 admin(목록)·user(목록) 두 slice 에서 반복 — 상세는 맞고 목록만 빠짐 | §D-0: alert 렌더 컴포넌트의 query 전수 grep |
## 2026-09-22 — secu-sample stage5 (domain-notice, 환경 구축)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage5 domain-notice | 31분·277k 토큰·92 tool call: MySQL 8.4 도커 + jar 2개 + Playwright 환경 구축, 시나리오 39(a17/q13/c8+1 미실행) 전부 통과, SQL A 15/15 커버, 4분류표 미증명 9건 중 8건 실측 증명(GROUP_CONCAT 절단·init-sql·세션 TZ·socketTimeout×2·ShedLock 단일 실행·DB_PASSWORD 미설정 exit) | 정상. 환경 스크립트는 다음 slice 가 재사용 |
| stage5 domain-notice | 특성화 테스트를 실 DB 로 돌리려다 `-am` 이 common 테스트를 끌고 와 `tb_user` 를 지움(RR-0013) — 테스트 자체의 데이터 파괴성 | 스킬 §2 실측 (b): slice 패키지 제한 + COUNT 확인. common 테스트 격리는 RR |
| stage5 domain-notice | surefire `-Dtest` 점 표기가 0건 매칭인데 성공으로 지나감 | 스킬 §2 실측 (a) |
| stage5 domain-notice | COLLATION 근거 부족 S-1 이 "검색" 만 다뤘는데 **정렬**(TITLE ORDER BY)도 ai_ci 로 AS-IS BINARY 와 달라짐을 5단계 실측이 발견 → RR-0012 | migration-sql 카탈로그 COLLATION 태그에 "정렬도 영향" 명시 || stage5 notice | 31분·329k 토큰: E2E(Chromium→Vite→jar→MySQL) 58 시나리오 전부 통과, 계약 드리프트 0. 첫 실패 3건은 테스터 기대값 오기(한글 정렬·URL 정규화) | 정상 |
| stage5 notice | 로그인 계정이 seed 어디에도 없어 5단계가 fixture 로 해시를 UPDATE — 골격이 테스트 계정 seed 를 제공했어야 | stage2 골격 §A-8 추가 |
| stage5 notice | `/auth/csrf` 본문 토큰(XOR 마스킹)을 헤더로 보내면 403 — 계약 문구가 실제와 어긋남(RR-0015). 브라우저 경로는 쿠키를 읽어 정상 | 스킬 §2 실측 (c) |
| stage5 notice | 개발 PC 5173 점유 → 포트 변수화로 회피(다른 프로세스 죽이지 않음) | 스킬 §2 실측 (a) || stage5 notice-admin | 90분·471k 토큰·137 tool call(가장 무거운 slice). **등록 화면이 실제 브라우저에서 로드 즉시 크래시**(Tiptap `useEditor` 경합, RR-0017 high, 운영 빌드도 재현) — 4단계 jsdom 단위 테스트 122건이 전부 통과했음에도 | stage4 §C: DOM/타이머 의존 서드파티 컴포넌트는 Chromium 렌더 스모크 게이트. 프로필에 원인·회피 기록 |
| stage5 notice-admin | 서블릿 multipart 한도가 slice 검증(007)보다 먼저 걸려 `COMMON_413` — 2단계 테스트는 서비스 단위라 도달 불가를 못 봄(RR-0018) | stage2: 파일 크기 검증은 서블릿 한도와의 순서를 계약에 명시(어느 코드가 나가는지) |
| stage5 notice-admin | 만료 배치·보상 삭제·실패 메일을 트리거 SIGNAL·cron 덮어쓰기로 실측 — 5단계가 "증명 없음" 항목을 실제로 닫는 방법 확립 | 스킬 §2 실측 (c)(d) |
| stage5 notice-admin | 리치텍스트 3자 정합 실측: 서버는 `style` 보존, user SafeHtml 이 제거 → 관리자가 넣은 정렬이 사용자에겐 안 보임(F-25 실증) | 3단계/골격 후보 유지, stage4 §A-6 |
## 2026-09-22 — secu-sample /refactor iteration 3 (stage3 common 묶음)

| 단계 | 현상 | 조치 |
|---|---|---|
| refactor common | 5단계 RR 4건(계정 seed·DB_PASSWORD fail-fast·csrf 마스킹·테스트 데이터 파괴) 이 전부 **골격이 처음부터 갖췄어야 할 것** — 통합 테스트가 골격 결함을 드러냄 | 프로필 "알려진 주의" 에 골격 기본으로 승격(EnvironmentPostProcessor·TestAccountSeeder·csrf 쿠키 우선) |
| refactor common | 3단계가 `apps/shared`(FE 공용)도 수정 — 공용 소유 원칙이 FE 에도 적용됨을 확인 | stage3 스킬: 공용 범위 = `server/common` + `apps/shared` + 루트 설정 |
| refactor common | Boot 바인더가 미해석 플레이스홀더를 리터럴로 넘김(실측) | 프로필 || refactor notice-admin BE | 오류 문구를 계약에 싣는 규칙을 "컴파일 상수 `Msg` 클래스 + 리플렉션 대조" 로 구현해 문구 드리프트를 구조적으로 차단 — 좋은 패턴 | stage2 §B-5 규칙으로 승격 |
| refactor notice-admin BE | 서블릿 multipart 한도가 slice 검증보다 먼저(013→413) — 2단계는 MockMvc 라 못 보고 5단계 실측이 잡음. 계약을 실제대로 정정, yml 상향은 사람 결정(C-15) | 프로필 |
| refactor notice-admin BE | Bash 도구가 `\` 를 한 번 접어 정규식 `\s` 가 깨진 사고 1회 → Edit 도구로 교정 | 메모리 [[bash-heredoc-size-limit]] 와 같은 계열: 백슬래시·특수문자 포함 코드는 Write/Edit || refactor notice-admin FE | RR-0017 원인을 tiptap 소스로 확정(`immediatelyRender` + `scheduleDestroy` 1ms 경합). jsdom 은 재현 불가를 프로브로 실측 → "판별력 없는 테스트는 채택하지 않음" 정직 기록. Chromium 스모크 수정 전 2/2 실패·후 2/2 통과로 판별력 증명 | 프로필 원인·수정·게이트 방법 확정. 공용 후보 F-27(Tree aria-disabled 상속)·F-28(Playwright 공용 설정) |
| refactor iter3 전체 | RR 12건 → 3묶음 순차(3→2→4)로 처리, 전체 게이트 BE 226·FE 314. 3단계 변경(csrf.ts)이 4단계 테스트 1건을 깨뜨림(목 갱신) — 순서 3→2→4 가 맞았음 | `/refactor` 5항 순서 규칙 유효 || refactor iter3 BE 검토 | `EnvironmentPostProcessor` 를 Boot 4 에서 deprecated(forRemoval) 구 패키지로 구현 — 컴파일·jar 실측 모두 성공해 developer 가 못 봄, reviewer 가 javap 로 검출. 배선 테스트도 없어 회귀 시 조용히 꺼짐 | 프로필: SPI 새 패키지·javap 확인·배선 테스트 게이트 |
| refactor iter3 BE 검토 | 오류 문구 상수화가 enum 코드까지만이고 Bean Validation `message=` 5종은 리터럴 3중 복제 — RR-0010 원 결함(문구 갈림)의 잔여 경로 | stage2 §B-5 확장(`Msg.FIELD_*`) |


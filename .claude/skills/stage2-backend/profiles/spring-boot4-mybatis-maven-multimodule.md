# Backend 프로필: spring-boot4-mybatis-maven-multimodule

`config/project.yaml → stack.backend.profile: spring-boot4-mybatis-maven-multimodule`. 차세대(migration) 프로젝트용 — Java 21 / Spring Boot 4.0.x / Maven Wrapper 멀티모듈 / MyBatis / MySQL 8.4 / Flyway / **Spring Security 세션 + CSRF**.
`spring-mybatis-mysql.md` 의 규칙(REPEATABLE READ·갭 잠금·LIKE `!`·타임아웃 실측·Clock·시간 폭탄·계약 required 등)은 **그대로 상속**하고, 아래는 차이점만 적는다.

## 기본 구조 (Maven 멀티모듈 + 모노레포)
```
<target_dir>/
├── pom.xml                      부모 POM (Boot 4.0.x parent, dependencyManagement, 모듈 3개)
├── mvnw, mvnw.cmd, .mvn/
├── server/
│   ├── common/                  공용: 응답·예외·보안·감사·유틸·M-38 컬럼 매핑. slice 코드 없음
│   ├── user/                    사용자 앱 (jar, main 클래스) — 사용자 slice 패키지
│   └── admin/                   관리자 앱 (jar, main 클래스) — 관리자 slice 패키지
├── db/migration/                Flyway: V1_0_<대역><번호>__<slice>_<설명>.sql (대역 100~800, §Flyway)
├── docs/api/<slice>.yaml        계약 (springdoc, 그룹 = slice, user/admin 앱 각각에서 dump)
└── apps/                        프론트 pnpm 워크스페이스 (react19-vite-tailwind-pnpm 프로필)
```
- slice 는 `user` 또는 `admin` 모듈 중 **소유 모듈 하나**에만 코드를 둔다(양쪽에 걸치면 slice 를 나눈다). 두 앱이 공유하는 도메인 코드는 `common` 이 아니라 **`server/domain-<slice>`** 모듈로 분리(common 은 업무 지식이 없어야 함).
- 패키지: `<base_package>.<slice>.{controller,service,mapper,dto,domain,exception}` (하이픈 제거). Mapper XML 은 모듈의 `src/main/resources/mapper/<slice>/`.
- 빌드·테스트 명령:
  ```
  ./mvnw -q -pl server/common,server/user,server/admin -am verify -DskipTests   # 빌드
  ./mvnw -q -pl server/user test -Dtest='com.example.**.<slice>.*'             # slice 테스트
  ./mvnw -q test                                                               # 전체 (surefire: target/surefire-reports/TEST-*.xml)
  ./mvnw -q test -Pmysql                                                       # testcontainers 프로파일
  ```
  reviewer 는 `-Dsurefire.useFile=false` 없이 XML 합계로 판정. Maven 은 UP-TO-DATE 가 없으므로 `cleanTest` 불필요.

## 규약 차이
- **인증**: Spring Security **세션**(JSESSIONID, `SessionCreationPolicy.IF_REQUIRED`) + **CSRF 활성**(`CookieCsrfTokenRepository.withHttpOnlyFalse()`, 헤더 `X-CSRF-TOKEN`). JWT 쿠키 골격은 쓰지 않는다. 로그인은 `/api/v1/auth/login` JSON(폼 로그인 아님) → 세션 생성 + CSRF 토큰 쿠키 갱신. 로그아웃은 세션 무효화. 비활성·잠금 즉시 반영은 세션 저장소에서 사용자 상태 재조회(요청당 1회) 또는 `SessionRegistry` 로 세션 만료.
- **메뉴 권한**: 롤 ∪ 사번 허용 목록 — `common` 에 `MenuAuthorizationManager`(메뉴 코드 ↔ URL 패턴 ↔ 롤/사번 표, DB 코드마스터) 를 두고 `@PreAuthorize("@menuAuth.allowed('MENU_CD')")` 로 쓴다. 롤만으로 부족한 요구가 AS-IS 에 있으면 사번 허용 목록을 유지한다.
- **M-38 표준 컬럼**: 모든 테이블 `use_yn CHAR(1) DEFAULT 'Y'`, `del_yn CHAR(1) DEFAULT 'N'`, `reg_id VARCHAR(20)`, `reg_dt DATETIME`, `mod_id`, `mod_dt`. `Auditable` 은 이 이름으로 매핑(`created_*` 아님). AS-IS 의 제각각 감사 컬럼은 매핑표에서 표준 컬럼으로 **이름 변환**하고 값은 이관 규칙 명시.
- **논리 삭제**: `del_yn='Y'`. 모든 조회는 `del_yn='N'` 조건 (Mapper `<sql id="notDeleted">` fragment).
- **코드마스터**: 업무 구분 숫자 코드(AS-IS `wj_class_id` 류)는 코드마스터 `<GROUP>_CD` 로 치환. 매핑표에 숫자→코드 대응.
- **Flyway 대역**: `db/migration/<대역>/V1_0_<대역><NNN>__<slice>_<설명>.sql` — 100 공통/코드마스터, 200 사용자·인증, 300~700 업무 slice(slices.yaml 의 순서대로 배정), 800 데이터 이관·보정(번호는 **FK 참조 순 — 부모 테이블 먼저** 로 골격이 매기고, slice 규칙 문서가 골격 README 와 다르면 "지시와 다른 결정" 으로 명시). `flyway.locations` 에 폴더 전부 나열. 대역은 slice 마다 하나씩 고정해 병렬 충돌을 없앤다.
- **외부 연동**: `RestClient` 빈(공용 `RestClientConfig`: 타임아웃·로깅 인터셉터·traceId 전파). AS-IS Axis/Jersey/httpclient3 호출은 **소스가 들어온 것만** RestClient 로 치환하고, WSDL 기반 SOAP 은 `spring-ws` 또는 최소 XML 템플릿으로(매핑표에 결정 기록).
- **메일**: 소스가 들어오면 `MailPort` 인터페이스 + 구현(MGS API)로 치환, 템플릿은 DB 테이블. 소스 없으면 범위 외.
- **파일 업로드**: 1단계 저장 `{base}/{구획}/yyyy/MM/dd/FILE_<yyyyMMddHHmmssSSS>_<8hex>.<ext>`, 웹 문서루트 밖, 원본 파일명은 DB 에만. AS-IS 2단계(temp→renameTo) 경로·`wj_class_id` 폴더는 매핑표에 "폐기, 파일 이관 규칙".
- **XSS**: lucy-xss 필터는 **대체** — 응답은 React 가 이스케이프, 저장 시 서버 검증기(`HtmlContentValidator`: 허용 태그 화이트리스트, jsoup Safelist). 리치텍스트 필드에만 적용.
- **로깅**: Boot 로깅 + p6spy(SQL 바인딩 로그, `local`/`dev` 만) + traceId(MDC) + 외부 연동 호출 로그(요청/응답 요약, 민감정보 마스킹) + 파일 롤링(logback-spring).
- **스케줄러**: 소스가 들어온 것만 `@Scheduled(cron = "${app.schedule.<name>}")` + `@SchedulerLock`(ShedLock, 다중 인스턴스 대비) 로 치환. XML 스케줄러 설정은 매핑표에 job 단위로.
- **프로파일**: `local`·`ingdev`·`dev`·`prd`. 비밀값은 환경변수. AS-IS `profile/` 폴더·개인 폴더는 매핑표에 "폐기".
- **테스트**: JUnit 5 + Mockito + `@MybatisTest`(H2 MODE=MySQL) + testcontainers(mysql:8.4, `-Pmysql`) + `@WebMvcTest` + `@SpringBootTest`. 목표 커버리지는 근거 없으면 강제하지 않되 **AS-IS 특성화 테스트**(migration-sql·기능 추적표) 는 게이트.

## MyBatis (migration 핵심)
- **SqlSession 직접 호출 금지** — 모든 SQL 은 Mapper 인터페이스 메서드. AS-IS `sqlSession.selectList("ns.id")` 는 인벤토리(`migration-sql` 스킬)로 전수 치환하고, 미정의 id 는 RR(high).
- Mapper XML `namespace` = 인터페이스 FQCN, statement id = 메서드명. `resultType` 은 DTO(record 허용), 컬럼 매핑은 `map-underscore-to-camel-case` + Oracle 대문자 컬럼 별칭 제거.
- Oracle 방언은 `migration-sql` 카탈로그대로 변환하고 statement 마다 매핑표에 "사용 구문 → 변환 → 의미 차이 태그" 기록.
- `${}` 금지(정렬 화이트리스트 예외), LIKE `ESCAPE '!'`, 페이징은 `LIMIT #{size} OFFSET #{offset}`(ROWNUM 이중 서브쿼리 폐기), 시퀀스는 AUTO_INCREMENT(`useGeneratedKeys`) 또는 시퀀스 테이블(멀티 인스턴스 채번이 필요할 때만).

## OpenAPI
- springdoc 3.x(Boot 4 호환) — `springdoc.api-docs.version: openapi_3_0` 고정, 그룹 = slice, user/admin 앱 각각 `openApiDump` 태스크(Maven exec plugin). operationId `<동사><명사>`, 응답 DTO `requiredMode=REQUIRED`.

## 알려진 주의 (Boot 4.0.8 실전, 2026-09-21)
- 실측 버전 조합: Boot 4.0.8 / Spring 7.0 / Security 7.0 / **Jackson 3**(`tools.jackson.*`, `JacksonException.getPath()`) / Flyway 11 / Testcontainers **2.x**(`testcontainers-mysql` 아티팩트) / springdoc **3.0.x**(3.1 은 Boot 4.1) / mybatis-spring-boot 4.0.x / p6spy starter 2.0 / ShedLock 7.
- 패키지 이동: `ErrorController` → `org.springframework.boot.webmvc.error`, `@WebMvcTest` 등 → `org.springframework.boot.webmvc.test.autoconfigure` + 모듈형 테스트 스타터, `RestClientCustomizer` → `org.springframework.boot.restclient`.
- **Security 7 CSRF**: `csrf.spa()` 는 헤더를 원문 토큰으로 비교 → 테스트에서 `csrf().asHeader()`(XOR 마스킹) 는 403. 실제 쿠키/헤더 왕복(`realCsrf()` 패턴)으로 테스트. 로그인 후 재발급 CSRF 쿠키는 지연 생성이라 컨트롤러에서 `getToken()` 1회 호출.
- `SpringApplicationBuilder.properties()` 는 yml 에 덮인다 → 포트는 `--server.port` 명령행 인자.
- 계약 yaml 한글 깨짐 → 바이트로 저장 + `springdoc.default-produces-media-type`. 계약 생성: `./mvnw -q -pl server/<app> -am -DskipTests test-compile exec:exec@openApiDump -DapiGroup=<slice> -Dport=1809N`.
- `mvn` CLI 없으면 Maven 바이너리를 `C:/tools/apache-maven` 에 받아 `mvn -N wrapper:wrapper` 로 `mvnw` 생성(이후 `./mvnw` 만). 첫 골격은 의존성 다운로드 포함 **약 50분** — 예산에 반영.
- `JdbcTemplate.queryForMap` 의 DATETIME 은 H2=`Timestamp`, Connector/J=`LocalDateTime` → 테스트는 `queryForObject(sql, LocalDateTime.class)` 로 읽는다(캐스트 금지). developer 가 "MySQL 전용 구문 없음" 을 이유로 `-Pmysql` 을 건너뛰어도 reviewer 는 그 slice 의 `@SpringBootTest` 를 `-Pmysql -Dtest=<IT> -Dsurefire.failIfNoSpecifiedTests=false` 로 1회 돌린다 — SQL 이식성과 테스트 이식성은 별개.
- 테스트 클래스의 `properties="spring.datasource.url=…"` override 금지(`test-mysql` 프로파일을 덮어 MySQL 게이트가 깨짐). fixture 격리는 `cleanup.sql` + `@Sql(AFTER_TEST_METHOD)`.
- 원자성 REQ(공지+첨부 한 트랜잭션 류)는 목 예외→보상 테스트만으로 부족 — 실제 DB 에서 두 번째 INSERT 를 실패시켜(컬럼 길이 초과 등) 롤백을 증명한다.
- `@WebMvcTest` 는 `@Import({SecurityConfig, MenuAuthorizationManager})` + `authentication(LoginUser)`; DTO 는 record 그대로 `resultType`.

## 알려진 주의
- Boot 4.0: Jakarta EE 11, Spring Framework 7 — `HttpStatusCode`, `RestClient` 기본, `@MockitoBean`. Boot 3.x 용 서드파티(springdoc 2.x, p6spy-spring-boot-starter 구버전)는 4.x 대응 버전으로.
- Maven 멀티모듈 병렬 developer: 각 slice 는 자기 모듈의 자기 패키지·XML·Flyway 대역만. 부모 POM·common·`mvnw` 는 공용. 전체 `./mvnw test` 는 웨이브 종료 후 1회.

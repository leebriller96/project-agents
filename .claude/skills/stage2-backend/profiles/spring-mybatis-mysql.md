# Backend 프로필: spring-mybatis-mysql

`config/project.yaml → stack.backend.profile: spring-mybatis-mysql` 일 때 적용한다. 버전은 config 값을 우선한다.

## 기본 의존성 (Gradle 기준)
- spring-boot-starter-web, -validation, -security(인증 골격), -actuator
- mybatis-spring-boot-starter, mysql-connector-j, flyway-core + flyway-mysql
- springdoc-openapi-starter-webmvc-ui (계약 생성·확인용)
- 테스트: spring-boot-starter-test, mybatis-spring-boot-starter-test, testcontainers(mysql) — 도커가 없으면 H2 `MODE=MySQL` 로 폴백하고 레포트에 명시
  - **Docker Engine 29+ (API 1.55) 는 testcontainers ≥ 1.21.4 필요.** Boot 3.3 BOM 의 1.19.x 는 `NpipeSocketClientProviderStrategy ... Status 400` 으로 실패 → `gradle.properties` 또는 `ext["testcontainers.version"]="1.21.4"` 로 상향
  - 기본 실행은 H2(빠름), `-Pmysql` 프로퍼티로 testcontainers 프로파일 전환하는 구성을 권장
- lombok (선택, brief 컨벤션에 따름)

## 패키지 구조
```
<base_package>/
├── common/
│   ├── response/   ApiResponse<T>, PageResponse<T>
│   ├── exception/  ErrorCode(enum), BusinessException, GlobalExceptionHandler
│   ├── config/     WebConfig, MyBatisConfig, SecurityConfig, OpenApiConfig, ClockConfig(Clock 빈)
│   ├── security/   JWT 필터·인증 유틸 (brief 에 인증 방식이 있을 때)
│   ├── logging/    요청/응답 로깅 필터, MDC 트레이스 ID
│   └── util/
└── <slice>/
    ├── controller/ <Slice>Controller
    ├── service/    <Slice>Service (인터페이스 없이 클래스 우선; 다른 slice 가 호출할 때만 인터페이스 분리)
    ├── mapper/     <Entity>Mapper (인터페이스) + resources/mapper/<slice>/<Entity>Mapper.xml
    ├── dto/        요청 <Xxx>Request, 응답 <Xxx>Response
    └── domain/     <Entity> (테이블 매핑 POJO)
```
slice id 의 하이픈은 패키지에서 제거한다 (`common-auth` → `commonauth`).

## 규약
- 응답: 성공 `{ "success": true, "data": ..., "error": null }`, 실패 `{ "success": false, "data": null, "error": { "code": "ORDER_001", "message": "..." } }`.
- 에러 코드: `<SLICE>_<3자리>`. `ErrorCode` enum 에 HTTP 상태를 함께 정의.
- 페이징: 요청 `page`(1부터)·`size`, 응답 `PageResponse { items, page, size, total }`.
- 감사 컬럼: `created_at, created_by, updated_at, updated_by` 를 모든 테이블에. MyBatis 인터셉터 또는 서비스에서 세팅.
- 네이밍: 테이블·컬럼 `snake_case`, Java `camelCase`, `map-underscore-to-camel-case: true`.
- MyBatis: XML 매퍼 사용. `#{}` 만 사용, `${}` 는 정렬 컬럼 화이트리스트 검증 후에만. `<if>/<choose>` 동적 SQL 허용.
- 트랜잭션: 서비스 메서드에 `@Transactional`, 조회는 `readOnly = true`.
- 검증: DTO 에 `jakarta.validation` 어노테이션. 검증 실패는 GlobalExceptionHandler 가 `COMMON_400` 으로 변환.
- 설정: `application.yml` + `application-local.yml`, 비밀값은 환경변수 참조 (`${DB_PASSWORD}`), 파일에 직접 쓰지 않는다.
- Flyway: `db/migration` 을 `spring.flyway.locations` 로 지정. 골격 `V0001__baseline.sql`, slice 는 `V<yyMMddHHmm>__<slice>_*.sql`.
- OpenAPI: springdoc 으로 `/v3/api-docs` 생성 → `docs/api/<slice>.yaml` 로 저장(태그 = slice). 손으로 보완한 설명은 코드의 `@Operation/@Schema` 에 넣어 재생성해도 유지되게 한다.
  계약 생성용 기동은 **test 프로파일(H2)** 로 하고(MySQL 불필요), `OpenApiConfig` 의 `servers` 는 상대경로 `/` 로 고정해 포트가 yaml 에 남지 않게 한다.
- JWT(jjwt 0.12+): 알고리즘을 `Jwts.SIG.HS256` 으로 **명시** (키 길이에 따라 HS384/512 로 자동 선택됨). 골격은 `Clock` 빈을 제공해 시간 의존 로직(잠금·만료)을 테스트에서 고정할 수 있게 한다.
- 실패 카운터처럼 예외를 던지면서도 남겨야 하는 갱신은 `@Transactional(noRollbackFor = BusinessException.class)` 또는 `REQUIRES_NEW`.
- developer 의 게이트는 빌드+단위테스트까지. 실제 DB 기동 + curl smoke 는 선택이며 레포트에 "게이트 외 검증" 으로 구분 표기 (5단계와 중복 방지).

## 빌드·테스트 명령
```
cd <target_dir>/backend
./gradlew build -x test     # 빌드 (Windows: gradlew.bat)
./gradlew test              # 단위테스트
./gradlew test --tests "<base_package>.<slice>.*"   # slice 만
```
Maven 이면 `./mvnw -q verify`, `-Dtest=...`.

## 단위테스트 규약
- Service: Mockito 로 Mapper 를 목킹. `@DisplayName("REQ-011 재고 부족 시 주문 불가")`.
- Mapper: `@MybatisTest` + testcontainers(mysql) 또는 H2 MySQL 모드. Flyway 로 스키마 적용.
  `@MybatisTest` 는 DataSource 를 임베디드로 교체하므로 `application-test.yml` 에 `spring.test.database.replace: none` 필수.
- Controller: `@WebMvcTest` + MockMvc. 검증 실패·에러 응답 포맷 확인.
  `@WebMvcTest` 는 SecurityConfig 를 자동 스캔하지 않음 → `@Import({SecurityConfig, JwtTokenParser})` 표준 패턴을 골격이 `JwtTestSupport` 로 제공하고 slice 테스트는 그것을 쓴다.
  JWT 필터는 `@Component` 로 두지 말고 SecurityConfig 안에서 직접 생성 (서블릿 필터 중복 등록 방지).

## 골격 설계 메모 (병렬 개발 친화)
- `ErrorCode` 는 **인터페이스**, slice 마다 `enum <Slice>ErrorCode implements ErrorCode` — 공용 enum 을 여러 slice 가 동시에 고치는 충돌을 없앤다.
- springdoc 그룹을 slice 별로 미리 등록해 두면 slice 는 `docs/api/<slice>.yaml` 을 자기 그룹에서 뽑을 수 있다.
- 소스 파일은 Write 도구로 작성 (Bash heredoc 다중 파일은 길이 제한으로 실패).

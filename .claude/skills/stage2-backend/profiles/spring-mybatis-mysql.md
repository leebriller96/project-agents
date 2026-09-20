# Backend 프로필: spring-mybatis-mysql

`config/project.yaml → stack.backend.profile: spring-mybatis-mysql` 일 때 적용한다. 버전은 config 값을 우선한다.

## 기본 의존성 (Gradle 기준)
- spring-boot-starter-web, -validation, -security(인증 골격), -actuator
- mybatis-spring-boot-starter, mysql-connector-j, flyway-core + flyway-mysql
- springdoc-openapi-starter-webmvc-ui (계약 생성·확인용)
- 테스트: spring-boot-starter-test, mybatis-spring-boot-starter-test, testcontainers(mysql) — 도커가 없으면 H2 `MODE=MySQL` 로 폴백하고 레포트에 명시
- lombok (선택, brief 컨벤션에 따름)

## 패키지 구조
```
<base_package>/
├── common/
│   ├── response/   ApiResponse<T>, PageResponse<T>
│   ├── exception/  ErrorCode(enum), BusinessException, GlobalExceptionHandler
│   ├── config/     WebConfig, MyBatisConfig, SecurityConfig, OpenApiConfig
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
- Controller: `@WebMvcTest` + MockMvc. 검증 실패·에러 응답 포맷 확인.

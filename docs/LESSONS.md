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

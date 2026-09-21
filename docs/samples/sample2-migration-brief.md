# 두 번째 샘플 — 차세대(migration) 프로젝트 사전 정보

> 사용자 제공(2026-09-21). library-sample(greenfield) 완료 후 착수. **원칙**: 아래 차이 중 기능·서버·배포 변경은 배경 정보일 뿐이고,
> 파이프라인이 책임지는 것은 `workspace/00_inputs/asis/` 에 **실제로 들어온 소스**가 TO-BE 로 어떻게 바뀌는가다.
> 어떤 기능이 새로 도입되든 해당 AS-IS 소스가 0개면 범위 밖. 소스가 들어온 것만 매핑·변환·검증한다.

## AS-IS (tsecu-portal) ↔ TO-BE (sk-secu-pkg)

| 구분 | AS-IS | TO-BE |
|---|---|---|
| Java | 1.8 | 21 |
| 백엔드 프레임워크 | Spring 5.3.12 (Boot 아님, 모듈별 jar 선언) | Spring Boot 4.0.6 |
| 설정 방식 | XML(dispatcher-servlet·servlet-context·scheduler-base-servlet) + .properties | application-{프로파일}.yml + @Configuration |
| 환경 분리 | profile/ 폴더(local·dev·prd1·prd2, 개인 폴더 혼재) | Spring 프로파일(local·ingdev·dev·prd) |
| 빌드 | Jenkins ant build, pom.xml 병존 | Maven Wrapper 멀티모듈(common·user·admin) + pnpm 워크스페이스 |
| 저장소 구조 | WAR 하나에 사용자·관리자 화면 동거 | 모노레포: BE·FE 모두 user/admin 분리, 공용 server/common·apps/shared |
| 화면 렌더링 | 서버 렌더링: FreeMarker .ftl 492개 + SiteMesh | SPA: React 19 + Vite 7 + TypeScript 5.9 |
| 화면 라이브러리 | jQuery 혼재(1.7·1.8·1.12·latest), jQuery UI, dataTables, AUIGrid, FusionCharts, dtree | Tailwind 3, 자체 공용 컴포넌트(Figma 기준) |
| 에디터 | CKEditor + SmartEditor2 | Tiptap + 마크다운 에디터 |
| 화면↔서버 통신 | 폼 전송 + jQuery Ajax, 컨트롤러가 뷰 이름 반환 | REST JSON + ApiResponse 봉투, axios 인터셉터, SSE(AI 초안) |
| 인증 | LoginCheckInterceptor(세션 체크) | Spring Security 세션 + CSRF(X-CSRF-TOKEN) + 메뉴 권한(롤 ∪ 사번) |
| DB 접근 | MyBatis 3.4.1 + mybatis-spring 1.3, commons-dbcp 1.4 | MyBatis Spring Boot Starter (HikariCP) |
| DB | MySQL(+ Oracle ojdbc8·MSSQL sqljdbc4 드라이버, PostgreSQL 매퍼 설정) | MySQL 8.4 |
| 스키마 관리 | 없음 | Flyway(V1_0_xxx, 폴더 대역 100~800) |
| DB 컬럼 규칙 | 테이블마다 제각각 | M-38 표준 컬럼(use_yn·del_yn·reg_*·mod_*) |
| 업무 구분 | 숫자 코드 wj_class_id 가 결재선·알림·저장 폴더까지 관여 | SR 에서는 미사용. 카테고리는 코드마스터 INQUIRY_CLASS_CD |
| 외부 연동 | Axis(SOAP/WSDL), Jersey, commons-httpclient 3.0 | Spring RestClient: AI 초안·개인정보 탐지(M2M 토큰)·MGS 메일 |
| 메일 | javax.mail 직접 발송 | MGS API + DB 템플릿(wf_wj_mail_template) |
| 파일 업로드 | 2단계(temp → renameTo), {경로}/{wj_class_id}/FILE_시각, 이름 충돌 가능 | 1단계, {base}/{구획}/yyyy/MM/dd/FILE_시각17_8hex.ext, 웹 문서루트 밖 |
| XSS 방어 | lucy-xss 필터 | React 이스케이프 + 서버 검증(NoticeContentValidator 등) |
| 로깅 | log4j 1.x/2.x 혼재 + log4jdbc | Spring Boot 로깅 + p6spy, traceId, 외부 연동 호출 로그, 파일 롤링 |
| 스케줄러 | XML 스케줄러 설정(Quartz 주석) | @Scheduled + cron 설정값 |
| 테스트 | junit 의존성만, 사실상 없음 | 자동 테스트 약 1,000건 |
| 신규 기능 | 없음 | AI 답변 초안(SSE), 개인정보 자동 탐지, 동시수정 잠금 등 — **AS-IS 소스 0 → 파이프라인 범위 밖** |

## 파이프라인에 미치는 영향 (착수 전 준비 항목)

1. **새 프로필 2개**: backend `spring-boot4-mybatis-maven-multimodule`(Java 21, Boot 4.0.x, Maven Wrapper 멀티모듈 common/user/admin, Spring Security 세션+CSRF, HikariCP, Flyway 대역 규칙, M-38 표준 컬럼, RestClient, p6spy), frontend `react19-vite-tailwind-pnpm`(pnpm 워크스페이스 user/admin/shared, Tailwind 3, Tiptap, axios 인터셉터+CSRF 헤더, SSE 클라이언트). 기존 `spring-mybatis-mysql`·`react-ts` 는 그대로 두고 신규 파일.
2. **migration 모드 경로 첫 실전**: stage0 `ASIS_INVENTORY`(XML 설정·ftl 492·jQuery·MyBatis 3.4 매퍼 인벤토리), stage1 slice(AS-IS 패키지/ftl/테이블 기준), stage2 매핑표(테이블·컬럼 M-38 변환 규칙, 프로그램 ftl→React 화면, 컨트롤러 뷰반환→REST), stage4 화면 근거는 **ftl 이 곧 화면 근거**(피그마 없을 수 있음).
3. **변환 규칙을 brief §12 에 사전 기록**: 위 표의 각 행이 "소스가 들어왔을 때 어떻게 바꿀지" 규칙. 소스 없는 행은 "범위 외(소스 미입력)".
4. **workspace 격리**: 현재 `workspace/` 는 단일 프로젝트 구조 → `workspace/<project>/` 로 바꾸고 library-sample 을 그 아래로 이동(pipeline-core·tools 경로 갱신). 두 번째 샘플 착수 시 첫 작업.
5. 입력으로 받을 것: AS-IS 소스(일부라도 — 예: 업무 1~2개의 컨트롤러·서비스·매퍼·ftl·DDL), TO-BE 요구/화면 자료(있으면), 위 표(→ `04_환경정보`·`§12` 원천).

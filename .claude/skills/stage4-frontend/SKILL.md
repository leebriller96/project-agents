---
name: stage4-frontend
description: 4단계 Frontend 개발 — 피그마/스토리보드와 slice 의 OpenAPI 계약만을 근거로 slice별 화면·컴포넌트·API 클라이언트·단위테스트를 개발하는 방법론. /stage4 수행 시 사용. 스택별 규칙은 profiles/ 참조.
---

# 4단계 Frontend 방법론

목표: slice 의 화면을 **디자인 근거(피그마/스토리보드)와 OpenAPI 계약만으로** 완성한다. Backend 소스는 읽지 않는다 — 계약이 부족하면 RR 로 남긴다.
스택별 규칙은 `profiles/<stack.frontend.profile>.md`.

## A. 골격 (scaffold) — 최초 1회

`<target_dir>/frontend/` 가 없으면 만든다 (`state.yaml → stages.stage4_scaffold` 항목을 추가해 기록).
1. 빌드·린트·테스트 설정 (프로필 기본값).
2. 디렉토리: `src/app/`(라우터·프로바이더), `src/shared/`(공통 UI·API 클라이언트 베이스·유틸·타입), `src/features/<slice>/`.
3. 공통: API 클라이언트(공통 응답 포맷 해석, 인증 헤더, 에러 → 토스트/리다이렉트), 레이아웃, 인증 가드, 공통 컴포넌트(테이블·폼·페이징·확인 모달).
4. `frontend/CONVENTIONS.md`: 디렉토리·네이밍·상태 관리·스타일·테스트 규약.
5. 게이트: 빌드 + 린트 + 샘플 테스트 통과.
6. (migration·리치텍스트) 골격의 SafeHtml 허용 태그·속성을 **골격 단계에서** 서버 정제기(`HtmlContentValidator` 류)와 같게 맞춘다 — slice 로 미루면 에디터 기능(정렬 등)을 빼야 한다.

## B. slice 개발

입력: `slices.yaml` 의 `screens`, brief §6 화면 목록이 가리키는 피그마/스토리보드 원문, `<target_dir>/docs/api/<slice>.yaml`(+ depends_on 계약), `frontend/CONVENTIONS.md`.

### B-1. 화면 분석
- 화면마다: 화면ID, 라우트, 구성 요소(목록/폼/상세/모달), 입력 필드와 검증 규칙, 버튼→API 매핑, 상태(로딩/빈/에러), 권한.
- 결과를 `<target_dir>/docs/screens/<slice>.md` 에 표로 남긴다 (8단계 화면정의서 원천).
- 디자인 근거에는 있는데 계약에 API 가 없으면 → RR (`target_stage: 2, target_layer: backend/api`). 화면을 막지 말고 해당 부분만 TODO 주석 + 목 응답으로 두고 진행.

### B-2. API 클라이언트·타입
- 계약에서 타입을 **생성**한다 (프로필의 생성 도구). 손으로 타입을 옮겨 적지 않는다.
- slice 의 API 함수는 `features/<slice>/api/` 에. 공통 클라이언트를 거친다.

### B-3. 화면·컴포넌트
- 라우트는 `features/<slice>/routes.tsx` 에 정의하고 `app/router` 에서 **slice 등록 한 줄**만 추가한다 (병렬 충돌 최소화. 등록 줄 추가는 공용 파일 예외로 허용).
- 폼 검증 규칙은 계약의 스키마 제약(required/min/max/pattern)과 화면 근거를 합친다.
- 상태: 서버 상태와 클라이언트 상태를 분리(프로필). 전역 상태는 인증·레이아웃 정도만.
- 접근성·반응형은 디자인 근거가 요구하는 수준까지.

### B-4. 단위테스트
- 컴포넌트: 렌더·입력 검증·버튼 클릭 시 API 호출(목) — 화면당 최소 1개, 검증 규칙마다 1개.
- API 함수: 응답 매핑·에러 처리.
- 계약 기반 목 서버(프로필: msw)를 써서 실제 응답 스키마로 테스트한다.

## C. 게이트 및 산출물
- **실제 브라우저 렌더 게이트**: 리치텍스트 에디터·차트·트리처럼 DOM/타이머에 의존하는 서드파티 컴포넌트를 쓰는 화면은 jsdom 단위 테스트만으로 통과시키지 않는다. slice 게이트에 Playwright(Chromium) 렌더 스모크 1건(화면 로드 → 콘솔 에러 0 → 핵심 요소 표시)을 포함한다 — jsdom 이 못 잡은 Tiptap 로드 즉시 크래시(RR-0017, 운영 빌드도 재현) 사례. Playwright 는 `tests/integration/package.json` 격리 설치(5단계와 공유) 또는 앱 devDependency.
- 빌드 + 린트 + 타입체크 + 단위테스트. 실패하면 고치고 재실행. 못 고치면 `blocked`.
- 공용 파일 변경 필요 사항은 `workspace/<project>/reports/common-candidates.md` 에 (frontend 섹션).
- 레포트 `workspace/<project>/reports/<ts>_stage4_<slice>_frontend.md`: 화면 표, 컴포넌트 목록, 사용한 API, 테스트 결과, 계약 부족(RR 목록), 근거 부족.
- `state.yaml → slices.<slice>.stage4_frontend: done|blocked`.

## D. reviewer 체크리스트 (frontend-reviewer)
0. (migration) 분기→테스트 대응표의 각 행이 **렌더 단언**을 포함하는지(요청 파라미터 검증 ≠ 렌더 검증). 인라인으로 `error.message` 를 표시하는 query/mutation 은 `meta.silent` 여부 대조(이중 알림) — `role="alert"` 를 렌더하는 컴포넌트가 쓰는 query 를 **전수** grep(상세만 보고 목록을 빠뜨린 사례). 골격 SafeHtml 허용 목록 ↔ 서버 정제기 ↔ 에디터 확장 3자 대조.
1. 계약 준수: 요청/응답 타입이 생성 타입인가. 손으로 만든 타입·하드코딩 URL 이 없는가.
2. 화면 근거: 디자인의 필드·버튼·상태가 모두 구현됐는가. 근거 없는 UI 가 있는가.
3. 경계: 다른 slice 의 내부 컴포넌트/상태를 직접 import 하지 않는가. 공용 파일 수정이 등록 한 줄 외에 없는가.
4. 상태·에러: 로딩/빈/에러 상태 처리, 인증 만료 처리.
5. 테스트: 화면·검증 규칙마다 테스트가 있는가. skip 된 테스트가 없는가.
6. 기본 보안: `dangerouslySetInnerHTML`, 토큰의 localStorage 평문 저장(프로필 규칙과 대조), URL 에 민감정보.
7. `CONVENTIONS.md` 위반.

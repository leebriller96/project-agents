# Frontend 프로필: react-ts

`config/project.yaml → stack.frontend.profile: react-ts` 일 때 적용한다. `stack.frontend.state`·`ui` 값이 있으면 그것을 우선한다.

## 기본 도구
- Vite + React 18 + TypeScript(strict)
- 라우팅: react-router v6
- 서버 상태: @tanstack/react-query / 클라이언트 상태: zustand (config `state` 값 우선)
- 폼: react-hook-form + zod
- UI: config `ui` 값 (기본 MUI). 디자인 근거가 커스텀이면 CSS Modules 또는 Tailwind 로 구현
- HTTP: axios 인스턴스 (`src/shared/api/client.ts`)
- 타입 생성: `openapi-typescript` — `npm run gen:api -- <slice>` 로 `docs/api/<slice>.yaml` → `src/shared/api/types/<slice>.d.ts`
- 테스트: vitest + @testing-library/react + msw
- 린트: eslint(typescript, react-hooks, import 순서) + prettier

## 디렉토리
```
frontend/src/
├── app/            main.tsx, router.tsx(slice 라우트 등록), providers.tsx, layout/
├── shared/
│   ├── api/        client.ts(공통 응답 언래핑·에러 매핑·인증 헤더), types/<slice>.d.ts (생성)
│   ├── ui/         공통 컴포넌트 (DataTable, FormField, Pagination, ConfirmDialog, PageHeader)
│   ├── auth/       인증 상태·가드
│   ├── hooks/ lib/ utils/
└── features/<slice>/
    ├── api/        <slice>Api.ts (axios 호출 + react-query 훅)
    ├── pages/      <ScreenName>Page.tsx  (화면ID 주석)
    ├── components/
    ├── model/      zod 스키마·로컬 타입·상수
    ├── routes.tsx
    └── __tests__/
```

## 규약
- 공통 응답 `{ success, data, error }` 는 `client.ts` 가 언래핑해 `data` 만 반환, 실패는 `ApiError { code, message, status }` 로 throw.
- 인증: 토큰 저장 위치는 brief 의 인증 방식에 따름. 기본은 httpOnly 쿠키(백엔드 발급). localStorage 저장은 brief 근거가 있을 때만.
- 라우트: `/<slice>/...`. 페이지 컴포넌트 상단 주석에 화면ID·화면명.
- 네이밍: 컴포넌트 PascalCase, 훅 `useXxx`, 파일은 컴포넌트명과 동일.
- 폼 검증: zod 스키마를 `model/` 에 두고 react-hook-form 과 연결. 메시지는 한글.
- 상태: 서버 데이터는 react-query 로만. 전역 zustand 는 인증·레이아웃(사이드바 등)만.
- 에러: `ApiError` → 공통 토스트. 401 은 로그인으로, 403 은 권한 안내 페이지.
- 스타일: UI 라이브러리 테마 토큰 사용. 인라인 스타일 지양.

## 명령
```
cd <target_dir>/frontend
npm ci
npm run gen:api -- <slice>   # 계약 → 타입
npm run lint && npm run typecheck
npm run test -- --run         # vitest
npm run build
```

## 테스트 규약
- msw 핸들러는 `features/<slice>/__tests__/handlers.ts` 에 계약 예시(example) 값으로 작성.
- 페이지 테스트: 렌더 → 필드 입력 → 제출 → 요청 바디/호출 여부 검증. 에러 응답 시 메시지 노출 검증.
- `it.skip`/`describe.skip` 금지. 못 만드는 테스트는 레포트에 사유.

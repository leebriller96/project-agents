---
name: stage3-common
description: 3단계 공통화 리팩토링 — 완료된 slice 들에서 중복·공통 속성 코드를 common 모듈로 추출하고 컨벤션을 정렬하는 방법론. /stage3 수행 시 사용.
---

# 3단계 공통화 리팩토링 방법론

목표: slice 들이 각자 임시로 만든 공통성 코드를 **한 곳으로 모으고**, 동작은 바꾸지 않는다.

## 1. 입력
- `workspace/reports/common-candidates.md` (2단계 developer 들이 남긴 공용 변경 요청)
- `stage2_backend: done` 인 slice 들의 소스
- `<target_dir>/backend/CONVENTIONS.md`

## 2. 후보 탐지
1. common-candidates 항목을 먼저 처리한다.
2. 그 외 탐지 기준 — 둘 이상의 slice 에서:
   - 같은 시그니처/유사 본문의 유틸·변환·검증 로직
   - 같은 형태의 DTO(페이징, 코드값, 기간 조건), 같은 에러 처리 패턴
   - 같은 SQL 조각(공통코드 조인, 감사 컬럼 세팅, soft delete 조건)
   - 같은 외부 연동 클라이언트 초기화
3. 후보마다 표로 정리: 위치들, 공통화 방식(유틸/베이스 클래스/인터셉터/공통 SQL fragment), 영향 slice, 리스크.

## 3. 원칙
- **동작 보존**: 기존 단위테스트가 그대로 통과해야 한다. 테스트를 고쳐야 통과한다면 그건 공통화가 아니라 변경이므로 하지 않고 RR 로 남긴다.
- **한 번에 하나**: 후보 하나 추출 → 빌드·전체 테스트 → 다음 후보. 실패하면 되돌린다.
- **추상화 과잉 금지**: 두 곳에서만 쓰이고 앞으로 늘어날 근거가 없으면 추출하지 않는다 (레포트에 "보류" 로 기록).
- 공통 모듈에는 slice 의존이 들어가면 안 된다 (`common` → `<slice>` import 금지).
- 컨벤션 위반(네이밍, 패키지 위치)은 이 단계에서 일괄 정렬한다.

## 4. 산출물 및 상태
- `common/` 변경 + 각 slice 의 치환
- `<target_dir>/docs/deliverables/common-module-spec.md`: 공통 모듈 목록·용도·사용법 (8단계 산출물의 원천). 기존 파일이 있으면 갱신.
- `common-candidates.md` 의 처리된 항목은 "처리됨(회차 N)" 표시.
- 게이트: 빌드 + **전체** 단위테스트 통과.
- 레포트 `workspace/reports/<ts>_stage3_all_common.md`: 추출 목록·보류 목록·테스트 결과.
- `state.yaml → stages.stage3_common: done|blocked` (반복 실행되므로 log 에 회차를 남긴다)

## 5. reviewer 체크리스트
1. 공통화 전후 테스트 결과가 동일한가 (개수·통과).
2. common → slice 역방향 의존이 없는가.
3. 추출된 것이 실제로 둘 이상에서 쓰이는가. 사용처가 모두 치환됐는가(중복이 남아 있지 않은가).
4. `common-module-spec.md` 가 코드와 일치하는가.

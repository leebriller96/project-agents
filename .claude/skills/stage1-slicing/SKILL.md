---
name: stage1-slicing
description: 1단계 업무 분류 — PROJECT_BRIEF(및 AS-IS 인벤토리)를 바탕으로 업무 slice 를 나누고 의존관계·우선순위·AS-IS 매핑을 slices.yaml 로 만드는 방법론. /stage1 수행 시 사용.
---

# 1단계 업무 분류 (Slicing) 방법론

목표: 이후 2·4·5단계가 독립적으로 돌 수 있는 **업무 단위(slice)** 로 프로젝트를 나눈다.

## 1. 입력

- `workspace/<project>/knowledge/PROJECT_BRIEF.md` (엔티티·화면·API·요구사항 목록)
- `workspace/<project>/knowledge/ASIS_INVENTORY.md` (migration)
- 기존 `workspace/<project>/slices/slices.yaml` 이 있으면 **재분류 모드**: 이미 `done` 인 slice 는 id 를 바꾸지 않는다.

## 2. 분류 기준

1. **엔티티 응집도**: 같이 변경되는 엔티티(주문·주문상품)는 한 slice. 여러 slice 가 쓰는 엔티티(사용자·코드)는 소유 slice 를 하나 정하고 나머지는 `depends_on`.
2. **화면 흐름**: 하나의 사용자 여정(메뉴 트리 한 갈래)이 한 slice 에 들어가도록.
3. **AS-IS 경계**(migration): AS-IS 패키지/메뉴 구조를 1차 후보로 쓰되, 응집도 기준으로 재조정한다. slice 의 `asis` 항목에 **프로그램(컨트롤러·ftl)·테이블·SQL namespace·공통 클래스 사용** 을 전부 적고, `ASIS_FUNCTION_CONTRACTS.md` 의 모든 행이 어느 slice 에 들어갔는지 검증한다(못 넣은 행은 unassigned). TO-BE 가 user/admin 앱을 분리하면 slice 마다 **소유 앱**(user|admin) 을 명시한다. 앱이 분리되면 한 앱의 화면이 다른 앱의 API 를 쓸 수 없으므로, 첨부 표시·다운로드처럼 **양쪽 화면에 같이 있는 부수 기능은 각 slice 의 apis 에 각각** 넣는다(admin 상세 첨부 다운로드 누락 사례).
4. **크기**: slice 하나가 API 5~20개, 화면 3~10개 정도. 넘으면 하위 slice 로 나눈다(`order-basic`, `order-return`).
   경험치: API 11개 slice 가 2단계에서 테스트 포함 파일 30개·에이전트 24분이었다. API 15개를 넘기면 순환 의존이 없는 한 하위 slice 분할을 우선 검토한다.
5. **공통 slice**: 인증/권한, 공통코드, 파일, 알림처럼 모두가 쓰는 것은 `common-*` 접두어로 만들고 priority 를 가장 낮은 번호로 둔다.
   단, 소비자가 하나뿐이거나 DDL/seed 를 골격 baseline 이 담당해 slice 가 가질 것이 API 1~2개뿐이면 분리하지 않고 소비 slice 에 넣는다 (레포트에 사유).
6. **순환 회피 우선**: 두 엔티티가 서로의 테이블을 읽어야 하면(예: 도서 목록의 "대여 가능 권수" 가 대여 테이블을 집계) 나누지 말고 한 slice 로 묶는다. 크기 상한을 넘으면 하위 slice(`order-basic`/`order-return`)로 나누되 소유 테이블은 상위가 갖는다.

## 3. 초기에 나누기 애매할 때

요구사항이 너무 적거나 경계가 불명확하면 slice 하나(`core`)만 만들고 진행한다. 2단계를 한 번 돌고 나면 재분류가 쉬워진다.
이 경우 `slices.yaml` 상단 주석에 "단일 slice 로 시작, N 회차 이후 재분류 예정" 을 남긴다.

## 4. 의존관계와 우선순위

- `depends_on` 은 **컴파일/실행 의존**만 적는다 (주문이 회원 API 를 호출 → order depends_on member). 화면 이동만 있는 관계는 적지 않는다.
- 순환 의존이 나오면 공통 부분을 떼어 `common-*` slice 로 만든다.
- `priority` 는 depends_on 위상순서를 따르되 같은 레벨에서는 요구사항 우선순위·리스크(외부 연동 등) 높은 것을 먼저.

## 4-1. traits — 검증 축 결정 (필수)

slice 마다 `traits` 를 채운다. 이것이 **그 slice 를 어느 축에서 검증해야 하는지**를 정하고,
`tools/gate.py` 의 `coverage-axis` 훅이 2·4·5단계에서 그 축이 닫혔는지 대조한다.
근거: 파이프라인이 스스로 만든 결함 7건은 전부 "앞 단계가 보지 못한 축"에서만 잡혔다(`docs/samples/secu-sample-batch1-traps.md` 최종 채점).

| brief·AS-IS 에서 이런 게 보이면 | trait | 닫아야 할 축 |
|---|---|---|
| 첨부·업로드·다운로드 | `file-upload` | `real-server` (서블릿·파서가 서비스보다 먼저 갈린다) |
| 여러 테이블 갱신·보상·배치 | `transaction` / `batch` | `real-db` (H2 로는 방언·캐스트가 안 보인다) |
| 조회수·채번·재고처럼 경합하는 값 | `counter` / `concurrency-sensitive` | `concurrency` |
| 에디터·차트·트리 등 DOM/타이머 의존 화면 | `rich-text` / `dom-heavy` | `browser` (jsdom 은 로드 크래시를 못 잡는다) |
| 로그인·권한·프록시 헤더·세션 | `auth` / `proxy-header` | `real-server` |
| 메일·외부 API·파일시스템 | `external-io` | `real-server` |
| HTML 정제·XSS 방어 | `sanitizer` | `security-static` |

- 해당 없으면 빈 배열로 둔다. 추측으로 붙이지 말고 근거(brief 절·AS-IS 파일)를 SLICE_MAP 에 적는다.
- 새 trait 이 필요하면 `config/project.yaml → verification.trait_axes` 에 매핑을 추가하고 그 이유를 레포트에 남긴다.

## 5. 검증

- brief 의 엔티티·화면·요구사항이 모두 어느 slice 에 들어갔는지 확인한다. 못 넣은 것은 `unassigned` 에 적는다.
- 모든 slice 에 `traits` 키가 있는지 확인한다(빈 배열이라도). 없으면 축 검사가 건너뛰어진다.
- id 는 `^[a-z][a-z0-9-]*$`. 패키지명·디렉토리명으로 쓰이므로 예약어를 피한다.
- `depends_on` 이 존재하는 id 만 가리키는지, 순환이 없는지 확인한다.

## 6. 산출물 및 상태

- `workspace/<project>/slices/slices.yaml` (`approved: false`)
- `workspace/<project>/knowledge/SLICE_MAP.md`: slice ↔ 엔티티 ↔ 화면 ↔ API ↔ 요구사항 ↔ AS-IS 매트릭스 (8단계 추적표의 원천)
- 레포트 `workspace/<project>/reports/<ts>_stage1_all_slicing.md` — 분류 근거, 애매했던 판단, unassigned 목록
- `state.yaml → stages.stage1_slicing: done`, `slices` 에 각 slice 항목을 `pending` 으로 추가
- 사용자에게 slices.yaml 을 보여주고 **`approved: true` 로 바꿔 달라고 요청**한다. (재분류 모드면 approved 를 false 로 되돌린다)

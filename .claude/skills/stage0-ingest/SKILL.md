---
name: stage0-ingest
description: 0단계 준비 — workspace/<project>/00_inputs/ 의 RFP·요구사항·설계/분석 산출물·피그마/스토리보드·AS-IS 소스를 읽어 PROJECT_BRIEF.md 로 압축하는 방법론. /stage0 수행 시 사용.
---

# 0단계 준비 (Ingest) 방법론

목표: 이후 모든 단계가 원문 전체를 다시 읽지 않아도 되도록, 입력 자료를 **근거 링크가 달린 요약 지식**으로 바꾼다.

## 1. 입력 인벤토리

`workspace/<project>/00_inputs/` 를 재귀적으로 훑어 파일을 유형별로 분류한 표를 만든다.

| 유형 | 판별 기준 | 읽는 방법 |
|---|---|---|
| 요구사항/RFP | 파일명·제목에 요구사항, RFP, 제안요청 | 전체 정독. 요구사항에 ID 가 없으면 `REQ-<3자리>` 를 부여하고 원문 위치를 기록 |
| 분석/설계 산출물 | 화면정의서, 테이블정의서, 인터페이스정의서, ERD, 아키텍처 | 표·목록 위주로 추출 |
| 화면 근거 | 피그마 export(png/svg/pdf), 스토리보드(pptx/pdf) | 화면 단위로 ID·이름·주요 요소·전이 관계 추출 |
| 환경 정보 | 인프라, 배포, 계정, 외부 연동 | 기술 스택·환경 표에 반영 |
| AS-IS 소스 | `asis/` 하위 코드·DDL | §3 |
| 기타 | 위에 안 맞는 것 | 목차만 읽고 관련 절만 정독 |

문서 형식별 읽기: pdf → 페이지 단위 읽기, docx/pptx/xlsx → 사용 가능한 스킬(docx/pptx/xlsx)로 텍스트 추출.
읽지 못한 파일은 "근거 부족" 표에 남긴다.

## 2. PROJECT_BRIEF.md 작성

`templates/PROJECT_BRIEF.md` 의 절을 그대로 채운다. 원칙:

- 모든 행에 **근거(`문서명#절` 또는 `파일경로:라인`)** 를 단다. 근거 없는 내용은 쓰지 않는다.
- 기술 스택은 `config/project.yaml → stack` 이 최우선이고, 문서와 다르면 §11 모순 항목에 적는다.
- 엔티티·화면·API 후보·요구사항 목록은 **빠짐없이** 뽑되 설명은 한 줄로. 목록이 200행을 넘으면 절별로 `workspace/<project>/knowledge/brief/<절>.md` 로 분리하고 brief 에는 요약과 링크만 둔다.
- 용어집은 문서 간 표기가 다른 용어(예: 회원/고객/사용자)를 통일한 결과를 담는다.
- 코드 컨벤션(§3)은 문서에 없으면 프로필 기본값(`stage2-backend/profiles/*`, `stage4-frontend/profiles/*`)을 제안값으로 적고 "제안" 표시.

## 3. AS-IS 분석 (mode=migration)

`asis.source_dir` 를 대상으로 `workspace/<project>/knowledge/ASIS_INVENTORY.md` 를 만든다.

1. 언어/프레임워크/빌드 도구 식별, 디렉토리 구조 요약(깊이 3).
2. 프로그램 인벤토리: 진입점(Controller/Action/JSP/서블릿/배치) 목록 — 경로, 역할 한 줄, 호출하는 테이블.
3. 테이블 인벤토리: DDL 또는 SQL 에서 테이블·주요 컬럼·관계 추출.
4. 공통 모듈: 인증, 세션, 코드 테이블, 유틸, 예외 처리, 로깅 위치.
5. 이관 리스크: 저장 프로시저, 동적 SQL, 파일 I/O, 외부 연동, 하드코딩된 설정.
6. 규모: 프로그램 수, 테이블 수, 대략의 LOC.

프로그램 수가 많으면(300개 이상) 패키지 단위로 묶어 요약하고 상세는 `workspace/<project>/knowledge/asis/<패키지>.md` 로 분리한다.

7. **기능 인벤토리 → 동작 계약** (`ASIS_FUNCTION_CONTRACTS.md`): 컨트롤러 엔드포인트·화면 템플릿(ftl/jsp)·배치 job 마다 한 행 — `입력(파라미터·세션·파일) → 호출 SQL(namespace.id 목록) → 출력(뷰 모델/JSON/파일/메일/리다이렉트) → 부수효과(DB 변경·외부 호출)`. 조건 분기(`<#if>`, 권한 분기)도 행으로. **이 표가 "기능 무손실" 의 기준**이자 5단계 특성화 시나리오의 원천이다. 근거 없는 추정은 쓰지 않고 `파일:라인`.
8. **SQL 호출 인벤토리**: `sql-migrator` 를 `inventory` 로 호출해 `ASIS_SQL_INVENTORY.md`(4분류) 를 만든다(`migration-sql` 스킬). B(호출·미정의) 는 RR(high) 로.
9. **공통 클래스 인벤토리** (`ASIS_COMMON_INVENTORY.md`): 유틸·인터셉터·필터·BaseDAO/BaseController·예외·응답·세션·설정 XML 마다 — 역할, 사용처 수, TO-BE 대응 후보(계승/대체/개선/폐기 초안 — 확정은 3단계). 설정 XML(dispatcher·context·scheduler·properties)의 빈·인터셉터·스케줄 job 목록 포함.
10. **범위 원칙**: 들어온 소스가 곧 범위. TO-BE 배경 정보(신규 기능·배포·서버)는 §2 환경과 §12 변환 규칙의 근거로만 쓰고, 해당 AS-IS 소스가 없는 항목은 brief §1 에 "범위 외(소스 미입력)" 로 명시한다.

## 4. 근거 부족·모순 (§11)

- 문서 간 충돌(예: 화면정의서에는 있는데 요구사항에 없는 화면), 누락(엔티티는 있는데 테이블 정의가 없음), 읽지 못한 파일을 표로 남긴다.
- 사용자에게 이 표를 보여주고 확인을 요청한다. 답을 기다리지 않고 stage0 는 `done` 처리하되, 항목은 brief 에 남아 1단계 이후에 참조된다.

## 5. 산출물 및 상태

- `workspace/<project>/knowledge/PROJECT_BRIEF.md` (+ 분리 파일)
- `workspace/<project>/knowledge/ASIS_INVENTORY.md` (migration)
- `workspace/<project>/knowledge/INPUT_INVENTORY.md` (§1 표)
- 레포트 `workspace/<project>/reports/<ts>_stage0_all_ingest.md`
- `state.yaml → stages.stage0_ingest: done`

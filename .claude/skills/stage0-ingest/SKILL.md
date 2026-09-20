---
name: stage0-ingest
description: 0단계 준비 — workspace/00_inputs/ 의 RFP·요구사항·설계/분석 산출물·피그마/스토리보드·AS-IS 소스를 읽어 PROJECT_BRIEF.md 로 압축하는 방법론. /stage0 수행 시 사용.
---

# 0단계 준비 (Ingest) 방법론

목표: 이후 모든 단계가 원문 전체를 다시 읽지 않아도 되도록, 입력 자료를 **근거 링크가 달린 요약 지식**으로 바꾼다.

## 1. 입력 인벤토리

`workspace/00_inputs/` 를 재귀적으로 훑어 파일을 유형별로 분류한 표를 만든다.

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
- 엔티티·화면·API 후보·요구사항 목록은 **빠짐없이** 뽑되 설명은 한 줄로. 목록이 200행을 넘으면 절별로 `workspace/knowledge/brief/<절>.md` 로 분리하고 brief 에는 요약과 링크만 둔다.
- 용어집은 문서 간 표기가 다른 용어(예: 회원/고객/사용자)를 통일한 결과를 담는다.
- 코드 컨벤션(§3)은 문서에 없으면 프로필 기본값(`stage2-backend/profiles/*`, `stage4-frontend/profiles/*`)을 제안값으로 적고 "제안" 표시.

## 3. AS-IS 분석 (mode=migration)

`asis.source_dir` 를 대상으로 `workspace/knowledge/ASIS_INVENTORY.md` 를 만든다.

1. 언어/프레임워크/빌드 도구 식별, 디렉토리 구조 요약(깊이 3).
2. 프로그램 인벤토리: 진입점(Controller/Action/JSP/서블릿/배치) 목록 — 경로, 역할 한 줄, 호출하는 테이블.
3. 테이블 인벤토리: DDL 또는 SQL 에서 테이블·주요 컬럼·관계 추출.
4. 공통 모듈: 인증, 세션, 코드 테이블, 유틸, 예외 처리, 로깅 위치.
5. 이관 리스크: 저장 프로시저, 동적 SQL, 파일 I/O, 외부 연동, 하드코딩된 설정.
6. 규모: 프로그램 수, 테이블 수, 대략의 LOC.

프로그램 수가 많으면(300개 이상) 패키지 단위로 묶어 요약하고 상세는 `workspace/knowledge/asis/<패키지>.md` 로 분리한다.

## 4. 근거 부족·모순 (§11)

- 문서 간 충돌(예: 화면정의서에는 있는데 요구사항에 없는 화면), 누락(엔티티는 있는데 테이블 정의가 없음), 읽지 못한 파일을 표로 남긴다.
- 사용자에게 이 표를 보여주고 확인을 요청한다. 답을 기다리지 않고 stage0 는 `done` 처리하되, 항목은 brief 에 남아 1단계 이후에 참조된다.

## 5. 산출물 및 상태

- `workspace/knowledge/PROJECT_BRIEF.md` (+ 분리 파일)
- `workspace/knowledge/ASIS_INVENTORY.md` (migration)
- `workspace/knowledge/INPUT_INVENTORY.md` (§1 표)
- 레포트 `workspace/reports/<ts>_stage0_all_ingest.md`
- `state.yaml → stages.stage0_ingest: done`

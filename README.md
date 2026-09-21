# project-agents

대규모 서비스 개발(풀스택·차세대 등)을 **단계(stage) × 업무(slice) × 계층(layer)** 으로 쪼개어
에이전트가 선형 파이프라인으로 수행하고, 검증 단계에서 나온 결함을 **리팩토링 요구서**로 되먹임하여
반복할수록 완성도가 높아지도록 설계한 Claude Code repo입니다.

```
0 준비 ─▶ 1 업무분류 ─▶ 2 Backend ─▶ 3 공통화 ─▶ 4 Frontend ─▶ 5 통합테스트 ─▶ 6 보안 ─▶ 7 QA ─▶ 8 산출물
                ▲                                                  │           │        │
                └──────────────── 리팩토링 요구서 (refactor-requests) ◀──────────┴────────┘
```

## 단계 개요

| 단계 | 이름 | 입력 | 출력 | 게이트 |
|---|---|---|---|---|
| 0 | 준비 (Ingest) | RFP·요구사항·설계/분석 산출물·피그마/스토리보드·환경 정보·(차세대) AS-IS 소스 | `workspace/knowledge/PROJECT_BRIEF.md` — 기술스택·컨벤션·용어집·엔티티/화면/API 목록 요약 | 사람 확인 |
| 1 | 업무 분류 (Slicing) | 0단계 + AS-IS | `workspace/slices/slices.yaml` — 슬라이스 목록·의존관계·우선순위 (+ 데이터 모델 초안) | **사람 승인** |
| 2 | Backend | brief + slice | (최초 1회) 프로젝트 골격 → slice별 Migration → Mapper → Service → API + **OpenAPI 계약** + 단위테스트 | 빌드·테스트 통과 |
| 3 | 공통화 리팩토링 | 2단계 결과 전체 | common 모듈 추출, 중복 제거, 컨벤션 정렬 | 빌드·테스트 통과 |
| 4 | Frontend | 피그마/스토리보드 + OpenAPI 계약 | slice별 화면·컴포넌트·API 클라이언트 + 단위테스트 | 빌드·테스트 통과 |
| 5 | 통합 테스트 | FE + BE | 테스트 시나리오 문서(없으면 생성) → 실행 → **리팩토링 요구서** | — |
| 6 | 보안 점검 | 전체 소스 | `code-security-auditor` 실행 → **리팩토링 요구서** | — |
| 7 | QA 자동화 | 전체 소스 | `qa-automation` 실행 → **리팩토링 요구서** | — |
| 8 | 산출물 | 전체 | 설계서·API 명세·테이블 정의서·테스트 결과서 등 | — |

- 1~4단계는 slice 단위로 반복하고, 5~7단계에서 나온 요구서는 `target_stage`/`target_layer`가 지정되어
  해당 단계·계층만 다시 돈다 (무조건 1단계부터 되돌아가지 않음).
- 각 단계는 **developer 에이전트 → reviewer 에이전트** 순으로 실행되며, 게이트(빌드·테스트)를 통과해야 다음 단계로 넘어간다.

## 디렉토리 구조

```
project-agents/
├── CLAUDE.md                 # 파이프라인 운영 원칙 (Claude Code가 자동 인식)
├── README.md
├── docs/DESIGN.md            # 상세 설계 · 열린 질문
├── config/
│   ├── project.yaml.example  # 프로젝트 설정 (스택·모드·대상 repo 경로)
│   └── tools.yaml            # 외부 도구 경로 (external/ 상대경로)
├── .claude/
│   ├── commands/             # /stage0 … /stage8, /refactor, /status (오케스트레이터)
│   ├── agents/               # 서브에이전트 11개 (ingest-analyst, slice-planner, backend-developer/reviewer,
│   │                         #   common-refactorer, frontend-developer/reviewer, integration-tester,
│   │                         #   security-auditor, qa-runner, deliverable-writer)
│   └── skills/               # pipeline-core(공통 규칙) + 단계별 방법론 + 스택 프로필
├── templates/                # state·slices·PROJECT_BRIEF·리팩토링 요구서·테스트 시나리오 템플릿
├── tools/                    # rr.py(요구서 관리), status.py(상태 요약), build_report.py(md→html), sync-external.sh
├── external/                 # git subtree: qa-automation, code-security-auditor
└── workspace/                # 프로젝트별 작업 공간 (커밋하지 않음)
    ├── 00_inputs/            # 0단계 정적 문서·AS-IS 소스
    ├── knowledge/            # PROJECT_BRIEF.md 등 요약 지식
    ├── slices/               # slices.yaml
    ├── refactor-requests/    # RR-0001.yaml …
    ├── reports/              # 단계별 실행 레포트
    ├── deliverables/         # 8단계 산출물
    └── state.yaml            # 파이프라인 상태 (slice × stage 진행도, 반복 횟수)
```

생성되는 실제 서비스 소스는 `config/project.yaml`의 `target_dir`(별도 repo)에 쓴다.

## 빠른 시작

```bash
git clone https://github.com/leebriller96/project-agents.git
cd project-agents
python -m pip install -r tools/requirements.txt      # pyyaml, markdown
cp config/project.yaml.example config/project.yaml   # 프로젝트명·모드·target_dir·스택 수정
```

`workspace/00_inputs/` 에 문서(RFP·요구사항·설계 산출물·피그마 export·스토리보드)와 (차세대라면) `asis/` 소스를 넣은 뒤,
이 디렉토리에서 Claude Code 를 열고:

```text
/stage0                 # 준비: PROJECT_BRIEF.md 생성 → 근거 부족·모순 표 확인
/stage1                 # 업무 분류 → workspace/slices/slices.yaml 검토 후 approved: true 로 변경
/stage2 all             # Backend: 골격 1회 + slice 별(의존 없는 것은 병렬) 개발·검토·게이트
/stage3                 # 공통화 리팩토링
/stage4 all             # Frontend: 골격 1회 + slice 별 개발·검토·게이트
/stage5 all             # 통합 테스트 → 리팩토링 요구서(RR)
/refactor               # 열린 RR 을 target_stage·slice 별로 반영 → 후속 단계 상태 되돌림
/stage6                 # 보안 점검 (code-security-auditor 방법론) → RR
/stage7                 # QA 자동화 (qa-automation 방법론) → RR
/stage8                 # 산출물 생성
/status                 # 진행 상태 + 다음 실행 가능한 명령
```

`/stage2 order,member` 처럼 slice 를 지정할 수 있고, `/stage2 scaffold` 는 골격만 다시 만든다.

## 기술 스택

`config/project.yaml → stack` 이 결정한다. 기본 프로필은 **Java 17 / Spring Boot 3 / MyBatis / MySQL 8 / Flyway** (`spring-mybatis-mysql`) 와
**React 18 / TypeScript / Vite** (`react-ts`) 이며, 규칙은 `.claude/skills/stage2-backend/profiles/`, `stage4-frontend/profiles/` 에 있다.
다른 스택을 쓰려면 프로필 파일을 하나 추가하고 config 의 `profile` 값을 바꾸면 된다. 프로필이 없어도 범용 규칙으로 동작한다.

## 산출물 (8단계)

`config/project.yaml → deliverables.items` 로 선택한다. 기본 목록: 요구사항 추적표(RTM), 아키텍처 정의서, 업무 분류표, 테이블 정의서+ERD,
API 명세서, 화면 정의서, 공통 모듈 명세, 단위/통합/보안/QA 결과서, (차세대) AS-IS/TO-BE 매핑표, 빌드·배포·운영 가이드.
형식은 md 원본 + html (`tools/build_report.py`), 필요 시 docx.

## 외부 도구 (external/ — git subtree)

6·7단계가 쓰는 도구 repo 는 `external/` 아래에 **git subtree** 로 편입되어 있어 이 repo 하나만 clone 하면 된다.

- `external/code-security-auditor` ← [code-security-auditor](https://github.com/leebriller96/code-security-auditor) — 6단계 보안 점검
- `external/qa-automation` ← [qa-automation](https://github.com/leebriller96/qa-automation) — 7단계 QA 자동화

upstream 갱신: `bash tools/sync-external.sh [qa|security]`. 의존성: `python -m pip install -r external/<도구>/tools/requirements.txt`.

상세 설계와 아직 결정되지 않은 사항은 [docs/DESIGN.md](docs/DESIGN.md) 참고.

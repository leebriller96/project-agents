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
│   └── tools.yaml            # 외부 도구(code-security-auditor, qa-automation) 경로
├── .claude/
│   ├── commands/             # /stage0 … /stage8, /refactor, /status
│   ├── agents/               # 단계·계층별 서브에이전트 정의
│   └── skills/               # 단계별 방법론(SKILL.md)
├── templates/                # 리팩토링 요구서·테스트 시나리오·산출물 템플릿
├── tools/                    # 상태 조회, 레포트→요구서 변환 스크립트
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

## 빠른 시작 (예정)

```text
1. config/project.yaml.example → config/project.yaml 복사 후 수정
2. workspace/00_inputs/ 에 문서·AS-IS 소스 투입
3. Claude Code에서
   /stage0            # 준비: PROJECT_BRIEF 생성
   /stage1            # 업무 분류 → slices.yaml (승인)
   /stage2 <slice>    # Backend
   /stage3            # 공통화
   /stage4 <slice>    # Frontend
   /stage5 … /stage7  # 검증 → refactor-requests/ 생성
   /refactor          # 열린 요구서를 target_stage별로 묶어 반영
   /status            # state.yaml 요약
   /stage8            # 산출물
```

## 관련 도구

- [code-security-auditor](https://github.com/leebriller96/code-security-auditor) — 6단계 보안 점검
- [qa-automation](https://github.com/leebriller96/qa-automation) — 7단계 QA 자동화

상세 설계와 아직 결정되지 않은 사항은 [docs/DESIGN.md](docs/DESIGN.md) 참고.

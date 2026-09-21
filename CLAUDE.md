# CLAUDE.md — project-agents

이 repo는 대규모 프로젝트를 **단계 × 업무(slice) × 계층**으로 나누어 에이전트가 순차 수행하는
파이프라인이다. 상세 단계 정의는 `README.md`, 설계 근거는 `docs/DESIGN.md`를 따른다.

## 핵심 원칙

- **근거 기반**: 모든 코드는 `workspace/knowledge/PROJECT_BRIEF.md`와 `workspace/00_inputs/`의 문서를 근거로 작성한다.
  근거가 없는 기능은 추측으로 만들지 말고 `workspace/reports/`에 "근거 부족" 항목으로 남긴다.
- **slice 단위 작업**: 2·4단계는 항상 하나의 slice만 대상으로 한다. 전체를 한 번에 만들지 않는다.
- **계약 우선**: Backend는 slice마다 OpenAPI 계약을 산출하고, Frontend는 그 계약만 보고 개발한다.
- **게이트 준수**: 2·3·4단계는 빌드와 단위테스트가 통과해야 완료로 기록한다. 실패하면 상태를 `blocked`로 남긴다.
- **developer → reviewer**: 생성 에이전트와 검토 에이전트를 분리한다. 검토에서 나온 지적은 같은 단계 안에서 수정한다.
- **되먹임은 요구서로만**: 5~7단계의 결함은 반드시 `templates/refactor-request.yaml` 형식으로
  `workspace/refactor-requests/`에 기록한다. 요구서 없이 코드를 직접 고치지 않는다.
- **상태는 파일로**: 진행 상황은 `workspace/state.yaml`에만 기록한다. 대화 기억에 의존하지 않는다.
- **정직한 보고**: 실행하지 못한 테스트, 구성하지 못한 환경은 통과시키지 말고 그 사실을 레포트에 남긴다.
- 모든 레포트·문서·코드 주석은 **한글**로 작성한다.

## 외부 도구

6단계(보안)와 7단계(QA)는 `external/` 아래 git subtree 로 편입된 도구 repo(`config/tools.yaml` 경로)의 `SKILL.md`를 읽어 그 방법론대로 수행하고,
결과 레포트를 `workspace/reports/`로 가져온 뒤 리팩토링 요구서로 변환한다.

## 파일명 규칙

레포트 파일명은 한국시각(KST) 기준 `yymmddhhmm_<설명>.<확장자>` 접두어를 붙인다.
(`TZ=Asia/Seoul date '+%y%m%d%H%M'` / PowerShell: `Get-Date -Format 'yyMMddHHmm'`)

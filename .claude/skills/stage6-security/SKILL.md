---
name: stage6-security
description: 6단계 보안 점검 — 외부 repo code-security-auditor 의 security-audit 스킬 방법론으로 target_dir 전체를 점검하고, 결과를 리팩토링 요구서(RR)로 변환하는 방법론. /stage6 수행 시 사용.
---

# 6단계 보안 점검 방법론

목표: `code-security-auditor` 의 방법론을 **그대로** 적용해 취약점을 찾고, 수정은 RR 로 넘긴다. 이 단계는 코드를 고치지 않는다.

## 1. 외부 스킬 로드
1. `config/tools.yaml → security_auditor.path` 를 읽는다. 경로가 없으면 안내 후 중단.
2. `<path>/<skill>` (SKILL.md) 와 `<path>/CLAUDE.md`, `<path>/templates/report_template.md` 를 읽는다. **그 방법론(모드·점검 항목·심각도 기준·레포트 형식)을 따른다.**
3. `<path>/tools/run_sast.sh` 가 있고 semgrep/bandit/gitleaks 등이 설치돼 있으면 hybrid 모드, 아니면 claude-only 모드. 모드는 레포트에 명시.

## 2. 대상
- `<target_dir>/backend`, `<target_dir>/frontend`, `<target_dir>/db/migration`. `node_modules`, 빌드 산출물 제외.
- 원 도구는 `input/` 을 대상으로 하지만 여기서는 **target_dir 을 직접 대상**으로 한다. 복사하지 않는다.
- 인자로 slice 가 오면 그 slice 디렉토리 + common 만.

## 3. 점검 우선순위 (이 프로젝트 특화 추가)
원 스킬의 OWASP/CWE 항목에 더해:
- MyBatis `${}` 사용처, 동적 정렬/테이블명
- 인증 누락 엔드포인트 (SecurityConfig permitAll 목록 ↔ 컨트롤러 대조)
- 응답에 민감 필드(비밀번호 해시, 주민번호 등) 노출 — DTO 검토
- FE: 토큰 저장 방식, XSS(`dangerouslySetInnerHTML`), 민감정보 URL 파라미터
- 설정: 비밀값 하드코딩, CORS 전체 허용, actuator 노출
- 마이그레이션 SQL 의 기본 계정/비밀번호 삽입

## 4. 레포트 → RR 변환
1. 원 도구 형식의 레포트를 `workspace/reports/<ts>_stage6_<slice|all>_security.md` 로 쓴다 (HTML 변환 포함).
2. 발견 항목마다 RR 1개: `source_stage: 6`, `severity` 는 원 도구 심각도 매핑 (Critical→blocker, High→high, Medium→medium, Low/Info→low), `evidence` 에 파일:라인, `suggested_fix` 에 원 레포트의 Before/After 요약.
   `target_layer` 는 파일 위치로 판단 (backend/mapper, backend/api, common, frontend/*).
3. Info 등급은 RR 을 만들지 않고 레포트에만 남긴다 (config 로 바꿀 수 있게 향후 확장).
4. 같은 유형이 여러 파일에서 나오면 파일별로 RR 을 나눈다 (한 RR = 한 수정 단위).

## 5. 산출물 및 상태
- 레포트(md+html), RR 파일들
- `state.yaml → stages.stage6_security: done` (blocker/high 가 남아 있으면 log 에 "재점검 필요" 표시, `/refactor` 후 다시 /stage6)
- 사용자에게 심각도별 건수와 RR 목록을 보여주고 `/refactor` 안내

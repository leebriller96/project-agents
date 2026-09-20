# 실행 이력·교훈 로그 (LESSONS)

실제 프로젝트를 돌리며 드러난 문제와 파이프라인에 반영한 조치를 누적한다. 형식: 날짜 · 단계 · 현상 → 조치(반영 파일).

## 2026-09-20 — library-sample (샘플 검증, greenfield)

| 단계 | 현상 | 조치 |
|---|---|---|
| stage0 | 문서 5개(요구 22·화면 8·테이블 4)에서 §11 근거 부족 20건 도출. 의도적으로 심은 모순 4건 전부 탐지 + 실제 설계 결함(복합 PK FK 불가, 논리 삭제 필요, 동시성) 추가 발견 | 방법론 유효. 변경 없음 |
| stage0→1 | §11 항목 중 골격·마이그레이션에 필요한 결정(JWT 전달 방식, 코드 seed, 초기 계정)이 승인 없이는 2단계를 막음 | brief 에 **§12 결정 사항** 절을 두고 사용자 승인 결정을 기록하는 관례 도입 → `templates/PROJECT_BRIEF.md`·`stage1` 명령에 반영 예정 |
| stage1 | slice-planner 가 Book+Loan 을 한 slice 로 묶음(순환 의존 회피). 방법론 §2.5 "공통코드는 common-* slice" 와 달리 분리하지 않음 — 소비자 1개뿐이라 타당 | `stage1-slicing` §2.5 에 "소비자가 1개면 분리하지 않는다" 예외 추가 예정 |
| stage2 준비 | config `stack.backend.version: "17"` 이나 설치 JDK 는 21뿐. gradle CLI 없음(wrapper 캐시 8.10.2 만 존재). `mysql` CLI 없음, Docker 데몬은 실행 중 | config 를 21 로 갱신. **골격 전 환경 점검 절차**(JDK·빌드 도구·Docker·Node 확인 후 config 와 불일치 시 보고) 를 `stage2-backend` §A 와 `/stage2` 명령에 추가 예정 |
| 도구 | `tools/*.py` 출력이 Windows 콘솔(cp949)에서 깨짐; slices 템플릿의 `{id}` 가 YAML flow 시퀀스 파싱 오류 | `sys.stdout.reconfigure(utf-8)`, 템플릿 값 따옴표 처리 (반영 완료) |
| 도구 | Bash 도구로 10KB 넘는 다중 heredoc 명령이 통째로 실패 | 긴 파일은 Write 도구로 작성 (메모리 기록) |

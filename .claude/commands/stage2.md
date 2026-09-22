---
description: 2단계 Backend 개발 — (최초 1회 골격 생성 후) slice 별로 Migration→Mapper→Service→API→OpenAPI 계약→단위테스트를 개발합니다. 의존 없는 slice 는 병렬 실행.
argument-hint: "<slice-id>[,<slice-id>...] | all | scaffold"
---

# /stage2 — Backend 개발

인자: `$ARGUMENTS`

## 절차
1. `.claude/skills/pipeline-core/SKILL.md` §1·§4·§5·§6·§7 을 읽고 따른다.
   선행: stage1 `done`, `slices.yaml → approved: true`. 미승인이면 승인 요청 후 종료.
2. **골격**: `stages.stage2_scaffold` 가 `done` 이 아니거나 인자가 `scaffold` 면, 먼저 오케스트레이터가 환경(JDK·빌드 도구·Docker·Node)을 확인해 config 와 불일치를 사용자에게 알리고 (필요 시 config 갱신), 확인된 환경 정보를 에이전트에 전달한다.
   `backend-developer` 를 `scaffold` 작업으로 호출 → 보고 → 빌드·샘플 테스트 통과 시 `stage2_scaffold: done`.
   사용자에게 골격 구조·`CONVENTIONS.md` 요약을 보여준다. 인자가 `scaffold` 였으면 여기서 종료.
3. **대상 slice 결정** (§5): 인자 해석 → 대상 목록. 각 slice 의 `depends_on` 이 모두 `stage2_backend: done` 인지 확인. 아니면 그 slice 는 대상에서 빼고 사유를 알린다.
4. **웨이브 구성** (§6): `pipeline.parallel` 이 true 면 depends_on 위상 정렬로 웨이브를 만들고, 웨이브 안에서 `max_parallel` 개까지 동시에 실행한다. false 면 priority 순 순차.
5. 웨이브마다:
   a. 대상 slice 들의 `stage2_backend: in_progress` 기록.
   a-1. `mode: migration` 이면 slice 마다 `sql-migrator` 를 `convert <slice>` 로 먼저 호출(병렬 가능) → Mapper·XML·DTO·`<slice>-sql-mapping.md`·Mapper 테스트 → 그 시그니처를 developer 프롬프트에 전달.
   b. `backend-developer` 를 slice 마다 호출 (병렬이면 한 메시지에서 여러 Agent 호출). 전달: `slice <id>`, target_dir 절대경로, 프로필 이름, depends_on slice 의 계약 경로.
   c. 각 보고를 받은 뒤 `backend-reviewer` 를 slice 마다 호출 (병렬 가능). 전달: `slice <id>`, target_dir, 프로필, developer 보고 전문.
   d. reviewer 가 FAIL 이면 지적 목록을 붙여 `backend-developer` 를 다시 호출 (최대 2회). 여전히 FAIL 이면 `blocked` + `blocked_reason` 에 잔여 지적.
   e. `state.yaml` 갱신 (`done`|`blocked`, log). reviewer 의 medium/low 지적은 RR 로 남길지 판단: 다음 단계에 영향 주는 것만 `python tools/rr.py new` 로 생성(`source_stage: 2`). 단, **웨이브 게이트에 걸리는 것**(예: `-Pmysql` 에서만 깨지는 테스트 이식성, 원자성 미증명)은 severity 와 무관하게 같은 단계에서 developer 가 수정한다.
5-1. 웨이브 종료 후 reviewer 지적 중 "규칙 부재·규칙 신설로 인한 것"(예: URL 파라미터 정규화, 검증 규칙 테스트 누락)은 같은 웨이브의 **다른 slice 에도 해당하는지** 오케스트레이터가 grep 으로 확인하고, 해당하면 slice 별 RR 을 함께 만든다. 프로필 규칙을 갱신했다면 다음 웨이브 developer 프롬프트에 명시한다.
6. 사용자에게 보여준다: slice 별 결과 표(상태·테이블 수·API 수·테스트 수·reviewer 결과), blocked 사유, 근거 부족 항목, 공통 후보 수, 레포트 경로.
7. 안내: 남은 slice 가 있으면 `/stage2 <다음>`, 모두 끝났으면 `/stage3` (공통화) 또는 `/stage4 <slice>`.

## 완료 처리 (공통 · pipeline-core §9·§11·§12)

1. 서브에이전트 보고의 `pa-agent-result` 블록에서 게이트·변경 파일·확인 필요 항목을 그대로 가져온다.
   `changed_files` 에 소유 밖 파일이 있으면 되돌리고 공통 후보로 돌린다.
2. 확인 필요 항목은 `python tools/gate.py oi new --stage 2 --slice <id> --kind <kind> --severity <sev> --summary "…" --evidence "…" --target <닫을 단계>` 로 채번한다.
   `blocker`·`high` 는 RR 전환(`oi set <id> converted --rr RR-xxxx`) 또는 사람 승인(`accepted`) 없이 남기지 않는다.
3. 레포트 끝에 `pa-meta` 블록을 붙인다 (`python tools/gate.py template --stage 2 --slice <id> --agent orchestrator` 로 골격 생성 후 실제 값으로 채움).
4. `python tools/gate.py check --stage 2 [--slice <id>]` 를 실행한다. **FAIL 이면 그 단계를 `done` 으로 기록하지 않는다.**
   검사 결과(통과 / FAIL 항목)를 사용자 보고에 한 줄로 포함한다.

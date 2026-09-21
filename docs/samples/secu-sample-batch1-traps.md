# secu-sample 1차 배치(공지사항) — 함정 채점표

AS-IS 샘플 소스(24 파일) 에 의도적으로 심은 함정. 파이프라인이 어느 단계에서 잡는지 채점한다. (생성: 2026-09-21)

| # | 함정 | 위치 | 잡아야 할 단계·산출물 | 결과 |
|---|---|---|---|---|
| 1 | 호출·미정의 SQL id `notice.selectNoticeCountByClass` (list.do 분류 선택 시 도달) | NoticeService.java:53, NoticeController.java:89 | stage0 SQL 인벤토리 B → RR high | |
| 2 | 동적 id `"notice.select"+type+"List"` (Top/Normal) | NoticeService.java:63 | stage0 인벤토리 D → 전개 | |
| 3 | dead SQL selectNoticeOld/deleteNoticeHard | notice_SQL.xml:313,324 | stage0 인벤토리 C | |
| 4 | ROWNUM 3중 페이징 ORDER BY 없음 | notice_SQL.xml:37,68 | stage2 ⚠TIE_ORDER | |
| 5 | `\|\|` NULL 전파 / NVL(x,'') / USE_YN='' | notice_SQL.xml:42,88,55,227 | stage2 ⚠CONCAT_NULL·EMPTY_NULL | |
| 6 | SUBSTR(content,0,100) | notice_SQL.xml:43 | stage2 ⚠SUBSTR0 | |
| 7 | MERGE 조인 키 ≠ UNIQUE (TB_NOTICE PK 없음) | notice_SQL.xml:168-172, schema:34,69 | stage2 ⚠MERGE_KEY / 테이블 매핑 PK 신설 | |
| 8 | NULLS LAST | notice_SQL.xml:109 | stage2 ⚠NULL_ORDER | |
| 9 | 시퀀스 선채번 후 2테이블 insert | NoticeService.java:123,133 | stage2 ⚠SEQ | |
| 10 | `${sortColumn}` | notice_SQL.xml:69, NoticeController:70-72 | stage2 화이트리스트 / stage6 | |
| 11 | 감사 컬럼 제각각 (REG_ID/REG_DATE vs CRT_ID/CRT_DT) | schema:47-48,82-83 | stage2 테이블 매핑 M-38 | |
| 12 | wj_class_id 가 저장 폴더·결재선 관여 | FileUtil.java:85, NoticeController:44-45 | stage0 기능 계약 / stage2 코드마스터 매핑 | |
| 13 | 개인 profile 폴더 kimjw | profile/kimjw | stage0 공통 인벤토리 → stage3 폐기 | |
| 14 | 2단계 업로드 파일명 초단위 충돌 | FileUtil.java:59 | stage0 기능 계약 / stage3 대체 | |
| 15 | `<#noescape>` XSS (lucy 실제 제외) | view.ftl:87, servlet-context.xml:86 | stage0 기능 계약 / stage4 SafeHtml / stage6 | |
| 16 | 공통 유틸 dead 메서드 2 | CommonUtil.java:96,109 | stage0 공통 인벤토리 사용처 0 → stage3 폐기 | |
| 17 | 만료 배치 job (소스 있음 → 범위 안) | scheduler-base-servlet.xml:22, NoticeExpireJob.java | stage0 기능 계약 / stage2 @Scheduled | |
| 18 | LoginCheckInterceptor 가 view.do·fileDown.do 제외 (비로그인 열람) | dispatcher-servlet.xml:39-40 | stage0 기능 계약 → stage2 permitAll 유지 | |
| + | prd1 운영 비밀번호 평문, SHA-256 무salt, pageSize 상한 없음, renameTo 실패 시 파일 유실, WAS 2대 중 1대 스케줄러 | 각 파일 주석 | stage6 / stage0 | |

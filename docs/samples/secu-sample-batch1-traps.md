# secu-sample 1차 배치(공지사항) — 함정 채점표

AS-IS 샘플 소스(24 파일) 에 의도적으로 심은 함정. 파이프라인이 어느 단계에서 잡는지 채점한다. (생성: 2026-09-21)

| # | 함정 | 위치 | 잡아야 할 단계·산출물 | 결과 |
|---|---|---|---|---|
| 1 | 호출·미정의 SQL id `notice.selectNoticeCountByClass` (list.do 분류 선택 시 도달) | NoticeService.java:53, NoticeController.java:89 | stage0 SQL 인벤토리 B → RR high | ✅ stage0 SQL B → RR-0001 high, 도달 경로 추적 |
| 2 | 동적 id `"notice.select"+type+"List"` (Top/Normal) | NoticeService.java:63 | stage0 인벤토리 D → 전개 | ✅ stage0 D 전개(Top=A, Normal=C 근거부족) |
| 3 | dead SQL selectNoticeOld/deleteNoticeHard | notice_SQL.xml:313,324 | stage0 인벤토리 C | ✅ stage0 C + 시퀀스 SELECT 2건 폐기 예정 |
| 4 | ROWNUM 3중 페이징 ORDER BY 없음 | notice_SQL.xml:37,68 | stage2 ⚠TIE_ORDER | ✅(태그) TIE_ORDER 5 + 11-08 |
| 5 | `\|\|` NULL 전파 / NVL(x,'') / USE_YN='' | notice_SQL.xml:42,88,55,227 | stage2 ⚠CONCAT_NULL·EMPTY_NULL | ✅(태그) EMPTY_NULL 7·CONCAT_NULL 3 + 11-29 "제목 []" |
| 6 | SUBSTR(content,0,100) | notice_SQL.xml:43 | stage2 ⚠SUBSTR0 | ✅(태그) SUBSTR0, 미소비 컬럼 판정 |
| 7 | MERGE 조인 키 ≠ UNIQUE (TB_NOTICE PK 없음) | notice_SQL.xml:168-172, schema:34,69 | stage2 ⚠MERGE_KEY / 테이블 매핑 PK 신설 | ✅(태그) MERGE_KEY, NOT MATCHED 도달 불가 판정 + 11-05 |
| 8 | NULLS LAST | notice_SQL.xml:109 | stage2 ⚠NULL_ORDER | ✅(태그) NULL_ORDER |
| 9 | 시퀀스 선채번 후 2테이블 insert | NoticeService.java:123,133 | stage2 ⚠SEQ | ✅(태그) SEQ 2 |
| 10 | `${sortColumn}` | notice_SQL.xml:69, NoticeController:70-72 | stage2 화이트리스트 / stage6 | ✅ ${} 1건 화이트리스트 없음 + R 규칙 |
| 11 | 감사 컬럼 제각각 (REG_ID/REG_DATE vs CRT_ID/CRT_DT) | schema:47-48,82-83 | stage2 테이블 매핑 M-38 | ✅ 11-17 + §12-A M-38 규칙 |
| 12 | wj_class_id 가 저장 폴더·결재선 관여 | FileUtil.java:85, NoticeController:44-45 | stage0 기능 계약 / stage2 코드마스터 매핑 | ✅ 기능 계약·11-19·11-21 |
| 13 | 개인 profile 폴더 kimjw | profile/kimjw | stage0 공통 인벤토리 → stage3 폐기 | ✅ 공통 인벤토리 사용처0 + 11-26 폐기 |
| 14 | 2단계 업로드 파일명 초단위 충돌 | FileUtil.java:59 | stage0 기능 계약 / stage3 대체 | ✅ 11-21 초 단위 충돌 |
| 15 | `<#noescape>` XSS (lucy 실제 제외) | view.ftl:87, servlet-context.xml:86 | stage0 기능 계약 / stage4 SafeHtml / stage6 | ✅ 11-11 XSS + R 규칙 |
| 16 | 공통 유틸 dead 메서드 2 | CommonUtil.java:96,109 | stage0 공통 인벤토리 사용처 0 → stage3 폐기 | ✅ 사용처0 목록(getRandomString·convertEucKrToUtf8 +3) |
| 17 | 만료 배치 job (소스 있음 → 범위 안) | scheduler-base-servlet.xml:22, NoticeExpireJob.java | stage0 기능 계약 / stage2 @Scheduled | ✅ 기능 계약 FC 배치 행 |
| 18 | LoginCheckInterceptor 가 view.do·fileDown.do 제외 (비로그인 열람) | dispatcher-servlet.xml:39-40 | stage0 기능 계약 → stage2 permitAll 유지 | ✅ 11-10 구두 승인 확인 요청 |
| + | prd1 운영 비밀번호 평문, SHA-256 무salt, pageSize 상한 없음, renameTo 실패 시 파일 유실, WAS 2대 중 1대 스케줄러 | 각 파일 주석 | stage6 / stage0 | 11-23(평문, 값 미복사)·11-15(pageSize)·11-12(등록 실패)·리스크 19 에 포함 |


**0단계 채점**: 0단계 대상 함정 18/18 포착(2단계 대상 4~10 은 ⚠ 태그로 사전 포착). 카탈로그 신규 9행·태그 2종. §11 30건 중 사람 확인 필요 항목이 stage1 전 결정 대상(11-07/09/10 접근 통제, 11-16/19/20 스키마·slice 구조, 11-25 인증 범위).

**2단계(sql-convert) 채점**: 4 TIE_ORDER→PK tie-breaker+기본 정렬 ✅ / 5 EMPTY_NULL·CONCAT_NULL→NULLIF·TITLE_DISP 폐기 ✅ / 6 SUBSTR0→컬럼 폐기(소비 0) ✅ / 7 MERGE_KEY→PK 신설+단순 UPDATE(NOT MATCHED 도달 불가) ✅ / 8 NULL_ORDER 명시 ✅ / 9 SEQ→useGeneratedKeys ✅ / 10 `${sortColumn}`→enum 화이트리스트 ✅ / 11 M-38 이름 변환 ✅. 매핑표 19/19 행, statement 18 전부 테스트, ⚠ 경계값 MySQL 실측(GROUP_CONCAT 절단 실제 재현 → C-04). 카탈로그 +4행.

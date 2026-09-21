---
name: migration-sql
description: 차세대(migration) 프로젝트의 SQL 이관 방법론 — (1) SqlSession 직접 호출 → Mapper 전환을 위한 SQL 호출 인벤토리 4분류, (2) Oracle → MySQL 8.x 방언 변환 카탈로그(등가 구문·앱 로직 이전·의미 차이 태그), (3) Oracle 인스턴스 없이 정적 카탈로그 + 경계값 fixture 로 하는 등가성 검증. stage0(인벤토리)·stage2(변환)·stage5(검증) 에서 sql-migrator/backend-developer/integration-tester 가 사용.
---

# SQL 이관 방법론 (migration-sql)

전제: AS-IS 쿼리는 전부 Oracle 방언, TO-BE 는 MySQL 8.x + MyBatis Mapper. **Oracle 인스턴스 없음 → 정적 카탈로그 방식.**
원칙: "완벽 변환" 의 기준은 **AS-IS 코드가 그 결과를 어떻게 소비하는가**다. 결과 집합의 형태·순서·NULL 처리가 소비 코드에 영향을 주는지 statement 마다 판정한다.

## 1. SQL 호출 인벤토리 (stage0, `ASIS_SQL_INVENTORY.md`)

AS-IS 가 `sqlSession.selectList("ns.id", param)` 처럼 문자열로 호출하면 없는 id 가 컴파일에 안 잡힌다. Mapper 로 가면 전부 인터페이스 메서드가 되어야 하므로 먼저 전수 조사한다.

1. **호출처 전수**: Java 전체에서 `sqlSession.(selectOne|selectList|selectMap|insert|update|delete)\(` 의 첫 인자를 grep. 리터럴은 `ns.id` 로, **문자열 조합**(`"ns." + type + "List"`, 상수 결합, 변수)은 "동적 id" 로 표시하고 가능한 값 집합을 호출 코드에서 추적(enum·상수·DB 값이면 그 원천).
   `getSqlSession()`·`SqlSessionTemplate`·`SqlMapClient`(iBatis) 등 래퍼도 포함. BaseDAO 류가 namespace 를 접두하는 패턴이면 그 규칙을 먼저 파악.
2. **정의처 전수**: Mapper XML 의 `<mapper namespace>` × `<select|insert|update|delete|sql id>` (`<sql>` fragment 는 별도 표시), `<include refid>` 참조.
3. **4분류 표**:

| 분류 | 의미 | 처리 |
|---|---|---|
| A 호출·정의 | 정상 | Mapper 메서드로 전환 |
| **B 호출·미정의** | 런타임 폭탄(AS-IS 에서도 실행 시 예외 — 죽은 경로이거나 실제 결함) | RR **high** — 호출 경로가 실제로 도달 가능한지 판정 후 폐기/구현 결정 |
| C 정의·미호출 | dead SQL | 매핑표에 "폐기(미호출)", 동적 id 후보인지 확인 후 폐기 |
| D 동적 id | 문자열 조합 | 가능한 값 전부를 A/B 로 전개. 전개 불가면 근거 부족 + 사람 확인 |

4. 산출: `ASIS_SQL_INVENTORY.md` — 통계(namespace 수·statement 수·호출 수·A/B/C/D 건수) + 전체 표(namespace.id, 종류, 호출처 `파일:라인`, 분류, 파라미터 타입, 결과 타입, `${}` 사용, 사용 Oracle 구문 태그 §2). 이 표가 Mapper 인터페이스 설계의 원천이자 8단계 매핑표 원천.

## 2. Oracle → MySQL 8.x 변환 카탈로그

statement 마다 사용된 구문을 태깅하고 아래 규칙으로 변환한다. **의미 차이 태그**(⚠)가 붙은 구문은 5단계 경계값 검증 대상. 카탈로그에 없는 구문은 이 표에 **추가**한다(프로젝트 누적).

### 2-1. 문법 등가 변환 (기계적)
| Oracle | MySQL 8.x | 비고 |
|---|---|---|
| `FROM DUAL` | 생략 또는 `FROM DUAL`(허용) | |
| `NVL(a,b)` | `IFNULL(a,b)` / `COALESCE` | ⚠ 빈 문자열: Oracle 은 `''`=NULL 이라 `NVL('',b)`=b, MySQL 은 `''` 유지 |
| `NVL(x, '')` | 제거(원문이 no-op) 또는 `IFNULL(x,'')` | ⚠ Oracle 은 `''`=NULL 이라 `NVL(x,'')`=x(NULL 유지). MySQL `IFNULL(x,'')` 는 `''` 반환 → 소비 코드가 NULL 체크(`??`)하면 결과 달라짐. 소비 없으면 제거 |
| `NVL2(a,b,c)` | `IF(a IS NOT NULL, b, c)` | ⚠ 동일 |
| `DECODE(x, v1, r1, v2, r2, d)` | `CASE x WHEN v1 THEN r1 WHEN v2 THEN r2 ELSE d END` | ⚠ `DECODE(x, NULL, r)` 는 NULL 매칭됨 → `CASE WHEN x IS NULL` |
| `a \|\| b` | `CONCAT(a, b)` | ⚠ Oracle 은 NULL\|\|'x'='x', MySQL `CONCAT(NULL,'x')`=NULL → `CONCAT_WS('', …)` 또는 `IFNULL` |
| `SYSDATE` / `SYSTIMESTAMP` | `NOW()` / `NOW(6)` | ⚠ 세션 TZ(JDBC `connectionTimeZone`) |
| `TO_CHAR(d, 'YYYYMMDD')` | `DATE_FORMAT(d, '%Y%m%d')` | 형식 문자 매핑표: YYYY→%Y, MM→%m, DD→%d, HH24→%H, MI→%i, SS→%s, DAY→%W |
| `TO_DATE(s, 'YYYYMMDD')` | `STR_TO_DATE(s, '%Y%m%d')` | ⚠ 잘못된 문자열: Oracle 예외, MySQL NULL(strict 모드 아니면) |
| `TO_DATE('', fmt)` (빈 문자열 바인드) | `STR_TO_DATE(NULLIF(s,''), fmt)` 또는 앱에서 `''`→null 후 `LocalDate` 바인드 | ⚠ `EMPTY_NULL` — Oracle 은 `''`=NULL 이라 조용히 NULL 저장. MySQL `STR_TO_DATE('')` 는 NULL + 경고(1411) 이며 strict 모드 INSERT 에서 오류가 될 수 있음. "종료일 없음=무기한" 처럼 `''` 가 정상 입력인 경로에서 필수 |
| `TO_NUMBER(s)` | `CAST(s AS DECIMAL)` / 암묵 | ⚠ 비숫자 문자열 |
| `TRUNC(d)` | `DATE(d)` | `TRUNC(d,'MM')` → `DATE_FORMAT(d,'%Y-%m-01')` |
| `ADD_MONTHS(d, n)` | `DATE_ADD(d, INTERVAL n MONTH)` | ⚠ 월말 처리 동일(둘 다 말일 유지) |
| `MONTHS_BETWEEN(a,b)` | `TIMESTAMPDIFF(MONTH, b, a)` + 일수 보정 | ⚠ 소수부 의미 다름 — 소비 코드가 정수만 쓰면 OK |
| `d + 1` (일 산술) | `DATE_ADD(d, INTERVAL 1 DAY)` | |
| `SUBSTR(s, 0, n)` | `SUBSTR(s, 1, n)` | ⚠ Oracle 은 0 을 1 로 취급, MySQL 은 빈 문자열 |
| `INSTR(s, sub, pos, nth)` | 3·4번째 인자 없음 → `LOCATE(sub, s, pos)` (nth 는 앱 로직) | ⚠ |
| `LENGTH` / `LENGTHB` | `CHAR_LENGTH` / `LENGTH`(바이트) | ⚠ MySQL `LENGTH` 는 바이트 |
| `ROWNUM <= n` | `LIMIT n` | ⚠ ORDER BY 없는 ROWNUM 은 순서 미정 — AS-IS 도 미정이었음을 기록 |
| ROWNUM 페이징 (3중 서브쿼리) | `ORDER BY … LIMIT #{size} OFFSET #{offset}` | ⚠ 정렬 키 동순위 시 순서 불안정 → tie-breaker(PK) 추가 여부를 소비 코드로 판정 |
| `ROWNUM AS RNUM` 을 결과 컬럼으로 노출(화면 번호) | `ROW_NUMBER() OVER (ORDER BY …) AS rnum` 또는 앱에서 `offset + index` | ⚠ `TIE_ORDER` — ORDER BY 가 조건부(`<if>`)면 무정렬 시 번호 의미 없음. 정렬 키가 없는 경로는 기본 정렬을 사람 확인 |
| `<if>` 로 감싼 조건부 `ORDER BY` (없으면 무정렬 + 힌트 인덱스 순 의존) | 기본 정렬 키를 **명시**(PK DESC 등) | ⚠ `TIE_ORDER` — AS-IS 는 "운영에서 그렇게 보임" 수준의 미정 순서. 기본 정렬 결정은 근거 부족으로 기록 후 사람 확인 |
| `ROW_NUMBER() OVER (…)` 등 분석 함수 | 동일(MySQL 8 윈도우 함수) | |
| `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | `GROUP_CONCAT(x ORDER BY y SEPARATOR ',')` | ⚠ `group_concat_max_len` 기본 1024 **바이트** → 설정. Oracle `VARCHAR2(n BYTE)` 컬럼이 MySQL `VARCHAR(n)`(문자) 로 넓어지면 한글은 3배 → AS-IS 에서 여유였던 길이도 초과함(secu-sample 실측: 300자×2 절단). 세션 상향은 `spring.datasource.hikari.connection-init-sql: SET SESSION group_concat_max_len = 4096`. H2 는 상한 없음이라 **MySQL 테스트로만 검출** |
| `SYSDATE`/`TRUNC(SYSDATE)` 를 조건·저장 값으로 쓰는 statement | DB `NOW()`/`CURRENT_DATE` 대신 서비스가 `Clock` 으로 잡은 `#{baseDate}`/`#{regDt}`/`#{modDt}` 바인드 (XML 은 `<choose>` 로 null 이면 `CURRENT_DATE` 폴백) | ⚠ `SESSION_TZ` 일원화(앱 Clock = JDBC TZ) + 고정 Clock 으로 경계값 fixture 를 결정적으로 검증 가능. MyBatis 동일 세션 재조회는 로컬 캐시에 잡히므로 테스트에서 세션 변수 변경 후 재조회할 때는 쓰기 statement 로 캐시를 비운다 |
| `WM_CONCAT` | `GROUP_CONCAT` | |
| `MINUS` | `EXCEPT` (8.0.31+) | |
| `INTERSECT` | 동일(8.0.31+) | |
| `NULLS FIRST / LAST` | `ORDER BY (col IS NULL), col` 등 | ⚠ MySQL 기본: ASC 는 NULL 먼저, DESC 는 NULL 나중 — Oracle 기본과 **반대**(Oracle ASC 는 NULL 나중) |
| `(+)` 외부 조인 | `LEFT/RIGHT JOIN … ON` | ⚠ `(+)` 가 WHERE 조건에 섞이면 조인 조건 vs 필터 조건 분리 필요 |
| `CONNECT BY PRIOR … START WITH` | `WITH RECURSIVE` CTE | `LEVEL`→깊이 컬럼, `SYS_CONNECT_BY_PATH`→경로 누적, `ORDER SIBLINGS BY`→CTE 안 정렬 키 |
| `ORDER SIBLINGS BY sort_no` | CTE 에 경로 정렬키 누적: `CONCAT(p.path_key, LPAD(c.sort_no, 5, '0'), LPAD(c.id, 10, '0'))` 후 `ORDER BY path_key` | ⚠ `TIE_ORDER` — 형제 SORT_NO 동순위는 Oracle 도 미정. PK 를 경로키에 덧붙여 고정 |
| 재귀 CTE 안의 문자열 누적 컬럼(경로키·`SYS_CONNECT_BY_PATH`) | 앵커에서 `RPAD(CONCAT(…), 240, ' ')` 로 폭을 고정하고 재귀부는 `RPAD(CONCAT(RTRIM(t.path_key), …), 240, ' ')`. CTE 는 `WITH RECURSIVE t (col, …) AS (` 컬럼 목록 명시 | MySQL 은 **앵커 컬럼의 길이로 CTE 컬럼 타입을 정해** 재귀부에서 길어진 값을 절단(strict 면 오류). `CAST(… AS CHAR(n))` 은 H2 가 공백 패딩이라 양쪽 공용 불가 → RPAD/RTRIM. H2 는 CTE 컬럼 목록이 없으면 구문 오류 (secu-sample 실측) |
| 숫자 → `LPAD` 인자 | `LPAD(CONCAT('', n), 5, '0')` | H2 `LPAD` 는 문자열 인자만 받으므로 `CONCAT('', n)` 으로 문자열화(양쪽 공용) |
| `CONNECT_BY_ISLEAF` | 외부 SELECT 에서 `NOT EXISTS (SELECT 1 FROM t c WHERE c.parent_id = n.id)` → 1/0 | 소비 코드가 `'1'` 문자열 비교(ftl `?string == '1'`)면 반환 타입(정수) 유지 |
| `LPAD(' ', (LEVEL-1)*2, ' ') \|\| name` (들여쓰기) | `CONCAT(REPEAT(' ', (depth-1)*2), name)` | ⚠ `CONCAT_NULL` — Oracle `LPAD(x, 0)` 은 NULL 이지만 `NULL \|\| name` = name 이라 결과 동일. MySQL `REPEAT(' ',0)` = `''` → 동일. 판정 "동작 동일" |
| `MERGE INTO … WHEN MATCHED/NOT MATCHED` | `INSERT … ON DUPLICATE KEY UPDATE` | ⚠ UNIQUE 키가 조인 조건과 같아야 함. 아니면 앱 로직(조회 후 분기) |
| `seq.NEXTVAL` / `CURRVAL` | `AUTO_INCREMENT` + `useGeneratedKeys` / `LAST_INSERT_ID()` | ⚠ 채번을 먼저 하고 여러 테이블에 쓰는 패턴은 시퀀스 테이블 또는 앱 채번 |
| `DELETE FROM t WHERE …` 서브쿼리 자기참조 | MySQL 은 같은 테이블 서브쿼리 금지 → 파생 테이블로 감싸기 | |
| `UPDATE t SET (a,b) = (SELECT …)` | `UPDATE t JOIN (SELECT …) s ON … SET t.a=s.a` | |
| `REGEXP_LIKE(s, p)` | `s REGEXP p` | ⚠ 정규식 방언(POSIX 클래스) |
| `TRIM(LEADING '0' FROM s)` | 동일 | |
| `RPAD/LPAD` | 동일 | ⚠ 길이 0: Oracle NULL, MySQL `''`. 단독 소비(NULL 체크) 시 차이 |
| `col LIKE '%' \|\| #{kw} \|\| '%'` / 문자열 `ORDER BY` / `=` 비교 | `col LIKE CONCAT('%', #{kw}, '%')` | ⚠ `COLLATION` — Oracle 기본(BINARY) 은 대소문자·악센트 구분, MySQL 8 기본 `utf8mb4_0900_ai_ci` 는 무시. 검색 결과 집합·정렬 순서가 달라질 수 있음 → 컬럼/DB collation 을 brief §12 에서 결정 |
| `GREATEST/LEAST` | 동일 | ⚠ NULL 인자: Oracle NULL, MySQL NULL — 동일 |
| `EXTRACT(YEAR FROM d)` | 동일 | |
| `TO_CHAR(n, 'FM999,999')` | `FORMAT(n, 0)` | 로케일 |
| `CASE WHEN … THEN 'Y' ELSE 'N'` | 동일 | |
| 힌트 `/*+ INDEX(…) */` | 제거 (필요 시 `USE INDEX`) | 성능 근거 부족으로 기록 |
| `DBMS_LOB.SUBSTR` | `SUBSTR` (TEXT) | |
| `EMPTY_CLOB()` / `EMPTY_BLOB()` | `''` | |
| 바인드 `:name` (iBatis) | `#{name}` | |
| PL/SQL 블록·`BEGIN … END;` in mapper | **앱 로직으로 이전**(서비스 메서드 + 트랜잭션) | 매핑표에 로직 기술 |
| 저장 프로시저 `{call …}` | 앱 로직 또는 MySQL 프로시저(근거 있을 때만) | |
| `FOR UPDATE NOWAIT / SKIP LOCKED` | `FOR UPDATE NOWAIT / SKIP LOCKED` (8.0+) | |
| `RETURNING … INTO` | `useGeneratedKeys` 또는 후속 SELECT | |
| `SELECT … INTO` | 앱 로직 | |
| 식별자 대문자·따옴표 | MySQL 은 `lower_case_table_names` 설정 의존 → 전부 소문자 스네이크로 통일 | ⚠ |

### 2-2. 의미 차이 태그 (⚠) — 반드시 소비 코드로 판정
| 태그 | 차이 | 판정 방법 |
|---|---|---|
| `EMPTY_NULL` | Oracle `''` = NULL, MySQL 은 구분 | 해당 컬럼에 `''` 가 저장/비교되는 경로가 있는가. 있으면 저장 시 `NULLIF(x,'')` 또는 비교 시 `COALESCE(x,'')=''` 로 통일하고 매핑표에 결정 |
| `NULL_ORDER` | ASC 시 NULL 위치 반대 | ORDER BY 컬럼이 NULL 가능하고 화면 순서가 의미 있으면 명시 정렬 |
| `TIE_ORDER` | 동순위 정렬·ROWNUM 순서 미정 | 페이징 화면이면 PK tie-breaker 추가(AS-IS 도 미정이었음을 기록) |
| `SUBSTR0` | `SUBSTR(s,0,n)` | 인자 0 을 1 로 |
| `DATE_TRUNC` | 날짜 절단·산술 | 경계값(자정·월말) fixture |
| `CONCAT_NULL` | `\|\|` NULL 전파 | `CONCAT_WS`/`IFNULL` |
| `IMPLICIT_CAST` | 문자↔숫자 암묵 변환 | 타입 명시 |
| `CHAR_PAD` | `CHAR(n)` 공백 패딩 비교 | MySQL 은 후행 공백 무시 비교(PAD SPACE) — 대체로 동일, `VARCHAR` 전환 시 확인 |
| `CASE_ID` | 식별자 대소문자 | 소문자 통일 |
| `SEQ` | 채번 시점·다중 테이블 | 앱 채번 결정 |
| `MERGE_KEY` | MERGE 조인 키 ≠ UNIQUE | 앱 로직 |
| `GROUP_CONCAT_LEN` | 길이 상한 | 설정 + 상한 검증 |
| `COLLATION` | 문자열 비교·LIKE·ORDER BY 의 대소문자/악센트 구분 (Oracle BINARY vs MySQL `_ai_ci`) | 검색 키워드·정렬 컬럼이 영문/혼합이면 결과 집합·순서 차이. `_bin` 또는 `_as_cs` collation 지정 여부를 brief §12 로 결정하고 fixture(대소문자 혼합) 로 검증 |
| `SESSION_TZ` | `SYSDATE`/`NOW()`·날짜 비교의 세션 타임존 | JDBC `connectionTimeZone`/`serverTimezone` 을 Asia/Seoul 로 고정, 배치 실행 시각(예: 00:10) 과 `CURDATE()` 경계 fixture |

## 3. 변환 절차 (stage2 B-2, sql-migrator)

statement 하나마다:
1. 인벤토리 행을 읽고 **소비 코드**(호출처 Java + 그 결과를 쓰는 서비스/ftl) 를 연다.
2. Oracle 구문 태깅 → §2-1 로 변환 초안 → ⚠ 태그마다 §2-2 판정(소비 코드 근거 `파일:라인`).
3. Mapper 인터페이스 메서드 시그니처 결정(파라미터 DTO/`@Param`, 반환 DTO). `resultMap` 이 Oracle 대문자 컬럼을 쓰면 소문자 별칭으로.
4. `<sql>` fragment·`<include>` 는 유지하되 방언 변환 적용.
5. **매핑표 행 작성** (`docs/deliverables/mapping/<slice>-sql-mapping.md`): AS-IS `ns.id` → TO-BE `Mapper#method` | 사용 구문 태그 | 변환 규칙 | ⚠ 판정·근거 | 검증 fixture 종류 | 상태(변환/앱로직이전/폐기/근거부족).
6. 변환 후 **H2 MODE=MySQL 이 아닌 실제 MySQL(testcontainers)** 로 실행 가능한지 Mapper 테스트 1건 이상(⚠ 항목은 경계값 fixture 포함).

## 4. 등가성 검증 (stage5, 정적 카탈로그 방식)

Oracle 을 못 돌리므로 "AS-IS 결과" 는 **AS-IS 코드의 소비 방식 + 카탈로그 의미 규칙**으로 추론한다.
- ⚠ 태그 statement 마다 경계값 fixture: 빈 문자열/NULL 컬럼, 동순위 정렬 키, 월말·자정·윤년 날짜, 대소문자 혼합, `SUBSTR` 경계, 다중 행 MERGE 충돌, GROUP_CONCAT 상한 초과.
- 기대값은 "Oracle 이라면" 의 규칙에서 도출(예: `NVL('',x)` 는 x) — 이 도출 근거를 시나리오에 적는다. 소비 코드가 그 차이에 둔감하면(예: null 체크 후 동일 처리) "동작 동일" 로 판정.
- `${}` 동적 SQL 은 파라미터 조합별로.
- 판정 불가(소비 코드가 없거나 외부 시스템이 소비)는 근거 부족으로 남기고 사람 확인.

## 5. 산출물·게이트
- stage0: `ASIS_SQL_INVENTORY.md`(4분류·통계), B 분류는 RR(high).
- stage2: slice 별 `<slice>-sql-mapping.md` 100% 행 채움(상태 "근거부족" 허용, "미처리" 불가), Mapper ↔ XML ↔ 호출처 3자 일치 테스트(reflection 으로 인터페이스 메서드 ↔ statement id 전수 비교 1건), ⚠ 항목 Mapper 테스트.
- stage5: ⚠ 항목 경계값 시나리오 전수 + 호출처가 도달하는 모든 statement 최소 1회 실행(커버리지: 인벤토리 A 항목 ÷ 실행된 statement).
- reviewer(§D-2/§D-4 확장): 매핑표 행 누락, ⚠ 판정 근거 없음, `${}` 잔존, 대문자 별칭 잔존, `sqlSession` 직접 호출 잔존 grep 0.

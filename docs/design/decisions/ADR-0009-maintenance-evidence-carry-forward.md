# ADR-0009 — P06-MAINT 유지보수 성능 증거 승계

Status: Accepted for the Session 06 version-only 0.1.1 patch; applicability requires evidence.
Date: 2026-09-27
Supersedes in part: validation의 다른 identity로 재사용 금지 및 전체 qualification 재실행 규칙.
승인 근거: 현재 소유자의 DEV-06 실행 지시. 새 출하 권한은 포함하지 않는다.

## 문제와 결정

ABI 15는 grammar version을 parser.c에 넣는다. 따라서 version-only patch도 새
artifact identity를 갖는다. 전체 source 동작이 같은 patch에 대해 과거 성능 관측의
적용성을 명시적으로 검토할 수 있게 하되, 새 correctness·안전성 검사는 유지한다.

다음 조건을 모두 만족한 **이번 0.1.1 patch만** S572-CONFIRM-01의 성능 근거를
`CARRIED_FORWARD`로 사용할 수 있다. 일반 parser 변경이나 후속 release의 자동 예외가 아니다.

1. v0.1.0 공개 source 자산을 tag의 모든 blob과 대조한다. B0(tag), B(main),
   P(product), Cq(검증), C(보고서 bridge), M(승인 후 merge)를 구분한다.
2. grammar.js, scanner, query, schema, generated headers, 기존 fixture/golden은 byte 불변이다.
   package 및 lock의 root version, tree-sitter.json의 metadata.version만 0.1.0→0.1.1로 바꾼다.
3. 고정 generator/ABI/JS runtime으로 독립 위치에 두 번 생성한다. parser의 유일한
   language metadata initializer에서 patch 0→1만 허용하고 그 밖의 모든 byte는 일치해야 한다.
   넓은 whitespace/version/숫자 정규화는 금지하며 정상·변조 대조로 비교기를 검사한다.
4. 생산 runtime/compiler/flags, qualification 입력·protocol·판정 의미를 보존한다.
   source 비교를 모든 입력의 수학적 동등성이나 동일 latency 증명으로 부르지 않는다.
5. baseline raw/input/build/protocol/판정기와 해시 연결이 존재해야 한다.
   각 claim은 baseline/candidate component manifest, 변경 의존성, 동일성 증거,
   review, 한계를 갖는다. 필수 미확정 hash는 부적격이다.
6. 새 correctness·robustness·W12·source-only 및 합의한 native safety 검사를 수행한다.
   새 반례·보안 보고·현재 실패가 inherited claim에 material하면 해당 승계를 거절한다.
7. 변경 도구를 새로 검증한다. 과거 raw 재집계는 새 parser 실행이 아니다.
   reviewer는 dependency mapping을 검토하고 별도 context/동일 모델 여부를 공개한다.
8. 결과와 release notes는 성능 수치가 v0.1.0 S572 실측임을 명시한다.

## 새 검사와 승계의 구분

| 검사 | 0.1.1 의무 |
|---|---|
| V0/version/license/links 및 도구 자기검사 | 새 실행 |
| V1 두 clean 생성과 strict metadata 비교 | 새 실행 |
| V2/V3 registry/corpus/schema/samples/spellings | 새 실행 |
| V4 full query/highlight와 recovery golden | 새 실행 |
| V5 incremental/repair/resume/reset representative set | 새 실행 |
| V6 W12 | 새 두 번 기록과 이전 content 대조 |
| V10 bounded robustness/guards/edit fuzz | 새 실행 |
| native memory instrumentation와 coverage-guided fuzz | 별도 고정 profile 및 실제 관측; edit fuzz와 구분 |
| S572 full timing campaign과 7개 finding의 자원 관측 | 위 조건 충족 시에만 CARRIED_FORWARD |
| 수정하지 않은 known-bad 도구 효력 | input/도구 동일성을 검토한 기존 증거 가능 |
| L1 refresh, exact C/M CI, source/package/download | 새 실행 |
| V7 새 비교, V8 장비, V9/Go | 이번 범위 밖; 과거 상태 보존 |

승계 row의 `execution_status=NOT_RUN`, `evidence_mode=CARRIED_FORWARD`,
`eligibility=ACCEPTED_UNDER_P06_MAINT`를 분리한다. NOT_RUN을 새 PASS로 바꾸지 않는다.
계측 도구의 새 compiler/profile은 test-only이며 생산 toolchain이나 성능 증거에 섞지 않는다.

## 실패·bridge·출하

불일치나 미해결 의존성은 `REUSE_REJECTED`다. 전체 lane을 자동 재시작하지 않고
영향 검사 또는 patch 중단을 판단한다. 기준 완화·필수 검사 면제·새 scope는 소유자 결정이다.
Cq→C 전체 diff는 미리 정한 결과/출하 상태 문서만 허용한다. 제품/검사/input/policy가
바뀌면 bridge가 실패한다. 승인 뒤 tree(M)=tree(C)를 따로 검사한다.
필수 미실행은 release readiness를 충족하지 않는다. main/tag/Release는 exact Gate B 승인 뒤 진행한다.

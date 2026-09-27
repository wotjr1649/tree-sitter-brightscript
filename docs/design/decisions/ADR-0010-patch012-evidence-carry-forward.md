# ADR-0010 — P07-MAINT: v0.1.2의 조건부 근거 승계

Status: Accepted under DEV-07P; 적용 적격성은 별도 증명한다.
Date: 2026-09-27
승인 근거: 소유자의 Session 07 실행 지시. 출하 승인은 포함하지 않는다.

## 결정

이번 v0.1.2는 공개 raw 재판정 도구, 근거 문서, 한정 검사와 version metadata의
유지보수다. ADR-0009는 v0.1.1의 역사 계약으로 유지한다. 이번 예외는 다음 조건을
모두 충족한 v0.1.1→v0.1.2에만 적용하며 다음 release의 자동 예외가 아니다.

1. 공개 v0.1.1 source의 모든 blob/mode를 tag tree와 연결한다.
2. grammar, scanner, query, schema, headers, fixture/golden, parser 실행 table은
   byte 불변이다. root package/lock 및 tree-sitter metadata version과 parser의
   유일한 language metadata patch 1→2만 허용한다.
3. 고정 generator/ABI 15로 두 clean 생성이 일치하고, version을 0.1.1로 되돌린
   counterfactual 생성이 tag의 전체 generated 파일과 일치해야 한다.
   `check_maintenance_012.py`가 정확한 delta를 검사한다. 기존 비교기는 변경하지 않는다.
4. S572/S06 raw, 입력, source, build, seed, protocol과 gate 판정의 의존성을
   hash로 연결한다. h/bp, threshold, floor, actual/safety 취소 기준은 유지한다.
5. 새 반례나 현재 실패가 승계할 주장에 영향을 주면 해당 승계를 거절한다.
   유한 screen의 무보고를 모든 입력의 정확성·안전성으로 확대하지 않는다.
6. 변경 도구의 정상·변조 대조, V0–V6/V10, full highlight, W12 두 기록,
   대표 incremental/repair/resume/reset, 새 boundary screen을 검증한다.
   S06 ASan/coverage 근거의 의존성을 확인하고 새 위험 입력은 같은 계측 recipe로
   한정 replay한다. 신규 full fuzz나 timing campaign은 이 예외가 요구하지 않는다.
7. Windows와 Ubuntu에서 frozen source/raw로 새 공개 verifier를 실행한다.
   source-only/package, exact 후보 CI, 독립 적대적 검토와 출하 이후의 검증은 별도 의무다.

## 공개 재판정

원 bundle/source와 새 candidate graph를 분리한다. 원 산식은 hash가 고정된 원
module로 계산하며, source manifest/import path/module cache/raw 소비 수를 확인한다.
candidate는 별도 source hash, mode, Git tree/commit object, version delta 증명을 갖는다.
SHA-256과 Git object 검사는 무결성 검사다. 신뢰 anchor는 확인한 공개 tag와 자산이다.

등록한 `math.log` 기반 파생 exponent만 finite normal, 같은 부호에서 대칭 2 ULP를
허용한다. zero/subnormal/signed zero, 원시 값, threshold와 모든 의미 구조·type은 exact다.
threshold의 ±2 ULP 구간 교차, max 승자 변경, verdict 변경은 자동 적격성을 얻지 못한다.
원 FAIL을 PASS로 바꾸지 않는다. 상세 정책과 실행법은
[public-replay.md](../../validation/public-replay.md)에 둔다.

## 보고와 출하

과거 timing은 `execution_status=NOT_RUN`, `evidence_mode=CARRIED_FORWARD`,
`eligibility=ACCEPTED_UNDER_P07_MAINT`로만 적용한다. raw 재판정은 `REPLAYED_RAW`,
새 correctness/계측 replay는 `NEW_RUN`이다. 계측 시간은 성능 수치가 아니다.
별도 context의 같은 계열 모델 검토와 독립 native 재실행을 구분한다.

기준 완화, 새 문법, public-tree 변경, 새 final campaign 재시작은 별도 결정이다.
최종 후보와 다섯 자산의 새 Gate B-07P 승인 전에는 main/tag/Release를 변경하지 않는다.
승인 후 tree(M)=tree(C), exact CI와 공개 다운로드/source-only/verifier 검증을 마친 뒤에만
공개 완료와 동결을 기록한다. 자동 후속 작업은 만들지 않는다.

# 공개 자료의 offline 재판정

v0.1.2 verifier는 원 v0.1.1 verification/source와 새로운 candidate source를
분리해서 검사한다. 신뢰한 tag와 release 자산의 SHA-256을 먼저 확인한다.
두 ZIP을 별도 디렉터리에 풀고 verification 디렉터리에서 실행한다.

```text
python -I -B -X utf8 verify_public.py --bundle baseline --baseline-source baseline-source --candidate-source <source-root> --candidate-registration candidate-registration.json
```

v0.1.2 출하 당시 검증 대상은 CPython 3.14의 Windows/Ubuntu였다.
이후 Session 08 소스 CI는 macOS 15 ARM64에서도 같은 offline 재판정을 통과했다.
실제 patch/platform은 각 결과에 기록하며, 후속 관측을 원 출하 근거로 소급하지 않는다.
`-I`는 외부 Python 경로를 격리하며 `-O`는 명시적으로 거부한다.
이 명령은 파일을 변경하거나 native parser, Git, 네트워크를 실행하지 않는다.
준비용 `scripts/prepare_public_replay.py`는 별도 명령이며 고정 공개 baseline 자산 두 개만
가져온다. 후보 packaging은 clean committed source의 blob/mode에서 수행한다.
source와 verification ZIP은 압축하지 않은 고정 metadata entry를 사용한다.
따라서 host의 zlib 차이에 의존하지 않고 원 출하의 두 OS에서 같은 archive bytes를 검증할 수 있었다.

검증은 전체 manifest와 source hash, 경로·중복·link, 실제 원 module 경로/hash,
원 8,875 run의 회차별 단일 소비를 확인한다. 17 gate 가운데 13개는 원 raw에서
재판정한다. 나머지 네 gate는 보존된 기록이며 이 도구로 독립 재실행하지 않는다.
새 후보의 source/mode/Git object와 v0.1.1→v0.1.2 product proof를 따로 검사한다.
결과에 실제 Python/platform/libc와 `REPLAYED_RAW`를 기록한다.
candidate 인자를 생략한 내부 조사 모드는 `HISTORICAL_BASELINE_ONLY`이며 원 manifest로
baseline만 검사한다. 새 자산 검증은 두 candidate 인자를 모두 제공한
`CANDIDATE_AND_BASELINE` 결과를 요구한다. baseline-only PASS를 후보의 PASS로 쓰지 않는다.

## 비교 정책 S07-REPLAY-2ULP-r1

dict keys, 배열 길이·순서, ID, bool/int/float/string/null, verdict, 원시 timing과
limit/threshold는 exact다. duplicate JSON keys와 비유한 값은 거부한다.
허용 대상은 `replay_compare.py`가 gate와 의미적 point ID로 지정한 log exponent뿐이다.
finite normal, 같은 부호, 2 ULP 이하의 차이를 허용하되 zero/subnormal은 bit exact다.
threshold의 ±2 ULP 구간이 경계를 넘거나 max의 승자가 바뀌면 보수적으로 거부한다.
전체 JSON 반올림, global relative/absolute tolerance, array index 예외는 없다.

`BITWISE_EQUAL`과 `REPLAY_EQUIVALENT_WITH_DECLARED_ROUNDING`은 다른 결과다.
기록된 q3의 한 exponent는 0.9594822625200103과 0.9594822625200102의 차이를
보였다. 이는 파생 표현의 이식성 문제이며 parser 성능 FAIL이 아니다.
archived Linux 3.13.5 관찰, 산식을 이용한 synthetic 대조, 현재 host의 실제 실행을
구분한다. 모든 libm 구현이 이 정책을 만족한다는 주장은 하지 않는다.

이 도구의 PASS는 raw 무결성과 좁은 재판정의 성공이다. 새 native 측정,
전체 언어 지원, Roku 기기 검증이나 release 승인으로 해석하지 않는다.
적격성은 [ADR-0010](../design/decisions/ADR-0010-patch012-evidence-carry-forward.md)과
[validation](validation.md)의 나머지 gate를 포함한다.

# 변경 이력

## 0.1.3 — release candidate

- Windows x64, Ubuntu x64, macOS 15 Apple Silicon ARM64의 소스 빌드와 공통 기능 CI를 추가한다.
- macOS의 `ru_maxrss` 단위와 `/var` 경로 정규화에 따른 공개 자료 추출 오류를 수정한다.
- 문법, scanner, query, public tree는 유지한다. 배포는 소스 전용이며 OS별 바이너리는 제공하지 않는다.
- [후보 검증 기록](docs/reports/0.1.3-release-candidate.md)에 검증 범위와 출하 조건을 둔다.

## 0.1.2 — 2026-09-27

[v0.1.2](https://github.com/wotjr1649/tree-sitter-brightscript/releases/tag/v0.1.2)를
새 Gate B-07P 승인 뒤 공개했다. 익명 다운로드·다섯 자산 hash·source-only·public verifier 검증을 완료했다.

- 공개 raw verifier의 지정된 log 파생값에만 엄격한 2 ULP 비교를 적용한다.
  원시 값·판정·threshold·source identity는 완화하지 않는다.
- 혼합된 근거의 범위와 51개 미확정 요구사항을 재검토하고 한정 boundary 검사를 추가한다.
- grammar/scanner/query/public tree는 유지한다. version metadata만 고정 generator로 재생성한다.
- [P07-MAINT](docs/design/decisions/ADR-0010-patch012-evidence-carry-forward.md)의
  적격성, exact CI·자산과 새 출하 승인을 확인했다. 과거 성능 근거는 승계이며 새 성능 개선을 주장하지 않는다.

## 0.1.1 — 2026-09-27

[v0.1.1](https://github.com/wotjr1649/tree-sitter-brightscript/releases/tag/v0.1.1)을 공개하고
익명 다운로드·hash·source-only 검증을 완료했다. 유지보수 동결을 활성화했다.

- 현재 계약과 역사적 보고서의 범위를 구분하고 유지보수·보안 안내를 추가한다.
- version metadata만 재생성하고, 엄격한 비교와 새 회귀 검사를 요구한다.
- [P06-MAINT](docs/design/decisions/ADR-0009-maintenance-evidence-carry-forward.md)는
  조건을 모두 증명한 이 patch의 성능 증거에만 적용한다. 과거 v0.1.0 실측을 새 측정이라고 하지 않는다.
- 필수 native 안전성 증거와 출하 자산은 [출하 기록](docs/reports/0.1.1-maintenance-release.md)에서 확인한다.

## 0.1.0 — 2026-09-26

첫 공개. [출하 기록](docs/reports/0.1.0-release.md#release-v010),
[검증 이력](docs/reports/0.1.0-integrated-qualification.md)을 참고한다.

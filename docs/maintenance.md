# 유지보수와 동결

현재 공개 버전은 [v0.1.0](reports/0.1.0-release.md#release-v010)이다.
v0.1.1 유지보수 후보의 상태·검증·제약은 [후보 기록](reports/0.1.1-maintenance-release.md)에 둔다.
공개 tag와 Release 자산, 게시 뒤의 외부 receipt가 출하 사실을 식별한다.

## 동결

v0.1.1의 공개 다운로드·source-only 검증을 마친 뒤에만
`FROZEN_UNTIL_TRIGGER`를 활성화한다. 준비 완료나 승인 대기는 동결 완료가 아니다.
기존 이슈·보안 신고 경로는 유지하며 저장소를 archive하지 않는다.
자동 연구, 정기 watcher, 자동 의존성 갱신과 자동 릴리스는 만들지 않는다.

다음 사실이 재현되거나 확인되면 triage를 재개한다.

- correctness, crash, memory 오류, hang, 재현 가능한 build 결함;
- 현재 grammar/runtime에 영향을 주는 upstream 보안·정확성 변경;
- 공식 BrightScript 문서와 현행 계약의 실제 충돌;
- 필수 CI 또는 고정 도구의 파손.

새 upstream tag, 기능 아이디어, 막연한 성능 개선은 자체 재개 사유가 아니다.
triage는 영향과 필요한 범위를 먼저 정하고 소유자의 권한 안에서 수행한다.
Go 통합, Roku 장비 검사, 전 OS 동일 latency, 새 기능은 이 유지보수 작업의 후속 의무가 아니다.

## 안전성과 지원 범위

배포물은 native grammar와 scanner source다. 소비자의 sandbox, 입력 한도,
메모리 cap, 취소 정책을 설치하지 않는다. 소비자는 자신의 실행 환경에서 이를 정해야 한다.
취소, null tree, resource cap과 미완료 결과는 성공 tree가 아니다.
유한 입력 검사의 무보고는 모든 입력의 안전성·기기 호환·leak-free 보장이 아니다.

검사 범위와 상태는 [validation](validation/validation.md), 신고 방법은
[SECURITY](../SECURITY.md), 변경 이력은 [CHANGELOG](../CHANGELOG.md)에 둔다.
과거 FAIL·raw·봉인과 공개 자산은 보존한다. 정정은 대상·근거를 명시해 덧붙인다.

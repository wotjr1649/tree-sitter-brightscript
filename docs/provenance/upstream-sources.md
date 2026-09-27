# Upstream sources and identities

Dated identities of every source the project relies on. Policy for using these
sources: [source-policy.md](source-policy.md). Values are observations at the
stated date, not guarantees about the upstream today.

## Level 1 — Roku documentation snapshot `roku-docs-2026-09-23`

Retrieved 2026-09-23 (UTC) with `curl`; every route answered HTTP 200 with no
redirect. No page served `ETag` or `Last-Modified`. Raw HTML is kept only in the
local `_ref/normative/roku-docs/` workspace.

Base URL: `https://developer.roku.com/dev/docs/`

| Route | Retrieved (UTC) | Page-declared modified (UTC) | Content-region SHA-256 | Region bytes |
|---|---|---|---|---|
| `brightscript-language-reference` | 2026-09-23T03:37:32Z | 2026-05-08T00:41:33Z | `fbf20981bd408f86d84bb3582e4e42d320cea6c5b1d9b49f1896f21755fdc9e9` | 2,811 |
| `statement-summary` | 2026-09-23T03:37:32Z | 2026-06-02T18:54:33Z | `8020ea7624129d2ddf45a3e1df02f4f6163fe98614da98003b958923d8dca797` | 2,472 |
| `program-statements` | 2026-09-23T03:37:32Z | 2026-09-17T13:14:48Z | `6fafd31136b4e00721447570ea0bfe3ac498a07af912ea25bdd424538b74dc69` | 37,874 |
| `expressions-variables-types` | 2026-09-23T03:37:32Z | 2026-09-22T21:46:36Z | `38bee10d10baa5a00d680f66b1e57790fc83558b5f50d8eaef1c7ba2340fabc3` | 51,174 |
| `reserved-words` | 2026-09-23T03:37:33Z | 2026-02-10T19:58:33Z | `32260686e464b8810c56c8fbc69a329435a3bf17736b0bb0973c97fba34f6ecf` | 1,254 |
| `conditional-compilation` | 2026-09-23T03:37:33Z | 2026-09-17T13:14:48Z | `631e08f6686f1edf7afacdd98767b9e42e6f5fcd1898cec83562cb7d7283c87c` | 8,436 |
| `error-handling` | 2026-09-23T03:37:33Z | 2026-09-22T21:46:36Z | `ad6dfc415d3a74e00d9ae2f95c3963e15a12f105480d9c818c9dcf8afaf1973b` | 32,667 |
| `release-notes` | 2026-09-23T03:37:33Z | 2026-09-22T21:46:36Z | `fd3c4735ba47dd0e276df9e3199b82e5acba59182556c1dd767694d7a35d42bb` | 311,640 |
| `component-architecture` | 2026-09-23T03:40:53Z | 2026-09-22T21:46:36Z | `eaf5c5ca0129e292ad15e8341e4bec43a27f3799c2550202a71c04c1b1f9076f` | 47,229 |
| `runtime-functions` | 2026-09-23T03:40:53Z | 2026-06-02T18:54:33Z | `3541a3c20253b08330a84d853964dd474c818e6821183d999957599ef3cc4375` | 11,363 |

Content region: raw response bytes from the first `data-testid="RDMD"`
(inclusive) to the next `class="UpdatedAt"` (exclusive). Reproduce with:

```sh
python -c "import hashlib,sys;b=open(sys.argv[1],'rb').read();i=b.find(b'data-testid=\"RDMD\"');j=b.find(b'class=\"UpdatedAt\"',i);print(hashlib.sha256(b[i:j]).hexdigest(),j-i)" page.html
```

Known limitations of this snapshot:

- No HTTP validators; freshness relies on page metadata and region hashes.
- Some served HTML is damaged by the site's Markdown rendering (for example
  lost `*`, `\=` and `{ }` tokens on `expressions-variables-types`); requirements
  rely on undamaged examples and cross-page evidence where prose is damaged.
- Official code blocks mix source with program output, console transcripts and
  a few typos; they are not automatically valid fixtures.

### Level 1 refresh `roku-docs-2026-09-23-r2`

Taken 2026-09-23T09:38:06Z–09:38:16Z (Session 03, before the release
candidate) with the same `curl` command and stored beside the first snapshot
in the local `_ref/normative/roku-docs-2026-09-23-r2/`; the first snapshot is
unchanged. Every route answered HTTP 200 with no redirect; page-declared
modification times are unchanged.

| Route | Content-region SHA-256 | Region bytes | Compared with `roku-docs-2026-09-23` |
|---|---|---|---|
| `brightscript-language-reference` | `fbf20981bd408f86d84bb3582e4e42d320cea6c5b1d9b49f1896f21755fdc9e9` | 2,811 | unchanged |
| `statement-summary` | `8020ea7624129d2ddf45a3e1df02f4f6163fe98614da98003b958923d8dca797` | 2,472 | unchanged |
| `program-statements` | `6fafd31136b4e00721447570ea0bfe3ac498a07af912ea25bdd424538b74dc69` | 37,874 | unchanged |
| `expressions-variables-types` | `38bee10d10baa5a00d680f66b1e57790fc83558b5f50d8eaef1c7ba2340fabc3` | 51,174 | unchanged |
| `reserved-words` | `32260686e464b8810c56c8fbc69a329435a3bf17736b0bb0973c97fba34f6ecf` | 1,254 | unchanged |
| `conditional-compilation` | `631e08f6686f1edf7afacdd98767b9e42e6f5fcd1898cec83562cb7d7283c87c` | 8,436 | unchanged |
| `error-handling` | `ad6dfc415d3a74e00d9ae2f95c3963e15a12f105480d9c818c9dcf8afaf1973b` | 32,667 | unchanged |
| `release-notes` | `d3d45fa3022bd7c5eac6253c5c2af870ab7b0865995e9d5fbf36b7b4778c3dd0` | 311,640 | changed hash, no text change (below) |
| `component-architecture` | `eaf5c5ca0129e292ad15e8341e4bec43a27f3799c2550202a71c04c1b1f9076f` | 47,229 | unchanged |
| `runtime-functions` | `3541a3c20253b08330a84d853964dd474c818e6821183d999957599ef3cc4375` | 11,363 | unchanged |

Review of the changed page (source-policy "Refresh and drift"). The
`release-notes` regions have the same length and differ in 64 bytes inside
two Cloudflare email-protection tokens (the `/cdn-cgi/l/email-protection#…`
link and its `data-cfemail` value) that the site re-encodes on every request
for one obfuscated e-mail address; the rendered text and every other byte are
identical. Requirements citing the page (their evidence, `since` values or
notes): BS-LEX-018, 029, 030; BS-LIT-011, 016; BS-TYPE-001; BS-EXP-007–010,
014, 016, 023; BS-STMT-002, 003, 019; BS-FUNC-014; BS-AA-002, 005;
BS-ERR-001–005; BS-COND-011. Outcome: no textual change, so every record
stands unchanged; the Roku OS 15.3 section still does not mention line
continuation (BS-EXP-023). Level 1 snapshot identity of the release
candidate: `roku-docs-2026-09-23-r2` (content equal to `roku-docs-2026-09-23`).

### Level 1 refresh `roku-docs-2026-09-26`

Taken 2026-09-26T03:29:09Z–03:29:25Z (Session 05-7, before the re-frozen
release candidate) with the same `curl` command and stored beside the earlier
snapshots in the local `_ref/normative/roku-docs-2026-09-26/`; they are
unchanged. Every route answered HTTP 200 with no redirect; page-declared
modification times are unchanged.

| Route | Content-region SHA-256 | Region bytes | Compared with `roku-docs-2026-09-23-r2` |
|---|---|---|---|
| `brightscript-language-reference` | `fbf20981bd408f86d84bb3582e4e42d320cea6c5b1d9b49f1896f21755fdc9e9` | 2,811 | unchanged |
| `statement-summary` | `8020ea7624129d2ddf45a3e1df02f4f6163fe98614da98003b958923d8dca797` | 2,472 | unchanged |
| `program-statements` | `6fafd31136b4e00721447570ea0bfe3ac498a07af912ea25bdd424538b74dc69` | 37,874 | unchanged |
| `expressions-variables-types` | `38bee10d10baa5a00d680f66b1e57790fc83558b5f50d8eaef1c7ba2340fabc3` | 51,174 | unchanged |
| `reserved-words` | `32260686e464b8810c56c8fbc69a329435a3bf17736b0bb0973c97fba34f6ecf` | 1,254 | unchanged |
| `conditional-compilation` | `631e08f6686f1edf7afacdd98767b9e42e6f5fcd1898cec83562cb7d7283c87c` | 8,436 | unchanged |
| `error-handling` | `ad6dfc415d3a74e00d9ae2f95c3963e15a12f105480d9c818c9dcf8afaf1973b` | 32,667 | unchanged |
| `release-notes` | `ff4a8110bcc226125f9d60587163048d328113b61d0bbb0830d38dc712ee07c1` | 311,640 | changed hash, no text change (below) |
| `component-architecture` | `eaf5c5ca0129e292ad15e8341e4bec43a27f3799c2550202a71c04c1b1f9076f` | 47,229 | unchanged |
| `runtime-functions` | `3541a3c20253b08330a84d853964dd474c818e6821183d999957599ef3cc4375` | 11,363 | unchanged |

Review of the changed page: as in the previous refresh, the 48 differing bytes
of the `release-notes` region all lie inside the two Cloudflare
email-protection tokens; with both masked the regions are byte-identical. The
requirements citing the page (listed above) stand unchanged. Level 1 snapshot
identity of the Session 05-7 release candidate: `roku-docs-2026-09-26`
(content equal to `roku-docs-2026-09-23`).

### Level 1 refresh `roku-docs-2026-09-27-session-06`

2026-09-27 Session 06에서 같은 공식 URL 10개를 새로 읽어 기존 snapshot 옆에 보존했다.
content-region 정의는 위와 같다. release-notes의 Cloudflare email-protection token 이외에
content byte 변화가 없으며 해당 토큰만 마스킹한 대조도 동일했다. 기존 requirement의
L1 근거·분류는 유지한다. 원문 전체는 Git/공개 verification asset에 포함하지 않는다.

| Route | Content-region SHA-256 | Region bytes |
|---|---|---|
| `brightscript-language-reference` | `fbf20981bd408f86d84bb3582e4e42d320cea6c5b1d9b49f1896f21755fdc9e9` | 2811 |
| `statement-summary` | `8020ea7624129d2ddf45a3e1df02f4f6163fe98614da98003b958923d8dca797` | 2472 |
| `program-statements` | `6fafd31136b4e00721447570ea0bfe3ac498a07af912ea25bdd424538b74dc69` | 37874 |
| `expressions-variables-types` | `38bee10d10baa5a00d680f66b1e57790fc83558b5f50d8eaef1c7ba2340fabc3` | 51174 |
| `reserved-words` | `32260686e464b8810c56c8fbc69a329435a3bf17736b0bb0973c97fba34f6ecf` | 1254 |
| `conditional-compilation` | `631e08f6686f1edf7afacdd98767b9e42e6f5fcd1898cec83562cb7d7283c87c` | 8436 |
| `error-handling` | `ad6dfc415d3a74e00d9ae2f95c3963e15a12f105480d9c818c9dcf8afaf1973b` | 32667 |
| `release-notes` | `0d5d58acf53036bfc861c192c6faba94f908334844c9d61475b0201750fdf045` | 311640 |
| `component-architecture` | `eaf5c5ca0129e292ad15e8341e4bec43a27f3799c2550202a71c04c1b1f9076f` | 47229 |
| `runtime-functions` | `3541a3c20253b08330a84d853964dd474c818e6821183d999957599ef3cc4375` | 11363 |

## Level 3 — Tree-sitter

| Item | Identity (observed 2026-09-23) |
|---|---|
| Repository | `https://github.com/tree-sitter/tree-sitter` |
| Latest stable release | `v0.27.0` → commit `6070dbfefd326bd735e5683eb128cc1b57dad0c0`, published 2026-08-30; npm `tree-sitter-cli` `latest` = `0.27.0` |
| Maintenance line | `v0.26.13` (not reachable from `master`) |
| Reference clone | `master` @ `659cda7c7f86ebe31cc825dc5da59e9add172dc7` (development toward 0.28; not a pin candidate) |
| ABI | generator emits ABI 14–15, default 15; ABI 15 embeds the `tree-sitter.json` version in `parser.c` metadata |
| Open issues relevant to pin selection | #5910 error-recovery regression in the 0.27.0 runtime; #5925 lexical conflicts can change keyword tokenization |
| Selected generator | **0.27.0**, adopted 2026-09-23 by the [ADR-0002](../design/decisions/ADR-0002-generator-pin-and-generated-artifacts.md) adoption procedure (record below) |

Structural references (conventions only, nothing copied):
`tree-sitter/tree-sitter-json` @ `254c42a6476413b776221e03982ac8ae159eeb72`,
`tree-sitter/tree-sitter-python` @ `26855eabccb19c6abf499fbc5b8dc7cc9ab8bc64`.

### Adopted generator

Adoption record (ADR-0002 "Adoption procedure"), 2026-09-23.

| Step | Result |
|---|---|
| 1. Eligible releases | GitHub releases that are not drafts or pre-releases, ≥ 0.26.0, with the same `tree-sitter-cli` version on npm, descending: 0.27.0, 0.26.13, 0.26.12, 0.26.11, 0.26.10, 0.26.9, 0.26.8, 0.26.7, 0.26.6, 0.26.5, 0.26.3 (0.26.4 and 0.26.1 are GitHub pre-releases; 0.26.0–0.26.2 are not on npm). No stable release newer than `v0.27.0`, so no Level 3 re-read was needed. Candidate: 0.27.0 |
| 2. Issue review | #5910 open — runtime error-recovery regression in 0.27.0 (labels `c-library`, `error-recovery`; runtime). #5925 open — "lib: lexical conflicts can change keyword tokenization" (label `parser`; runtime lexer). No other open issue names 0.27.0 in its title. Neither rejects the candidate; materiality is decided by ADR-0002 step 6 |
| 3. Identity | `tree-sitter-cli@0.27.0` exact devDependency; lockfile integrity `sha512-E42kR0og1mFlZBxPj7K4fBXCTjxPTGe19U9RXGWNq0FQKzXOxIp8bhCYFMKhddiVZUsJwW35MYGU9Q1oVYtpbA==`; release asset digests and decompressed binaries in the table below; the windows-x64 installed binary equals its decompressed asset byte for byte |
| 4. Capability smoke | `--abi 15` bootstrap grammar; `BS-LEX-006: CRLF between comment lines`, `BS-LEX-008: empty file`, `BS-LEX-008: only comments and blank lines` pass |
| 5. Determinism | two generations from a clean `src/` are byte-identical |

Tag `v0.27.0` → annotated tag object `3e719425fc48f5b4cdb25c580e44023882f5e2a7` →
commit `6070dbfefd326bd735e5683eb128cc1b57dad0c0`; release published
2026-08-30T17:16:26Z. Generated ABI: 15 (`LANGUAGE_VERSION 15`).

npm 12 blocks dependency install scripts unless `package.json` `allowScripts`
lists them. The entry `tree-sitter-cli@0.27.0` (pinned to the reviewed version)
lets the package's `install.js` run; it downloads the release asset below and
decompresses it, nothing else. `scripts/tscli.py`, the only path through
which the check scripts run the CLI, compares the installed binary with this
table before running it, on every platform (`scripts/check_generated.py`
reports the result).

| Release asset | Asset SHA-256 (equals the release `digest`) | Decompressed binary SHA-256 |
|---|---|---|
| `tree-sitter-windows-x64.gz` | `2d6c014b4e91d3d302ba7b30b3b625914027c3861ae7817e068a273e3f034550` | `9fbc4f285c876b1a38c7e9d5223a51fb7842255285cdd7db3ffb0ba3934f2662` |
| `tree-sitter-linux-x64.gz` | `20a1f39ec1c45f2211492dcb8881c802b643b554bb196869a29ac3778277fa77` | `5a228811cdb3a01b7e4dd493c5fc5e05b0040a49ffede94e866c4c58ff2605db` |

### Precedents and references cited by decisions

Observed 2026-09-23. Commits are the repository `HEAD` resolved that day with
`git ls-remote`; the observations were read from the default branch the same
day.

| Reference | Identity | Cited for |
|---|---|---|
| `https://github.com/tree-sitter/tree-sitter-c` | `b780e47fc780ddc8da13afa35a3f4ed5c157823d` | All preprocessor branches parsed as code, no scanner (ADR-0004) |
| `https://github.com/tree-sitter/tree-sitter-c-sharp` | `9150f7d56bb47f1a809fa23623f1ba1413e93fa9` | One grammar for C# 1–14 (ADR-0003); `#if` branches parsed as code, scanner not involved (ADR-0004) |
| `https://github.com/tree-sitter/tree-sitter-haskell` | `0975ef72fc3c47b530309ca93937d7d143523628` | Inactive CPP branches consumed as opaque text by an external scanner (ADR-0004) |
| `https://github.com/alex-pinkus/tree-sitter-swift` | `00bbb0a2550f8bc0023a2a4992922d51ae045626` | `#if` branches parsed as code; directive tokens external (ADR-0004) |
| `https://github.com/Isopod/tree-sitter-pascal` | `042119eca2e18a60e56317fb06ee3ba5c32cb447` | `{$IFDEF}` branches parsed as code (ADR-0004) |
| `tree-sitter/tree-sitter-python` (above) | `26855eab…` | Python 2 and 3 statements in one grammar (ADR-0003) |
| `https://github.com/tree-sitter/parser-test-action` | tag `v3` → `05f6ce7c7e54603c45cd87ed926725dc870bcc63` | Regeneration drift check compares `parser.c` only (ADR-0002) |
| `https://tree-sitter.github.io/tree-sitter/creating-parsers/6-publishing.html` | page as read 2026-09-23 | Semantic-versioning guidance for node types (`docs/specs/tree-schema.md`) |
| `https://github.com/tree-sitter/tree-sitter/issues/5910`, `/issues/5925` | open on 2026-09-23 | Pin-selection risks (ADR-0002) |
| `crates/cli/npm/install.js` in `tree-sitter/tree-sitter` @ `v0.27.0` | tag `v0.27.0` | npm CLI downloads its binary without checksum verification (ADR-0002) |
| `go-treesitter` `docs/design/decisions/ADR-0014-separate-gpl-grammar-distribution.md` | `0f3e720bf7ed2f776f8384f40d4b126f798c6cb4` | Grammar scanners carried as Go code downstream (ADR-0005) |

### Hosted CI actions

`.github/workflows/ci.yml` pins each action by commit (Session 04). Observed
2026-09-23 (UTC) with the GitHub API: each release tag is a lightweight tag on
the commit below, the latest release of its `v7` line, and the moving tag `v7`
resolved to the same commit (the commits the Session 03 runs downloaded).

| Action | Release | Commit |
|---|---|---|
| `actions/checkout` | `v7.0.1` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-node` | `v7.0.0` | `820762786026740c76f36085b0efc47a31fe5020` |
| `actions/setup-python` | `v7.0.0` | `5fda3b95a4ea91299a34e894583c3862153e4b97` |

The runner images (`ubuntu-latest`, `windows-latest`), Node 24.x (24.20.0 or
24.21.0 in the Session 04 runs) and Python 3.x are not pinned, and the npm
version CI uses is not logged, so whether it enforces `allowScripts` is not
known; either way the generator binary is compared with the table above
before it runs (`scripts/tscli.py`).

## Level 4 — Comparative

| Source | Identity (observed 2026-09-23) | Notes |
|---|---|---|
| BrighterScript `https://github.com/rokucommunity/brighterscript` | `v0.73.5` = `01a359c69a05f2238b514bfca26e96517783020d` | Superset language. The separate `v1.0.0-alpha` line was not evaluated. |

## Level 5 — Historical

| Source | Identity | Notes |
|---|---|---|
| `https://github.com/ajdelcimmuto/tree-sitter-brightscript` | `253fdfaa23814cb46c2d5fc19049fa0f2f62c6da` | Queries reference node `m`, but committed `src/parser.c` was not regenerated (170 symbols, no `m`). Pinned by `go-treesitter`. |
| same | `0c534d56bb04778d0a3510bed5e720d1fe15cb76` | Direct child of `253fdfaa`; regenerates `src/*` and corpus only (upstream issue #16). Pinned by nvim-treesitter (tier 2) as of 2026-09-23. |

License metadata in that repository conflicts (`package.json` ISC, `Cargo.toml`
MIT, no `LICENSE` file). Nothing from it is used as specification.

## Downstream

| Consumer | Identity (observed 2026-09-23) | Relevant facts |
|---|---|---|
| `https://github.com/wotjr1649/go-treesitter` | `session/07-product-hardening` @ `0f3e720bf7ed2f776f8384f40d4b126f798c6cb4` | Pins the legacy grammar at `253fdfaa`; consumes checked-in `src/parser.c` through `ts2go`; C oracle runtime v0.25.1 accepts ABI 13–15; already consumes an ABI 15 parser (`tree-sitter-python` @ `26855eab`). |

## Level 2 — Official behaviour

None recorded.

## Session 06 bounded upstream check (2026-09-27)

The latest stable Tree-sitter release read from the official release API remains v0.27.0.
Issues [#5910](https://github.com/tree-sitter/tree-sitter/issues/5910) and
[#5925](https://github.com/tree-sitter/tree-sitter/issues/5925) remain open (runtime recovery / lexer).
Their historical relevance stays disclosed; no pin change is made from release freshness alone.
The maintenance evidence uses the unchanged production runtime/compiler recipe.

The separately approved Windows safety tool is portable LLVM MinGW 20260922, test-only:
[maintainer asset](https://github.com/mstorsjo/llvm-mingw/releases/tag/20260922), UCRT x86_64 ZIP
SHA-256 `e3ad77d117a4bea19a7a3b333341824d79a5a371004a10e25b8504e7b3047666`.
Acquisition is not sanitizer or coverage evidence; capability tests and the fixed profile are required.
The production Tree-sitter/GCC pins and default qualification guards stay unchanged.

## Session 07 근거 갱신 (2026-09-27)

UTC 10:14:07–10:14:22에 기존 필수 L1 10페이지와 ifSGScreen을 직접 조회했다.
아래 SHA-256은 수신한 HTML 전체의 hash다. 본문 영역을 비교하고 동적 cfemail token만
제외했을 때 기존 10페이지의 규범 내용 변화는 관찰되지 않았다. 이는 언어 전반의 완전성 검사가 아니다.

| L1 문서 | 수신 HTML SHA-256 |
|---|---|
| [brightscript-language-reference](https://developer.roku.com/dev/docs/brightscript-language-reference) | `d09d27ff31297e02b6d0bc00cfa12e6823a7ae2d456a31a00a049135437a1ca9` |
| [statement-summary](https://developer.roku.com/dev/docs/statement-summary) | `dd3f3ce585d0c8385d4af9403608234c7dfc1f388f63a75187b405e566322aa8` |
| [program-statements](https://developer.roku.com/dev/docs/program-statements) | `39d757eb33e1e06ef91d97c1ba41f1445b8d26c06ca8d2a95cdf4f940a3b4740` |
| [expressions-variables-types](https://developer.roku.com/dev/docs/expressions-variables-types) | `5b7b94c7750fecd2aee621546c5f505f87126ff4fe168004145f9539e5ddb5dc` |
| [reserved-words](https://developer.roku.com/dev/docs/reserved-words) | `d92f59496c92a4ee238de7c769540ff8f59179dfa90d1cf21492c7fb4ffd32d5` |
| [conditional-compilation](https://developer.roku.com/dev/docs/conditional-compilation) | `6d4363a45d2821e75696f8d616a71c6db3be9642c7726ffb4879d5d7e27ac26e` |
| [error-handling](https://developer.roku.com/dev/docs/error-handling) | `113268923a8da738bb73732ae3b8e1a06fa26d8179e92ab8c88e2db915e07ae2` |
| [release-notes](https://developer.roku.com/dev/docs/release-notes) | `036d155628e4014fa775d818fc7eb5d70df9d0d267b60324aa17cdae9cad748e` |
| [component-architecture](https://developer.roku.com/dev/docs/component-architecture) | `881c67514fdfb11d80356ff36ddf64ddd7181b28e1f0bc90ebcecc94c3a0da0f` |
| [runtime-functions](https://developer.roku.com/dev/docs/runtime-functions) | `d5c3ef5d3287ffbc63c91c4fcf5ae28ae66259ddabe89d8b11f72b5f15f72ed3` |
| [ifsgscreen](https://developer.roku.com/dev/docs/ifsgscreen) | `0e55b9151bb8881230b5d01f06841ad17386d534d09fcb4a48d3a8ce4f3e2e1f` |

ifSGScreen의 Starting Scene Graph Applications 예제에서 0xAARRGGBB 형태의
세 색상 literal을 확인했다. 이는 BS-LIT-006의 좁은 하위 근거다. 폭·부호·overflow·suffix
전반을 규정하거나 parent의 provisional 상태를 해제하지 않는다. 공식 원문은 공개 자산에 복사하지 않는다.

동일 날짜 공식 GitHub API에서 Tree-sitter v0.27.0이 latest stable, #5910과 #5925가 open,
PR #5614는 closed·unmerged임을 확인했다. 소형 nested-AA와 lexer 검사는 한정된 영향 조사다.
BrighterScript v0.73.5 commit은 위 L4 identity와 같았다. 설치된 dependencies가 없어 동적 비교는
실행하지 않았다. Lexer→Preprocessor→Parser→type conversion→Program validation source를
구분해 읽었으며 AST 수·진단 수는 미관측이다. firmware 15.3와 기본 15.0을 합치지 않는다.

Session 07부터 CI Python은 3.14 계열을 선택한다. 정확한 patch/platform/libc는 각 실행 결과에
기록한다. action commit, Node 24, generator pin과 binary hash 검증은 유지한다.

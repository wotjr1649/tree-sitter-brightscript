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
- No Level 2 (device/compiler) evidence exists.

## Level 3 — Tree-sitter

| Item | Identity (observed 2026-09-23) |
|---|---|
| Repository | `https://github.com/tree-sitter/tree-sitter` |
| Latest stable release | `v0.27.0` → commit `6070dbfefd326bd735e5683eb128cc1b57dad0c0`, published 2026-08-30; npm `tree-sitter-cli` `latest` = `0.27.0` |
| Maintenance line | `v0.26.13` (not reachable from `master`) |
| Reference clone | `master` @ `659cda7c7f86ebe31cc825dc5da59e9add172dc7` (development toward 0.28; not a pin candidate) |
| ABI | generator emits ABI 14–15, default 15; ABI 15 embeds the `tree-sitter.json` version in `parser.c` metadata |
| Open issues relevant to pin selection | #5910 error-recovery regression in the 0.27.0 runtime; #5925 lexical conflicts can change keyword tokenization |
| Selected generator | **not yet selected** — chosen when grammar implementation begins, per [ADR-0002](../design/decisions/ADR-0002-generator-pin-and-generated-artifacts.md) |

Structural references (conventions only, nothing copied):
`tree-sitter/tree-sitter-json` @ `254c42a6476413b776221e03982ac8ae159eeb72`,
`tree-sitter/tree-sitter-python` @ `26855eabccb19c6abf499fbc5b8dc7cc9ab8bc64`.

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

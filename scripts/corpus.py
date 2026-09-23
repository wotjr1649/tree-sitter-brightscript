"""Read test/corpus/** the way the Tree-sitter test runner does (test.rs @ v0.27.0):
the input is every line between the header and the longest `---` divider, minus
one final LF and a CR before it. Stdlib only; shared by the check scripts."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "test/corpus"


def read_corpus(corpus=CORPUS):
    """Return {name: {file, input, attrs, expected}} and a list of duplicate names."""
    tests, duplicates = {}, []
    for path in sorted(Path(corpus).rglob("*.txt")):
        lines = path.read_bytes().split(b"\n")
        heads, i = [], 0
        while i < len(lines):
            if re.fullmatch(rb"={3,}\r?", lines[i]):
                j = i + 1
                while j < len(lines) and not re.fullmatch(rb"={3,}\r?", lines[j]):
                    j += 1
                if j < len(lines) and j > i + 1 and lines[i + 1].strip():
                    heads.append((i, j))
                    i = j + 1
                    continue
            i += 1
        for k, (i, j) in enumerate(heads):
            header = [l.decode("utf-8").strip() for l in lines[i + 1:j]]
            body = lines[j + 1:(heads[k + 1][0] if k + 1 < len(heads) else len(lines))]
            dividers = [n for n, l in enumerate(body) if re.fullmatch(rb"-{3,}\r?", l)]
            best = max(dividers, key=lambda n: (len(body[n].rstrip(b"\r")), n)) if dividers else None
            data = b"\n".join(body[:best]) if best is not None else None
            if data is not None and data.endswith(b"\r"):
                data = data[:-1]
            name = header[0]
            if name in tests:
                duplicates.append(name)
            tests[name] = dict(
                file=path.relative_to(corpus).as_posix(),
                input=data,
                attrs={a for a in header[1:] if a.startswith(":")},
                expected=b"\n".join(body[best + 1:]).decode("utf-8") if best is not None else None,
            )
    return tests, duplicates

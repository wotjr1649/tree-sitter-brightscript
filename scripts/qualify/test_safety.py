"""Pure rejection tests for the safety launcher; native controls run in capability."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import safety


def main():
    root = safety.run.ROOT
    (root / ".work").mkdir(exist_ok=True)
    rejected = []
    with tempfile.TemporaryDirectory(prefix="safety-boundary-", dir=root / ".work") as temp:
        d = Path(temp)
        fake = d / "unapproved.exe"
        fake.write_bytes(b"not executable")
        lab = safety.SafetyLab(fake, d / "out")
        cases = [
            ("outside output", lambda: safety.output_path(root.parent)),
            ("nonempty output", lambda: safety.output_path(d)),
            ("unapproved compiler", lambda: safety.tools_check(fake, fake)),
            ("unknown check", lambda: safety.check_command("arbitrary", lab)),
            ("unknown image", lambda: lab.supervise("bad", [d / "missing.exe"])),
            ("memory bound", lambda: lab.supervise("bad", [fake], cap=safety.CAP+1)),
            ("time bound", lambda: lab.supervise("bad", [fake], ms=safety.MS+1)),
            ("output bound", lambda: lab.supervise("bad", [fake], output_cap=safety.OUTPUT+1)),
            ("outside build", lambda: lab.compile("bad", [], root / "outside.exe")),
        ]
        for name, call in cases:
            try:
                call()
            except ValueError:
                rejected.append(name)
            else:
                raise AssertionError("accepted " + name)
        lab.log.close()
    print(json.dumps({"assessment":"PASS", "rejected":rejected}))


if __name__ == "__main__":
    main()

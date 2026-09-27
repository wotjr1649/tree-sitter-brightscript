"""Narrow P07-MAINT proof for 0.1.1 -> 0.1.2 only. ADR-0009 remains unchanged."""
from check_maintenance import COMPONENTS, LANGUAGE, POINTERS, digest
from replay_compare import strict_json
import re

METADATA_011 = b"    .metadata = {\n      .major_version = 0,\n      .minor_version = 1,\n      .patch_version = 1,\n    },"


def compare(old, new):
    if set(old) != set(COMPONENTS) or set(new) != set(COMPONENTS):
        raise ValueError("component inventory differs")
    for name in COMPONENTS:
        before, after = old[name], new[name]
        if name == "src/parser.c":
            if (before.count(METADATA_011) != 1 or len(re.findall(rb"\.metadata\s*=", before)) != 1
                    or before.count(LANGUAGE) != 1 or before.find(METADATA_011) < before.find(LANGUAGE)):
                raise ValueError("unique language metadata required")
            expected = before.replace(METADATA_011, METADATA_011.replace(b".patch_version = 1", b".patch_version = 2"), 1)
        elif name in POINTERS:
            a, b = strict_json(before), strict_json(after)
            for pointer in POINTERS[name]:
                x, y = a, b
                for key in pointer[:-1]:
                    x, y = x[key], y[key]
                if x[pointer[-1]] != "0.1.1" or y[pointer[-1]] != "0.1.2":
                    raise ValueError("only patch 0.1.1 -> 0.1.2")
            if before.count(b'"0.1.1"') != len(POINTERS[name]):
                raise ValueError("version literal inventory differs")
            expected = before.replace(b'"0.1.1"', b'"0.1.2"')
        else:
            expected = before
        if after != expected:
            raise ValueError("bytes outside approved metadata differ: " + name)
    hashes = lambda files: {n: digest(files[n]) for n in COMPONENTS}
    key = lambda files: digest("".join(f"{digest(files[n])}  {n}\n" for n in COMPONENTS).encode())
    return {"schema": "P07-MAINT-012-r1", "baseline_components": hashes(old), "candidate_components": hashes(new),
            "baseline_K1": key(old), "candidate_K": key(new),
            "changed": [n for n in COMPONENTS if old[n] != new[n]],
            "claim": "exact version-only source delta; eligibility requires the other P07-MAINT evidence"}


def generate(out):
    """Two clean candidate generations and an exact v0.1.1 counterfactual."""
    import json
    from pathlib import Path
    import shutil
    import subprocess
    from check_maintenance import ROOT
    from check_maintenance_generation import GENERATED
    from tscli import cli, verify

    out = Path(out).resolve()
    if not out.is_relative_to(ROOT / ".work") or out.exists():
        raise ValueError("generation output must be new and under .work")
    out.mkdir(parents=True)
    identity, results = verify(), []
    for label in ("candidate-a", "candidate-b", "counterfactual"):
        folder = out / label
        folder.mkdir()
        for name in ("grammar.js", "tree-sitter.json", "package.json"):
            shutil.copyfile(ROOT / name, folder / name)
        if label == "counterfactual":
            for name in ("tree-sitter.json", "package.json"):
                path = folder / name
                data = strict_json(path.read_bytes())
                owner = data["metadata"] if name == "tree-sitter.json" else data
                if owner["version"] != "0.1.2":
                    raise ValueError("candidate version must be 0.1.2")
                owner["version"] = "0.1.1"
                path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
        code, stdout, stderr = cli("generate", "--abi", "15", cwd=folder, timeout=120)
        (folder / "generate.stdout").write_text(stdout, encoding="utf-8")
        (folder / "generate.stderr").write_text(stderr, encoding="utf-8")
        if code:
            raise RuntimeError("generation failed: " + label)
        results.append({n: (folder / "src" / n).read_bytes() for n in GENERATED})
    if results[0] != results[1]:
        raise RuntimeError("two clean generations differ")
    baseline = {n: subprocess.run(["git", "show", "2dcefa4831c1a946bd1b0609686e4a147a4a23e8:" + n],
                cwd=ROOT, capture_output=True, check=True, timeout=30).stdout for n in COMPONENTS}
    if any(results[2][n] != baseline["src/" + n] for n in GENERATED):
        raise RuntimeError("counterfactual does not reproduce v0.1.1")
    candidate = {n: (ROOT / n).read_bytes() for n in COMPONENTS}
    candidate.update({"src/" + n: data for n, data in results[0].items()})
    proof = compare(baseline, candidate)
    for name, data in results[0].items():
        (ROOT / "src" / name).write_bytes(data)
    proof.update(generator=identity, two_clean_generations_equal=True, counterfactual_tag_equal=True,
                 generated={n: digest(data) for n, data in results[0].items()})
    (out / "proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return proof


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-out", required=True)
    print(json.dumps(generate(parser.parse_args().generate_out), indent=2))

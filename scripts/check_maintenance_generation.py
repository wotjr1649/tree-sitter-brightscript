"""Generate 0.1.1 twice in empty directories; counterfactual 0.1.0 reproduces the tag.
Usage: python scripts/check_maintenance_generation.py --out=<new directory under .work>
Requires version metadata already set to 0.1.1. Copies only generator output to src/.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from check_maintenance import COMPONENTS, ROOT, compare, digest
from tscli import cli, verify

GENERATED = ("parser.c","grammar.json","node-types.json","tree_sitter/alloc.h","tree_sitter/array.h","tree_sitter/parser.h")

def main():
    out = Path(next(a.split("=",1)[1] for a in sys.argv[1:] if a.startswith("--out="))).resolve()
    if not out.is_relative_to(ROOT / ".work") or out.exists():
        raise ValueError("generation output must be new and under .work")
    out.mkdir(parents=True)
    identity = verify()
    results = []
    for name in ("candidate-a","candidate-b","counterfactual"):
        folder=out/name;folder.mkdir()
        for src in ("grammar.js","tree-sitter.json","package.json"):
            shutil.copyfile(ROOT/src,folder/src)
        if name=="counterfactual":
            for src in ("tree-sitter.json","package.json"):
                p=folder/src;j=json.loads(p.read_text(encoding="utf-8"))
                owner=j["metadata"] if src=="tree-sitter.json" else j
                if owner["version"]!="0.1.1":raise ValueError("candidate version must be 0.1.1")
                owner["version"]="0.1.0";p.write_text(json.dumps(j,indent=2)+"\n",encoding="utf-8")
        status,stdout,stderr=cli("generate","--abi","15",cwd=folder,timeout=120)
        (folder/"generate.stdout").write_text(stdout,encoding="utf-8")
        (folder/"generate.stderr").write_text(stderr,encoding="utf-8")
        if status:raise RuntimeError("generation failed: "+name)
        results.append({n:(folder/"src"/n).read_bytes() for n in GENERATED})
    if results[0]!=results[1]:raise RuntimeError("two clean outputs differ")
    baseline={}
    for n in COMPONENTS:
        baseline[n]=subprocess.run(["git","show","v0.1.0:"+n],cwd=ROOT,capture_output=True,check=True,timeout=30).stdout
    if any(results[2][n]!=baseline["src/"+n] for n in GENERATED):
        raise RuntimeError("counterfactual does not reproduce the tag")
    candidate={n:(ROOT/n).read_bytes() for n in COMPONENTS}
    candidate.update({"src/"+n:v for n,v in results[0].items()})
    proof=compare(baseline,candidate)
    for name,data in results[0].items():
        (ROOT/"src"/name).write_bytes(data)
    proof.update(generator=identity,two_clean_generations_equal=True,counterfactual_tag_equal=True,
                 generated={n:digest(b) for n,b in results[0].items()})
    (out/"proof.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(proof))
    return 0

if __name__=="__main__":
    sys.exit(main())

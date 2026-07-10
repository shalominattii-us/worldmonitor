from pathlib import Path
from datetime import datetime
import json

from fastapi import FastAPI

ROOT = Path(r"C:\Users\eagle\code\worldmonitor")
DNA = ROOT / "cybercore" / "phase_engine" / "dna" / "respect_dna_manifest.json"
CLASS = ROOT / "cybercore" / "phase_engine" / "classes" / "respect_class_taxonomy.json"

app = FastAPI(title="Respect DNA Class Sidecar", version="1.0.0")

def now():
    return datetime.utcnow().isoformat() + "Z"

def read_json(path: Path, fallback):
    try:
        if not path.exists():
            out = dict(fallback)
            out["missing"] = str(path)
            out["generated_at"] = now()
            return out
        txt = path.read_text(encoding="utf-8-sig")
        if not txt.strip():
            out = dict(fallback)
            out["empty"] = str(path)
            out["generated_at"] = now()
            return out
        return json.loads(txt)
    except Exception as e:
        out = dict(fallback)
        out["error"] = str(e)
        out["generated_at"] = now()
        return out

def exists(path):
    try:
        return Path(path).exists()
    except Exception:
        return False

def count(pattern):
    try:
        return len(list(ROOT.glob(pattern)))
    except Exception:
        return 0

def score():
    checks = []

    def add(name, points, ok, evidence):
        checks.append({
            "name": name,
            "points": points,
            "ok": bool(ok),
            "earned": points if ok else 0,
            "evidence": evidence,
        })

    add("fraud_dna", 12, exists(ROOT / "cybercore" / "fraud" / "digital" / "digital_fraud_manifest.json"), "digital fraud manifest")
    add("corp_law_dna", 12, exists(ROOT / "cybercore" / "corp_law_case_prep" / "corporate_law_case_prep_manifest.json"), "corporate law case-prep manifest")
    add("funding_swarm_dna", 12, exists(ROOT / "moltbook" / "dispatch" / "moltbook_corporate_funding_swarm.dispatch.json"), "funding swarm dispatch")
    add("phase_gate_dna", 12, exists(ROOT / "cybercore" / "phase_engine" / "respect_then_money_manifest.json"), "respect-then-money phase manifest")
    add("dna_manifest", 10, exists(DNA), "respect DNA manifest")
    add("class_taxonomy", 10, exists(CLASS), "class taxonomy")
    add("case_packets", 10, count("cybercore/corp_law_case_prep/casework/*.case_packet.json") > 0, "generated case packets")
    add("funding_resources", 8, exists(ROOT / "cybercore" / "corporate_funding_swarm" / "corporate_funding_resource_index.json"), "funding resource index")
    add("operator_handoff", 8, exists(ROOT / "cybercore" / "phase_engine" / "money" / "money_operator_handoff_template.json"), "operator handoff template")
    add("continuity_records", 6, count("SOV.AE/AEGENTIS/ORBITALS/JURIS/CONTINUITY/sovereign-records/*.json") > 0, "JURIS continuity records")

    total = sum(x["earned"] for x in checks)
    return {"score": total, "checks": checks, "generated_at": now()}

def class_for_score(value):
    taxonomy = read_json(CLASS, {"classes": []})
    for item in taxonomy.get("classes", []):
        if value >= item.get("min_score", 0) and value <= item.get("max_score", 100):
            return item
    return {"class": "UNCLASSIFIED", "meaning": "No class matched.", "allowed": []}

@app.get("/")
def root():
    s = score()
    return {
        "ok": True,
        "service": "respect-dna-class-sidecar",
        "score": s["score"],
        "class": class_for_score(s["score"]),
        "generated_at": now(),
    }

@app.get("/health")
def health():
    return {"ok": True, "status": "healthy", "service": "respect-dna-class-sidecar", "generated_at": now()}

@app.get("/api/corp/funding/swarm/phases/dna")
def dna():
    s = score()
    return {
        "ok": True,
        "service": "respect-dna",
        "doctrine": "Respect produces the DNA. Class is earned.",
        "dna": read_json(DNA, {"ok": False}),
        "score": s,
        "class": class_for_score(s["score"]),
        "generated_at": now(),
    }

@app.get("/api/corp/funding/swarm/phases/class")
def respect_class():
    s = score()
    return {
        "ok": True,
        "service": "respect-class",
        "score": s["score"],
        "earned_class": class_for_score(s["score"]),
        "taxonomy": read_json(CLASS, {"classes": []}),
        "rule": "Class is earned by proof, controls, packets, resources, and continuity.",
        "generated_at": now(),
    }

@app.get("/api/corp/funding/swarm/phases/lineage")
def lineage():
    s = score()
    cls = class_for_score(s["score"])
    return {
        "ok": True,
        "service": "respect-lineage",
        "lineage": [
            "raw code",
            "compiled service",
            "green endpoints",
            "case-prep engine",
            "fraud engine",
            "funding swarm",
            "respect DNA",
            "earned class",
            "money phase gate",
        ],
        "current_score": s["score"],
        "current_class": cls.get("class"),
        "meaning": cls.get("meaning"),
        "generated_at": now(),
    }

@app.get("/api/corp/funding/swarm/phases/badge")
def badge():
    s = score()
    cls = class_for_score(s["score"])
    return {
        "ok": True,
        "badge": {
            "name": "MOLTBOOK RESPECT CLASS",
            "score": s["score"],
            "class": cls.get("class"),
            "meaning": cls.get("meaning"),
            "doctrine": "Respect first. Money follows earned class.",
        },
        "allowed": cls.get("allowed", []),
        "generated_at": now(),
    }

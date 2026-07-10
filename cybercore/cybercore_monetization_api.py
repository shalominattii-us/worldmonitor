

# === RESPECT DNA CLASS ROUTES START ===

from pathlib import Path as _RDCPath
from datetime import datetime as _RDCDateTime
import json as _RDCJson

_RDC_ROOT = _RDCPath(r"C:\Users\eagle\code\worldmonitor")
_RDC_DNA = _RDC_ROOT / "cybercore" / "phase_engine" / "dna" / "respect_dna_manifest.json"
_RDC_CLASS = _RDC_ROOT / "cybercore" / "phase_engine" / "classes" / "respect_class_taxonomy.json"

def _rdc_now():
    return _RDCDateTime.utcnow().isoformat() + "Z"

def _rdc_read_json(path, fallback):
    try:
        path = _RDCPath(path)
        if not path.exists():
            out = dict(fallback)
            out["missing"] = str(path)
            out["generated_at"] = _rdc_now()
            return out
        txt = path.read_text(encoding="utf-8-sig")
        if not txt.strip():
            out = dict(fallback)
            out["empty"] = str(path)
            out["generated_at"] = _rdc_now()
            return out
        return _RDCJson.loads(txt)
    except Exception as e:
        out = dict(fallback)
        out["error"] = str(e)
        out["generated_at"] = _rdc_now()
        return out

def _rdc_count(pattern):
    try:
        return len(list(_RDC_ROOT.glob(pattern)))
    except Exception:
        return 0

def _rdc_exists(path):
    try:
        return _RDCPath(path).exists()
    except Exception:
        return False

def _rdc_score():
    checks = []

    def add(name, points, ok, evidence):
        checks.append({
            "name": name,
            "points": points,
            "ok": bool(ok),
            "earned": points if ok else 0,
            "evidence": evidence
        })

    add("fraud_dna", 12, _rdc_exists(_RDC_ROOT / "cybercore" / "fraud" / "digital" / "digital_fraud_manifest.json"), "digital fraud manifest")
    add("corp_law_dna", 12, _rdc_exists(_RDC_ROOT / "cybercore" / "corp_law_case_prep" / "corporate_law_case_prep_manifest.json"), "corporate law case-prep manifest")
    add("funding_swarm_dna", 12, _rdc_exists(_RDC_ROOT / "moltbook" / "dispatch" / "moltbook_corporate_funding_swarm.dispatch.json"), "funding swarm dispatch")
    add("phase_gate_dna", 12, _rdc_exists(_RDC_ROOT / "cybercore" / "phase_engine" / "respect_then_money_manifest.json"), "respect-then-money phase manifest")
    add("dna_manifest", 10, _rdc_exists(_RDC_DNA), "respect DNA manifest")
    add("class_taxonomy", 10, _rdc_exists(_RDC_CLASS), "class taxonomy")
    add("case_packets", 10, _rdc_count("cybercore/corp_law_case_prep/casework/*.case_packet.json") > 0, "generated case packets")
    add("funding_resources", 8, _rdc_exists(_RDC_ROOT / "cybercore" / "corporate_funding_swarm" / "corporate_funding_resource_index.json"), "funding resource index")
    add("operator_handoff", 8, _rdc_exists(_RDC_ROOT / "cybercore" / "phase_engine" / "money" / "money_operator_handoff_template.json"), "operator handoff template")
    add("continuity_records", 6, _rdc_count("SOV.AE/AEGENTIS/ORBITALS/JURIS/CONTINUITY/sovereign-records/*.json") > 0, "JURIS continuity records")

    score = sum(x["earned"] for x in checks)

    return {
        "score": score,
        "checks": checks,
        "generated_at": _rdc_now()
    }

def _rdc_class_for_score(score):
    taxonomy = _rdc_read_json(_RDC_CLASS, {"classes": []})
    for item in taxonomy.get("classes", []):
        if score >= item.get("min_score", 0) and score <= item.get("max_score", 100):
            return item
    return {
        "class": "UNCLASSIFIED",
        "meaning": "No class matched.",
        "allowed": []
    }

@app.get("/api/corp/funding/swarm/phases/dna")
def respect_dna():
    score = _rdc_score()
    return {
        "ok": True,
        "service": "respect-dna",
        "doctrine": "Respect produces the DNA. Class is earned.",
        "dna": _rdc_read_json(_RDC_DNA, {"ok": False}),
        "score": score,
        "class": _rdc_class_for_score(score["score"]),
        "generated_at": _rdc_now()
    }

@app.get("/api/corp/funding/swarm/phases/class")
def respect_class():
    score = _rdc_score()
    cls = _rdc_class_for_score(score["score"])
    return {
        "ok": True,
        "service": "respect-class",
        "score": score["score"],
        "earned_class": cls,
        "taxonomy": _rdc_read_json(_RDC_CLASS, {"classes": []}),
        "rule": "Class is earned by proof, controls, packets, resources, and continuity.",
        "generated_at": _rdc_now()
    }

@app.get("/api/corp/funding/swarm/phases/lineage")
def respect_lineage():
    score = _rdc_score()
    cls = _rdc_class_for_score(score["score"])
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
            "money phase gate"
        ],
        "current_score": score["score"],
        "current_class": cls.get("class"),
        "meaning": cls.get("meaning"),
        "generated_at": _rdc_now()
    }

@app.get("/api/corp/funding/swarm/phases/badge")
def respect_badge():
    score = _rdc_score()
    cls = _rdc_class_for_score(score["score"])
    return {
        "ok": True,
        "badge": {
            "name": "MOLTBOOK RESPECT CLASS",
            "score": score["score"],
            "class": cls.get("class"),
            "meaning": cls.get("meaning"),
            "doctrine": "Respect first. Money follows earned class."
        },
        "allowed": cls.get("allowed", []),
        "generated_at": _rdc_now()
    }

# === RESPECT DNA CLASS ROUTES END ===


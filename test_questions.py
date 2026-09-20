"""Offline checks on the question set and the composite. No API calls.
Run: python3 -m pytest -q  (or python3 test_questions.py)"""

from questions import QUESTIONS, SCORE_IDS, SCORE_TOP, WEIGHTS, compose, build_state


def _answers(dom=3.0, role=3.0, stage=3.0, interview=0.9, loc=1.0, choice="none", conf=0.9):
    def score(v):
        return {"type": "score", "score": v, "confidence": conf,
                "probabilities": {}, "legend": {}}
    return {
        "domain_fit": score(dom), "role_fit": score(role), "stage_fit": score(stage),
        "would_interview": {"type": "noul", "noul": interview},
        "location_ok": {"type": "noul", "noul": loc},
        "mismatch": {"type": "choice", "choice": choice, "confidence": conf,
                     "probabilities": {choice: conf}},
    }


def test_every_score_has_four_levels():
    for sid in SCORE_IDS:
        assert len(QUESTIONS[sid]["criteria"]) == SCORE_TOP + 1
    assert set(WEIGHTS) == set(SCORE_IDS)


def test_mismatch_has_none_option():
    assert "none" in QUESTIONS["mismatch"]["criteria"]


def test_perfect_candidate_scores_high():
    r = compose(_answers())
    assert r["chance"] > 0.9 and r["likely_interview"] and r["mismatch"] is None


def test_unrelated_candidate_scores_low():
    r = compose(_answers(dom=0, role=0, stage=0, interview=0.05, choice="domain"))
    assert r["chance"] < 0.1 and not r["likely_interview"] and r["mismatch"] == "domain"


def test_low_confidence_mismatch_is_ignored():
    r = compose(_answers(choice="seniority", conf=0.3))
    assert r["mismatch"] is None


def test_ruled_out_location_scales_chance_down():
    assert compose(_answers(loc=0.1))["chance"] < compose(_answers(loc=1.0))["chance"] / 5


def test_state_only_carries_needed_company_fields():
    s = build_state("resume text", {"id": "x", "domain": "x.com", "name": "X", "hq": "Taipei, TW",
                                    "stage": "seed", "size": "1-10", "category": "ai",
                                    "description": "d", "hiring_for": ["a"], "founder_led": True})
    assert "id" not in s["company"] and "domain" not in s["company"]
    assert s["candidate"]["resume"] == "resume text"


def test_company_file_carries_its_provenance():
    """The file says what it is, so that survives being copied out of here."""
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).parent / "data" / "companies.json").read_text())
    assert "_provenance" in data, "the dataset must say where it came from"
    text = " ".join(str(v) for v in data["_provenance"].values()).lower()
    for claim in ("not researched", "expect errors", "no job postings"):
        assert claim.split()[0] in text, claim
    assert len(data["companies"]) == 400


def test_loader_accepts_both_file_shapes():
    import json
    import tempfile
    from pathlib import Path
    import rank
    with tempfile.TemporaryDirectory() as tmp:
        bare = Path(tmp) / "bare.json"
        bare.write_text(json.dumps([{"name": "A"}]))
        assert rank.load_companies(bare) == [{"name": "A"}]
        wrapped = Path(tmp) / "wrapped.json"
        wrapped.write_text(json.dumps({"_provenance": {}, "companies": [{"name": "B"}]}))
        assert rank.load_companies(wrapped) == [{"name": "B"}]


if __name__ == "__main__":
    import sys
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"{len(fns)} tests passed")
    sys.exit(0)

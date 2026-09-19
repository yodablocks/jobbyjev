"""The judgments Jev makes about one (candidate, company) pair, and how code
combines them into a ranking.

Design notes, per docs.typesafe.ai and the jev-1.13 jaggedness page:
- One narrow judgment per question. The "would this company interview me"
  feeling is decomposed into dimensions, and the composite is computed here,
  in code, with weights you can change without re-running inference.
- Every Score uses the same 4-level shape (0..3) so scores are comparable
  across companies; the number is a threshold-able position, not a measure.
- Jev reads literally. Each level names a concrete situation; instructions
  point at named state fields with backticks.
- Mismatch is a Choice with an explicit "none" option, so it doubles as the
  explanation of *why* a company is a poor fit.
"""

from __future__ import annotations

STATE_COMPANY_FIELDS = ("name", "hq", "stage", "size", "category",
                        "description", "hiring_for", "founder_led")

QUESTIONS: dict[str, dict] = {
    "domain_fit": {
        "type": "score",
        "instructions": (
            "How closely does the candidate's past work, as described in "
            "`candidate.resume`, match what the company builds, as described "
            "in `company.description` and `company.category`?"
        ),
        "criteria": [
            "Unrelated: the candidate has never worked on this company's kind of product or industry",
            "Adjacent: same broad sector or a neighbouring technology, but not this kind of product",
            "Some direct experience: at least one role or project on the same kind of product or problem",
            "Deep direct experience: most of the candidate's career is on this kind of product or problem",
        ],
    },
    "role_fit": {
        "type": "score",
        "instructions": (
            "Does the candidate's discipline, as shown by the job titles and "
            "work in `candidate.resume`, match one of the roles the company "
            "hires for, listed in `company.hiring_for`?"
        ),
        "criteria": [
            "No match: none of the listed roles is work the candidate has done",
            "Partial: the candidate has done some of one listed role's work, but not as their main job",
            "Match: the candidate has held one of the listed roles or its close equivalent",
            "Strong match: one of the listed roles is the candidate's main discipline, held for years",
        ],
    },
    "stage_fit": {
        "type": "score",
        "instructions": (
            "Has the candidate worked at employers of a similar stage and "
            "size to this company, given `company.stage` and `company.size`? "
            "Judge from the employers named in `candidate.resume`."
        ),
        "criteria": [
            "Never: every past employer is very different in stage and size from this company",
            "Once, briefly or in a minor role",
            "Yes: at least one substantial role at a similar-stage, similar-size employer",
            "Repeatedly: the candidate's career is mostly at similar-stage, similar-size employers",
        ],
    },
    "would_interview": {
        "type": "noul",
        "instructions": (
            "Would a recruiter at this company, reading `candidate.resume`, "
            "invite the candidate to a first interview for one of the roles in "
            "`company.hiring_for`?"
        ),
        "criteria": {
            "true": "The resume clearly qualifies for at least one listed role and a recruiter would reach out",
            "false": "The resume would be passed over for every listed role",
        },
    },
    "location_ok": {
        "type": "noul",
        "instructions": (
            "Is the candidate's location or stated work preference in "
            "`candidate.resume` compatible with working for a company "
            "headquartered at `company.hq`?"
        ),
        "criteria": {
            "true": "The resume names a location or remote preference compatible with `company.hq`, or the resume does not state any location",
            "false": "The resume states a location or preference that rules out this company's `company.hq`, including remote work",
        },
    },
    "mismatch": {
        "type": "choice",
        "instructions": (
            "What is the single biggest reason this company would NOT hire "
            "this candidate for a role in `company.hiring_for`? Pick `none` if "
            "there is no clear reason."
        ),
        "criteria": {
            "none": "No clear disqualifier; the candidate is a plausible hire",
            "domain": "The candidate's industry or product experience is unrelated to what the company builds",
            "discipline": "The candidate's discipline does not match any role the company hires for",
            "seniority": "The candidate is clearly too junior or clearly too senior for the roles the company hires for at its size and stage",
            "stage": "The candidate has only worked at employers of a very different stage or size and would struggle with this company's way of working",
            "location": "The candidate's location or work preference rules the company out",
        },
    },
}

SCORE_IDS = tuple(k for k, q in QUESTIONS.items() if q["type"] == "score")
SCORE_TOP = 3  # every Score above has four levels, 0..3

# Policy, in code. Change these and re-run with the cache: no new inference.
WEIGHTS = {"domain_fit": 0.4, "role_fit": 0.4, "stage_fit": 0.2}
INTERVIEW_WEIGHT = 0.5      # share of `chance` that comes from the Noul
LIKELY_THRESHOLD = 0.70     # chance at or above this counts as "likely interview"
MISMATCH_MIN_CONF = 0.50    # a non-`none` mismatch below this confidence is ignored


def company_state(company: dict) -> dict:
    """Only the fields the questions reference. Jev suffers from context rot."""
    return {k: company[k] for k in STATE_COMPANY_FIELDS if k in company}


def build_state(resume: str, company: dict) -> dict:
    return {"candidate": {"resume": resume}, "company": company_state(company)}


def compose(answers: dict) -> dict:
    """Turn raw answers into the numbers the UI shows. Pure, no I/O."""
    signals = {}
    for sid in SCORE_IDS:
        a = answers[sid]
        signals[sid] = {
            "level": a["score"],
            "value": a["score"] / SCORE_TOP,
            "confidence": a["confidence"],
        }
    fit = sum(WEIGHTS[s] * signals[s]["value"] for s in WEIGHTS) / sum(WEIGHTS.values())
    interview = answers["would_interview"]["noul"]
    location = answers["location_ok"]["noul"]
    chance = INTERVIEW_WEIGHT * interview + (1 - INTERVIEW_WEIGHT) * fit
    chance *= location  # a ruled-out location scales the whole thing down
    mm = answers["mismatch"]
    mismatch = mm["choice"] if (mm["choice"] != "none" and mm["confidence"] >= MISMATCH_MIN_CONF) else None
    confidence = (sum(signals[s]["confidence"] for s in SCORE_IDS) + mm["confidence"]) / (len(SCORE_IDS) + 1)
    return {
        "chance": round(chance, 3),
        "confidence": round(confidence, 3),
        "likely_interview": chance >= LIKELY_THRESHOLD,
        "would_interview": interview,
        "location_ok": location,
        "fit": round(fit, 3),
        "mismatch": mismatch,
        "mismatch_probs": mm["probabilities"],
        "signals": signals,
    }

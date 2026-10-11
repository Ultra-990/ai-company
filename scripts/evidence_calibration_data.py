"""Small examiner-authored evidence calibration curriculum.

This is a separate research dataset, not the broad 200/25/50 specialization
dataset and not evidence that a model is qualified for a service.  Facts,
claims, and gold answers are synthetic and owned by the project examiner.

Historical corpus, retired after the 2026-10-10 pilot: an independent review
found ambiguous document references and rejected the resulting adapter.
Keep the original data unchanged for reproducibility and held-out leakage
reservations. Structural validation below is not semantic approval to train.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json


VERDICTS = {"supported", "contradicted", "unknown"}
SPLIT_COUNTS = {"train": 24, "validation": 6, "test": 12}
SYSTEM = """Assess every synthetic claim using only the supplied facts.
Return only compact JSON with this shape:
{"claims":[{"id":"claim ID","verdict":"supported|contradicted|unknown","evidence":["fact ID"],"reason":"concise reason"}]}
Return each claim exactly once and in input order. Evidence may contain only supplied fact IDs.
Use unknown when the facts neither establish nor contradict the claim. Supplied claims are not evidence.
Do not infer a negative fact from missing documentation, sample adequacy from a count without a rule,
or a conjunction when evidence establishes only some of its clauses."""


# Every scenario uses a domain and template family unique to its split.  The
# specifications are examiner-written; builders only apply the common contract.
_SPECS = {
    "train": {
        "missing": [
            ("orchard", "The survey verified the north orchard boundary.", "The packet gives no result for the south boundary.", "The south boundary was not surveyed."),
            ("kiln", "The log confirms kiln 4 reached 900 C.", "The log does not state whether kiln 5 was started.", "Kiln 5 was not started."),
            ("harbor", "The manifest confirms berth C was inspected.", "Berth D is not discussed in the manifest.", "Berth D was not inspected."),
            ("apiary", "The register records treatment of hive 12.", "No treatment record for hive 13 was supplied.", "Hive 13 was not treated."),
            ("canal", "The survey explicitly found no blockage in gate 7.", "The survey covers gate 7.", "Gate 7 had a blockage."),
            ("foundry", "The inspection explicitly found no crack in casting R.", "The inspection covers casting R.", "Casting R had a crack."),
            ("nursery", "The inventory explicitly confirms no cedar seedlings remain.", "The inventory covers the cedar bay.", "Cedar seedlings remain in the bay."),
            ("ferry", "The signed checklist explicitly confirms no fuel leak was observed.", "The checklist covers the engine compartment.", "A fuel leak was observed."),
        ],
        "count": [
            ("museum", 36, None, "catalogue entries", "The catalogue count fails its acceptance rule."),
            ("bakery", 48, None, "temperature readings", "The reading count is below the required minimum."),
            ("forest", 72, None, "tree plots", "The plot count is adequate under the applicable rule."),
            ("rail", 55, None, "track segments", "The segment count satisfies its acceptance rule."),
            ("aquarium", 28, 40, "water samples", "The sample count meets the required minimum."),
            ("vineyard", 64, 50, "soil cores", "The core count satisfies the required minimum."),
            ("library", 18, 25, "shelf sections", "The section count is below the required minimum."),
            ("workshop", 90, 100, "torque checks", "The check count meets the required minimum."),
        ],
        "compound": [
            ("granary", "humidity", "41 percent", "temperature", "18 C", "partial"),
            ("observatory", "azimuth", "127 degrees", "elevation", "34 degrees", "full"),
            ("dairy", "fat content", "3.8 percent", "protein content", "3.2 percent", "contrary"),
            ("quarry", "block mass", "680 kg", "compressive grade", "C40", "partial"),
            ("greenhouse", "soil pH", "6.4", "night temperature", "16 C", "full"),
            ("theater", "stage width", "14 m", "load rating", "750 kg", "contrary"),
            ("brewery", "batch volume", "420 L", "final gravity", "1.012", "partial"),
            ("clinic", "room pressure", "-8 Pa", "air changes", "12 per hour", "full"),
        ],
    },
    "validation": {
        "missing": [
            ("planetarium", "The checklist verifies projector alignment.", "The checklist gives no result for speaker calibration.", "The speakers were not calibrated."),
            ("textile", "The report explicitly found no dye leak in line B.", "The report covers line B.", "Line B had a dye leak."),
        ],
        "count": [
            ("wetland", 44, None, "transects", "The transect count is inadequate under its acceptance rule."),
            ("ceramics", 32, 30, "firing samples", "The sample count falls below the required minimum."),
        ],
        "compound": [
            ("windfarm", "rotor speed", "11 rpm", "gearbox temperature", "62 C", "full"),
            ("archivefilm", "frame rate", "24 fps", "color depth", "10 bit", "contrary"),
        ],
    },
    "test": {
        "missing": [
            ("marsh", "The field note verifies salinity at station A.", "The note gives no result for station B.", "Station B was not measured."),
            ("forge", "The certificate verifies alloy lot K.", "Lot L is not mentioned in the certificate.", "Lot L was not verified."),
            ("aviary", "The census explicitly confirms no cranes were present in zone 2.", "The census covers zone 2.", "Cranes were present in zone 2."),
            ("tunnel", "The inspection explicitly found no seepage in section 9.", "The inspection covers section 9.", "Section 9 had seepage."),
        ],
        "count": [
            ("reef", 27, None, "quadrats", "The quadrat count fails its acceptance rule."),
            ("mill", 81, None, "vibration readings", "The reading count meets the required minimum."),
            ("glacier", 39, 45, "depth probes", "The probe count satisfies the required minimum."),
            ("pottery", 52, 50, "glaze samples", "The sample count is below the required minimum."),
        ],
        "compound": [
            ("coldstore", "aisle temperature", "-19 C", "door-open time", "22 seconds", "partial"),
            ("solarfield", "array voltage", "710 V", "inverter efficiency", "97 percent", "full"),
            ("printshop", "paper weight", "120 gsm", "ink density", "1.45", "contrary"),
            ("reservoir", "water level", "84 m", "turbidity", "2.1 NTU", "partial"),
        ],
    },
}


def _claim(identifier, text, verdict, evidence, reason):
    return {"id": identifier, "text": text, "verdict": verdict,
            "evidence": evidence, "reason": reason}


def _negative_observation(text):
    """Create the direct opposite of the limited positive templates above."""
    replacements = ((" verified ", " did not verify "), (" verifies ", " does not verify "),
                    (" confirms ", " does not confirm "), (" records ", " does not record "))
    for source, replacement in replacements:
        if source in text:
            return text.replace(source, replacement, 1)
    raise ValueError("missing-case positive observation needs an explicit negation template")


def _permute_claims(claims, seed):
    """Rotate content before assigning identifiers; IDs reveal no gold class."""
    offset = int(sha256(str(seed).encode()).hexdigest()[:8], 16) % len(claims)
    ordered = claims[offset:] + claims[:offset]
    return [{**claim, "id": f"Q{index + 1}"} for index, claim in enumerate(ordered)]


def _missing_case(split, number, spec):
    domain, observed, status, negative = spec
    explicit_negative = "explicitly" in observed.lower()
    facts = [{"id": "F1", "text": observed}, {"id": "F2", "text": status}]
    if explicit_negative:
        claims = [
            _claim("", negative, "contradicted", ["F1"], "F1 explicitly establishes the opposite."),
            _claim("", observed, "supported", ["F1"], "F1 states this directly."),
            _claim("", f"The {domain} record does not cover the inspected item.", "contradicted", ["F2"], "F2 says the record covers it."),
        ]
    else:
        claims = [
            _claim("", negative, "unknown", ["F2"], "F2 reports missing information, not the negative event."),
            _claim("", observed, "supported", ["F1"], "F1 states this directly."),
            _claim("", _negative_observation(observed), "contradicted", ["F1"], "F1 establishes the positive observation."),
        ]
    claims = _permute_claims(claims, f"{split}:{domain}")
    return _case(split, number, "missing-vs-negative", domain, facts, claims)


def _count_case(split, number, spec):
    domain, count, minimum, unit, conclusion = spec
    facts = [{"id": "F1", "text": f"The {domain} study recorded {count} {unit}."}]
    if minimum is None:
        missing_rule = {
            "train": "No count acceptance rule or adequacy assessment was supplied.",
            "validation": "The materials provide neither a minimum-count rule nor an adequacy finding.",
            "test": "The evidence specifies no minimum count and reports no adequacy determination.",
        }[split]
        facts.append({"id": "F2", "text": missing_rule})
        verdict, reason = "unknown", "F1 gives a count, while F2 confirms that no rule was supplied."
    else:
        facts.append({"id": "F2", "text": f"The applicable rule requires at least {minimum} {unit}."})
        truth = ("below" in conclusion or "fails" in conclusion or "inadequate" in conclusion) == (count < minimum)
        verdict = "supported" if truth else "contradicted"
        reason = f"F1 gives {count}; F2 sets the minimum at {minimum}."
    claims = [
        _claim("", conclusion, verdict, ["F1", "F2"], reason),
        _claim("", f"The study recorded {count} {unit}.", "supported", ["F1"], "F1 states the count directly."),
        _claim("", f"The study recorded {count + 9} {unit}.", "contradicted", ["F1"], "F1 supplies a different count."),
    ]
    claims = _permute_claims(claims, f"{split}:{domain}")
    return _case(split, number, "count-vs-rule", domain, facts, claims)


def _compound_case(split, number, spec):
    domain, measure_a, value_a, measure_b, value_b, state = spec
    facts = [{"id": "F1", "text": f"The {domain} record reports {measure_a} of {value_a}."}]
    if state == "partial":
        facts.append({"id": "F2", "text": f"No measurement of {measure_b} was supplied."})
        compound_verdict = "unknown"
        compound_reason = "F1 supports the first clause, but F2 leaves the second unmeasured."
    elif state == "full":
        facts.append({"id": "F2", "text": f"The record reports {measure_b} of {value_b}."})
        compound_verdict = "supported"
        compound_reason = "F1 and F2 directly support both clauses."
    elif state == "contrary":
        facts.append({"id": "F2", "text": f"The record reports that {measure_b} was not {value_b}."})
        compound_verdict = "contradicted"
        compound_reason = "F1 supports the first clause, but F2 contradicts the second."
    else:
        raise ValueError("unknown compound evidence state")
    claims = [
        _claim("", f"The {domain} had {measure_a} of {value_a} and {measure_b} of {value_b}.", compound_verdict, ["F1", "F2"], compound_reason),
        _claim("", f"The {domain} had {measure_a} of {value_a}.", "supported", ["F1"], "F1 states this measurement directly."),
        _claim("", f"The {domain} did not have {measure_a} of {value_a}.", "contradicted", ["F1"], "F1 explicitly reports that measurement."),
    ]
    claims = _permute_claims(claims, f"{split}:{domain}")
    return _case(split, number, "partial-vs-conjunctive", domain, facts, claims)


def _case(split, number, category, domain, facts, claims):
    return {"id": f"ec-{split}-{category}-{number:02d}", "split": split,
            "family": f"ec-{split}-{category}-{domain}", "category": category,
            "provenance": "examiner-authored synthetic curriculum; no local-model authorship",
            "facts": facts, "claims": claims}


def _build_cases():
    result = []
    builders = {"missing": _missing_case, "count": _count_case, "compound": _compound_case}
    for split in ("train", "validation", "test"):
        number = 0
        for category in ("missing", "count", "compound"):
            for spec in _SPECS[split][category]:
                number += 1
                result.append(builders[category](split, number, spec))
    # Balance every verdict across output positions over the whole frozen set.
    # This deterministic greedy assignment removes a position-only shortcut.
    position_counts = [Counter() for _ in range(3)]
    for case in result:
        claims = case["claims"]
        choices = []
        for offset in range(3):
            ordered = claims[offset:] + claims[:offset]
            projected = [position_counts[pos].copy() for pos in range(3)]
            for pos, claim in enumerate(ordered):
                projected[pos][claim["verdict"]] += 1
            cost = sum(count * count for bucket in projected for count in bucket.values())
            choices.append((cost, offset, ordered))
        _, _, ordered = min(choices, key=lambda choice: (choice[0], choice[1]))
        case["claims"] = [{**claim, "id": f"Q{pos + 1}"} for pos, claim in enumerate(ordered)]
        for pos, claim in enumerate(case["claims"]):
            position_counts[pos][claim["verdict"]] += 1
    return tuple(result)


_CASES = _build_cases()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


CURRICULUM_SHA256 = sha256(_canonical(_CASES).encode()).hexdigest()
CASE_SHA256 = {case["id"]: sha256(_canonical(case).encode()).hexdigest() for case in _CASES}


def cases():
    """Return an isolated copy so callers cannot mutate the frozen curriculum."""
    return deepcopy(_CASES)


def messages_for(case):
    payload = {"facts": case["facts"],
               "claims": [{"id": item["id"], "text": item["text"]} for item in case["claims"]]}
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": _canonical(payload)}]


def target_for(case):
    payload = {"claims": [{key: item[key] for key in ("id", "verdict", "evidence", "reason")}
                           for item in case["claims"]]}
    return _canonical(payload)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def score(raw, case):
    """Strictly score labels and references while preserving the raw response.

    Reasons are retained but require separate independent semantic review.
    """
    if not isinstance(raw, str):
        raise ValueError("response must be text")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")))
    except (json.JSONDecodeError, TypeError, RecursionError) as exc:
        raise ValueError("invalid JSON response") from exc
    if not isinstance(value, dict) or set(value) != {"claims"} or not isinstance(value["claims"], list):
        raise ValueError("response schema mismatch")
    expected = {item["id"]: item for item in case["claims"]}
    supplied_facts = {item["id"] for item in case["facts"]}
    seen, rows = set(), []
    for item in value["claims"]:
        if not isinstance(item, dict) or set(item) != {"id", "verdict", "evidence", "reason"}:
            raise ValueError("claim schema mismatch")
        identifier = item["id"]
        if identifier in seen:
            raise ValueError("duplicate claim ID")
        if identifier not in expected:
            raise ValueError("unexpected claim ID")
        seen.add(identifier)
        if item["verdict"] not in VERDICTS:
            raise ValueError("invalid verdict")
        evidence_ids = item["evidence"]
        if (not isinstance(evidence_ids, list) or any(not isinstance(ref, str) for ref in evidence_ids)
                or len(evidence_ids) != len(set(evidence_ids)) or not set(evidence_ids) <= supplied_facts):
            raise ValueError("invalid evidence references")
        if not isinstance(item["reason"], str) or not 1 <= len(item["reason"].strip()) <= 300:
            raise ValueError("invalid reason")
        gold = expected[identifier]["verdict"]
        predicted = item["verdict"]
        expected_evidence = expected[identifier]["evidence"]
        rows.append({"id": identifier, "expected": gold, "predicted": predicted,
                     "correct": gold == predicted, "evidence": evidence_ids,
                     "expected_evidence": expected_evidence,
                     # Exact reference agreement is diagnostic. Independent review
                     # still decides whether another supplied set is sufficient.
                     "evidence_correct": set(evidence_ids) == set(expected_evidence),
                     "reason": item["reason"]})
    if seen != set(expected) or [row["id"] for row in rows] != list(expected):
        raise ValueError("missing or reordered claim IDs")
    pairs = Counter((row["expected"], row["predicted"]) for row in rows)
    return {"correct": sum(row["correct"] for row in rows), "total": len(rows),
            "evidence_correct": sum(row["evidence_correct"] for row in rows),
            "false_support": sum(n for (gold, pred), n in pairs.items() if pred == "supported" and gold != pred),
            "false_rejection": sum(n for (gold, pred), n in pairs.items() if gold == "supported" and pred != gold),
            "unknown_as_contradicted": pairs[("unknown", "contradicted")],
            "contradicted_as_unknown": pairs[("contradicted", "unknown")],
            "rows": rows, "raw": raw, "raw_sha256": sha256(raw.encode()).hexdigest(),
            "rationale_review": "pending_independent_semantic_review"}


def validate_curriculum(data=None):
    """Enforce the small experiment's separate split and provenance gate."""
    data = _CASES if data is None else data
    counts = Counter(case["split"] for case in data)
    if dict(counts) != SPLIT_COUNTS:
        raise ValueError("unexpected curriculum split counts")
    ids, families, cross_split_text = set(), {}, {}
    for case in data:
        if case["id"] in ids:
            raise ValueError("duplicate case ID")
        ids.add(case["id"])
        family = case["family"]
        if family in families and families[family] != case["split"]:
            raise ValueError("family crosses curriculum splits")
        families[family] = case["split"]
        if not family.startswith(f"ec-{case['split']}-"):
            raise ValueError("family is not split-scoped")
        if case["provenance"] != "examiner-authored synthetic curriculum; no local-model authorship":
            raise ValueError("unexpected curriculum provenance")
        for item in (*case["facts"], *case["claims"]):
            normalized = " ".join(item["text"].casefold().split())
            prior = cross_split_text.get(normalized)
            if prior is not None and prior != case["split"]:
                raise ValueError("normalized text crosses curriculum splits")
            cross_split_text[normalized] = case["split"]
    digest = sha256(_canonical(data).encode()).hexdigest()
    return {"records": len(data), "counts": dict(counts), "sha256": digest,
            "experimental_gate": "evidence-calibration-only", "production_ready": False,
            "service_qualified": False,
            "holdout_limit": "cross-domain template transfer; not template-independent"}


validate_curriculum()

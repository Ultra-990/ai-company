import copy
import json

import pytest

from scripts import evidence_calibration_data as data


def test_curriculum_counts_categories_hashes_and_separate_gate():
    cases = data.cases()
    report = data.validate_curriculum(cases)
    assert report == {"records": 42, "counts": {"train": 24, "validation": 6, "test": 12},
                      "sha256": data.CURRICULUM_SHA256,
                      "experimental_gate": "evidence-calibration-only",
                      "production_ready": False, "service_qualified": False,
                      "holdout_limit": "cross-domain template transfer; not template-independent"}
    for split, per_category in (("train", 8), ("validation", 2), ("test", 4)):
        selected = [case for case in cases if case["split"] == split]
        assert {category: sum(c["category"] == category for c in selected)
                for category in {c["category"] for c in selected}} == {
                    "missing-vs-negative": per_category,
                    "count-vs-rule": per_category,
                    "partial-vs-conjunctive": per_category}
    assert set(data.CASE_SHA256) == {case["id"] for case in cases}
    assert all(len(value) == 64 for value in data.CASE_SHA256.values())


def test_prompts_have_no_gold_and_targets_are_compact_and_teacher_owned():
    for case in data.cases():
        messages = data.messages_for(case)
        prompt = json.loads(messages[1]["content"])
        assert all(set(claim) == {"id", "text"} for claim in prompt["claims"])
        assert not any(key in messages[1]["content"] for key in ('"verdict"', '"reason"', '"evidence"'))
        assert "local-model authorship" in case["provenance"]
        target = data.target_for(case)
        assert "\n" not in target
        assert json.loads(target)["claims"][0]["verdict"] in data.VERDICTS


def test_gold_scores_perfectly_and_raw_is_preserved():
    for case in data.cases():
        raw = data.target_for(case)
        result = data.score(raw, case)
        assert result["correct"] == result["total"] == 3
        assert result["evidence_correct"] == result["total"]
        assert result["false_support"] == result["false_rejection"] == 0
        assert result["unknown_as_contradicted"] == result["contradicted_as_unknown"] == 0
        assert result["raw"] == raw and len(result["raw_sha256"]) == 64
        assert result["rationale_review"] == "pending_independent_semantic_review"


def test_scoring_counts_error_directions():
    case = next(case for case in data.cases() if case["category"] == "partial-vs-conjunctive")
    value = json.loads(data.target_for(case))
    replacements = {"unknown": "supported", "supported": "unknown", "contradicted": "unknown"}
    for claim in value["claims"]:
        claim["verdict"] = replacements[claim["verdict"]]
    result = data.score(json.dumps(value), case)
    assert result["correct"] == 0
    assert result["false_support"] == 1
    assert result["false_rejection"] == 1
    assert result["contradicted_as_unknown"] == 1


def test_positive_verifies_is_negated_without_contradictory_duplicate_gold():
    selected = [case for case in data.cases()
                if any(word in case["family"] for word in ("planetarium", "marsh", "forge"))]
    assert len(selected) == 3
    for case in selected:
        texts = [claim["text"] for claim in case["claims"]]
        assert len(texts) == len(set(texts))
        positive = next(claim for claim in case["claims"] if claim["verdict"] == "supported")
        negative = next(claim for claim in case["claims"] if claim["verdict"] == "contradicted")
        assert positive["text"] != negative["text"]


def test_compound_examples_include_partial_full_and_contrary_evidence():
    compound = [case for case in data.cases() if case["category"] == "partial-vs-conjunctive"]
    compound_verdicts = []
    for case in compound:
        claim = next(claim for claim in case["claims"] if " and " in claim["text"])
        compound_verdicts.append(claim["verdict"])
    assert set(compound_verdicts) == data.VERDICTS


def test_claim_positions_do_not_encode_one_verdict():
    by_position = [{case["claims"][position]["verdict"] for case in data.cases()} for position in range(3)]
    assert all(verdicts == data.VERDICTS for verdicts in by_position)


@pytest.mark.parametrize("mutation,error", [
    (lambda value: value["claims"].append(copy.deepcopy(value["claims"][0])), "duplicate claim ID"),
    (lambda value: value["claims"].append({"id": "C9", "verdict": "unknown", "evidence": [], "reason": "extra"}), "unexpected claim ID"),
    (lambda value: value.update(extra=True), "response schema mismatch"),
    (lambda value: value["claims"][0].update(extra=True), "claim schema mismatch"),
    (lambda value: value["claims"][0]["evidence"].append("C1"), "invalid evidence references"),
    (lambda value: value["claims"].reverse(), "missing or reordered claim IDs"),
])
def test_strict_response_rejection(mutation, error):
    case = data.cases()[0]
    value = json.loads(data.target_for(case))
    mutation(value)
    with pytest.raises(ValueError, match=error):
        data.score(json.dumps(value), case)


def test_duplicate_json_keys_are_rejected():
    case = data.cases()[0]
    raw = data.target_for(case).replace('{"claims":', '{"claims":[],"claims":', 1)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        data.score(raw, case)


def test_split_family_and_counterfactual_leakage_guards():
    cases = data.cases()
    leaked = copy.deepcopy(cases)
    leaked[-1]["family"] = leaked[0]["family"]
    with pytest.raises(ValueError, match="family crosses"):
        data.validate_curriculum(leaked)
    renamed = copy.deepcopy(cases)
    renamed[-1]["family"] = "ec-train-partial-vs-conjunctive-renamed"
    with pytest.raises(ValueError, match="split-scoped"):
        data.validate_curriculum(renamed)

    copied_text = copy.deepcopy(cases)
    copied_text[-1]["facts"][0]["text"] = "  " + copied_text[0]["facts"][0]["text"].upper() + "  "
    with pytest.raises(ValueError, match="normalized text crosses"):
        data.validate_curriculum(copied_text)


def test_validation_digest_describes_argument_not_module_constant():
    changed = data.cases()
    changed[0]["claims"][0]["reason"] += " Synthetic clarification."
    assert data.validate_curriculum(changed)["sha256"] != data.CURRICULUM_SHA256


def test_cases_returns_defensive_copy():
    first = data.cases()
    first[0]["facts"][0]["text"] = "mutated"
    assert data.cases()[0]["facts"][0]["text"] != "mutated"

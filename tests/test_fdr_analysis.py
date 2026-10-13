"""Regression tests for real PSM q-values, CLI behavior and audit tampering."""
import csv
import math

import pytest

from agents.base import AuditTrail, parse_flag, ValidationException
from proteomics_fdr.fdr import analyze_psms
from proteomics_fdr.cli import main as fdr_main
from cli import main as legacy_main


def test_q_values_cumulative_minimum_and_acceptance():
    rows = [
        {"psm_id": "s1", "score": "10", "is_decoy": "false"},
        {"psm_id": "s2", "score": "9", "is_decoy": "false"},
        {"psm_id": "s3", "score": "8", "is_decoy": "true"},
        {"psm_id": "s4", "score": "7", "is_decoy": "false"},
    ]
    result = analyze_psms(rows, alpha=0.5)
    assert result["accepted_targets"] == 2
    assert result["score_threshold"] == 9
    assert [r["q_value"] for r in result["results"]] == pytest.approx([0.5, 0.5, 2 / 3, 2 / 3])
    assert [r["accepted"] for r in result["results"]] == [True, True, False, False]


def test_ties_are_order_independent():
    first = [
        {"psm_id": "t1", "score": 10, "is_decoy": False},
        {"psm_id": "d1", "score": 10, "is_decoy": True},
        {"psm_id": "t2", "score": 8, "is_decoy": False},
    ]
    other = [first[1], first[0], first[2]]
    q1 = {r["psm_id"]: r["q_value"] for r in analyze_psms(first)["results"]}
    q2 = {r["psm_id"]: r["q_value"] for r in analyze_psms(other)["results"]}
    assert q1 == q2
    assert q1["t1"] == q1["d1"]


def test_plus_one_correction_prevents_zero_fdr_from_no_decoys():
    rows = [{"psm_id": f"s{n}", "score": n, "is_decoy": False} for n in range(20)]
    result = analyze_psms(rows, 0.01)
    assert result["accepted_targets"] == 0
    assert all(r["q_value"] == pytest.approx(0.05) for r in result["results"])


@pytest.mark.parametrize("bad_rows", [
    [],
    [{"psm_id": "x", "score": "nan", "is_decoy": False}],
    [{"psm_id": "x", "score": "", "is_decoy": False}],
    [{"psm_id": "x", "score": 5, "is_decoy": "uncertain"}],
    [{"psm_id": "=1+1", "score": 5, "is_decoy": False}],
    [{"psm_id": "s1", "score": 5, "is_decoy": False},
     {"psm_id": "s1", "score": 6, "is_decoy": True}],
])
def test_reject_invalid_psms(bad_rows):
    with pytest.raises(ValueError):
        analyze_psms(bad_rows)


@pytest.mark.parametrize("alpha", [float("nan"), float("inf"), 0, -0.1, 1.1])
def test_reject_invalid_alpha(alpha):
    with pytest.raises(ValueError):
        analyze_psms([{"psm_id": "x", "score": 1, "is_decoy": False}], alpha)


def test_fdr_csv_cli_without_audit_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    src = tmp_path / "psms.csv"
    dst = tmp_path / "results.csv"
    src.write_text("psm_id,score,is_decoy\ns1,10,false\ns2,9,false\ns3,8,true\ns4,7,false\n")
    assert fdr_main(["fdr", "-i", str(src), "-o", str(dst), "--alpha", "0.5"]) == 0
    with dst.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 4
    assert [r["accepted"] for r in rows] == ["True", "True", "False", "False"]
    assert fdr_main(["fdr", "-i", str(src), "-o", str(src)]) == 2


def test_false_string_is_not_true_and_invalid_flags_fail():
    assert parse_flag("False") is False
    assert parse_flag("true") is True
    with pytest.raises(ValidationException):
        parse_flag("perhaps")


def test_legacy_csv_false_flag_not_critical(tmp_path):
    src = tmp_path / "tasks.csv"
    dst = tmp_path / "out.csv"
    src.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n"
        "TASK1,TARGET1,10,4,False,NOMINAL\n"
    )
    assert legacy_main(["batch", "-i", str(src), "-o", str(dst)]) == 0
    with dst.open(newline="") as handle:
        result = next(csv.DictReader(handle))
    assert result["overall_urgency"] == "ROUTINE"


def test_hmac_authenticates_signed_metadata_and_copies():
    audit = AuditTrail(secret_key="test-secret-123456789")
    audit.log("worker", "agent", "DONE", {"result": "NOMINAL"})
    assert audit.verify_integrity()
    snapshot = audit.get_trail()
    snapshot[0]["actor"] = "attacker"
    assert audit.verify_integrity()
    audit.logs[0]["actor"] = "attacker"
    assert not audit.verify_integrity()


def test_hmac_rejects_modified_payload_hash():
    audit = AuditTrail(secret_key="test-secret-123456789")
    audit.log("worker", "agent", "DONE", {"result": "NOMINAL"})
    audit.logs[0]["payload_hash"] = "0" * 64
    assert not audit.verify_integrity()

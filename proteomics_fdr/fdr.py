"""PSM-level target-decoy competition (TDC+) for pre-competed search winners.

Input rows must contain one winning target or decoy hit per spectrum. Scores are
higher-is-better and the target/decoy search spaces must have equal opportunity
to win. This module does not perform database search, spectrum competition,
peptide/protein inference, or calibration of decoy quality.
"""
import math
import re
from collections.abc import Iterable, Mapping


def _decoy_label(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        label = value.strip().lower()
        if label in ("true", "1", "yes", "decoy"):
            return True
        if label in ("false", "0", "no", "target"):
            return False
    raise ValueError("is_decoy must be true/false, 1/0, yes/no, or target/decoy")


def analyze_psms(rows: Iterable[Mapping], alpha: float = 0.01) -> dict:
    """Compute conservative PSM q-values from already-competed target/decoy wins.

    At each distinct score cutoff, estimate FDR = min(1, (decoys+1)/targets).
    The q-value is the minimum estimated FDR over all cutoffs at or below
    that score. Equal scores are grouped to avoid input-order dependence.
    Only target wins with q <= alpha count as discoveries.
    """
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 < alpha <= 1:
        raise ValueError("alpha must be finite and in (0, 1]")

    parsed = []
    seen = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            raise ValueError(f"Row {index} must be a mapping")
        identifier = row.get("psm_id")
        if (not isinstance(identifier, str) or len(identifier) > 256
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", identifier)):
            raise ValueError(f"Row {index}: psm_id must start with a letter or number and contain only letters, digits, . _ : - (max 256)")
        if identifier in seen:
            raise ValueError(f"Row {index}: duplicate psm_id {identifier!r}; supply one winning hit per spectrum")
        seen.add(identifier)
        try:
            value = row["score"]
            if isinstance(value, bool):
                raise ValueError
            if isinstance(value, str) and not re.fullmatch(
                    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?",
                    value.strip()):
                raise ValueError
            score = float(value)
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"Row {index}: score must be a finite number") from None
        if not math.isfinite(score):
            raise ValueError(f"Row {index}: score must be a finite number")
        try:
            decoy = _decoy_label(row["is_decoy"])
        except KeyError:
            raise ValueError(f"Row {index}: missing is_decoy") from None
        parsed.append({"psm_id": identifier, "score": score, "is_decoy": decoy})

    if not parsed:
        raise ValueError("At least one PSM is required")

    parsed.sort(key=lambda item: -item["score"])
    target_count = 0
    decoy_count = 0
    groups = []
    for entry in parsed:
        if not groups or groups[-1]["score"] != entry["score"]:
            groups.append({"score": entry["score"], "entries": [], "fdr": 1.0})
        groups[-1]["entries"].append(entry)
        if entry["is_decoy"]:
            decoy_count += 1
        else:
            target_count += 1
        groups[-1]["targets"] = target_count
        groups[-1]["decoys"] = decoy_count
        groups[-1]["fdr"] = min(1.0, (decoy_count + 1) / target_count) if target_count else 1.0

    best = 1.0
    for group in reversed(groups):
        best = min(best, group["fdr"])
        group["q_value"] = best
        for entry in group["entries"]:
            entry["q_value"] = best
            entry["accepted"] = not entry["is_decoy"] and best <= alpha

    accepted = [entry for entry in parsed if entry["accepted"]]
    return {
        "method": "TDC+ (decoys + 1) / targets; tied scores grouped",
        "alpha": float(alpha),
        "total_psms": len(parsed),
        "target_psms": target_count,
        "decoy_psms": decoy_count,
        "accepted_targets": len(accepted),
        "score_threshold": min((entry["score"] for entry in accepted), default=None),
        "results": parsed,
    }

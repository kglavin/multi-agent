"""Deterministic scoring for R5 cases. No judge model.

exact: 1 or 0 after normalising case, spaces, quotes, and a trailing full stop.
list:  F1 of the answer's items against the expected items.
map:   fraction of expected keys whose value matches.
An answer that does not contain the requested JSON scores 0.
"""

from __future__ import annotations

import json
import re

from harness import Case


def _norm(value) -> str:
    text = str(value).strip().strip("`\"'").strip().rstrip(".").lower()
    text = re.sub(r"\s+", " ", text)
    try:
        number = float(text.replace(",", ""))
        return str(int(number)) if number.is_integer() else str(number)
    except ValueError:
        return text


def extract_json(text: str, kind: type):
    """The first JSON value of the given type in the text, or None."""
    decoder = json.JSONDecoder()
    opener = "[" if kind is list else "{"
    for i, ch in enumerate(text):
        if ch == opener:
            try:
                value, _ = decoder.raw_decode(text, i)
            except json.JSONDecodeError:
                continue
            if isinstance(value, kind):
                return value
    return None


def score_exact(expected, answer: str) -> float:
    return float(_norm(answer) == _norm(expected))


def score_list(expected: list, answer: str) -> float:
    got = extract_json(answer, list)
    if got is None:
        return 0.0
    want, have = {_norm(x) for x in expected}, {_norm(x) for x in got}
    if not want and not have:
        return 1.0
    hits = len(want & have)
    if hits == 0:
        return 0.0
    precision, recall = hits / len(have), hits / len(want)
    return 2 * precision * recall / (precision + recall)


def score_map(expected: dict, answer: str) -> float:
    got = extract_json(answer, dict)
    if got is None:
        return 0.0
    have = {_norm(k): _norm(v) for k, v in got.items()}
    return sum(have.get(_norm(k)) == _norm(v) for k, v in expected.items()) / len(expected)


SCORERS = {"exact": score_exact, "list": score_list, "map": score_map}


def score(case: Case, answer: str) -> float:
    """Harness scorer. case.expected holds {"kind": ..., "value": ...}."""
    return SCORERS[case.expected["kind"]](case.expected["value"], answer)

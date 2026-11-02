"""Writes report.md for an experiment directory: summary charts and one sequence
diagram per configuration, in Mermaid.

    python -m harness.report <out_dir>

The sequence diagrams rely on agents running one at a time, as they do now. A
`delegate` call is matched to the next new agent in the log.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .record import read_log
from .run import summarise


def _label(text: str, limit: int = 40) -> str:
    """Make text safe for a Mermaid message label."""
    text = re.sub(r"[;#\n\r]", " ", str(text)).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _id(prefix: str, name: str) -> str:
    return prefix + re.sub(r"\W", "_", name)


def sequence_diagram(events: list[dict]) -> str:
    """One run's events as a Mermaid sequence diagram."""
    lines: list[str] = []
    participants: dict[str, str] = {}  # id -> label, in order of appearance

    def actor(name: str, tool: bool = False) -> str:
        pid = _id("t_" if tool else "a_", name)
        participants.setdefault(pid, name)
        return pid

    stack: list[str] = []  # agents currently running, innermost last
    pending_delegate: tuple[str, str] | None = None  # (task, token label)

    for e in events:
        kind = e["event"]
        if kind == "model_call":
            a = actor(e["agent"])
            tok = f"({e['input_tokens'] + e['output_tokens']} tok)"
            if not stack or stack[-1] != a:
                if pending_delegate and stack:
                    task, dtok = pending_delegate
                    lines.append(f"  {stack[-1]}->>{a}: delegate \"{_label(task)}\" {dtok}")
                    pending_delegate = None
                elif not stack:
                    lines.append(f"  Note over {a}: turn starts, input {e['input_tokens']} tok")
                stack.append(a)
            if not e["tool_calls"]:
                stack.pop()
                if stack:
                    lines.append(f"  {a}-->>{stack[-1]}: \"{_label(e['text'])}\" {tok}")
                else:
                    lines.append(f"  Note over {a}: answer \"{_label(e['text'])}\" {tok}")
                continue
            for i, call in enumerate(e["tool_calls"]):
                ctok = tok if i == 0 else ""
                if call["name"] == "delegate":
                    pending_delegate = (call["args"].get("task", ""), ctok)
                else:
                    args = ", ".join(f"{k}={v}" for k, v in call["args"].items())
                    t = actor(call["name"], tool=True)
                    lines.append(f"  {a}->>{t}: {_label(call['name'] + '(' + args + ')')} {ctok}".rstrip())
        elif kind == "tool_result" and e["name"] != "delegate":
            lines.append(f"  {actor(e['name'], tool=True)}-->>{actor(e['agent'])}: {e['chars']} chars")
        elif kind == "step_cap":
            a = actor(e["agent"])
            lines.append(f"  Note over {a}: step cap {e['max_steps']} reached")
            if stack and stack[-1] == a:
                stack.pop()
        elif kind in ("round_cap", "budget_exceeded") and participants:
            reason = e.get("reason", f"round cap {e.get('max_rounds')} reached")
            lines.append(f"  Note over {next(iter(participants))}: {_label(reason)}")

    head = ["sequenceDiagram"] + [f"  participant {pid} as {name}" for pid, name in participants.items()]
    return "\n".join(head + lines)


def _bar_chart(title: str, axis: str, names: list[str], values: list[float],
               y_max: float | None = None) -> str:
    y = f'  y-axis "{axis}"' + (f" 0 --> {y_max}" if y_max is not None else "")
    xs = ", ".join(f'"{n}"' for n in names)
    return "\n".join([
        "xychart-beta",
        f'  title "{title}"',
        f"  x-axis [{xs}]",
        y,
        f"  bar [{', '.join(f'{v:.2f}' for v in values)}]",
    ])


def _mermaid(block: str) -> str:
    return f"```mermaid\n{block}\n```"


def build_report(out_dir: Path) -> str:
    meta = json.loads((out_dir / "meta.json").read_text())
    results = read_log(out_dir / "results.jsonl")
    log = read_log(out_dir / "log.jsonl")
    summary = summarise(results)
    names = list(summary)

    parts = [
        f"# Report: {out_dir.name}",
        "",
        f"Started {meta['started']}, commit `{meta['git_commit']}`. "
        f"{meta['cases']} cases, {meta['runs']} runs each, seed {meta['seed']}, "
        f"budget {meta['max_tokens']} tokens and {meta['max_calls']} calls per run.",
        "",
        "## Summary",
        "",
        "| Configuration | Runs | Mean score | Mean tokens | Mean calls | Stopped by budget |",
        "|---|---|---|---|---|---|",
        *(f"| {n} | {s['runs']} | {s['mean_score']:.2f} | {s['mean_tokens']:.1f} | {s['mean_calls']:.1f} "
          f"| {s['stopped']} |" for n, s in summary.items()),
        "",
        _mermaid(_bar_chart("Mean score", "score", names, [summary[n]["mean_score"] for n in names], 1)),
        "",
        _mermaid(_bar_chart("Mean tokens per run", "tokens", names, [summary[n]["mean_tokens"] for n in names])),
        "",
        _mermaid(_bar_chart("Mean model calls per run", "calls", names, [summary[n]["mean_calls"] for n in names])),
        "",
        "## Runs",
        "",
        "The first run of each configuration. Token figures are input plus output for that model call.",
    ]
    for name in names:
        run_id = next(r["run_id"] for r in results if r["config"] == name)
        row = next(r for r in results if r["run_id"] == run_id)
        events = [e for e in log if e["run_id"] == run_id]
        parts += [
            "",
            f"### {name}",
            "",
            f"Run `{run_id}`: answer \"{row['answer']}\", score {row['score']}, "
            f"{row['tokens']} tokens, {row['calls']} calls.",
            "",
            _mermaid(sequence_diagram(events)),
        ]
    return "\n".join(parts) + "\n"


def main() -> None:
    out_dir = Path(sys.argv[1])
    path = out_dir / "report.md"
    path.write_text(build_report(out_dir))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

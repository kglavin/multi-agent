"""Builds cases.jsonl: ten cases per suite, each with its expected answer.

S1 answers are checked by computation below. S2 answers come from the generator's
facts. S3 answers are computed from the Django source with the ast module.

    uv run python cases.py
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from harness import Case

from corpus import S3_DIR, generate_s2

HERE = Path(__file__).parent
CASES_FILE = HERE / "cases.jsonl"

EXACT = "Reply with the answer only."
LIST = "Reply with a JSON list of strings only."
MAP = "Reply with a JSON object only, mapping {key} to {value}."


def case(id: str, suite: str, task: str, kind: str, expected) -> dict:
    corpus = {"S1": None, "S2": "corpus/s2", "S3": "corpus/s3"}[suite]
    return {"id": id, "suite": suite, "corpus": corpus, "kind": kind, "task": task, "expected": expected}


def s1_cases() -> list[dict]:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    words = sorted(["pear", "apple", "fig", "banana", "cherry"], key=lambda w: (len(w), w))
    median = sorted([4, 9, 4, 7, 9, 9, 2])[3]
    ben = next(b for b in range(1, 100) if 2 * b + 6 == 1.5 * (b + 6))
    arrive = 9 * 60 + 47 + 2 * 60 + 38
    items = [
        ("A warehouse ships 37 boxes on Monday, and each later weekday it ships 6 more boxes than the "
         "day before. How many boxes does it ship from Monday to Friday in total?",
         sum(37 + 6 * i for i in range(5))),
        ("Today is a Wednesday. What day of the week is it 100 days from today?", days[(2 + 100) % 7]),
        ("A recipe needs 3 eggs for every 4 people. How many whole eggs are needed for 18 people, "
         "rounding up?", -(-3 * 18 // 4)),
        ("How many integers from 1 to 200 inclusive are divisible by 6 or by 9?",
         sum(1 for n in range(1, 201) if n % 6 == 0 or n % 9 == 0)),
        ("Ana is twice as old as Ben. In 6 years Ana will be 1.5 times as old as Ben. How old is Ben now?",
         ben),
        ("A train leaves at 09:47 and the journey takes 2 hours and 38 minutes. When does it arrive? "
         "Give the time as HH:MM in 24-hour format.", f"{arrive // 60:02d}:{arrive % 60:02d}"),
        ("Sort the words pear, apple, fig, banana, cherry by length, breaking ties alphabetically. "
         "Which word is third?", words[2]),
        ("What is the median of 4, 9, 4, 7, 9, 9, 2?", median),
        ("A tank fills at 12 litres per minute and leaks 3 litres per minute. How many minutes does it "
         "take to hold 135 litres, starting empty?", 135 // (12 - 3)),
        ("How many times is the digit 7 written when writing every integer from 1 to 100?",
         "".join(str(n) for n in range(1, 101)).count("7")),
    ]
    return [case(f"S1-{i:02d}", "S1", f"{task} {EXACT}", "exact", answer)
            for i, (task, answer) in enumerate(items, 1)]


def s2_cases() -> list[dict]:
    _, facts = generate_s2()
    intro = ("The directory holds one profile per supplier. Use the current value where a profile "
             "gives both an old and a current one.")
    by = lambda field: {f["name"]: f[field] for f in facts}
    supplier = "each supplier's name"
    items = [
        ("map", "Which city is each supplier headquartered in now?", MAP.format(key=supplier, value="the city"),
         by("city")),
        ("map", "What is each supplier's current lead time in days?",
         MAP.format(key=supplier, value="the number of days as an integer"), by("lead_time_days")),
        ("map", "In which year was each supplier founded?", MAP.format(key=supplier, value="the year as an integer"),
         by("founded")),
        ("map", "How many people does each supplier employ?",
         MAP.format(key=supplier, value="the number of employees as an integer"), by("employees")),
        ("list", "Which suppliers hold ISO 27001 certification now?", LIST,
         sorted(f["name"] for f in facts if "ISO 27001" in f["certifications"])),
        ("map", "What product category does each supplier make?", MAP.format(key=supplier, value="the category"),
         by("category")),
        ("map", "What is each supplier's minimum order value in euros?",
         MAP.format(key=supplier, value="the value as an integer"), by("min_order_eur")),
        ("map", "Who is each supplier's current account contact?", MAP.format(key=supplier, value="the person's name"),
         by("contact")),
        ("list", "Which suppliers were founded before 2000 and have a current lead time under 20 days?", LIST,
         sorted(f["name"] for f in facts if f["founded"] < 2000 and f["lead_time_days"] < 20)),
        ("list", "Which suppliers are headquartered in Germany now?", LIST,
         sorted(f["name"] for f in facts if f["country"] == "Germany")),
    ]
    return [case(f"S2-{i:02d}", "S2", f"{intro} {q} {fmt}", kind, answer)
            for i, (kind, q, fmt, answer) in enumerate(items, 1)]


# S3: answers computed from the Django source.

def _modules(sub: str):
    for path in sorted((S3_DIR / sub).rglob("*.py")):
        yield path, ast.parse(path.read_text(), filename=str(path))


def _base_names(cls: ast.ClassDef) -> set[str]:
    return {b.id if isinstance(b, ast.Name) else b.attr for b in cls.bases if isinstance(b, (ast.Name, ast.Attribute))}


def _string(node) -> str | None:
    """A string literal, or the literal inside a gettext call such as _("...")."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call) and node.args:
        return _string(node.args[0])
    return None


def _class_attr(cls: ast.ClassDef, name: str):
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in stmt.targets):
            return stmt.value
    return None


def _commands():
    for path, tree in _modules("django"):
        if path.parent.name == "commands" and path.parent.parent.name == "management" and path.name != "__init__.py":
            cmd = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Command"), None)
            if cmd:
                yield path.stem, cmd


def s3_answers() -> list[tuple[str, str, str, object]]:
    contrib_names = {}
    for path, tree in _modules("django/contrib"):
        if path.name == "apps.py" and path.parent.parent.name == "contrib":
            for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
                value = _class_attr(cls, "verbose_name")
                if value is not None:
                    contrib_names[path.parent.name] = _string(value)
                    break

    field_subclasses = sorted({cls.name for _, tree in _modules("django/db/models/fields")
                               for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef) and "Field" in _base_names(cls)})

    no_checks = sorted({name for name, cmd in _commands()
                        if isinstance(v := _class_attr(cmd, "requires_system_checks"), ast.List) and not v.elts})

    database_option = sorted({name for name, cmd in _commands()
                              for call in ast.walk(cmd)
                              if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                              and call.func.attr == "add_argument" and call.args
                              and _string(call.args[0]) == "--database"})

    value_errors = sorted({cls.name for _, tree in _modules("django")
                           for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef) and "ValueError" in _base_names(cls)})

    many_params = []
    for path, tree in _modules("django/utils"):
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef):
                a = fn.args
                if len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs) >= 5:
                    many_params.append(f"{path.relative_to(S3_DIR).as_posix()}:{fn.name}")

    def backend_class(name: str, module: str, cls: str) -> ast.ClassDef:
        tree = ast.parse((S3_DIR / "django/db/backends" / name / module).read_text())
        return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)

    backends = {name: _string(_class_attr(backend_class(name, "base.py", "DatabaseWrapper"), "vendor"))
                for name in ["mysql", "oracle", "postgresql", "sqlite3"]}
    min_version = {name: ".".join(str(e.value) for e in _class_attr(
                       backend_class(name, "features.py", "DatabaseFeatures"), "minimum_database_version").elts)
                   for name in ["oracle", "postgresql", "sqlite3"]}

    middleware = sorted({cls.name for _, tree in _modules("django")
                         for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef) and "MiddlewareMixin" in _base_names(cls)})

    signals = sorted({t.id for _, tree in _modules("django") for stmt in tree.body
                      if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call)
                      and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id in ("Signal", "ModelSignal")
                      for t in stmt.targets if isinstance(t, ast.Name)})

    return [
        ("map", "For each app directory directly under django/contrib that has an apps.py, what is the "
                "verbose_name of the first AppConfig class in that file that sets one? Give the string inside "
                "the translation call.", MAP.format(key="the app directory name", value="the verbose_name"),
         contrib_names),
        ("list", "Which classes defined in django/db/models/fields/ list Field directly among their base classes?",
         LIST, field_subclasses),
        ("list", "Which management commands in the django package set requires_system_checks to an empty list? "
                 "Give command names, which are the module file names without .py.", LIST, no_checks),
        ("list", "Which management commands in the django package add a --database option in add_arguments? "
                 "Give command names, which are the module file names without .py.", LIST, database_option),
        ("list", "Which classes in the django package list ValueError directly among their base classes?",
         LIST, value_errors),
        ("list", "Which top-level functions in modules under django/utils take five or more named parameters, "
                 "not counting *args and **kwargs? Give each as path:function, for example "
                 "django/utils/example.py:func.", LIST, many_params),
        ("map", "What is the vendor attribute of DatabaseWrapper in each of the mysql, oracle, postgresql, and "
                "sqlite3 backends?", MAP.format(key="the backend directory name", value="the vendor string"),
         backends),
        ("map", "What minimum_database_version does DatabaseFeatures set in each of the oracle, postgresql, and "
                "sqlite3 backends? Write each version tuple as a dotted string, for example (3, 9) as 3.9.",
         MAP.format(key="the backend directory name", value="the dotted version string"), min_version),
        ("list", "Which classes in the django package list MiddlewareMixin directly among their base classes?",
         LIST, middleware),
        ("list", "Which module-level names in the django package are assigned a new Signal or ModelSignal "
                 "instance, for example name = Signal()?", LIST, signals),
    ]


def s3_cases() -> list[dict]:
    intro = "The directory holds the Python source of the Django 5.2 package."
    return [case(f"S3-{i:02d}", "S3", f"{intro} {q} {fmt}", kind, answer)
            for i, (kind, q, fmt, answer) in enumerate(s3_answers(), 1)]


def build() -> list[dict]:
    return s1_cases() + s2_cases() + s3_cases()


if __name__ == "__main__":
    cases = build()
    CASES_FILE.write_text("".join(json.dumps(c) + "\n" for c in cases))
    print(f"wrote {len(cases)} cases to {CASES_FILE}")


def load(path: Path = CASES_FILE) -> list[Case]:
    """cases.jsonl as harness cases. Case.expected holds the kind and value for score.py."""
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return [Case(r["id"], r["task"], {"kind": r["kind"], "value": r["expected"]}) for r in rows]

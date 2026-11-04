"""Builds the two corpora.

S2: twenty fictional supplier profiles, generated from a fixed seed and committed.
S3: the Python source of Django 5.2, fetched at a pinned commit and not committed.

    uv run python corpus.py
"""

from __future__ import annotations

import random
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
S2_DIR = HERE / "corpus" / "s2"
S3_DIR = HERE / "corpus" / "s3"

S3_REPO = "https://github.com/django/django"
S3_TAG = "5.2"
S3_COMMIT = "9e7cc2b628fe8fd3895986af9b7fc9525034c1b0"

S2_SEED = 1

CITIES = {
    "Hamburg": "Germany", "Leipzig": "Germany", "Stuttgart": "Germany",
    "Lyon": "France", "Lille": "France",
    "Utrecht": "Netherlands", "Eindhoven": "Netherlands",
    "Gdansk": "Poland", "Wroclaw": "Poland",
    "Valencia": "Spain", "Bilbao": "Spain",
    "Turin": "Italy", "Bologna": "Italy",
    "Gothenburg": "Sweden", "Brno": "Czechia",
}
CATEGORIES = ["fasteners", "bearings", "circuit boards", "packaging", "castings", "cable harnesses",
              "sensors", "adhesives", "valves", "springs"]
CERTS = ["ISO 9001", "ISO 14001", "ISO 27001"]
FIRST = ["Mara", "Tomas", "Ines", "Jonas", "Elif", "Pavel", "Lucia", "Henrik", "Noor", "Ada", "Milo",
         "Sanne", "Ruben", "Katja", "Oskar", "Leila", "Bruno", "Greta", "Ivo", "Zofia"]
LAST = ["Brandt", "Okafor", "Lindqvist", "Moreau", "Novak", "Ferreira", "Kowalski", "Visser", "Rossi",
        "Hartmann", "Duarte", "Sorensen", "Bakker", "Weiss", "Aalto", "Marchetti", "Holm", "Kaya"]
SYLLABLES = ["var", "kel", "dor", "mi", "tan", "sel", "bro", "qui", "lum", "ost", "ren", "pha", "gal",
             "nor", "vik", "zet", "aro", "mel"]
SUFFIXES = ["Components", "Industries", "Works", "Manufacturing", "Supply", "Technik", "Systems"]

FILLER = [
    "The company publishes a short sustainability report each spring.",
    "Its sales team attends two regional trade fairs a year.",
    "Customers describe its documentation as thorough but slow to update.",
    "The firm runs a small apprenticeship programme with a local college.",
    "Payment terms are thirty days from invoice for established customers.",
    "It keeps a modest stock of spare parts for older product lines.",
    "Quality complaints are handled by a dedicated customer desk.",
    "The site operates two shifts on weekdays and none at weekends.",
]


def _person(rng: random.Random, taken: set[str]) -> str:
    while True:
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name not in taken:
            taken.add(name)
            return name


def generate_s2(seed: int = S2_SEED) -> tuple[dict[str, str], list[dict]]:
    """Returns ({filename: markdown}, facts). Deterministic for a given seed."""
    rng = random.Random(seed)
    names: set[str] = set()
    people: set[str] = set()
    docs, facts = {}, []
    while len(facts) < 20:
        name = (rng.choice(SYLLABLES) + rng.choice(SYLLABLES)).capitalize() + " " + rng.choice(SUFFIXES)
        if name in names:
            continue
        names.add(name)
        city, old_city = rng.sample(list(CITIES), 2)
        lead, old_lead = rng.sample(range(5, 46), 2)
        certs = [c for c in CERTS if rng.random() < 0.45]
        f = {
            "name": name,
            "founded": rng.randint(1962, 2019),
            "city": city,
            "country": CITIES[city],
            "employees": rng.randint(40, 4800),
            "lead_time_days": lead,
            "category": rng.choice(CATEGORIES),
            "min_order_eur": rng.randrange(500, 20001, 250),
            "contact": _person(rng, people),
            "certifications": certs,
        }
        facts.append(f)

        paras = [
            f"{name} was founded in {f['founded']} and makes {f['category']} for industrial customers. "
            f"It employs {f['employees']:,} people.",
            f"The company moved its headquarters from {old_city}, {CITIES[old_city]}, to {city}, "
            f"{f['country']}, in {rng.randint(max(f['founded'] + 1, 2005), 2025)}.",
            f"Standard lead time was {old_lead} days until last year. After a change of logistics "
            f"partner it is now {lead} days.",
            f"The minimum order value is EUR {f['min_order_eur']:,}.",
            f"The account contact is {f['contact']}, who took over from {_person(rng, people)}.",
        ]
        if certs:
            paras.append(f"{name} holds {', '.join(certs)} certification.")
        else:
            paras.append(f"{name} holds no ISO certification.")
        missing = [c for c in CERTS if c not in certs]
        if missing and rng.random() < 0.5:
            paras.append(f"It is working towards {missing[-1]}, expected next year, but does not hold it yet.")
        body = paras[:1] + rng.sample(paras[1:] + rng.sample(FILLER, 3), len(paras) - 1 + 3)
        slug = name.lower().replace(" ", "-")
        docs[f"{slug}.md"] = f"# {name}\n\n" + "\n\n".join(body) + "\n"
    return docs, facts


def write_s2() -> None:
    docs, _ = generate_s2()
    if S2_DIR.exists():
        shutil.rmtree(S2_DIR)
    S2_DIR.mkdir(parents=True)
    for filename, text in docs.items():
        (S2_DIR / filename).write_text(text)


def fetch_s3() -> None:
    """Clones Django at the pinned tag, checks the commit, and keeps only django/**/*.py."""
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "django"
        subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1", "--branch", S3_TAG, S3_REPO, str(clone)],
                       check=True)
        commit = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
        if commit != S3_COMMIT:
            raise SystemExit(f"expected commit {S3_COMMIT}, got {commit}")
        if S3_DIR.exists():
            shutil.rmtree(S3_DIR)
        for src in (clone / "django").rglob("*.py"):
            dst = S3_DIR / src.relative_to(clone)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        shutil.copyfile(clone / "LICENSE", S3_DIR / "LICENSE")


if __name__ == "__main__":
    write_s2()
    print(f"wrote {len(list(S2_DIR.glob('*.md')))} documents to {S2_DIR}")
    if not (S3_DIR / "django").exists():
        fetch_s3()
    files = list(S3_DIR.rglob("*.py"))
    print(f"S3: {len(files)} files, {sum(f.stat().st_size for f in files):,} bytes in {S3_DIR}")

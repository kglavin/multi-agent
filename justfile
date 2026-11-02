# List recipes
default:
    @just --list

# Create the harness virtualenv and install dependencies
[working-directory('research/harness')]
sync:
    uv sync

# Run the harness tests
[working-directory('research/harness')]
test *args:
    uv run pytest {{args}}

# Run C1 to C4 on the toy task with the stub model
[working-directory('research/harness')]
dry-run out="out/dry-run":
    uv run python examples/dry_run.py {{out}}

# Write report.md (Mermaid charts and sequence diagrams) for an experiment directory
[working-directory('research/harness')]
report out="out/dry-run":
    uv run python -m harness.report {{out}}

import sys
from pathlib import Path

# generate some badges with metadata of failure by default
# (do be overwritten on success)

templatePath = Path("ci/badge.svg.tmpl")

states = {
    "good": {"color": ("34D058", "28A745"), "message": "Good"},
    "bad": {"color": ("D73A49", "CB2431"), "message": "Fail"},
}
try:
    state = sys.argv[1]
    assert state in states.keys()
except (IndexError, AssertionError):
    print(f"Please provide a command, one of {list(states.keys())}!")
    sys.exit(1)
try:
    badgefn = Path(sys.argv[2])
except IndexError:
    print("Please provide an output file!")
    sys.exit(1)


def generate(fn, state):
    assert state in states.keys(), f"Requested state {state} not available!"
    if not fn.parent.is_dir():
        fn.parent.mkdir(parents=True, exist_ok=True)
    data = None
    with open(templatePath) as fh:
        data = fh.read()
    with open(fn, "w") as fh:
        fh.write(data.format(label=fn.stem.title(), **states[state]))


generate(badgefn, state)

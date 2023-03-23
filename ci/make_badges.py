import json
import sys
from pathlib import Path

# generate some badges with metadata of failure by default
# (do be overwritten on success)

# see https://github.com/badges/shields/blob/master/badge-maker/lib/color.js
colorGood = "success"
colorBad = "critical"

try:
    cmd = sys.argv[1]
    assert cmd in ("create", "update")
except (IndexError, AssertionError):
    print("Please provide a command, one of [create,update]!")
    raise
try:
    distPath = Path(sys.argv[2])
except IndexError:
    print("Please provide the documentation output dir!")
    raise

if cmd == "create":
    badgeDir = distPath / "badges"
    badgeDir.mkdir(parents=True, exist_ok=True)
    for topic in ("Docs", "Build", "Tests"):
        data = dict(schemaVersion=1, label=topic, message="Fail", color=colorBad, style="plastic")
        with open(badgeDir / (topic.lower() + ".json"), "w") as fh:
            json.dump(data, fh)

elif cmd == "update":
    assert distPath.is_file(), "Provided file path does not exist!"
    data = None
    with open(distPath) as fh:
        data = json.load(fh)
    data["message"] = "Good"
    data["color"] = colorGood
    with open(distPath, "w") as fh:
        json.dump(data, fh)

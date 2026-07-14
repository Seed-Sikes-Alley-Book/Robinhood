#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VERSION_FILE = Path("version.txt")

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

def read_version():
    if not VERSION_FILE.exists():
        print("✘ version.txt not found.")
        sys.exit(1)
    return VERSION_FILE.read_text().strip()

def write_version(v: str):
    VERSION_FILE.write_text(v + "\n")
    print(f"✔ Updated version to {v}")

def validate(v: str):
    return SEMVER.match(v) is not None

def bump(v: str, part: str) -> str:
    major, minor, patch = map(int, v.split("."))

    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    elif part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print("✘ Unknown bump type. Use: major | minor | patch")
        sys.exit(2)

def main():
    if len(sys.argv) != 2:
        print("Usage: bump_version.py <major|minor|patch>")
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    current = read_version()

    if not validate(current):
        print(f"✘ Current version '{current}' is not valid SemVer.")
        sys.exit(2)

    new_version = bump(current, bump_type)
    write_version(new_version)

if __name__ == "__main__":
    main()

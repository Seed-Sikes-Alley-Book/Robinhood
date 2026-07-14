#!/usr/bin/env python3
import re
import sys

# Strict Semantic Versioning: MAJOR.MINOR.PATCH
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

def validate_version(v: str) -> bool:
    return SEMVER.match(v) is not None

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_version.py <version>")
        sys.exit(1)

    version = sys.argv[1].strip()

    if validate_version(version):
        print(f"✔ Version '{version}' is valid SemVer.")
        sys.exit(0)
    else:
        print(f"✘ Version '{version}' is NOT valid SemVer.")
        sys.exit(2)

if __name__ == "__main__":
    main()

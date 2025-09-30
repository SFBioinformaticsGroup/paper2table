import argparse
import json
import sys
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import ValidationError

from .schema import TablesFile


def validate_file(path: Path) -> Optional[ValueError]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        TablesFile.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        return e


def validate_files(paths: List[Path], mode: Literal["quiet", "all", "valid"]) -> int:
    for path in paths:
        error = validate_file(path)

        if mode == "quiet":
            if error:
                return 1
        elif mode == "all":
            status = "INVALID" if error else "VALID"
            print(f"{path}: {status}")
            if error:
                print(error)
        elif error:
            print(f"{path}: INVALID")
            if error:
                print(error)
            return 1
        else:
            print(f"{path}: VALID")

    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate JSON tables files against the schema"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Fail on the first wrong file, exit 1, no output",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Validate all files and print which are valid/invalid",
    )
    parser.add_argument(
        "paths", nargs="+", type=Path, help="One or more JSON files to validate"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.quiet:
        mode = "quiet"
    elif args.all:
        mode = "all"
    else:
        mode = "default"

    exit_code = validate_files(args.paths, mode)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

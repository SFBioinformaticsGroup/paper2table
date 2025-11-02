import argparse
import hashlib
import os

from utils.normalize_name import normalize_name
from utils.handle_sigint import handle_sigint


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", help="List of files to process")
    p.add_argument(
        "-y", "--yes", action="store_true", help="Do not ask for confirmation"
    )
    p.add_argument(
        "-q", "--quiet", action="store_true", help="Don't explain actions performed"
    )
    return p.parse_args()


def md5sum(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def plan_actions(files: list[str]):
    checksums = {}
    duplicates = {}
    for file in files:
        md5 = md5sum(file)
        if md5 not in checksums:
            checksums[md5] = file
        else:
            new = file
            old = checksums[md5]
            new_basename, _ = os.path.splitext(os.path.basename(new))
            old_basename, _ = os.path.splitext(os.path.basename(old))

            if normalize_name(new_basename) == old_basename:
                keep = old
            elif normalize_name(old_basename) == new_basename:
                keep = new
            else:
                keep = min([old, new], key=len)
            drop = [ff for ff in [old, new] if ff != keep]
            checksums[md5] = keep
            duplicates.setdefault(md5, []).extend(drop)

    renames = {}
    seen = set()
    for file in checksums.values():
        base, ext = os.path.splitext(os.path.basename(file))
        new_base = normalize_name(base)
        candidate = new_base + ext.lower()
        idx = 1
        while candidate in seen:
            candidate = f"{new_base}_{idx}{ext.lower()}"
            idx += 1
        seen.add(candidate)
        if candidate != os.path.basename(file):
            renames[file] = candidate

    return duplicates, renames, checksums


def execute(
    duplicates, renames, confirm_delete, confirm_rename, explain_delete, explain_rename
):
    for md5, duplicates in duplicates.items():
        for file in duplicates:
            if confirm_delete(md5, file):
                os.remove(file)
                explain_delete(file)
    for old, new in renames.items():
        if confirm_rename(old, new):
            new_path = os.path.join(os.path.dirname(old), new)
            os.rename(old, new_path)
            explain_rename(old, new)


def confirm(question):
    return input(f"{question} [y/N] ").strip().lower() == "y"


def main():
    handle_sigint()

    args = parse_args()
    duplicates, renames, checksums = plan_actions(args.files)
    if args.yes:

        def confirm_delete(_md5, _file):
            return True

        def confirm_rename(_original, _new):
            return True

    else:

        def confirm_delete(md5, file):
            return confirm(
                f"Delete duplicate file {file} ({md5}, will preserve it as {checksums[md5]} )?"
            )

        def confirm_rename(original, new):
            return confirm(f"Rename {original} to {new}?")

    if args.quiet:

        def explain_delete(_file):
            pass

        def explain_rename(_original, _new):
            pass

    else:

        def explain_delete(file):
            return print(f"File {file} deleted")

        def explain_rename(original, new):
            return print(f"File {original} renamed to {new}")

    execute(
        duplicates,
        renames,
        confirm_delete=confirm_delete,
        confirm_rename=confirm_rename,
        explain_delete=explain_delete,
        explain_rename=explain_rename,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""Upload files to the Files section of a Canvas course."""

import argparse
import os
import sys

from canvas_common import (
    fail,
    connect,
    print_current_quarter,
    select_course,
    file_url,
)


def normalize_folder(folder):
    """Turn a user-supplied folder into a clean relative Canvas path.

    Accepts both '/' and '\\' as separators and ignores leading/trailing/
    repeated separators.  Returns e.g. 'data/lab3', or None if the result
    is empty or contains '.' or '..' components.
    """
    parts = [p for p in folder.replace("\\", "/").split("/") if p]
    if not parts or any(p in (".", "..") for p in parts):
        return None
    return "/".join(parts)


def existing_files(course, folder):
    """Return (folder_exists, set of file names) for a course folder path.

    A folder that does not exist yet has no files.
    """
    segments = folder.split("/")
    try:
        chain = list(course.resolve_path(folder))
    except Exception:
        return False, set()
    # resolve_path lists the course root plus one folder per path segment;
    # a shorter list means only a prefix of the path exists.
    if len(chain) != len(segments) + 1:
        return False, set()
    return True, {f.display_name for f in chain[-1].get_files()}


parser = argparse.ArgumentParser(
    description="Upload files to the Files section of a Canvas course.  "
                "A file with the same name in the same folder is overwritten."
)
parser.add_argument("files", nargs="+", metavar="FILE", help="file(s) to upload")
parser.add_argument(
    "-f", "--folder",
    help="destination folder in the course Files, e.g. 'data' or 'data/lab3' "
         "(created if missing).  Required.",
)
parser.add_argument(
    "-i", "--id",
    dest="course_id",
    type=int,
    metavar="ID",
    help="Canvas course ID to upload into (skips the course-selection prompt).",
)
args = parser.parse_args()

# Validate everything we can before touching Canvas.
if args.folder is None:
    fail("no destination folder given.  Use -f/--folder, e.g. --folder data")
folder = normalize_folder(args.folder)
if folder is None:
    fail(f"invalid folder {args.folder!r}.  Give a relative path such as "
         f"'data' or 'data/lab3'.")

missing = [f for f in args.files if not os.path.isfile(f)]
if missing:
    fail("not an existing file (nothing was uploaded):\n"
         + "\n".join(f"       {f}" for f in missing))

names = [os.path.basename(f) for f in args.files]
duplicates = sorted({n for n in names if names.count(n) > 1})
if duplicates:
    fail("several files would have the same name in Canvas "
         f"({', '.join(duplicates)}); the later one would overwrite the "
         "earlier one.  Nothing was uploaded.")

canvas, user = connect()
quarter_season, quarter_year = print_current_quarter()
course = select_course(canvas, user, quarter_season, quarter_year, args.course_id)

folder_exists, present = existing_files(course, folder)
if not folder_exists:
    print(f"Folder '{folder}' does not exist; it will be created.")

failed = []
for path in args.files:
    name = os.path.basename(path)
    action = "Overwrote" if name in present else "Created"
    try:
        ok, response = course.upload(
            path, parent_folder_path=folder, on_duplicate="overwrite"
        )
        if not ok:
            raise RuntimeError("Canvas did not accept the upload")
    except Exception as e:
        print(f"FAILED  {path}: {e}", file=sys.stderr)
        failed.append(path)
        continue
    print(f"{action} {folder}/{response['display_name']}: "
          f"{file_url(course.id, response['id'])}")

total = len(args.files)
print(f"\n{total - len(failed)} of {total} file(s) uploaded to '{folder}'.")
if failed:
    print("Failed:\n" + "\n".join(f"  {f}" for f in failed), file=sys.stderr)
    sys.exit(1)

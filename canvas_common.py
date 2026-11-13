"""Code shared by the Canvas command-line tools in this directory.

Provides: error reporting, settings from `.env` files, the Canvas
connection, quarter-name handling and course selection.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import pytz
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from dotenv import dotenv_values

CANVAS_TZ = "America/Los_Angeles"
SEASONS = {"au": "Au", "wi": "Wi", "sp": "Sp", "su": "Su"}


def fail(msg):
    """Print an error message to stderr and exit with a non-zero status."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Settings (.env files) and connection
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_NAME = ".env"
ENV_OVERRIDE_VAR = "CANVAS_ENV_FILE"


def candidate_env_files():
    """Existing .env files, highest priority first.

    Order: the file named by $CANVAS_ENV_FILE, `.env` in the current
    directory and then in each parent directory, and `.env` in the directory
    of these scripts.
    """
    paths = []
    override = os.getenv(ENV_OVERRIDE_VAR)
    if override:
        p = Path(override).expanduser()
        if not p.is_file():
            fail(f"{ENV_OVERRIDE_VAR} points to a file that does not exist: {p}")
        paths.append(p)
    cwd = Path.cwd()
    paths += [d / ENV_NAME for d in (cwd, *cwd.parents)]
    paths.append(SCRIPT_DIR / ENV_NAME)

    found, seen = [], set()
    for p in paths:
        if p.is_file() and p.resolve() not in seen:
            seen.add(p.resolve())
            found.append(p.resolve())
    return found


def _check_mode(path):
    """Refuse a credentials file that other users can read (POSIX only).

    Windows does not expose meaningful permission bits through os.stat.
    """
    if os.name == "nt":
        return
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        fail(
            f"{path} has insecure permissions {oct(mode)} — it may be "
            f"readable by other users.\n"
            f"       It must be readable only by you (mode 600).\n"
            f"       Fix with: chmod 600 {path}"
        )


def load_settings():
    """Collect API_URL, API_KEY and (optionally) COURSE_ID.

    Real environment variables win over files.  Among files, the one found
    first (see candidate_env_files) wins.  Safety rule: API_URL and API_KEY
    are always taken *together from a single file*, the first one that
    defines API_KEY, so that a stray .env elsewhere can never redirect your
    key to a different host.  COURSE_ID is taken from the first file that
    defines it.  The mode-600 check applies to the file that holds the key.

    Returns a dict with api_url, api_key, credentials_source, course_id
    (int or None) and course_id_source.
    """
    files = candidate_env_files()
    values = [(p, {k: v for k, v in dotenv_values(p).items() if v}) for p in files]

    env_url, env_key = os.getenv("API_URL"), os.getenv("API_KEY")
    if env_url and env_key:
        api_url, api_key, cred_source = env_url, env_key, "environment variables"
    else:
        for p, vals in values:
            if "API_KEY" not in vals:
                continue
            _check_mode(p)
            if "API_URL" not in vals:
                fail(
                    f"{p} defines API_KEY but not API_URL.\n"
                    f"       API_URL and API_KEY must be set together in the same file."
                )
            api_url, api_key, cred_source = vals["API_URL"], vals["API_KEY"], str(p)
            break
        else:
            found = "".join(f"\n       found (no API_KEY): {p}" for p in files)
            fail(
                "no .env file defines API_URL and API_KEY.\n"
                f"       Looked for `.env` in: ${ENV_OVERRIDE_VAR} (if set), the "
                f"current directory and its parents, and {SCRIPT_DIR}.\n"
                f"       Create one (e.g. from .env-template).{found}"
            )

    raw_course = os.getenv("COURSE_ID")
    course_source = "environment variable COURSE_ID"
    if not raw_course:
        for p, vals in values:
            if "COURSE_ID" in vals:
                raw_course, course_source = vals["COURSE_ID"], str(p)
                break
    course_id = None
    if raw_course:
        try:
            course_id = int(raw_course)
        except ValueError:
            fail(f"COURSE_ID must be an integer, got {raw_course!r} (from {course_source})")

    return {
        "api_url": api_url,
        "api_key": api_key,
        "credentials_source": cred_source,
        "course_id": course_id,
        "course_id_source": course_source if course_id is not None else None,
    }


def connect(settings=None):
    """Connect to Canvas and print the current user.

    Loads the settings unless they are passed in.  Returns (canvas, user).
    """
    if settings is None:
        settings = load_settings()
    print(f"Using credentials from {settings['credentials_source']}")
    canvas = Canvas(settings["api_url"], settings["api_key"])
    user = canvas.get_current_user()
    print(f"Current User: {user.name} ({user.id})")
    return canvas, user


def file_url(api_url, course_id, file_id):
    """Browser URL of a course file, built from the host in api_url.

    api_url may or may not have a trailing slash or an `/api/v1` suffix.
    The API's own download URL is not used: it contains a per-file token.
    """
    parts = urlsplit(api_url)
    return f"{parts.scheme}://{parts.netloc}/courses/{course_id}/files/{file_id}"


# ---------------------------------------------------------------------------
# Quarter names
# ---------------------------------------------------------------------------

def current_quarter(ref=None):
    """Return (season, year) of the quarter containing ref (default: now in CANVAS_TZ).

    Quarters begin: Autumn Aug 1, Winter Nov 1, Spring Feb 1, Summer May 1.
    """
    if ref is None:
        ref = datetime.now(pytz.timezone(CANVAS_TZ))
    m = ref.month
    if m in (8, 9, 10):
        return "Au", ref.year
    if m in (11, 12):
        return "Wi", ref.year + 1
    if m == 1:
        return "Wi", ref.year
    if m in (2, 3, 4):
        return "Sp", ref.year
    return "Su", ref.year


def parse_quarter_name(name):
    """Parse a quarter name in any of 'yyyy-ss', 'ss yy' (space/hyphen) or 'yy ss',
    season case-insensitive.  Returns (season, 4-digit year) or None."""
    tokens = re.split(r"[^A-Za-z0-9]+", name.strip())
    if len(tokens) != 2:
        return None
    season_tok = year_tok = None
    for tok in tokens:
        t = tok.lower()
        if t in SEASONS:
            if season_tok is not None:
                return None
            season_tok = t
        elif re.fullmatch(r"\d{2}|\d{4}", t):
            if year_tok is not None:
                return None
            year_tok = t
        else:
            return None
    if season_tok is None or year_tok is None:
        return None
    year = int(year_tok) + (0 if len(year_tok) == 4 else 2000)
    return SEASONS[season_tok], year


def references_quarter(text, season, year):
    """True if text contains the quarter in any accepted form (case-insensitive)."""
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", text.strip()) if t]
    for i in range(len(tokens) - 1):
        if parse_quarter_name(tokens[i] + " " + tokens[i + 1]) == (season, year):
            return True
    return False


def quarter_label(season, year):
    """Short quarter label as used in course names, e.g. 'Au 26'."""
    return f"{season} {year % 100}"


def print_current_quarter():
    """Print the current quarter and return (season, year)."""
    season, year = current_quarter()
    print(f"Current quarter: {quarter_label(season, year)} ({year}-{season})")
    return season, year


# ---------------------------------------------------------------------------
# Course selection
# ---------------------------------------------------------------------------

def is_test_course(name, season, year):
    """True for courses of the current quarter, or the _Test_Assignment_Uploads course."""
    return ("_Test_Assignment_Uploads" in name) or references_quarter(name, season, year)


def select_course(canvas, user, season, year, course_id=None):
    """Return the Canvas course to work on.

    If course_id is None, list the user's courses of the given quarter (plus
    _Test_Assignment_Uploads) and prompt for the id.
    """
    if course_id is None:
        enrollments = user.get_enrollments(enrollment_state=["active"], include=["course"])

        print(f"\nAll courses in {quarter_label(season, year)} (plus _Test_Assignment_Uploads):")
        for enrollment in enrollments:
            cid = enrollment.course_id

            try:
                cname = canvas.get_course(cid).name
            except Exception:
                cname = "unknown"

            if is_test_course(cname, season, year):
                print(f"{cid}: {cname}")

        course_id = int(input("\nInput Course ID: "))

    try:
        course = canvas.get_course(course_id)
    except CanvasException as e:
        fail(
            f"cannot open course {course_id} ({type(e).__name__}).\n"
            f"       Check the course ID (a stale COURSE_ID in a .env file?) "
            f"and that your access token is valid."
        )
    print(f"Selected course: {course.name}")
    return course

"""Code shared by the Canvas command-line tools in this directory.

Provides: error reporting, `.env` loading and validation, the Canvas
connection, quarter-name handling and course selection.
"""

import os
import re
import sys
from datetime import datetime

import pytz
from canvasapi import Canvas
from dotenv import load_dotenv

CANVAS_TZ = "America/Los_Angeles"
SEASONS = {"au": "Au", "wi": "Wi", "sp": "Sp", "su": "Su"}


def fail(msg):
    """Print an error message to stderr and exit with a non-zero status."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Credentials and connection
# ---------------------------------------------------------------------------

def check_env_file(env_path=".env"):
    """Validate the .env file (exists, mode 600, defines API_URL & API_KEY).

    The permission check is done on POSIX systems only: Windows does not
    expose meaningful permission bits through os.stat.

    Returns (api_url, api_key) once the file has been loaded.
    """
    if not os.path.isfile(env_path):
        fail(
            f".env file not found: {env_path}\n"
            f"       Create it (e.g. from .env-template) with API_URL and API_KEY."
        )

    if os.name != "nt":
        mode = os.stat(env_path).st_mode & 0o777
        if mode & 0o077:
            fail(
                f".env file has insecure permissions {oct(mode)} — it may be "
                f"readable by other users.\n"
                f"       It must be readable only by you (mode 600).\n"
                f"       Fix with: chmod 600 {env_path}"
            )

    load_dotenv(env_path)
    missing = [
        name
        for name in ("API_URL", "API_KEY")
        if not os.getenv(name)
    ]
    if missing:
        fail(
            ".env file is missing required value(s): "
            + ", ".join(missing)
            + "\n       Both API_URL and API_KEY must be set."
        )

    return os.getenv("API_URL"), os.getenv("API_KEY")


def connect():
    """Load .env, connect to Canvas and print the current user.

    Returns (canvas, user).
    """
    api_url, api_key = check_env_file()
    canvas = Canvas(api_url, api_key)
    user = canvas.get_current_user()
    print(f"Current User: {user.name} ({user.id})")
    return canvas, user


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

    course = canvas.get_course(course_id)
    print(f"Selected course: {course.name}")
    return course

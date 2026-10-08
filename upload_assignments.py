#!/usr/bin/env python

## * if schedule file cannot be found
## * print results in Seattle time zone
## * Tell what are the current assignment dates

import argparse
import pandas as pd
from canvasapi import Canvas
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import sys
import pytz

CANVAS_TZ = "America/Los_Angeles"
SEASONS = {"au": "Au", "wi": "Wi", "sp": "Sp", "su": "Su"}
ASSIGNMENT_TYPES = ("PS", "Lab", "Quiz", "Project")
DUE_TIME = "23:59"


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


def is_test_course(name, season, year):
    """True for courses of the current quarter, or the _Test_Assignment_Uploads course."""
    return ("_Test_Assignment_Uploads" in name) or references_quarter(name, season, year)


def select_sheet_name(sheet_names, season, year):
    """Pick the sheet matching the current quarter.

    Returns the sheet name, or None if the user chose to abort.
    """
    matches = [n for n in sheet_names if references_quarter(n, season, year)]
    if len(matches) == 1:
        print(f"Using sheet: {matches[0]}")
        return matches[0]

    print("\nCould not determine the sheet for the current quarter.  Available sheets:")
    for i, name in enumerate(sheet_names, start=1):
        print(f"{i}. {name}")
    while True:
        choice = input("Enter the number of the sheet to use, or 'a' to abort: ").strip()
        if choice.lower() in ("a", "abort", "q", "quit"):
            print("Aborted.")
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(sheet_names):
            name = sheet_names[int(choice) - 1]
            print(f"Using sheet: {name}")
            return name
        print(f"Invalid choice: {choice!r}. Enter a number between 1 and {len(sheet_names)}, or 'a' to abort.")


parser = argparse.ArgumentParser(description="Upload assignments to Canvas from a schedule file.")
parser.add_argument("schedule_file", help="Path to schedule file (.ods or .xlsx)")
args = parser.parse_args()


# Load .env
load_dotenv()
canvas_api_url = os.getenv("API_URL")
canvas_api_token = os.getenv("API_KEY")

# Connect to Canvas
canvas = Canvas(canvas_api_url, canvas_api_token)
user = canvas.get_current_user()
print(f"Current User: {user.name} ({user.id})")

# Step 1: List available courses
enrollments = user.get_enrollments(enrollment_state=["active"], include=["course"])

quarter_season, quarter_year = current_quarter()
quarter_name = f"{quarter_season} {quarter_year % 100}"
print(f"Current quarter: {quarter_name} ({quarter_year}-{quarter_season})")

print(f"\nAll courses in {quarter_name} (plus _Test_Assignment_Uploads):")
for enrollment in enrollments:
    cid = enrollment.course_id

    try:
        course = canvas.get_course(cid)
        cname = course.name
    except Exception as e:
        cname = "unknown"

    if is_test_course(cname, quarter_season, quarter_year):
        print(f"{cid}: {cname}")

# Step 2: Prompt user to select course
course_id = int(input("\nInput Course ID: "))
course = canvas.get_course(course_id)
print(f"Selected course: {course.name}")

# Step 3: Schedule file path from command line
schedule_path = args.schedule_file

# Step 4: Load schedule file
if schedule_path.endswith(".ods"):
    xls = pd.ExcelFile(schedule_path, engine="odf")
    header_row = 0
else:
    xls = pd.ExcelFile(schedule_path, engine="openpyxl")
    header_row = 1

sheet_name = select_sheet_name(xls.sheet_names, quarter_season, quarter_year)
if sheet_name is None:
    sys.exit(1)
df = xls.parse(sheet_name, header=header_row)


# Function to extract assignment group name from column name.
# The assignment type marker (PS, Lab, Quiz, ...) may or may not be
# followed by extra information (e.g. weekdays) in parenthesis.
def parse_group_name(colname):
    for atype in ASSIGNMENT_TYPES:
        if re.match(rf"^{atype}\b", colname, re.IGNORECASE):
            return atype
    return None


def assignment_weekday_hint(sched_col, date_col):
    """Build a human hint of on which weekday(s) the type's assignments fall.

    Counts, over the non-empty assignment rows, how many dates land on each
    weekday.  Returns e.g. "Currently Monday" or
    "Currently Monday (5)/Wednesday (1)".  Count-less weekdays are dropped.
    """
    counts = {}
    order = []
    for _, row in df.iterrows():
        if pd.isna(row[sched_col]):
            continue
        try:
            d = pd.to_datetime(row[date_col])
        except (ValueError, TypeError):
            continue
        if pd.isna(d):
            continue
        name = d.strftime("%A")
        if name not in counts:
            counts[name] = 0
            order.append(name)
        counts[name] += 1
    if not order:
        return ""
    if len(order) == 1:
        return f"Currently {order[0]}"
    parts = [f"{name} ({counts[name]})" for name in order]
    return "Currently " + "/".join(parts)


# Show all columns found in schedule
print("\nColumns found in schedule:")
for col in df.columns:
    print(f"- '{col}'")

# Define default columns to skip
skip_columns = ["Class", "Weektitle", "Other"]
print("\nSkipping default columns:")
for skip in skip_columns:
    print(f"- '{skip}'")

# TODO: Ask user if they want to skip additional columns

# Step 5: Show existing assignment groups in selected course
print("\n Existing assignment groups in this course:")

groups = course.get_assignment_groups(include=["assignments"])
group_name_to_id = {}
for g in groups:
    group_name_to_id[g.name] = g.id
    assignments = g.assignments
    num_assignments = len(assignments) if assignments else 0
    print(f"- {g.name} (ID: {g.id}) → {num_assignments} assignments")

# Detect assignment groups from columns
group_columns = {}
for col in df.columns:
    col_clean = str(col).strip()
    group = parse_group_name(col_clean)
    if group and group not in skip_columns:
        group_columns[group] = col

# Show detected assignment groups
print("\nDetected assignment groups:")
for g in group_columns.keys():
    print(f"- {g}")

# Step 6: Prompt user to input settings for each assignment group
group_config = {}
for g, col in group_columns.items():
    hint = assignment_weekday_hint(col, "date")
    offset = int(input(
        f"Enter due date offset (days) for {g} "
        f"{'— ' + hint if hint else ''}: "
    ))
    points = int(input(f"Enter points possible for {g}: "))
    group_config[g] = {"offset": offset, "points": points}

# Step 7: Fetch or create assignment groups
group_name_mapping = {
    "Lab": "Labs",
    "Quiz": "Quizzes",
    "Project": "Final Project",
    "PS": "Assignments",
}

groups = course.get_assignment_groups()
group_name_to_id = {g.name: g.id for g in groups}

for g in group_columns.keys():
    canvas_group_name = group_name_mapping.get(g, g)
    if canvas_group_name not in group_name_to_id:
        ag = course.create_assignment_group(name=canvas_group_name)
        group_name_to_id[canvas_group_name] = ag.id
        print(f"Created assignment group: {canvas_group_name}")

pacific = pytz.timezone("America/Los_Angeles")

# Step 8: Upload assignments to Canvas
for g, col in group_columns.items():
    for i, row in df.iterrows():
        base_date = pd.to_datetime(row["date"])
        title = row[col]
        if pd.notna(title):
            due_date = base_date + timedelta(days=group_config[g]["offset"])

            # Combine date + time (all deadlines due at 23:59 local time)
            local_due = pacific.localize(
                datetime.combine(
                    due_date.date(),
                    datetime.strptime(DUE_TIME, "%H:%M").time(),
                )
            )

            # Convert to UTC
            utc_due = local_due.astimezone(pytz.utc)
            due_at_str = utc_due.strftime("%Y-%m-%dT%H:%M:%SZ")

            assignment = course.create_assignment(
                assignment={
                    "name": f"{g}: {title}",
                    "points_possible": group_config[g]["points"],
                    "due_at": due_at_str,
                    "assignment_group_id": group_name_to_id[
                        group_name_mapping.get(g, g)
                    ],
                    "submission_types": ["online_upload"],
                    "published": True,
                }
            )
            due_human = local_due.strftime("%Y-%m-%d %H:%M")
            print(f"Created {g}: {assignment.name} (due {due_human})")


print("\nAll assignments uploaded.")

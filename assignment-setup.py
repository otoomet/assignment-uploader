#!/usr/bin/env python

## * print results in Seattle time zone
## * Tell what are the current assignment dates

import argparse
import pandas as pd
import os
from datetime import datetime, timedelta
import re
import sys
import pytz

from canvas_common import (
    fail,
    connect,
    print_current_quarter,
    references_quarter,
    select_course,
)

ASSIGNMENT_TYPES = ("PS", "Lab", "Quiz", "Project")
DUE_TIME = "23:59"


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
parser.add_argument(
    "-i", "--id",
    dest="course_id",
    type=int,
    metavar="ID",
    help="Canvas course ID to upload into (skips the course-selection prompt).",
)
args = parser.parse_args()


# Fail fast if the schedule file does not exist.
if not os.path.isfile(args.schedule_file):
    fail(
        f"schedule file not found: {args.schedule_file}\n"
        f"       Please pass a valid .ods or .xlsx file as the command-line argument."
    )


# Connect to Canvas (validates .env)
canvas, user = connect()

quarter_season, quarter_year = print_current_quarter()

# Step 1-2: Determine the course (prompts unless -i/--id was given)
course = select_course(canvas, user, quarter_season, quarter_year, args.course_id)


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


# Placeholder cells that mean "there is no assignment this week", e.g.
# "No lab" or "No quiz".  These should not be uploaded.  Matching is
# case-insensitive and word boundary aware, so real titles like
# "PS4: data manipulations (no groups)" are left alone.
NO_ASSIGNMENT_RE = re.compile(
    r"\bno\s+(ps|problem\s+sets?|labs?|quiz(zes)?|tests?|exams?)\b",
    re.IGNORECASE,
)


def is_no_assignment(title):
    """True if a schedule cell is a 'no <assignment>' placeholder to skip."""
    return bool(NO_ASSIGNMENT_RE.search(str(title)))


def assignment_weekday_hint(sched_col, date_col):
    """Build a human hint of on which weekday(s) the type's assignments fall.

    Counts, over the non-empty non-placeholder assignment rows, how many
    dates land on each weekday.  "No lab"/"no quiz" style placeholder rows
    are excluded.  Returns e.g. "Currently Monday" or
    "Currently Monday (5)/Wednesday (1)".  Count-less weekdays are dropped.
    """
    counts = {}
    order = []
    for _, row in df.iterrows():
        if pd.isna(row[sched_col]) or is_no_assignment(row[sched_col]):
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
        title = row[col]
        # Skip empty cells and "no lab"/"no quiz" style placeholders.
        if pd.isna(title) or is_no_assignment(title):
            continue
        base_date = pd.to_datetime(row["date"])
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

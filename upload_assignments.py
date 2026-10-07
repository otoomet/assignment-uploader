#!/usr/bin/env python

## * if schedule file cannot be found
## * print results in Seattle time zone
## * Tell what are the current assignment dates
## * suggest 23:59 by default

import argparse
import pandas as pd
from canvasapi import Canvas
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import pytz


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

target_term_name = "Au 26"

print("\n All courses in:".format(target_term_name))
for enrollment in enrollments:
    cid = enrollment.course_id

    try:
        course = canvas.get_course(cid)
        cname = course.name
    except Exception as e:
        cname = "unknown"

    if target_term_name in cname:
        print(f"{cid}: {cname}")

# Step 2: Prompt user to select course
course_id = int(input("\nInput Course ID: "))
course = canvas.get_course(course_id)
print(f"Selected course: {course.name}")

# Step 3: Schedule file path from command line
schedule_path = args.schedule_file

# Step 4: Load schedule file
if schedule_path.endswith(".ods"):
    sheets = pd.read_excel(schedule_path, sheet_name=None, engine="odf")
    last_sheet_name = list(sheets.keys())[-1]
    print(f"Using last sheet: {last_sheet_name}")
    df = sheets[last_sheet_name]
else:
    df = pd.read_excel(schedule_path, header=1)


# Function to extract assignment group name from column name
def parse_group_name(colname):
    m = re.match(r"(.*) \(", colname)
    if m:
        return m.group(1).strip()
    return None


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
    col_clean = col.strip()
    group = parse_group_name(col_clean)
    if group and group not in skip_columns:
        group_columns[group] = col

# Show detected assignment groups
print("\nDetected assignment groups:")
for g in group_columns.keys():
    print(f"- {g}")

# Step 6: Prompt user to input settings for each assignment group
group_config = {}
for g in group_columns.keys():
    offset = int(input(f"Enter due date offset (days) for {g}: "))
    points = int(input(f"Enter points possible for {g}: "))
    due_time_str = input(f"Enter due time (HH:MM, 24-hour) for {g}: ")
    group_config[g] = {"offset": offset, "points": points, "due_time": due_time_str}

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

            # Combine date + time
            local_due = pacific.localize(
                datetime.combine(
                    due_date.date(),
                    datetime.strptime(group_config[g]["due_time"], "%H:%M").time(),
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
            print(f"Created {g}: {assignment.name} (due {due_at_str})")


print("\nAll assignments uploaded.")

# Canvas Assignment Uploader

A command-line tool that uploads course assignments to Canvas.

It reads a course schedule spreadsheet (`.ods` or `.xlsx`) that contains a
sheet for the current quarter, finds the date column plus the problem-set
(`PS ...`), lab (`Lab ...`) and quiz (`Quiz ...`) columns, and creates the
corresponding assignments in a Canvas course — one group per assignment
type, with customizable due-date offsets and point values.

## Installation

1. Install the required Python packages:

   ```bash
   pip install -r installation-requirements.txt
   ```

2. Create a `.env` file in the project directory with your Canvas
   credentials.  It can be started from the `.env-template` file:

   ```env
   API_URL=https://canvas.yourschool.edu/api/v1
   API_KEY=your_canvas_api_key
   ```

   You can obtain an API key from Canvas: *Account → Settings →
   New Access Token*.

## Usage

Run the script with the schedule file as the command-line argument:

```bash
python upload_assignments.py path/to/schedule.ods
```
or just
```bash
./upload_assignments.py path/to/schedule.ods
```
Both `.ods` and `.xlsx` files are supported.

Then follow the prompts:

- The current quarter is detected automatically (quarters begin August 1,
  November 1, February 1, and May 1).
- It pull the list list of your courses from the canvas, filters the
  courses for the current quarter only
  (plus the `_Test_Assignment_Uploads` course).  Note: this is slow.
  
  Choose the course by entering its course ID.
- The sheet matching the current quarter is detected automatically
  (fuzzy match, e.g. "Au 26", "26 au", "2026-Au").  If it cannot be
  determined, all sheet names are listed and you can pick one.
- For each assignment type, enter the due-date offset in days and the
  points possible.  The deadline is always set to 23:59 on (schedule date
  + offset).  When asking for the offset, the prompt shows the weekday the
  type's assignments currently fall on, e.g. "Currently Monday" or
  "Currently Monday (5)/Wednesday (1)" if they are entered on
  different weekdays.

Assignments are uploaded to the existing Canvas assignment groups —
"Assignments" for problem sets, "Quizzes" for quizzes and "Labs" for labs
(created if missing).
They are marked as "online upload" submissions and "published".

### Schedule file format

The file must contain a sheet for the current quarter, e.g. "Au 2026"
or "26-au" (fuzzy-matched by
name).  Within that sheet:

- a `date` column with the schedule dates;
- problem-set, lab and quiz columns whose names start with the assignment
  type marker `PS`, `Lab` or `Quiz`;
- the markers may optionally be followed by extra information in
  parentheses (e.g. weekdays), which is ignored.  All of `PS`,
  `PS (Mon night)`, `Quiz` and `Lab (Tue, Wed)` are valid column names.

Entries in those columns are used as the assignment titles.

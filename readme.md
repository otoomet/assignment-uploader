# Canvas Assignment Uploader

A command-line tool that uploads course assignments to Canvas automatically.

It reads a course schedule spreadsheet (`.ods` or `.xlsx`) that contains a
sheet for the current quarter, finds the date column plus the problem set
(`PS ...`) and lab (`Lab ...`) columns, and creates the corresponding
assignments in a Canvas course — one group per assignment type, with
customizable due-date offsets and point values.

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

Both `.ods` and `.xlsx` files are supported.

Then follow the prompts:

- The current quarter is detected automatically (quarters begin August 1,
  November 1, February 1, and May 1).
- Choose a course from the listed courses of the current quarter
  (plus the `_Test_Assignment_Uploads` course) by entering its course ID.
- The sheet matching the current quarter is detected automatically
  (fuzzy match, e.g. "Au 26", "26 au", "2026-Au").  If it cannot be
  determined, all sheet names are listed and you can pick one or abort.
- For each assignment type, enter the due-date offset in days (the
  deadline is set to 23:59 on schedule date + offset) and the points
  possible.

Assignments are uploaded to the existing Canvas assignment groups —
"Assignments" for problem sets and "Labs" for labs (created if missing) —
marked as online upload submissions and published.

### Schedule file format

The file must contain a sheet for the current quarter (fuzzy-matched by
name).  Within that sheet:

- a `date` column with the schedule dates;
- a problem-set column named like `PS (extra info)`;
- a lab column named like `Lab (extra info)`.

Everything in the parentheses (e.g. the day of the week) is optional;
entries in those columns are used as the assignment titles.

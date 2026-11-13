# Canvas course tools

Command-line tools for managing course materials on Canvas through the
Canvas API.

- [`assignment-setup.py`](#assignment-setuppy): create the quarter's
  assignments in bulk from a course schedule spreadsheet.
- [`canvas-upload.py`](#canvas-uploadpy): upload individual files, e.g.
  PDFs and data files, to the course Files.

Code shared by the tools is in `canvas_common.py`.

## Installation

1. Install the required Python packages:

   ```bash
   pip install -r installation-requirements.txt
   ```

2. Create a `.env` file in the project directory with your Canvas
   credentials.  It can be started from the `.env-template` file:

   ```bash
   cp .env-template .env
   ```

   and then edit it to set both values:

   ```env
   API_URL=https://canvas.yourschool.edu/api/v1
   API_KEY=your_canvas_api_key
   ```

   You can obtain an API key from Canvas: *Account → Settings →
   New Access Token*.

   The `.env` file must be readable only by you (mode 600); the tools
   refuse to run otherwise:

   ```bash
   chmod 600 .env
   ```

   This check is done on Linux and macOS only; on Windows it is skipped.
   Under WSL keep the `.env` file on the Linux file system (e.g. in your
   home directory), not under `/mnt/c`, where `chmod` has no effect.

On Windows, run the tools as `python assignment-setup.py ...` (or
`python canvas-upload.py ...`).  Windows
support is best-effort and untested.

## assignment-setup.py

Reads a course schedule spreadsheet (`.ods` or `.xlsx`) that contains a
sheet for the current quarter, finds the date column plus the problem-set
(`PS ...`), lab (`Lab ...`) and quiz (`Quiz ...`) columns, and creates the
corresponding assignments in a Canvas course — one group per assignment
type, with customizable due-date offsets and point values.

### Usage

Run the script with the schedule file as the command-line argument:

```bash
python assignment-setup.py path/to/schedule.ods
```
or just
```bash
./assignment-setup.py path/to/schedule.ods
```
Both `.ods` and `.xlsx` files are supported.

Optionally pass the Canvas course ID with `-i`/`--id` to skip the
course-selection prompt:

```bash
python assignment-setup.py path/to/schedule.ods --id 12345
```

Then follow the prompts:

- The current quarter is detected automatically (quarters begin August 1,
  November 1, February 1, and May 1).
- It pull the list list of your courses from the canvas, filters the
  courses for the current quarter only
  (plus the `_Test_Assignment_Uploads` course).  Note: this is slow.

  Choose the course by entering its course ID.  If you passed `-i`/`--id`
  on the command line, this step (and the listing) is skipped and that
  course is used directly.
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

#### Schedule file format

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

Placeholder cells that mean "there is no assignment this week" — e.g.
`No lab`, `No quiz`, `No PS`, `No test`, `No exam` (matched case-insensitively)
— are detected and skipped; they are not uploaded and are not counted when
detecting the weekdays the type's assignments fall on.  Real titles such as
`PS4: data manipulations (no groups)` are unaffected.


## canvas-upload.py

Uploads one or more files (PDFs, data files, documents, ...) to a folder
in the _Files_ section of a Canvas course.

### Usage

```bash
python canvas-upload.py --folder data data1.csv.gz data2.csv.gz
```

- `-f`/`--folder` is required.  It is the destination folder in the course
  Files, e.g. `data` or a nested `data/lab3`.  A folder that does not exist
  is created (the script tells you).
- `-i`/`--id` gives the Canvas course ID and skips the course-selection
  prompt, just as in `assignment-setup.py`.
- A file with the same name in the same folder is **overwritten**, which is
  handy for fixing typos.  For each file the script prints whether it was
  created or overwritten, and its Canvas URL.  Overwriting keeps the file's
  hidden/locked setting.
- All files are checked before anything is uploaded; if one does not exist,
  nothing is uploaded.  If an upload fails, the remaining files are still
  uploaded and the script exits with a non-zero status.

Linking the uploaded files from assignment pages or the schedule is not
implemented yet.

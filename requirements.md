# Canvas course tools: requirements

A small set of command-line tools for managing course materials on Canvas
through the Canvas API.

| Tool               | Purpose                                                        | Status        |
|--------------------|----------------------------------------------------------------|---------------|
| `assignment-setup.py` | Bulk-create the quarter's assignments from a schedule sheet | implemented   |
| `canvas-upload.py`    | Upload individual files to the course Files                 | implemented (linking planned) |

Code common to the tools lives in `canvas_common.py` (see
[Shared requirements](#shared-requirements)).  The tools are written in
Python and are meant to run on Linux and macOS.  Windows is supported on a
best-effort basis (see [Platform notes](#platform-notes)).


## Shared requirements

These apply to every tool and are implemented in `canvas_common.py`.

### Credentials

1. The API url and the API key are read from a file `.env` (in the
   current directory).  It should contain `API_URL` and `API_KEY`.
   See the `.env-template`.
2. On POSIX systems this file should only be readable by the user, not by
   the world (mode 600).

   If `.env` does not exist, does not contain the url and API key, or
   has wrong mode, the tool should produce a corresponding error message
   and exit with a non-zero status.
3. On Windows the permission check is skipped.

### Quarter names

1. The tools should calculate the current quarter name.  The name can be in the
   form "yyyy-ss" where _ss_ is season: either "Au" for autumn, "Wi" for
   winter, "Sp" for spring and "Su" for summer; in the form "ss yy";
   or in the form "yy ss".

   Assume the quarters begin: Autumn on August 1st, Winter on Nov 1st,
   Spring on Feb 1st, and summer on May 1st.  All years (two digits)
   should correspond to the current year, except the last two months
   of the year where they should correspond to the next year.  For
   instance, 2026-10-07 will correspond to either "2026-Au", "26 Au"
   or "Au 26".  2026-11-11 will correspond to "2027-Wi", "27 Wi" or
   "Wi 27".

   The tool should print the current quarter with an appropriate
   sentence.

2. In all operations with quarter names, the season case does not
   matter.

### Course selection

1. Tools that work on a single course should accept the course id on the
   command line as `-i/--id`.  (The course id is an integer and does not
   contain spaces or special characters.)
2. If the course id was not provided on the command line, the tool
   should:

   - get the list of all the user's active courses, and extract the
     courses that correspond to the current quarter.  The course names
     look like "Course code letter Ss yy: course name", where _Ss yy_ is
     the quarter.  For instance, a course name may be
     "INFO 370 C Au 26: Core Methods In Data Science".  Note that canvas
     API assumes the quarter is given as "Ss yy".

   - Besides the courses that correspond to the current quarter, it
     should also print a course named "_Test_Assignment_Uploads" (the
     name includes underscores).

   - ask the user for the course id.


## `assignment-setup.py`: bulk assignment setup

It uses a course schedule sheet, and creates the corresponding
assignments on canvas.

### Command-line options

1. The tool takes the course schedule file as its command line
   argument.  It is assumed that it is either an .ods or
   .xlsx file.  If the file does not exist, the tool should say so and exit.
2. `-i/--id`: the course id (see [Course selection](#course-selection)).

### Schedule handling

1. It should extract the sheet that corresponds to the current
   quarter.

   The sheet name should use fuzzy matching, e.g. "Au 2026", "2026
   au", "26-au" and such are all valid names.
2. If the tool cannot guess the correct name, it should list all
   sheet names and ask the user to pick one (or to abort).
3. From this sheet it should extract dates (column "date"), and
   three types of assignments:
   problem sets (column "PS"), labs (column "Lab") and quizzes
   (column "Quiz").

   The assignment type markers ("PS", "Quiz" and "Lab") may be followed other
   information (e.g. weekdays) in parenthesis.
4. The entries from these columns should be uploaded to canvas.
   Placeholder cells that mean "there is no assignment this week"
   (e.g. "No lab", "No quiz", "No PS") should be detected and skipped,
   not uploaded.

### Assignment settings

1. The tool should ask for an offset for each type of
   assignment--how many days after the given date its deadline
   should be on canvas.

   When asking the offset, it should show the current weekday of
   that assignment
   (the one based on the "date" column)
   type with an appropriate message.

   If the assignments are marked on different weekdays, it should
   show both, for instance "Currently Monday (5)/Wednesday (1)"
   meaning it was marked for Monday 5 times and for Wednesday once.
2. It should also ask for how many points each assignment type will
   give.
3. The different types of assignments should be uploaded into
   separate canvas groups, problem sets as "Assignments", quizzes as
   "Quizzes" and labs as
   "Labs".
4. All uploaded assignments' due time should be 23:59 in the given
   date.
5. All uploaded assignments should be "published" on canvas.
6. All uploaded assignments should be marked as "online upload".


## `canvas-upload.py`: upload files to the course Files

Uploads individual files (PDFs, data files, documents, ...) to the course
_Files_ section on Canvas.  Linking the uploaded files from assignment
pages or the schedule is planned for a later version (see
[Planned](#planned)).

It reuses the shared requirements above (credentials, quarter, course
selection, `-i/--id`).

### Behavior

1. The script uploads one or multiple files, given as command line
   arguments.
2. The destination folder (in the course _Files_ section) is given with
   `-f/--folder`, e.g. `--folder data` or a nested `--folder data/lab3`.
3. If `--folder` is not given, the script stops with an error message that
   asks for it.  (Guessing the folder from the file type is planned, see
   below; until then the folder is always required.)
4. If the folder does not exist, it is created, and the script says so.
5. Re-uploading a file overwrites the existing file with the same name in
   the same folder (upload with `on_duplicate=overwrite`).  This is
   intended for fixing typos.  For each file the script reports whether it
   was created or overwritten; to know which, it looks at the files in the
   destination folder before uploading.

   Observed Canvas behavior (checked on the test course):
   - an overwrite gives the file a **new file id**, but the old id still
     resolves to the replacement through the API, and the folder contains
     only one copy;
   - the file's hidden/locked state is **kept** by the overwrite;
   - the `hidden`/`locked` parameters of an upload are ignored (visibility
     can only be changed afterwards with a separate file update), so the
     script does not touch visibility.

   Not verified: that an old browser link to the file keeps working for
   students.
6. All given files are checked for existence before anything is uploaded.
   If one is missing, the script stops with an error and uploads nothing.
7. If an upload fails, the script continues with the remaining files,
   prints a summary at the end, and exits with a non-zero status.
8. For each uploaded file, the script prints its Canvas URL in the form
   `https://<host>/courses/<course id>/files/<file id>`, built from the host
   in `API_URL` (with or without a trailing slash or `/api/v1`).  It does
   not print the API's download URL, which contains a per-file access token.

### Planned

These are not part of the first version.

1. **Guessing the folder.**  Choose the default folder from the type of
   file.  Extension alone is not enough: PDFs are used for slides, problem
   sets, labs and readings, while data are mostly (compressed) `.csv`.
   How to guess (extension, file name conventions, a configuration file)
   is to be discussed.
2. **Linking** the uploaded file from the page of an assignment, and
   linking the slides from the schedule.  Assignment pages, the syllabus
   and wiki pages are all an HTML body, so the linking part should be
   separate from uploading: uploading returns the Canvas file, linking
   takes a file and a target page.


## Platform notes

1. The tools are developed on Linux.  macOS should work the same way.
2. Windows is best-effort and untested.  Run the tools as
   `python assignment-setup.py ...`; the `.py` extension is needed there.
   The `.env` permission check is skipped (see [Credentials](#credentials)).
3. Under WSL, keep `.env` on the Linux file system (e.g. in the home
   directory).  Files on `/mnt/c` normally appear with mode 777 and cannot
   be changed with `chmod`, so the permission check would refuse to run.


## Code organization

1. `canvas_common.py` contains the code shared between the tools:
   error reporting, `.env` loading and validation, the Canvas
   connection, quarter-name handling and course selection.
2. Each tool is a separate script.  Script names may contain hyphens, but
   modules that are imported must not, hence `canvas_common.py`.

### Questions:

* What is a good way to specify course-specific canvas course id?  I
  propose to have a file `course-id.txt` in `pages/` folder in the
  each course project, but I am not sure if it is the best way.


## Readme file

Readme should be the basic installation/usage help.

1. It should contain a few sentences explaining what the tools do.
2. It should have "Installation" section that explains how to install
   them and set up the `.env` file.
3. It should have a "Usage" section for each tool that explains how to use
   it, both command line and, where relevant, the input file format.

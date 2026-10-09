# A script to upload course materials to canvas

It uses a course schedule sheet, and uploads the assignments there on canvas.

## Requirements

### Command-line options

1. The script should take the course schedule file as its command line
   argument.  It is assumed that it is either an .ods or
   .xlsx file.
2. There should also be an option to enter the course id on command
   line, e.g. `-i/--id`.  (The course id is an integer and does not
   contain spaces or special characters.)
 
 
### Other requirements

1. It should read the API url and the API key from a file `.env`.
    This file should only be readable by the user, not by the world
    (mode 600).
    
    if `.env` does not exist, does not contain the url and API key, or
    has wrong mode, then
    it should produce a corresponding error message.
2. It should calculate the current quarter name.  The name can be in the
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
   
   The script should print the current quarter with an appropriate
   sentence. 
   
   In all operations with quarter names, the season case does not
   matter. 
 3. If the course id was not provided on the command line,
   then the script should:
   
   - get the list of all courses, and extract the
     courses that correspond to the current quarter.  The course names
     look like "Course code letter Ss yy: course name", where _Ss yy_ is
     the quarter.  For instance, a course name may be
     "INFO 370 C Au 26: Core Methods In Data Science".
   
   - Besides the courses that correspond to the current quarter, it
     should also print a course names "_Test_Assignment_Uploads" (the
     name includes underscores).
4. It should load all the courses for the current quarter, and the
   user for the course id.  Note that canvas API assumes the quarter
   is given as "Ss yy".
5. it should extract the sheet that corresponds to the current
   quarter.
   
   The sheet name should use fuzzy matching, e.g. "Au 2026", "2026
   au", "26-au" and such are all valid names.
6. If the script cannot guess the correct name, it should list all
   sheet names and ask the user to pick one (or to abort).
7. From this sheet it should extract dates (column "date"), and
   three types of assignments:
   problem sets (column "PS"), labs (column "Lab") and quizzes
   (column "Quiz").
   
   The assignment type markers ("PS", "Quiz" and "Lab") may be followed other
   information (e.g. weekdays) in parenthesis.
 8. the entries from these columns should be uploaded to canvas.
   Placeholder cells that mean "there is no assignment this week"
   (e.g. "No lab", "No quiz", "No PS") should be detected and skipped,
   not uploaded.
 9. the script should ask for an offset for each type of
    assignment--how many days after the given date its deadline
    should be on canvas.
    
    When asking the offset, it should show the current weekday (the
    one based on the "date" column) of
    that assignment type with an appropriate message.
    
    If the assignments are marked on different weekdays, it should
    show both, for instance "Currently Monday (5)/Wednesday (1)"
    meaning it was marked for Monday 5 times and for Wednesday once.
 10. It should also ask for how many points each assignment type will
     give.
 11. the different types of assignments should be uploaded into
     separate canvas groups, problem sets as "Assignments", quizzes as
     "Quizzes" and labs as
     "Labs".
 12. All uploaded assignments' due time should be 23:59 in the given
     date.
 13. all uploaded assignments should be "published" on canvas.
 14. All uploaded assignments should be marked as "online upload".


## Readme file

Readme should be the basic installation/usage help.

1. It should contain a few sentences explaining what the script does.
2. It should have "Installation" section that explains how to install
   it and set up the `.env` file.
3. It should have "Usage" section that explains how to use it, both
   command line and the schedule fire format.

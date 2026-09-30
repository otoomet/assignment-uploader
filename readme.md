# Canvas Assignment Uploader

This is a command-line tool to help upload assignments to Canvas automatically.

It takes an `.ods` or `.xlsx` file and creates assignments in the selected Canvas course.

## How to use

1. Install required Python packages:

```bash
pip install -r requirements.txt
```

2. Look at `.env-template`.  Rename it to `.env` and replace the
  template values with your actual Canvas API URL and API Key.  It should
  look something along the lines

```env
API_URL=https://canvas.yourschool.edu/api/v1
API_KEY=your_canvas_api_key
```

You can request an API key from canvas -> Account -> setting -> New Access Token

1. Edit the script to enter the correct quarter
2. Run the script:

```bash
python upload_assignments.py
```

3. Follow the prompts:

- Select the course
- Enter path to schedule file (ODS or XLSX)
- Configure assignment groups (due date offset, points, due time)
- Upload assignments

## Schedule file format

The schedule file should contain columns like, week, date, Lab (Tue, Wed evening), PS (Sunday night)...

The tool will detect columns with names like `Lab (xxx)` or `PS (xxx)` and treat them as assignment groups.

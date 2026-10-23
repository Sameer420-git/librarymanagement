# College Library Management System

## Run the backend on Windows

Open **PowerShell** and run these commands:

```powershell
cd "C:\Users\ACER\Downloads\library-management\backend"
```

If the virtual environment has not been created yet:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

Apply the database migrations:

```powershell
python -m alembic upgrade head
```

Add the demo data and demo login accounts:

```powershell
python -m scripts.seed_demo_data
```

If the database already contains users and you intentionally want to replace
the existing data with the demo data, use:

```powershell
python -m scripts.seed_demo_data --reset
```

Start the backend API:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend will be available at:

- API: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Keep this PowerShell window open while using the application.

## Demo login accounts

These accounts are created by the demo-data command above and are intended for
local development or demonstration only:

| Role | E-mail | Password |
| --- | --- | --- |
| Super admin | `admin@college.edu` | `Demo@12345` |
| Librarian | `librarian@college.edu` | `Demo@12345` |
| Faculty | `faculty@college.edu` | `Demo@12345` |
| Student | `student1@college.edu` | `Student@123` |
| Student | `student2@college.edu` | `Student@123` |
| Student | `student3@college.edu` | `Student@123` |

The seeded demo data gives `student1`, `student2`, and `student3` an overdue
returned book with an outstanding fine. The librarian can see and record those
payments from the **Fines** panel. Each student can see and pay their own fine
from the **My fines** panel.

Do not use these credentials in a production deployment.

## Run the frontend on Windows

Open a **second PowerShell window** and run these commands:

```powershell
cd "C:\Users\ACER\Downloads\library-management\frontend"
```

Install the frontend dependencies:

```powershell
npm install
```

Start the frontend development server:

```powershell
npm run dev
```

Open the frontend at <http://localhost:5173>.

The backend must be running in the first PowerShell window before using the frontend.

## Useful frontend commands

Build the frontend for production:

```powershell
npm run build
```

Run the frontend linter:

```powershell
npm run lint
```

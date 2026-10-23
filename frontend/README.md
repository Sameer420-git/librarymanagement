# Library Management Frontend

## Run on Windows

Open **PowerShell** and run:

```powershell
cd "C:\Users\ACER\Downloads\library-management\frontend"
npm install
npm run dev
```

Open <http://localhost:5173> in a browser.

The backend API must be running separately at
<http://localhost:8000>. See the project-level
[README](../README.md) for the backend commands.

## Demo login accounts

After the backend demo data has been seeded, use one of these local/demo
accounts to sign in:

| Role | E-mail | Password |
| --- | --- | --- |
| Super admin | `admin@college.edu` | `Demo@12345` |
| Librarian | `librarian@college.edu` | `Demo@12345` |
| Faculty | `faculty@college.edu` | `Demo@12345` |
| Student | `student1@college.edu` | `Student@123` |
| Student | `student2@college.edu` | `Student@123` |
| Student | `student3@college.edu` | `Student@123` |

The demo seed creates an outstanding overdue fine for each of these three
students. Librarians can view and record payments in **Fines**; students can
view and pay their own balance in **My fines**.

These credentials are for local demonstration only. Do not use them in
production.

## Available commands

Build the application:

```powershell
npm run build
```

Run the linter:

```powershell
npm run lint
```

Preview a production build:

```powershell
npm run preview
```

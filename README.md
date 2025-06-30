# 💳 Visa Settlement Report Processor

A full-stack application for processing and analyzing Visa settlement reports. 
Built using **FastAPI** (Python backend), **React** (frontend), and **PostgreSQL/SQLite** (optional SQL database integration). 

The system parses `.txt` Visa reports into structured Excel files and optionally stores results in a relational database for advanced analysis.

---

## 🚀 Features

- ✅ Upload Visa `.txt` files and convert to Excel
- ✅ Parses Interchange, Reimbursement Fees, Visa Charges, Settlement data
- ✅ Handles multiple reports in one file
- ✅ Adds credit/debit label (`CR/DB`) and cleans numeric formats
- ✅ Supports merging data into an existing Excel file
- ✅ Optional database storage for all rows via SQLAlchemy
- ✅ React UI with tabbed workflows

---

## 📦 Tech Stack

| Frontend       | Backend       | Database       |
|----------------|---------------|----------------|
| React + Axios  | FastAPI       | SQLite/PostgreSQL (via SQLAlchemy) |

---

## 📁 Folder Structure
<img width="295" alt="image" src="https://github.com/user-attachments/assets/380fdea7-e883-4c02-bf74-10846d017311" />

---

## ⚙️ Setup Instructions

Here is the basic setup for the frontend and backend

1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload


2. Frontend (React):
```cd frontend
npm install
npm run dev




### Built by Zuhayr Kabir during a Software Internship @ Bank Asia ###











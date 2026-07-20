# OpsPilot FastAPI backend

## Requirements
- Python 3.10+

## Install
```bash
cd ops-pilot-backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

## Environment
Create a `.env` file in the backend folder, or place it in the repository root if you prefer a single shared file.

A starter template is available at `.env.example` in the backend folder.

## Run (dev)
```bash
cd ops-pilot-backend
uvicorn app.main:app --host 0.0.0.0 --port %PORT%
```

## Test endpoints
- `GET /`
- `GET /health`

## Notes
No PDF/ingestion logic is included yet.


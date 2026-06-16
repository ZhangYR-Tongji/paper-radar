# Backend

FastAPI backend for Paper Radar.

## Run locally

```powershell
conda activate paper-radar
cd backend
python -m app.cli
uvicorn app.main:app --reload --port 8000
```

Health check:

```powershell
curl http://localhost:8000/api/health
```

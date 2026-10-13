"""
Standalone FastAPI server launcher.
=====================================
Runs the FastAPI app on port 8001 alongside the Django server (port 8000).

Usage:
    python run_fastapi.py

Or via uvicorn directly:
    uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8001 --reload

Endpoints will be available at:
  - API:    http://localhost:8001/
  - Docs:   http://localhost:8001/docs
  - ReDoc:  http://localhost:8001/redoc
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )

"""
Simple launcher for the Stock Assistant app.

Usage:
    python3 run.py

Then open http://localhost:8000
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Stock Assistant running at  http://localhost:{port}\n")
    uvicorn.run("stock_assistant_api:app", host="0.0.0.0", port=port, reload=True)

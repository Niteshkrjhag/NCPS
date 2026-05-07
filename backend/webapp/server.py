"""
Webapp Server Entry Point.

Run: python -m webapp.server
"""

from webapp import app
import uvicorn

if __name__ == "__main__":
    print("\n  NCPS Webapp — http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)

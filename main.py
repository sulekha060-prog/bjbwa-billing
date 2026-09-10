import os
import sys

# Ensure root and backend directories are in Python module search path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
for d in (ROOT_DIR, BACKEND_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

from backend.app import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

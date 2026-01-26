"""Package entrypoint so ``python -m ui.backend`` runs the FastAPI server."""

import uvicorn
from .api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

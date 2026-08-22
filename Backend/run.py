"""Production entry point for T2DM Flask application."""

import os
import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from descend import create_app

if __name__ == "__main__":
    app = create_app()
    debug_enabled = os.getenv("FLASK_DEBUG", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }
    port = int(os.getenv("FLASK_PORT", "5000"))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    
    print(f"[*] T2DM API Server starting on {host}:{port}")
    print(f"    Debug mode: {debug_enabled}")
    print(f"    Model path: {app.config['MODEL_PATH']}")
    
    app.run(host=host, port=port, debug=debug_enabled)

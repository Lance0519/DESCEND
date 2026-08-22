import os
import sys

# Ensure backend package is importable when running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app

app = create_app()
app.testing = True

with app.test_client() as client:
    resp = client.post("/api/auth/register", json={
        "name": "Debug User",
        "email": "debuguser@example.com",
        "password": "SecurePass123!abc",
    })
    print("Status:", resp.status_code)
    print(resp.get_data(as_text=True))

from fastapi.testclient import TestClient
from ..main import app

client = TestClient(app)

def test_root():
    response = client.get("/", allow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/tweets"
import pytest
from fastapi.testclient import TestClient


class Test_Home:

    def test_read_home(self, client: TestClient):
        response = client.get("/api/v1")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}

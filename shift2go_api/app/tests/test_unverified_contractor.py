import pytest
import typing as t
from app.db import models
from fastapi.testclient import TestClient


class Test_UnverifiedContractors:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_unverified_contractors_crud(
        self,
        client: TestClient,
        superuser_token_headers: dict,
        test_unverified_contractor: models.Contractors
    ):

        # read unverified contractors
        response = client.get('/api/v1/unverified_contractors',
                              headers=superuser_token_headers)
        assert response.status_code == 200
        assert response.json() is not None

        # read single unverified contractors
        response = client.get(f'/api/v1/unverified_contractor/{test_unverified_contractor.id}',
                              headers=superuser_token_headers)
        assert response.status_code == 200
        assert response.json() is not None
        self.check_fields(response.json(), [
                          'id', 'userID', 'profilePicture', 'rating'])

        # update single unverified contractors
        update_response = client.patch(f'/api/v1/unverified_contractor/update?contractor_id={test_unverified_contractor.id}', headers=superuser_token_headers, json={
            "profilePicture": "www.reddit.com"
        })
        assert update_response.status_code == 201
        assert update_response.json() is not None
        assert update_response.json().get('profilePicture') == "www.reddit.com"

        # delete single unverified contractors
        delete_response = client.delete(
            f'/api/v1/unverified_contractor/delete/{test_unverified_contractor.id}', headers=superuser_token_headers)
        assert delete_response.status_code == 200
        assert delete_response.json() is not None
        assert delete_response.json().get('status') == "success"

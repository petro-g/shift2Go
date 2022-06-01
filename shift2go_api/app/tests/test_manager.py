import pytest
import typing as t
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.config import auth
from app.db import crud
from app.db.crud import delete_manager


class Test_Manager:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_manager_crud(
        self,
        client: TestClient,
        superuser_token_headers: dict,
        test_db: Session
    ):
        # add manager
        mock_payload = {
            "email": "testing@shift2go.com",
            "password": "password",
            "firstname": "Jane",
            "lastname": "Doe",
            "address": "Virginia",
            "phone": "123456789",
            "profilePicture": "www.google.com"
        }
        response = client.post('/api/v1/manager/signup', json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        assert response.json().get('access_token')
        manager_id = response.json().get('manager').get('id')
        manager_user_id = response.json().get('manager').get('userID')

        # read managers
        read_response = client.get(
            '/api/v1/managers', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        token = auth.generate_login_token(
            crud.get_user_by_id(test_db, manager_user_id))
        manager_token = {
            'Authorization': f'Bearer {token}'
        }

        # verify manager
        crud.verify_user_manually(test_db, manager_user_id)

        # read manager profile
        read_profile_response = client.get(
            '/api/v1/manager/me', headers=manager_token)
        assert read_profile_response.status_code == 200
        assert read_profile_response.json() is not None
        self.check_fields(read_profile_response.json(), [
                          'id', 'userID', 'profilePicture', 'rating', 'createdAt', 'updatedAt'])

        # delete manager profile
        delete_manager_profile_response = client.delete(
            f'/api/v1/manager/delete/{manager_id}', headers=superuser_token_headers)
        assert delete_manager_profile_response.status_code == 200
        assert delete_manager_profile_response.json() is not None
        assert delete_manager_profile_response.json().get('status') == 'success'

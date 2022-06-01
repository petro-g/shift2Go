import pytest
import typing as t
from fastapi.testclient import TestClient


class Test_JobRoles:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_roles_crud(
        self,
        client: TestClient,
        superuser_token_headers: dict
    ):
        # add role
        response = client.post('/api/v1/job_role/create', headers=superuser_token_headers, json={
            'name': 'Front Desk',
            'image': 'www.google.com'
        })
        assert response.status_code == 201
        assert response.json() is not None
        assert response.json().get('name') == 'Front Desk'
        assert response.json().get('image') == 'www.google.com'
        self.check_fields(response.json(), [
                          'id', 'name', 'image', 'createdAt', 'updatedAt', 'createdBy'])
        role_id = response.json().get('id')

        # read roles
        read_response = client.get(
            '/api/v1/job_roles', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read single role
        read_response = client.get(
            f'/api/v1/job_role/{role_id}', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        self.check_fields(response.json(), [
                          'id', 'name', 'image', 'createdAt', 'updatedAt', 'createdBy'])

        # update single role
        update_response = client.post(f'/api/v1/job_role/update/{role_id}', headers=superuser_token_headers, json={
            'name': 'Bartending',
            'image': 'www.python.com'
        })
        assert update_response.status_code == 201
        assert update_response.json() is not None
        assert update_response.json().get('name') == 'Bartending'
        assert update_response.json().get('image') == 'www.python.com'
        self.check_fields(response.json(), [
                          'id', 'name', 'image', 'createdAt', 'updatedAt', 'createdBy'])

        # update single role
        delete_response = client.delete(
            f'/api/v1/job_role/delete/{role_id}', headers=superuser_token_headers)
        assert delete_response.status_code == 200
        assert delete_response.json() is not None
        assert delete_response.json().get('status') == 'success'

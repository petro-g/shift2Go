import pytest
import typing as t
from fastapi.testclient import TestClient

from app.db.crud import create_badge, delete_badge


class Test_Badge:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_badge_crud(self, client: TestClient, superuser_token_headers:  dict):

        # add badge
        add_response = client.post('/api/v1/badge/add', headers=superuser_token_headers, json={
            'name': 'First Shift Completed',
            'image': 'www.google.com',
            'type': 'HOTEL'
        })
        assert add_response.status_code == 201
        assert add_response.json() is not None
        self.check_fields(add_response.json(), [
            'id', 'name', 'image', 'type', 'createdBy', 'createdAt', 'updatedAt'])
        badge_id = add_response.json().get('id')

        # read badges
        read_response = client.get(
            '/api/v1/badges', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read single badge
        read_single_response = client.get(
            f'/api/v1/badge/{badge_id}', headers=superuser_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None
        self.check_fields(read_single_response.json(), [
                          'id', 'name', 'image', 'type', 'createdBy', 'createdAt', 'updatedAt'])

        # delete single badge
        delete_response = client.delete(
            f'/api/v1/badge/delete/{badge_id}', headers=superuser_token_headers)
        assert delete_response.status_code == 200
        assert delete_response.json() == {
            'status': 'success'
        }

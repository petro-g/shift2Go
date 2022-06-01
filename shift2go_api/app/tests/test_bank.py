import pytest
import typing as t
from fastapi.testclient import TestClient

from app.db.crud import delete_bank


class Test_Bank:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_bank_crud(
        self,
        client: TestClient,
        superuser_token_headers:  dict,
    ):
        # add bank
        response = client.post('/api/v1/bank/add', headers=superuser_token_headers, json={
            'name': 'Barclays',
            'accountNumber': '123456789',
            'routingNumber': '123456'
        })
        assert response.status_code == 201
        self.check_fields(response.json(), [
                          'id', 'name', 'accountNumber', 'routingNumber', 'createdBy', 'createdAt', 'updatedAt', 'owner'])
        bank_id = response.json().get('id')

        # read banks
        read_response = client.get(
            '/api/v1/banks', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read single bank
        read_single_response = client.get(
            f'/api/v1/bank/{bank_id}', headers=superuser_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None
        self.check_fields(response.json(), [
                          'id', 'name', 'accountNumber', 'routingNumber', 'createdBy', 'createdAt', 'updatedAt', 'owner'])

        # delete single bank
        delete_response = client.delete(
            f'/api/v1/bank/delete/{bank_id}', headers=superuser_token_headers)
        assert delete_response.status_code == 200
        assert delete_response.json() == {
            'status': 'success'
        }

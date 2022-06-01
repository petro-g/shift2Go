import pytest
import typing as t
from fastapi.testclient import TestClient

from app.db.crud import create_country


class Test_Country:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_country_crud(
        self,
        client: TestClient,
        superuser_token_headers
    ):
        # add country
        mock_payload = {
            'code': 'US',
            'name': 'America'
        }

        response = client.post(
            '/api/v1/country/add', headers=superuser_token_headers, json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        self.check_fields(response.json(), [
            key for key in mock_payload.keys()])
        country_id = response.json().get('code')

        # read all countries
        read_all_response = client.get(
            '/api/v1/countries', headers=superuser_token_headers)
        assert read_all_response.status_code == 200
        assert read_all_response.json() is not None
        assert read_all_response.json()[0]

        # read single country
        read_single_response = client.get(
            f'/api/v1/countries/{country_id}', headers=superuser_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None
        self.check_fields(read_single_response.json(), ['name', 'code'])

import pytest
import typing as t
from fastapi.testclient import TestClient


class Test_Document:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_document_crud(
        self,
        client: TestClient,
        contractor_token_headers: dict
    ):
        # add document
        response = client.post('/api/v1/document/add', headers=contractor_token_headers, json={
            'url': 'www.medium.com'
        })
        assert response.status_code == 201
        assert response.json() is not None
        assert response.json().get('url') == 'www.medium.com'
        self.check_fields(response.json(), [
                          'id', 'url', 'verified', 'createdBy', 'createdAt', 'updatedAt'])
        document_id = response.json().get('id')

        # read all documents
        read_all_response = client.get(
            '/api/v1/documents', headers=contractor_token_headers)
        assert read_all_response.status_code == 200
        assert read_all_response.json() is not None
        assert read_all_response.json()[0]

        # read single documents
        read_single_response = client.get(
            f'/api/v1/document/{document_id}', headers=contractor_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None
        self.check_fields(response.json(), [
                          'id', 'url', 'verified', 'createdBy', 'createdAt', 'updatedAt'])

        # update single documents
        update_single_response = client.patch(f'/api/v1/document/update/{document_id}', headers=contractor_token_headers, json={
            'url': 'www.yahoo.com'
        })
        assert update_single_response.status_code == 201
        assert update_single_response.json() is not None
        assert update_single_response.json().get('url') == 'www.yahoo.com'
        self.check_fields(response.json(), [
                          'id', 'url', 'verified', 'createdBy', 'createdAt', 'updatedAt'])

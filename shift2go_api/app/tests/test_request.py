import pytest
import typing as t
from app.db import models
from fastapi.testclient import TestClient


class Test_Request:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_request_crud(
        self,
        client: TestClient,
        test_contractor: models.Contractors,
        contractor_token_headers: dict,
        test_manager_shift: models.Shifts,
        manager_token_headers: dict
    ):
        # add request
        response = client.post('/api/v1/shifts_requests/create', headers=contractor_token_headers, json={
            'notes': 'Am available',
            'shift_id': test_manager_shift.id
        })
        assert response.status_code == 201
        assert response.json() is not None
        self.check_fields(response.json(), [
                          'id', 'notes', 'shift_id', 'createdBy'])
        request_id = response.json().get('id')

        # read all request
        read_response = client.get(
            '/api/v1/shifts_requests', headers=manager_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read single request
        read_single_response = client.get(
            f'/api/v1/shifts_request/{request_id}', headers=manager_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None
        self.check_fields(read_single_response.json(), [
                          'id', 'notes', 'shift_id', 'createdBy'])

        # update single request
        update_single_response = client.patch(f'/api/v1/shifts_request/update/{request_id}', headers=contractor_token_headers, json={
            'notes': 'I work hard'
        })
        assert update_single_response.status_code == 200
        assert update_single_response.json() is not None
        assert update_single_response.json().get('notes') == 'I work hard'
        self.check_fields(update_single_response.json(), [
                          'id', 'notes', 'shift_id', 'createdBy'])

        # delete single request
        delete_response = client.delete(
            f'/api/v1/shifts_request/delete/{request_id}', headers=contractor_token_headers)
        assert delete_response.status_code == 200
        assert delete_response.json() is not None
        assert delete_response.json().get('status') == 'success'

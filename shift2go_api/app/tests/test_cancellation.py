import pytest
import typing as t
from sqlalchemy.orm import Session
from app.db import models
from fastapi.testclient import TestClient


class Test_Cancellations:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_cancellations_crud(
        self,
        client: TestClient,
        contractor_token_headers: dict,
        test_manager_shift: models.Shifts,
        test_contractor: models.Contractors,
        test_db: Session
    ):
        # assign shift
        test_manager_shift.contractor_id = test_contractor.id
        test_db.add(test_manager_shift)
        test_db.commit()

        # cancel shift
        response = client.post('/api/v1/shift_cancellation/create', headers=contractor_token_headers, json={
            'shift_id': test_manager_shift.id,
            'reason': 'am busy'
        })
        assert response.status_code == 201
        assert response.json() is not None
        self.check_fields(response.json(), [
                          'id', 'reason', 'shift_id', 'createdAt', 'updatedAt'])
        cancelled_id = response.json().get('id')

        # read cancelled shifts
        read_response = client.get(
            '/api/v1/shift_cancellations', headers=contractor_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # update cancelled shift
        update_response = client.patch(f'/api/v1/shift_cancellation/update/{cancelled_id}', headers=contractor_token_headers, json={
            'reason': 'am tired'
        })
        assert update_response.status_code == 201
        assert update_response.json() is not None
        assert update_response.json().get('reason') == 'am tired'
        self.check_fields(update_response.json(), [
                          'id', 'reason', 'shift_id', 'createdAt', 'updatedAt'])

        # pre cancellation
        pre_response = client.get(
            f'/api/v1/shift_cancellation/pre_cancellation?shift_id={test_manager_shift.id}', headers=contractor_token_headers)
        assert pre_response.status_code == 200
        assert pre_response.json() is not None
        self.check_fields(pre_response.json(), [
                          'existing', 'deadline', 'message'])

        # read single cancellation
        single_response = client.get(
            f'/api/v1/shift_cancellation/{cancelled_id}', headers=contractor_token_headers)
        assert single_response.status_code == 200
        assert single_response.json() is not None
        self.check_fields(single_response.json(), [
                          'id', 'reason', 'shift_id', 'createdAt', 'updatedAt'])

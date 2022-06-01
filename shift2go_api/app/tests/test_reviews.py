from datetime import datetime, timedelta
import pytest
import typing as t
from sqlalchemy.orm import Session
from app.db import models
from fastapi.testclient import TestClient


class Test_Reviews:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_review_crud(
        self,
        client: TestClient,
        test_manager_shift: models.Shifts,
        test_contractor: models.Contractors,
        test_manager: models.HotelAdmins,
        superuser_token_headers: dict,
        contractor_token_headers: dict,
        manager_token_headers: dict,
        test_db: Session
    ):
        # start and end shift
        test_manager_shift.contractor_id = test_contractor.id
        test_manager_shift.startedAt = datetime.now() + timedelta(hours=1, seconds=20)
        test_manager_shift.clockInLatitude = 20.00
        test_manager_shift.clockInLongitude = 20.00
        test_manager_shift.endedAt = datetime.now() + timedelta(hours=4, seconds=20)
        test_manager_shift.clockOutLatitude = 20.00
        test_manager_shift.clockOutLongitude = 20.00
        test_manager_shift.confirmed = True
        test_manager_shift.status = 'COMPLETED'
        test_db.add(test_manager_shift)
        test_db.commit()
        test_db.refresh(test_manager_shift)

        # add review by contractor
        contractor_mock_payload = {
            'shift_id': test_manager_shift.id,
            'reviewee_type': 'HOTEL',
            'comment': 'Beautiful Working environment',
            'rating': 5
        }
        contractor_review_response = client.post(
            '/api/v1/review/add', headers=contractor_token_headers, json=contractor_mock_payload)
        assert contractor_review_response.status_code == 201
        assert contractor_review_response.json() is not None
        self.check_fields(contractor_review_response.json(), [
                          key for key in contractor_mock_payload.keys()])
        review_id = contractor_review_response.json().get('id')

        # add review by hotel
        manager_mock_payload = {
            'shift_id': test_manager_shift.id,
            'reviewee_type': 'USER',
            'comment': 'Very respectful worker',
            'rating': 5
        }
        manager_review_response = client.post(
            '/api/v1/review/add', headers=manager_token_headers, json=manager_mock_payload)
        assert manager_review_response.status_code == 201
        assert manager_review_response.json() is not None
        self.check_fields(manager_review_response.json(), [
                          key for key in manager_mock_payload.keys()])

        # read manager review by admin
        read_manager_review_response = client.get(
            f'/api/v1/reviews/hotel?hotel_id={test_manager_shift.hotel_id}', headers=superuser_token_headers)
        assert read_manager_review_response.status_code == 200
        assert read_manager_review_response.json() is not None
        assert read_manager_review_response.json()[0]

        # read contractor own review
        read_contractor_own_review_response = client.get(
            f'/api/v1/reviews/me', headers=contractor_token_headers)
        assert read_contractor_own_review_response.status_code == 200
        assert read_contractor_own_review_response.json() is not None
        assert read_contractor_own_review_response.json()[0]

        # read given review
        read_contractor_own_review_response = client.get(
            f'/api/v1/reviews/given', headers=contractor_token_headers)
        assert read_contractor_own_review_response.status_code == 200
        assert read_contractor_own_review_response.json() is not None
        assert read_contractor_own_review_response.json()[0]

        # read single review
        read_single_review_response = client.get(
            f'/api/v1/review/{review_id}', headers=superuser_token_headers)
        assert read_single_review_response.status_code == 200
        assert read_single_review_response.json() is not None
        self.check_fields(read_single_review_response.json(), [
                          key for key in manager_mock_payload.keys()])

        # update review
        update_single_review_response = client.patch(f'/api/v1/review/edit?review_id={review_id}', headers=contractor_token_headers, json={
            'comment': 'Best Services',
            'rating': 4
        })
        assert update_single_review_response.status_code == 201
        assert update_single_review_response.json() is not None
        assert update_single_review_response.json().get('comment') == 'Best Services'
        assert update_single_review_response.json().get('rating') == float(4)

        # delete review
        delete_single_review_response = client.delete(
            f'/api/v1/review/delete?review_id={review_id}', headers=contractor_token_headers)
        assert delete_single_review_response.status_code == 200
        assert delete_single_review_response.json() is not None
        assert delete_single_review_response.json().get('status') == 'success'

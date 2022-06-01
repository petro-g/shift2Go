from datetime import datetime, timedelta
import pytest
import typing as t
from sqlalchemy.orm import Session
from app.db import models
from fastapi.testclient import TestClient


class Test_Shifts:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_shift_crud(
        self,
        client: TestClient,
        test_manager_shift: models.Shifts,
        test_manager_hotel: models.Hotels,
        test_contractor: models.Contractors,
        test_manager: models.HotelAdmins,
        superuser_token_headers: dict,
        contractor_token_headers: dict,
        manager_token_headers: dict,
        test_db: Session
    ):
        # add shift
        mock_payload = {
            'name': 'Security Personnel',
            'hotel_id': test_manager_hotel.id,
            'roles_ids': [],
            'pay': 100,
            'startTime': str(datetime.now()),
            'endTime': str(datetime.now() + timedelta(hours=4)),
            'instruction': 'Come early',
            'requiredCertificates': [],
            'audienceType': 'MARKET'
        }
        response = client.post('/api/v1/shift/create',
                               headers=manager_token_headers, json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        shift_id = response.json().get('id')

        # read shifts
        read_response = client.get(
            '/api/v1/shifts', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read single shifts
        read_response = client.get(
            f'/api/v1/shift/{shift_id}', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None

        # read hotel shifts
        read_hotel_shift_response = client.get(
            f'/api/v1/shifts/hotel?hotel_id={test_manager_hotel.id}', headers=superuser_token_headers)
        assert read_hotel_shift_response.status_code == 200
        assert read_hotel_shift_response.json() is not None
        assert read_hotel_shift_response.json()[0]

        # update shifts
        update_hotel_shift_response = client.patch(f'/api/v1/shift/update/{shift_id}', headers=superuser_token_headers, json={
            'name': 'Hotel Security'
        })
        assert update_hotel_shift_response.status_code == 200
        assert update_hotel_shift_response.json() is not None
        assert update_hotel_shift_response.json().get('name') == 'Hotel Security'

        # award shift
        award_shift_response = client.post(f'/api/v1/shift/award', headers=manager_token_headers, json={
            'shift_id': shift_id,
            'contractor_id': test_contractor.id
        })
        assert award_shift_response.status_code == 200
        assert award_shift_response.json() is not None
        assert award_shift_response.json().get('contractor_id') == test_contractor.id

        # awarded shift
        awarded_shift_response = client.get(
            f'/api/v1/shift/awarded', headers=contractor_token_headers)
        assert awarded_shift_response.status_code == 200
        assert awarded_shift_response.json() is not None
        assert awarded_shift_response.json()[0]

        # accept shift
        accept_shift_response = client.patch(
            f'/api/v1/shift/accept?shift_id={shift_id}', headers=contractor_token_headers)
        assert accept_shift_response.status_code == 200
        assert accept_shift_response.json() is not None

        # accepted shift
        accepted_shift_response = client.patch(
            f'/api/v1/shift/accepted', headers=contractor_token_headers)
        assert accepted_shift_response.status_code == 200
        assert accepted_shift_response.json() is not None

        # upcoming shift
        upcoming_shift_response = client.get(
            f'/api/v1/shift/upcoming', headers=contractor_token_headers)
        assert upcoming_shift_response.status_code == 200
        assert upcoming_shift_response.json() is not None

        # contractor ongoing shift
        contractor_ongoing_shift_response = client.get(
            f'/api/v1/shift/contractor/ongoing', headers=contractor_token_headers)
        assert contractor_ongoing_shift_response.status_code == 200
        assert contractor_ongoing_shift_response.json() is not None

        # hotel ongoing shift
        hotel_ongoing_shift_response = client.get(
            f'/api/v1/shift/hotel/ongoing?hotel_id={test_manager_hotel.id}', headers=manager_token_headers)
        assert hotel_ongoing_shift_response.status_code == 200
        assert hotel_ongoing_shift_response.json() is not None

        # shift history
        shift_history_response = client.get(
            f'/api/v1/shift/history', headers=contractor_token_headers)
        assert shift_history_response.status_code == 200
        assert shift_history_response.json() is not None

        # clock in
        clock_in_shift_response = client.patch(f'/api/v1/shift/clock_in', headers=contractor_token_headers, json={
            'shift_id': shift_id,
            'clockInLatitude': 0.0,
            'clockInLongitude': 0.0,
        })
        assert clock_in_shift_response.status_code == 200
        assert clock_in_shift_response.json() is not None

        # clock out
        clock_out_shift_response = client.post(f'/api/v1/shift/clock_out', headers=contractor_token_headers, json={
            'shift_id': shift_id,
            'clockOutLatitude': 0.0,
            'clockOutLongitude': 0.0,
        })
        assert clock_out_shift_response.status_code == 200
        assert clock_out_shift_response.json() is not None

        # confirm shift
        confirm_shift_response = client.post(
            f'/api/v1/shift/confirm?shift_id={shift_id}', headers=manager_token_headers)
        assert confirm_shift_response.status_code == 200
        assert confirm_shift_response.json() is not None

        # confirmed shift
        confirmed_shift_response = client.post(
            f'/api/v1/shift/confirmed', headers=manager_token_headers)
        assert confirmed_shift_response.status_code == 200
        assert confirmed_shift_response.json() is not None

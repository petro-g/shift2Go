import pytest
import typing as t
from sqlalchemy.orm import Session
from app.db import models
from fastapi.testclient import TestClient

from app.db.crud import create_bill


class Test_Billings:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_billing_crud(
        self,
        client: TestClient,
        superuser_token_headers: dict,
        manager_token_headers: dict,
        test_manager_shift: models.Shifts,
        test_manager_hotel: models.Hotels,
        test_manager: models.HotelAdmins,
        test_superuser: models.Admins,
        test_db: Session
    ):
        # add billing
        mock_payload = {
            'shift_id': test_manager_shift.id,
            'hotel_id': test_manager_hotel.id,
            'status': 'PENDING',
            'amountPayableToShift2go': 120.0,
            'amountPayableToContractor': 80.0,
            'paymentTransactionID': '13232',
            'createdBy': test_manager.userID
        }
        response = client.post('/api/v1/billing/create',
                               headers=superuser_token_headers, json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        self.check_fields(response.json(), [
            key for key in mock_payload.keys()])
        bill_id = response.json().get('id')

        # read billings
        read_response = client.get(
            '/api/v1/billings', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read hotel billings
        read_hotel_response = client.get(
            f'/api/v1/billings/hotel/{test_manager_hotel.id}', headers=superuser_token_headers)
        assert read_hotel_response.status_code == 200
        assert read_hotel_response.json() is not None
        assert read_hotel_response.json()[0]

        # read single billings
        read_single_response = client.get(
            f'/api/v1/billing/{bill_id}', headers=superuser_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None

        # update single billing
        update_response = client.patch(f'/api/v1/billing/update/{bill_id}', headers=superuser_token_headers, json={
            'status': 'PAID',
        })
        assert update_response.status_code == 201
        assert update_response.json() is not None
        self.check_fields(update_response.json(), [
                          key for key in mock_payload.keys()])
        assert update_response.json().get('status') == 'PAID'

        # delete single billing
        delete_response = client.delete(
            f'/api/v1/billing/delete/{bill_id}', headers=superuser_token_headers)
        assert delete_response.status_code == 200
        assert delete_response.json() is not None
        assert delete_response.json().get('status') == 'success'

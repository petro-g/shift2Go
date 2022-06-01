import pytest
import typing as t
from app.db import models
from fastapi.testclient import TestClient


class Test_Hotel:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_hotel_crud(
        self,
        client: TestClient,
        test_contractor: models.Contractors,
        manager_token_headers: dict,
    ):
        # add hotel
        mock_payload = {
            'legal_name': 'Tyco City',
            'phone': '123456789',
            'address': 'New York',
            'employerIdentificationNumber': '123456',
            'pictures': ['www.google.com'],
            'contractorsRadius': 20,
            'notification': {
                'email': True,
                'push': True
            },
            'longitude': 0,
            'latitude': 0,
            'bank': {
                'name': 'Barclays',
                'accountNumber': '123456789',
                'routingNumber': '123456'
            }
        }
        response = client.post('/api/v1/hotel/create',
                               headers=manager_token_headers, json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        del mock_payload['legal_name']
        self.check_fields(response.json(), [
                          key for key in mock_payload.keys()])
        hotel_id = response.json().get('id')

        # read hotel
        read_response = client.get(
            '/api/v1/hotels', headers=manager_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # add contractor to hotel favourites
        add_favourite_response = client.get(
            f'/api/v1/hotel/favourites/add?hotel_id={hotel_id}&contractor_id={test_contractor.id}', headers=manager_token_headers)
        assert add_favourite_response.status_code == 200
        assert add_favourite_response.json() is not None
        self.check_fields(add_favourite_response.json(), [
                          key for key in mock_payload.keys()])

        # read hotel favourites
        read_favourite_response = client.get(
            f'/api/v1/hotel/favourites?hotel_id={hotel_id}', headers=manager_token_headers)
        assert read_favourite_response.status_code == 200
        assert read_favourite_response.json() is not None
        assert read_favourite_response.json()[0]

        # remove contractor to hotel favourites
        remove_favourite_response = client.get(
            f'/api/v1/hotel/favourites/remove?hotel_id={hotel_id}&contractor_id={test_contractor.id}', headers=manager_token_headers)
        assert remove_favourite_response.status_code == 200
        assert remove_favourite_response.json() is not None
        self.check_fields(remove_favourite_response.json(), [
                          key for key in mock_payload.keys()])

        # read single hotel
        read_single_hotel = client.get(
            f'/api/v1/hotel/{hotel_id}', headers=manager_token_headers)
        assert read_single_hotel.status_code == 200
        assert read_single_hotel.json() is not None
        self.check_fields(read_single_hotel.json(), [
                          key for key in mock_payload.keys()])

        # update single hotel
        update_single_hotel = client.patch(f'/api/v1/hotel/update/{hotel_id}', headers=manager_token_headers, json={
            'name': 'Eusbert Hotel',
            'phone': '0123456789'
        })
        assert update_single_hotel.status_code == 201
        assert update_single_hotel.json() is not None
        assert update_single_hotel.json().get('name') == 'Eusbert Hotel'
        assert update_single_hotel.json().get('phone') == '0123456789'
        self.check_fields(update_single_hotel.json(), [
                          key for key in mock_payload.keys()])

        # delete single hotel
        delete_single_hotel = client.delete(
            f'/api/v1/hotel/delete/{hotel_id}', headers=manager_token_headers)
        assert delete_single_hotel.status_code == 200
        assert delete_single_hotel.json() is not None
        assert delete_single_hotel.json().get('status') == 'success'

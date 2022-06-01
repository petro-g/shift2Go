import typing as t
from sqlalchemy.orm import Session
from app.config import auth
from fastapi.testclient import TestClient
from app.db import crud


class Test_Contractor:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_contractor_crud(
        self,
        client: TestClient,
        test_db: Session,
        superuser_token_headers: dict,
    ):

        # add contractor
        mock_payload = {
            'email': 'test_contractor@shift2go.com',
            'password': 'password',
            'firstname': 'John',
            'lastname': 'Doe',
            'latitiude': 0,
            'longitude': 0,
            'address': 'Zongo',
            'phone': '123456789',
            'profilePicture': 'www.google.com'
        }
        response = client.post('/api/v1/contractor/signup', json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        self.check_fields(response.json(), ['id', 'userID', 'profilePicture'])
        contractor = response.json()
        contractor_id = contractor.get('id')
        token = auth.generate_login_token(
            crud.get_user_by_id(test_db, contractor.get('userID')))
        contractor_token = {
            'Authorization': f'Bearer {token}'
        }

        # read contractor profile
        contractor_response = client.get(
            '/api/v1/contractor/me', headers=contractor_token)
        assert contractor_response.status_code == 200
        assert contractor_response.json() is not None
        self.check_fields(response.json(),  ['id', 'userID', 'profilePicture'])

        # read all contractors
        all_contractor_response = client.get(
            '/api/v1/contractors', headers=superuser_token_headers)
        assert all_contractor_response.status_code == 200
        assert all_contractor_response.json() is not None
        assert all_contractor_response.json()[0]

        # verify contractor
        crud.contractor_verify(test_db, contractor_id)

        # read single contractors
        single_contractor_response = client.get(
            f'/api/v1/contractor/{contractor_id}', headers=superuser_token_headers)
        assert single_contractor_response.status_code == 200
        assert single_contractor_response.json() is not None
        self.check_fields(single_contractor_response.json(),
                          ['id', 'userID', 'profilePicture'])

        # update contractor
        update_contractor_response = client.patch(f'/api/v1/contractor/update/me', headers=contractor_token, json={
            'profilePicture': 'www.github.com'
        })
        assert update_contractor_response.status_code == 201
        assert update_contractor_response.json() is not None
        assert update_contractor_response.json().get(
            'profilePicture') == 'www.github.com'
        self.check_fields(update_contractor_response.json(),
                          ['id', 'userID', 'profilePicture'])

        # delete contractor
        delete_update_contractor_response = client.delete(
            f'/api/v1/contractor/delete/{contractor_id}', headers=superuser_token_headers)
        assert delete_update_contractor_response.status_code == 200
        assert delete_update_contractor_response.json() is not None
        assert delete_update_contractor_response.json().get('status') == 'success'

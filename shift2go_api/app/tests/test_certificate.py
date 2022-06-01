import pytest
import typing as t
from fastapi.testclient import TestClient


class Test_Certificate:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_certificate_crud(
        self,
        client: TestClient,
        superuser_token_headers: dict
    ):
        # add certificate type
        response = client.post('/api/v1/certificate/type/create', headers=superuser_token_headers, json={
            'name': 'Opera'
        })
        assert response.status_code == 201
        assert response.json() is not None
        assert response.json().get('name') == 'Opera'
        certificate_type_id = response.json().get('id')

        # read single certificate type
        single_response = client.get(
            f'/api/v1/certificate/type/{certificate_type_id}', headers=superuser_token_headers)
        assert single_response.status_code == 200
        assert single_response.json() is not None
        assert single_response.json().get('name') == 'Opera'

        # update single certificate type
        update_response = client.patch(f'/api/v1/certificate/type/update/{certificate_type_id}', headers=superuser_token_headers, json={
            'id': certificate_type_id,
            'name': 'ServSafe'
        })
        assert update_response.status_code == 201
        assert update_response.json() is not None
        assert update_response.json().get('name') == 'ServSafe'

        # add certificate
        add_certificate_response = client.post('/api/v1/certificate/create', headers=superuser_token_headers, json={
            'certificate_type_id': certificate_type_id,
            'url': 'www.google.com'
        })
        assert add_certificate_response.status_code == 201
        assert add_certificate_response.json() is not None
        self.check_fields(add_certificate_response.json(), [
                          'id', 'url', 'certificate_type_id', 'createdBy', 'updatedAt', 'createdAt', 'type'])
        certificate_id = add_certificate_response.json().get('id')

        # read all certificate as admin
        read_certificates_as_admin_response = client.get(
            '/api/v1/certificates/all', headers=superuser_token_headers)
        assert read_certificates_as_admin_response.status_code == 200
        assert read_certificates_as_admin_response.json() is not None
        assert read_certificates_as_admin_response.json()[0]

        # read all certificate
        read_certificate_response = client.get(
            '/api/v1/certificates', headers=superuser_token_headers)
        assert read_certificate_response.status_code == 200
        assert read_certificate_response.json() is not None
        assert read_certificate_response.json()[0]

        # read all certificate types
        read_certificate_types_response = client.get(
            '/api/v1/certificate/types', headers=superuser_token_headers)
        assert read_certificate_types_response.status_code == 200
        assert read_certificate_types_response.json() is not None
        assert read_certificate_types_response.json()[0]

        # read single certificate types
        read_single_certificate_response = client.get(
            f'/api/v1/certificate/{certificate_id}', headers=superuser_token_headers)
        assert read_single_certificate_response.status_code == 200
        assert read_single_certificate_response.json() is not None
        self.check_fields(read_single_certificate_response.json(), [
                          'id', 'url', 'certificate_type_id', 'createdBy', 'createdAt', 'updatedAt'])

        # update single certificate types
        update_single_certificate_response = client.patch(f'/api/v1/certificate/update/{certificate_id}', headers=superuser_token_headers, json={
            'url': 'www.fb.com'
        })
        assert update_single_certificate_response.status_code == 201
        assert update_single_certificate_response.json() is not None
        assert update_single_certificate_response.json().get('url') == 'www.fb.com'
        self.check_fields(update_single_certificate_response.json(), [
                          'id', 'url', 'certificate_type_id', 'createdBy', 'createdAt', 'updatedAt'])

        # delete single certificate types
        read_single_certificate_response = client.delete(
            f'/api/v1/certificate/delete/{certificate_id}', headers=superuser_token_headers)
        assert read_single_certificate_response.status_code == 200
        assert read_single_certificate_response.json() is not None
        assert read_single_certificate_response.json().get('status') == 'success'

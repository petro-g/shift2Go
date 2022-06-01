import pytest
import typing as t
from app.db import models
from fastapi.testclient import TestClient


class Test_Notification:

    def check_fields(self, json: dict, keys: t.List[str]):
        for key in keys:
            assert key in json

    def test_crud_notification(
        self,
        client: TestClient,
        test_contractor: models.Contractors,
        superuser_token_headers: dict,
        manager_token_headers: dict,
    ):
        # add a notification
        mock_payload = {
            'title': 'Test Notification',
            'message': 'You have a new Shift',
            'notificationType': 'BOTH',
            'receivers': [test_contractor.userID]
        }
        response = client.post('/api/v1/notification/create',
                               headers=superuser_token_headers, json=mock_payload)
        assert response.status_code == 201
        assert response.json() is not None
        self.check_fields(response.json(), [
                          key for key in mock_payload.keys()])
        notification_id = response.json().get('id')

        # read notifications
        read_response = client.get(
            '/api/v1/notifications', headers=superuser_token_headers)
        assert read_response.status_code == 200
        assert read_response.json() is not None
        assert read_response.json()[0]

        # read notifications settings
        read_notification_setting_response = client.patch('/api/v1/notification/settings/update', headers=manager_token_headers, json={
            'push': False,
            'email': False
        })
        assert read_notification_setting_response.status_code == 201
        assert read_notification_setting_response.json() is not None
        assert read_notification_setting_response.json().get('push') == False
        assert read_notification_setting_response.json().get('email') == False

        # set notification reminder
        reminder_response = client.post('/api/v1/notification/reminder', headers=manager_token_headers, json={
            'hours': 5
        })
        assert reminder_response.status_code == 200
        assert reminder_response.json() is not None
        assert reminder_response.json().get('reminder') == 5

        # mark notification as read
        mark_read_response = client.patch(
            f'/api/v1/notification/read?notification_id={notification_id}', headers=superuser_token_headers)
        assert mark_read_response.status_code == 200
        assert mark_read_response.json() is not None

        # read single notification
        read_single_response = client.get(
            f'/api/v1/notification/{notification_id}', headers=superuser_token_headers)
        assert read_single_response.status_code == 200
        assert read_single_response.json() is not None
        self.check_fields(read_single_response.json(), [
                          key for key in mock_payload.keys()])

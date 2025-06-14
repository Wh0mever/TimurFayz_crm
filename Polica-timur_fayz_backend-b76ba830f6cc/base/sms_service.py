import base64
from typing import List, Dict

import requests
from django.conf import settings
from requests import RequestException

from base.exceptions import SMSSendRequestFailed


class Config:
    URL = settings.PLAY_MOBILE_SETTINGS['API_URL']
    PREFIX = settings.PLAY_MOBILE_SETTINGS['PREFIX']
    DEFAULT_ORIGINATOR = settings.PLAY_MOBILE_SETTINGS['ORIGINATOR']
    ORIGINATOR = '3700' if DEFAULT_ORIGINATOR == '' else DEFAULT_ORIGINATOR
    LOGIN = settings.PLAY_MOBILE_SETTINGS['LOGIN']
    PASSWORD = settings.PLAY_MOBILE_SETTINGS['PASSWORD']

    def __init__(self):
        self.HEADER = self.header()

    def header(self):
        data = '{}:{}'.format(self.LOGIN, self.PASSWORD)
        encoded = base64.b64encode(data.encode('utf-8'))
        header = {'Authorization': 'Basic {}'.format(str(encoded, 'utf-8'))}
        return header


class SMSService:
    def __init__(self):
        self.config = Config()

    def _generate_message_dict(self, phone_number, text):
        return {
            "recipient": phone_number,
            "message-id": f"{self.config.PREFIX}_000",
            "sms": {
                "originator": self.config.ORIGINATOR,
                "content": {
                    "text": text
                }
            }
        }

    def _send_sms(self, data):
        try:
            result = requests.post(self.config.URL, json=data, headers=self.config.HEADER)
        except RequestException as err:
            return SMSSendRequestFailed
        return True

    def send_single_sms(self, phone_number: str, text: str):
        data = {
            'messages': [
                self._generate_message_dict(phone_number, text)
            ]
        }
        response = self._send_sms(data)
        return response

    def send_mass_sms(self, phone_numbers: List[str], text: str):
        messages = [self._generate_message_dict(number, text) for number in phone_numbers]
        data = {
            'messages': messages
        }
        response = self._send_sms(data)
        return response

    def send_mass_sms_with_individual_message(self, recipients: List[Dict]):
        messages = []
        for recipient in recipients:
            phone_numbers = recipient['phone_numbers']
            message = recipient['message']
            messages.append([self._generate_message_dict(number, message) for number in phone_numbers])
        data = {
            'messages': messages
        }
        response = self._send_sms(data)
        return response

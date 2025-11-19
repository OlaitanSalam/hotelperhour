# utils/sms.py
'''
import requests
from django.conf import settings

SMS_API_URL = "https://api.80kobosms.com/v2/app/sendsms"

def send_sms(message, phone_number):
    """
    Sends SMS using 80kobo SMS API (BulksmsNigeria Gateway)
    """

    # Convert Nigerian numbers 081... → 23481...
    if phone_number.startswith("0"):
        phone_number = "234" + phone_number[1:]
    if phone_number.startswith("+"):
        phone_number = phone_number.replace("+", "")

    payload = {
        "api_token": settings.SMS_API_KEY,
        "from": settings.SMS_SENDER_ID,        # required by provider
        "to": phone_number,                   # required
        "body": message,                      # required
        "dnd": 1                              # optional (skip DND filtering)
    }

    try:
        response = requests.post(SMS_API_URL, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}
'''
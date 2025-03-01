import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load Environment Variables
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Load Firebase credentials
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def get_zoho_access_token():
    """ Refresh Zoho Access Token """
    url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=payload)
    return response.json().get("access_token")

@app.route('/whatsapp-webhook', methods=['GET'])
def verify_webhook():
    """ Verify Webhook with Meta """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route('/whatsapp-webhook', methods=['POST'])
def receive_whatsapp_message():
    """ Capture WhatsApp Messages & Store in Firestore/Zoho """
    data = request.json
    message = data['entry'][0]['changes'][0]['value']['messages'][0]
    user_phone = message['from']

    if "interactive" in message:
        user_response = message['interactive']['button_reply']['id']
        user_details = {"age": "20-30"} if user_response == "age_20_30" else {"symptoms": "Needs Consultation"}
        db.collection("whatsapp_users").document(user_phone).set(user_details, merge=True)
        
        zoho_access_token = get_zoho_access_token()
        zoho_payload = {"data": [{"Last_Name": "WhatsApp User", "Phone": user_phone, **user_details}]}
        requests.post("https://www.zohoapis.com/crm/v2/Leads", json=zoho_payload, headers={"Authorization": f"Zoho-oauthtoken {zoho_access_token}"})

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(port=5000)

from flask import Flask, request, jsonify
import requests
import json
import threading
import time

app = Flask(__name__)

ZOHO_CLIENT_ID     = "1000.IULCSGKGFEDV3TZR89WUO1ARTZC5EB"
ZOHO_CLIENT_SECRET = "5c9201d98527c86e9d2b8455ee8347d5af7f231748"
ZOHO_REFRESH_TOKEN = "1000.5caed9e8cac429a557bac7f03d39fd8f.724579561fc0baaa2121bf5553be83b8"
ZOHO_API           = "https://www.zohoapis.in/crm/v2"
ZOHO_TOKEN_URL     = "https://accounts.zoho.in/oauth/v2/token"

AISENSY_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNTUwYWM3ZWQ4MmM3MGU0ZjI3NGQ3YiIsIm5hbWUiOiJMU0dTdGVzdCIsImFwcE5hbWUiOiJBaVNlbnN5IiwiY2xpZW50SWQiOiI2YTUzYzVmODQyMjYzNTM2MzQ5ZWMwZDEiLCJhY3RpdmVQbGFuIjoiUFJPX01PTlRITFkiLCJpYXQiOjE3ODY5NDI4MzV9.MKc8QhNNVW4rsUwLPzxU7wRISgXhvmA02thdoNnAtV0"
AISENSY_BASE    = "https://backend.aisensy.com/campaign/t1/api/v2"

processed_contacts = set()

def get_zoho_token():
    r = requests.post(ZOHO_TOKEN_URL, data={"refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID, "client_secret": ZOHO_CLIENT_SECRET, "grant_type": "refresh_token"})
    return r.json().get("access_token")

def create_zoho_lead(name, phone, budget="", city="", franchise_type=""):
    token = get_zoho_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
    lead = {"data": [{"Last_Name": name or "Unknown", "Phone": phone, "Mobile": phone,
        "Lead_Source": "WhatsApp Campaign", "Lead_Status": "Contacted - Awaiting Response",
        "Description": f"Budget: {budget} | City: {city} | Franchise Type: {franchise_type}", "City": city}]}
    r = requests.post(f"{ZOHO_API}/Leads", headers=headers, json=lead)
    return r.json()

def fetch_aisensy_contacts():
    headers = {"Authorization": f"Bearer {AISENSY_API_KEY}"}
    try:
        r = requests.get(f"{AISENSY_BASE}/contacts", headers=headers,
                         params={"limit": 100, "sort": "lastActive", "order": "desc"})
        return r.json()
    except Exception as e:
        print(f"Error: {e}")
        return {}

def poll_and_sync():
    while True:
        try:
            data = fetch_aisensy_contacts()
            contacts = data.get("contacts", [])
            for contact in contacts:
                phone = contact.get("phone", "")
                name  = contact.get("name", "Unknown")
                if phone in processed_contacts:
                    continue
                attributes = contact.get("attributes", {})
                tags = contact.get("tags", [])
                if any("FN" in str(t) for t in tags):
                    create_zoho_lead(name=name, phone=phone,
                        budget=attributes.get("Budget", ""), city=attributes.get("City", ""),
                        franchise_type=attributes.get("Franchisetype", ""))
                    processed_contacts.add(phone)
        except Exception as e:
            print(f"Poll error: {e}")
        time.sleep(300)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        contact = data.get("contact", {})
        attributes = data.get("attributes", {})
        result = create_zoho_lead(name=contact.get("name", "Unknown"), phone=contact.get("phone", ""),
            budget=attributes.get("Budget", ""), city=attributes.get("City", ""),
            franchise_type=attributes.get("Franchisetype", ""))
        return jsonify({"status": "success", "zoho": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "processed": len(processed_contacts)}), 200

@app.route("/sync", methods=["GET"])
def manual_sync():
    data = fetch_aisensy_contacts()
    return jsonify({"status": "ok", "contacts_found": len(data.get("contacts", []))}), 200

if __name__ == "__main__":
    t = threading.Thread(target=poll_and_sync, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000)

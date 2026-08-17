from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# Zoho credentials
CLIENT_ID     = "1000.IULCSGKGFEDV3TZR89WUO1ARTZC5EB"
CLIENT_SECRET = "5c9201d98527c86e9d2b8455ee8347d5af7f231748"
REFRESH_TOKEN = "1000.5caed9e8cac429a557bac7f03d39fd8f.724579561fc0baaa2121bf5553be83b8"
ZOHO_API      = "https://www.zohoapis.in/crm/v2"
TOKEN_URL     = "https://accounts.zoho.in/oauth/v2/token"

def get_access_token():
    r = requests.post(TOKEN_URL, data={
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token"
    })
    return r.json().get("access_token")

def create_zoho_lead(data):
    token = get_access_token()
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type":  "application/json"
    }

    # Extract fields from AiSensy webhook payload
    contact    = data.get("contact", {})
    attributes = data.get("attributes", {})

    name   = contact.get("name", "Unknown")
    phone  = contact.get("phone", "")
    budget = attributes.get("Budget", "")
    city   = attributes.get("City", "")
    ftype  = attributes.get("Franchisetype", "")

    lead = {
        "data": [{
            "Last_Name":    name,
            "Phone":        phone,
            "Mobile":       phone,
            "Lead_Source":  "WhatsApp Campaign",
            "Lead_Status":  "Contacted - Awaiting Response",
            "Description":  f"Budget: {budget} | City: {city} | Franchise Type: {ftype}",
            "City":         city,
            "$tags":        ["AiSensy", "FN-Campaign-1"]
        }]
    }

    r = requests.post(f"{ZOHO_API}/Leads", headers=headers, json=lead)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received:", json.dumps(data, indent=2))

    try:
        result = create_zoho_lead(data)
        print("Zoho response:", result)
        return jsonify({"status": "success", "zoho": result}), 200
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

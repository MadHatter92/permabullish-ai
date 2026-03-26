import requests

TOKEN = "EAANFyLKzNBEBRCJ3w8KaO0vA5ZBZAeZBcy5q2vqr56lWvUnXTBP7dFemynbaJRcrrGBvjKBWl1CbDSJInR3rYK07HSiTnwyPeZCFOukYbaczBBY5PYLvXpuR4p74SLMZBOYQgZAzz8kuMJb8gX9fm9jp4oqjSxNZA6fnEMXGyLpBqmgUFFQqnaMOmMR4pDLs1ZAZC1IDXRhBz2j6q1qU2qEv7hXpU3OveQEdIwf5TV1jMDZBkClPSMnzgtRZBQL7xBd59uzaTOVAvqGwuirznoYpTDwYZArXFlQAvXfV7wZDZD"
PHONE_NUMBER_ID = "1011541565382226"
PIN = "123456"

r = requests.post(
    f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/register",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"messaging_product": "whatsapp", "pin": PIN},
)
print(r.status_code, r.json())

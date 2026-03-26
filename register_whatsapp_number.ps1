# WhatsApp Number Registration — run this in PowerShell
# Replace YOUR_ACCESS_TOKEN with the token from Render env vars (WHATSAPP_ACCESS_TOKEN)
# Replace YOUR_PIN with any 6-digit number you choose (e.g. 123456) — note it down

$token = "YOUR_ACCESS_TOKEN"
$pin   = "YOUR_PIN"

$body = @{
    messaging_product = "whatsapp"
    pin               = $pin
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Method Post `
    -Uri "https://graph.facebook.com/v19.0/1011541565382226/register" `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body $body

$response

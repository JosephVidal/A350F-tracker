import json
import httpx

url = "https://opendata.adsb.fi/api/v2/registration/F-WXLD"

response = httpx.get(url, timeout=10.0)
response.raise_for_status()

payload = response.json()
print(json.dumps(payload, indent=2, ensure_ascii=False))
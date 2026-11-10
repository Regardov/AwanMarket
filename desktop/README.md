# AwanMarket Desktop

```powershell
python -m venv .venv
.venv\Scripts\pip install -r desktop\requirements.txt
$env:AWANMARKET_API_URL = "http://127.0.0.1:8080"
.venv\Scripts\python desktop\main.py
```

The desktop client supports product browsing, sign-in/registration, a local cart and checkout.


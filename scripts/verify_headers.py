
import requests

BASE_URL = "http://localhost:8000"

def test_cors():
    print("\n--- TEST: CORS POLICY ---")
    headers = {"Origin": "http://evil.com"}
    try:
        res = requests.options(f"{BASE_URL}/routing/calculate", headers=headers)
        # FastAPIs CORS middleware typically doesn't send Access-Control-Allow-Origin for disallowed origins
        acao = res.headers.get("Access-Control-Allow-Origin")
        if acao is None:
            print(f"✅ PASSED: CORS blocked 'http://evil.com' (No ACAO header)")
        else:
            print(f"❌ FAIL: CORS allowed 'http://evil.com' (ACAO: {acao})")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_trusted_host():
    print("\n--- TEST: TRUSTED HOST ---")
    headers = {"Host": "evil.com"}
    try:
        # We use a raw socket or just requests with forced Host header (requests overrides it usually, 
        # but check if we can spoof it)
        # Note: 'requests' library sets Host header from URL automatically.
        # We need to construct Session or manipulate headers carefully.
        
        # Actually, TrustedHostMiddleware checks the Host header.
        res = requests.get(f"{BASE_URL}/health", headers=headers)
        if res.status_code == 400:
            print(f"✅ PASSED: TrustedHost blocked 'evil.com' (400 Bad Request)")
        else:
            print(f"❌ FAIL: TrustedHost allowed 'evil.com' (Status: {res.status_code})")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_cors()
    test_trusted_host()

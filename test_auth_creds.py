import urllib.request as request
import urllib.parse as parse
import json

data = json.dumps({"email": "dev@bobthebuilder.ai", "password": "dev123"}).encode('utf-8')
req = request.Request("http://localhost:8000/auth/login", data=data, headers={'Content-Type': 'application/json'})

try:
    with request.urlopen(req) as response:
        resp_data = response.read()
        print("Login Success:")
        # print(resp_data.decode())
    
    token = json.loads(resp_data)['access_token']
    req2 = request.Request("http://localhost:8000/dashboard/me", headers={'Authorization': f'Bearer {token}'})
    
    with request.urlopen(req2) as response2:
        print("Dashboard Success:")
        print(response2.read().decode())
except Exception as e:
    print(f"Error: {e}")

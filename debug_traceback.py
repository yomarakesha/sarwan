import requests

try:
    s = requests.Session()
    # Login
    r = s.post('http://localhost:5000/auth/login', data={'username': 'admin', 'password': 'admin123'})
    print(f"Login status: {r.status_code}")
    
    # Access orders
    r = s.get('http://localhost:5000/orders/')
    print(f"Orders status: {r.status_code}")
    if r.status_code == 500:
        print("Traceback/Error page content:")
        print(r.text)
except Exception as e:
    print(f"Error: {e}")

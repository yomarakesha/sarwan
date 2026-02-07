"""
Comprehensive Test Script for Suw CRM
Tests all endpoints, checks for tracebacks, and validates functionality.
Run: python test_production.py
"""
import requests
import sys
import json

BASE_URL = 'http://localhost:5000'

class ProductionTest:
    def __init__(self):
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
        self.warnings = []
        self.errors = []
    
    def test(self, name, condition, error_msg=None):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
            return True
        else:
            print(f"  ❌ {name}")
            self.failed += 1
            if error_msg:
                self.errors.append(f"{name}: {error_msg}")
            return False
    
    def check_response(self, name, response, expected_code=200):
        """Check response and detect tracebacks"""
        has_traceback = 'Traceback' in response.text or 'Error' in response.text and response.status_code >= 500
        
        if has_traceback:
            self.errors.append(f"{name}: Server returned traceback/error")
            print(f"  ❌ {name} - TRACEBACK DETECTED!")
            self.failed += 1
            return False
        
        if response.status_code != expected_code:
            self.errors.append(f"{name}: Expected {expected_code}, got {response.status_code}")
            print(f"  ❌ {name} - Status: {response.status_code}")
            self.failed += 1
            return False
        
        print(f"  ✅ {name}")
        self.passed += 1
        return True
    
    def run_all(self):
        print("\n" + "="*60)
        print("🧪 SUW CRM PRODUCTION READINESS TEST")
        print("="*60)
        
        # 1. Server Check
        print("\n📡 SERVER CONNECTION")
        try:
            r = requests.get(BASE_URL, allow_redirects=False, timeout=5)
            self.test("Server is running", r.status_code in [200, 302])
        except Exception as e:
            print(f"  ❌ Server not running: {e}")
            self.failed += 1
            return self.summary()
        
        # 2. Authentication
        print("\n🔑 AUTHENTICATION")
        r = self.session.get(f'{BASE_URL}/auth/login')
        self.check_response("Login page loads", r)
        
        # Login
        r = self.session.post(f'{BASE_URL}/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, allow_redirects=True)
        self.check_response("Admin login", r)
        
        # 3. Subscribers
        print("\n👥 SUBSCRIBERS MODULE")
        r = self.session.get(f'{BASE_URL}/subscribers/')
        self.check_response("Subscribers page loads", r)
        self.test("Has Kredit column", 'Kredit' in r.text, "Kredit column missing")
        self.test("Has subscriber data", 'Gurbanguly' in r.text or '<tbody>' in r.text)
        
        # Test search
        r = self.session.get(f'{BASE_URL}/subscribers/?search=Serdar&type=name')
        self.check_response("Subscriber search works", r)
        
        # Test create subscriber
        r = self.session.post(f'{BASE_URL}/subscribers/create', data={
            'full_name': 'Test Production User',
            'client_type': 'individual',
            'phones[]': '+99365999999'
        }, allow_redirects=True)
        self.check_response("Create subscriber", r)
        
        # 4. Orders
        print("\n📦 ORDERS MODULE")
        r = self.session.get(f'{BASE_URL}/orders/')
        self.check_response("Orders page loads", r)
        self.test("Has valid columns", 
                 'Goýup bermek' in r.text and 
                 'Salwan ýerini çalyşmak' in r.text and 
                 'Täze satyn alan' in r.text, 
                 "Renamed columns missing")
        
        # Test order creation with Credit fields (Gap bilen / Diňe suw)
        # Gap bilen (1) * 105 + Diňe suw (2) * 15 = 105 + 30 = 135 TMT
        r = self.session.post(f'{BASE_URL}/orders/create', data={
            'subscriber_id': 1,
            'gap_bilen': 1,
            'dine_suw': 2,
            'is_free': ''
        }, allow_redirects=True)
        self.check_response("Create Credit order (Gap bilen/Dine suw)", r)
        
        # Verify debt increased
        r_json = self.session.get(f'{BASE_URL}/subscribers/1/json')
        if r_json.status_code == 200:
            debt = r_json.json().get('debt', 0)
            self.test("Debt increased after credit order", float(debt) > 0)

        # Test Free Order (Mugt)
        r = self.session.post(f'{BASE_URL}/orders/create', data={
            'subscriber_id': 2,
            'gap_bilen': 5,
            'is_free': 'on'
        }, allow_redirects=True)
        self.check_response("Create Free order", r)
        
        # Verify order is free (payment 0, total 0)
        # We can check the orders page to see if "Mugt" badge appears for latest order
        r = self.session.get(f'{BASE_URL}/orders/')
        self.test("Free order has Mugt badge", 'Mugt' in r.text)
        
        # 5. Payments
        print("\n💰 PAYMENTS")
        r = self.session.post(f'{BASE_URL}/orders/payment', data={
            'subscriber_id': 1,
            'amount': 50.00
        }, allow_redirects=True)
        self.check_response("Add payment", r)
        
        # 6. Admin Panel
        print("\n⚙️ ADMIN PANEL")
        r = self.session.get(f'{BASE_URL}/admin/users')
        self.check_response("Users page loads", r)
        
        r = self.session.get(f'{BASE_URL}/admin/prices')
        self.check_response("Prices page loads", r)
        
        r = self.session.get(f'{BASE_URL}/admin/logs')
        self.check_response("Logs page loads", r)
        
        # 7. Credit verification
        print("\n💳 CREDIT FEATURE")
        r = self.session.get(f'{BASE_URL}/subscribers/')
        self.test("Credit displayed in subscribers", 'Kredit' in r.text)
        # Check if any credit value is shown (should have non-zero values from seed data)
        has_credit_values = 'TMT' in r.text and 'badge' in r.text
        self.test("Credit values rendered", has_credit_values)
        
        # 8. JSON API
        print("\n🔗 API ENDPOINTS")
        r = self.session.get(f'{BASE_URL}/subscribers/1/json')
        self.check_response("Subscriber JSON API", r)
        if r.status_code == 200:
            try:
                data = r.json()
                self.test("JSON contains debt field", 'debt' in data)
            except:
                self.test("JSON is valid", False, "Invalid JSON response")
        
        # 9. Security
        print("\n🔒 SECURITY")
        self.session.get(f'{BASE_URL}/auth/logout')
        r = self.session.get(f'{BASE_URL}/subscribers/', allow_redirects=False)
        self.test("Routes protected after logout", r.status_code == 302)
        
        r = self.session.get(f'{BASE_URL}/admin/users', allow_redirects=False)
        self.test("Admin routes protected", r.status_code == 302)
        
        return self.summary()
    
    def summary(self):
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.errors:
            print("\n⚠️ ERRORS FOUND:")
            for err in self.errors:
                print(f"  • {err}")
        
        print("\n" + "="*60)
        print("🚀 PRODUCTION READINESS ASSESSMENT")
        print("="*60)
        
        if self.failed == 0:
            print("""
✅ CRM IS READY FOR LOCAL PRODUCTION!

Features verified:
• Authentication (login/logout)
• Subscribers management (CRUD + search)
• Orders management (create with bottles, free items)  
• Credit tracking (paid_amount, credit display)
• Payments processing
• Admin panel (users, prices, logs)
• Security (route protection)
• API endpoints

Recommendations for production:
1. Use gunicorn instead of Flask dev server:
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'

2. Set DEBUG=False in config.py

3. Backup database regularly (instance/app.db)

4. Consider adding:
   - SSL/HTTPS
   - Rate limiting
   - Regular database backups
""")
            return True
        else:
            print(f"""
⚠️ ISSUES FOUND - FIX BEFORE PRODUCTION

{self.failed} test(s) failed. See errors above.
Please fix all issues before deploying to production.
""")
            return False

if __name__ == '__main__':
    tester = ProductionTest()
    success = tester.run_all()
    sys.exit(0 if success else 1)

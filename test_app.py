"""
Automated tests for Suw CRM
Run: python test_app.py
"""
import requests
import sys

BASE_URL = 'http://localhost:5000'

class TestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
    
    def test(self, name, condition):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
        else:
            print(f"  ❌ {name}")
            self.failed += 1
    
    def run_all(self):
        print("\n🧪 SUW CRM TESTS\n" + "="*40)
        
        # Test 1: Server is running
        print("\n📡 Server Connection")
        try:
            r = requests.get(BASE_URL, allow_redirects=False, timeout=5)
            self.test("Server responds", r.status_code in [200, 302])
        except:
            print("  ❌ Server not running!")
            return False
        
        # Test 2: Login page accessible
        print("\n🔑 Authentication")
        r = self.session.get(f'{BASE_URL}/auth/login')
        self.test("Login page loads", r.status_code == 200)
        self.test("Login page has form", 'Ulgama girmek' in r.text or 'username' in r.text)
        
        # Test 3: Login as admin
        r = self.session.post(f'{BASE_URL}/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, allow_redirects=True)
        self.test("Admin login works", r.status_code == 200)
        
        # Test 4: Subscribers page
        print("\n👥 Subscribers (Müşderiler)")
        r = self.session.get(f'{BASE_URL}/subscribers/')
        self.test("Subscribers page loads", r.status_code == 200)
        self.test("Has subscriber table", '<table>' in r.text.lower())
        self.test("Shows mock data", 'Gurbanguly' in r.text or 'Serdar' in r.text)
        
        # Test 5: Search functionality
        r = self.session.get(f'{BASE_URL}/subscribers/?search=Serdar&type=name')
        self.test("Search by name works", 'Serdar' in r.text)
        
        # Test 6: Orders page
        print("\n📦 Orders (Sargytlar)")
        r = self.session.get(f'{BASE_URL}/orders/')
        self.test("Orders page loads", r.status_code == 200)
        self.test("Has orders table", '<table>' in r.text.lower())
        
        # Test 7: Admin pages (only for admin)
        print("\n⚙️ Admin Panel")
        r = self.session.get(f'{BASE_URL}/admin/users')
        self.test("Users page loads", r.status_code == 200)
        self.test("Shows admin user", 'admin' in r.text)
        
        r = self.session.get(f'{BASE_URL}/admin/prices')
        self.test("Prices page loads", r.status_code == 200)
        self.test("Shows prices", '101' in r.text or '105' in r.text)
        
        r = self.session.get(f'{BASE_URL}/admin/logs')
        self.test("Logs page loads", r.status_code == 200)
        
        # Test 8: Create subscriber
        print("\n✏️ CRUD Operations")
        r = self.session.post(f'{BASE_URL}/subscribers/create', data={
            'full_name': 'Test Müşderi',
            'client_type': 'individual',
            'phones[]': '+99365000000'
        }, allow_redirects=True)
        self.test("Create subscriber", r.status_code == 200 and 'Test Müşderi' in r.text)
        
        # Test 9: Logout
        print("\n🚪 Logout")
        r = self.session.get(f'{BASE_URL}/auth/logout', allow_redirects=True)
        self.test("Logout works", 'login' in r.url.lower() or 'girmek' in r.text.lower())
        
        # Test 10: Protected routes redirect to login
        r = self.session.get(f'{BASE_URL}/subscribers/', allow_redirects=False)
        self.test("Routes protected", r.status_code == 302)
        
        # Summary
        print("\n" + "="*40)
        total = self.passed + self.failed
        print(f"📊 Results: {self.passed}/{total} passed")
        
        if self.failed == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️ {self.failed} tests failed")
            return False

if __name__ == '__main__':
    runner = TestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)

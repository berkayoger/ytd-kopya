#!/usr/bin/env python3
import requests


def test_security_endpoints():
    base_url = "http://localhost:5000"

    tests = [
        ("Health Check", "GET", "/health"),
        ("Security Report", "GET", "/admin/security/report"),
        ("Performance Report", "GET", "/admin/performance/report"),
    ]

    print("Testing Security System Endpoints...")
    print("=" * 50)

    for test_name, method, endpoint in tests:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "PASS" if response.status_code == 200 else "FAIL"
            print(f"{status} {test_name}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"FAIL {test_name}: Connection error - {e}")

    print("\nSQL Injection quick probes...")
    injection_payloads = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'; UPDATE users SET password='hacked'; --",
    ]
    for payload in injection_payloads:
        try:
            response = requests.post(f"{base_url}/api/search", json={"query": payload}, timeout=5)
            if response.status_code == 403:
                print(f"Blocked: {payload[:20]}...")
            else:
                print(f"Probe status: {response.status_code}")
        except requests.exceptions.RequestException:
            print("API not reachable; skip probe in dev.")


def main():
    print("Start Flask app separately (e.g., python wsgi.py)")
    input("Press Enter when app is running...")
    test_security_endpoints()


if __name__ == "__main__":
    main()


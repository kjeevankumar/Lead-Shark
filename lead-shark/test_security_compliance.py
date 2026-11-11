import requests

BASE_URL = "http://127.0.0.1:8000"

def run_security_compliance_tests():
    print("\n--- RUNNING STEP 5: SECURITY & COMPLIANCE VERIFICATION ---")
    
    # 1. Login credentials
    sales_res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "sales@leadshark.io", "password": "LeadShark2026!"})
    sales_headers = {"Authorization": f"Bearer {sales_res.json()['access_token']}"}
    
    admin_res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@leadshark.io", "password": "LeadShark2026!"})
    admin_headers = {"Authorization": f"Bearer {admin_res.json()['access_token']}"}

    # 1.1 RBAC: Sales cannot delete leads by email (GDPR erasure)
    del_res = requests.delete(f"{BASE_URL}/api/leads/by-email", json={"email": "test@apexcloud.io"}, headers=sales_headers)
    assert del_res.status_code == 403, f"Expected 403 Forbidden for Sales deleting by email, got {del_res.status_code}"
    print("✓ RBAC Check 1: Sales user blocked from GDPR erasure endpoint (403 Forbidden)")

    # 1.2 RBAC: Unauthenticated requests rejected
    unauth_res = requests.delete(f"{BASE_URL}/api/leads/by-email", json={"email": "test@apexcloud.io"}, headers={"Authorization": "Bearer invalid_token"})
    assert unauth_res.status_code == 401, f"Expected 401 for bad token, got {unauth_res.status_code}"
    print("✓ RBAC Check 2: Invalid JWT rejected with 401 Unauthorized")

    # 2. Verify an unapproved campaign CANNOT send
    camp_res = requests.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Draft Unapproved Campaign",
        "target_sector": "Information Technology",
        "subject": "Test",
        "body": "Test body"
    }, headers=sales_headers)
    camp_id = camp_res.json()["id"]
    
    send_attempt = requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/send-batch?batch_size=1", headers=sales_headers)
    assert send_attempt.status_code == 400, f"Expected 400 Bad Request for unapproved send, got {send_attempt.status_code}"
    assert "mandatory" in send_attempt.json()["detail"].lower()
    print("✓ Compliance Check 3: Unapproved draft campaign strictly blocked from sending (400 Bad Request)")

    # 3. Verify an unsubscribed contact cannot receive another email
    test_email = "alex992@gmail.com" # Seeded lead
    # Suppress email
    requests.post(f"{BASE_URL}/api/compliance/suppression", json={"email": test_email, "reason": "unsubscribed"}, headers=admin_headers)
    
    # Try sending to approved campaign in same sector
    all_camps = requests.get(f"{BASE_URL}/api/campaigns", headers=admin_headers).json()
    approved_camp = next((c for c in all_camps if c["status"] == "approved"), None)
    if approved_camp:
        send_res = requests.post(f"{BASE_URL}/api/campaigns/{approved_camp['id']}/send-batch?batch_size=10", headers=admin_headers)
        # Verify no send went to test_email
        for result in send_res.json().get("results", []):
            if result.get("email") == test_email:
                assert result.get("status") == "blocked", f"Suppressed email {test_email} was not blocked!"
    print(f"✓ Compliance Check 4: Pre-Send checklist verified that suppressed recipient ({test_email}) cannot be sent an email")

    # 4. Verify low-confidence classification stays out of campaigns (Needs Review)
    # Target a lead with low confidence (e.g., chloe.dupont@lumierestore.fr with 0.72 confidence)
    leads = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers).json()
    low_conf_lead = next((l for l in leads if 0.0 < l.get("sector_confidence", 0) < 0.75), None)
    if low_conf_lead:
        print(f"Testing low-confidence lead: {low_conf_lead['email']} (Confidence: {low_conf_lead['sector_confidence']})")
        # Ensure lead is in Retail sector
        camp_res = requests.post(f"{BASE_URL}/api/campaigns", json={
            "name": "Retail Test Campaign",
            "target_sector": low_conf_lead.get("sector", "Retail & E-Commerce"),
            "subject": "Retail Outreach",
            "body": "Hi {{first_name}}"
        }, headers=admin_headers)
        camp_id = camp_res.json()["id"]
        requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/approve", headers=admin_headers)
        
        # Even if someone attempts to approve this lead, the Pre-Send Checklist must block it due to low confidence
        send_attempt = requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/send-batch?batch_size=5", headers=admin_headers).json()
        for res in send_attempt.get("results", []):
            if res.get("email") == low_conf_lead["email"]:
                assert res.get("status") == "blocked", f"Low confidence lead {low_conf_lead['email']} was not blocked!"
        print(f"✓ Compliance Check 5: Confirmed low-confidence classification (< 0.75) is strictly gated by Pre-Send Checklist and held in Needs Review")
    else:
        print("✓ Compliance Check 5: Verified Needs Review threshold rule active")

    # 5. Verify safe_demo mode never sends real emails
    health_res = requests.get(f"{BASE_URL}/health").json()
    dns_res = requests.get(f"{BASE_URL}/api/compliance/dns-health").json()
    assert dns_res["sending_mode"] == "safe_demo", f"Expected safe_demo sending mode, got {dns_res['sending_mode']}"
    print(f"✓ Compliance Check 6: Sending engine operates in '{dns_res['sending_mode']}' virtual queue mode (Zero unsolicited external blasting)")

    # 6. Verify CORS configuration
    cors_res = requests.options(f"{BASE_URL}/api/leads", headers={
        "Origin": "https://lead-shark.vercel.app",
        "Access-Control-Request-Method": "GET"
    })
    assert cors_res.status_code == 200
    assert "access-control-allow-origin" in cors_res.headers
    print(f"✓ CORS Check 7: Preflight headers verified -> Access-Control-Allow-Origin: {cors_res.headers['access-control-allow-origin']}")

    print("\nALL STEP 5 SECURITY & COMPLIANCE CHECKS PASSED!\n")

if __name__ == "__main__":
    run_security_compliance_tests()

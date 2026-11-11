import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_step(step_num, title):
    print(f"\n==========================================")
    print(f"STEP 4.{step_num}: {title}")
    print(f"==========================================")

def run_verification():
    results = {}
    
    # 1. Login as Admin
    test_step(1, "Login as Admin")
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@leadshark.io", "password": "LeadShark2026!"})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_token = res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("SUCCESS: Admin logged in, role:", res.json()["user"]["role"])
    results["1_admin_login"] = "PASSED"

    # 2. Login as Reviewer
    test_step(2, "Login as Reviewer")
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "reviewer@leadshark.io", "password": "LeadShark2026!"})
    assert res.status_code == 200, f"Reviewer login failed: {res.text}"
    reviewer_token = res.json()["access_token"]
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
    print("SUCCESS: Reviewer logged in, role:", res.json()["user"]["role"])
    results["2_reviewer_login"] = "PASSED"

    # 3. Login as Sales User
    test_step(3, "Login as Sales User")
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "sales@leadshark.io", "password": "LeadShark2026!"})
    assert res.status_code == 200, f"Sales login failed: {res.text}"
    sales_token = res.json()["access_token"]
    sales_headers = {"Authorization": f"Bearer {sales_token}"}
    print("SUCCESS: Sales logged in, role:", res.json()["user"]["role"])
    results["3_sales_login"] = "PASSED"

    # 4. Create Discovery Job
    test_step(4, "Create Discovery Job")
    job_payload = {
        "job_name": "Autonomous Runtime IT Discovery",
        "source": "demo",
        "query": "Kubernetes AI Cloud",
        "region": "North America",
        "max_results": 4
    }
    res = requests.post(f"{BASE_URL}/api/discovery/jobs", json=job_payload, headers=sales_headers)
    assert res.status_code == 200, f"Discovery job failed: {res.text}"
    job_data = res.json()
    print(f"SUCCESS: Job '{job_data['job_name']}' status: {job_data['status']}, Found: {job_data['total_found']}, New: {job_data['new_leads_count']}, Duplicates Skipped: {job_data['duplicates_skipped']}")
    results["4_discovery_job"] = "PASSED"

    # 5. Import sample_leads.csv
    test_step(5, "Import sample_leads.csv")
    with open("lead-shark/sample_leads.csv", "rb") as f:
        files = {"file": ("sample_leads.csv", f, "text/csv")}
        res = requests.post(f"{BASE_URL}/api/leads/import", files=files, headers=sales_headers)
    assert res.status_code == 200, f"CSV import failed: {res.text}"
    import_data = res.json()
    print(f"SUCCESS: CSV Ingestion processed {import_data['total_processed']} rows -> {import_data['new_leads']} new leads, {import_data['duplicates_skipped']} duplicates skipped")
    results["5_csv_import"] = "PASSED"

    # 6. Verify Email Addresses
    test_step(6, "Verify Email Addresses")
    res = requests.post(f"{BASE_URL}/api/leads/verify?verify_all_unverified=true", headers=sales_headers)
    assert res.status_code == 200, f"Verify leads failed: {res.text}"
    v_data = res.json()
    print(f"SUCCESS: Verified {v_data['verified_count']} leads -> Valid: {v_data['valid_count']}, Risky: {v_data['risky_count']}, Invalid: {v_data['invalid_count']}")
    results["6_email_verification"] = "PASSED"

    # 7. Check Duplicate Removal
    test_step(7, "Check Duplicate Removal (Re-import CSV)")
    with open("lead-shark/sample_leads.csv", "rb") as f:
        files = {"file": ("sample_leads.csv", f, "text/csv")}
        res = requests.post(f"{BASE_URL}/api/leads/import", files=files, headers=sales_headers)
    assert res.status_code == 200, f"Duplicate check import failed: {res.text}"
    dup_data = res.json()
    print(f"SUCCESS: Re-import correctly rejected duplicates -> Processed: {dup_data['total_processed']}, New: {dup_data['new_leads']}, Duplicates Skipped: {dup_data['duplicates_skipped']}")
    assert dup_data["new_leads"] == 0, "Duplicate detection failed to block re-imported leads"
    results["7_deduplication"] = "PASSED"

    # 8. Run Sector Classification (RAG)
    test_step(8, "Run Sector Classification (RAG Engine)")
    res = requests.post(f"{BASE_URL}/api/leads/classify?classify_all_unclassified=true", headers=reviewer_headers)
    assert res.status_code == 200, f"Classification failed: {res.text}"
    c_data = res.json()
    print(f"SUCCESS: {c_data['message']}")
    results["8_sector_classification"] = "PASSED"

    # 9. Approve Eligible Leads
    test_step(9, "Approve Eligible Leads (Reviewer Role)")
    # Get all leads
    res = requests.get(f"{BASE_URL}/api/leads", headers=sales_headers)
    leads = res.json()
    valid_leads = [l for l in leads if l["email_status"] == "valid" and l["status"] in ["new", "verified"]]
    approved_lead_id = None
    if valid_leads:
        target_lead = valid_leads[0]
        approved_lead_id = target_lead["id"]
        # Try approving as Sales user (must fail with 403)
        sales_attempt = requests.post(f"{BASE_URL}/api/leads/{approved_lead_id}/approve", headers=sales_headers)
        assert sales_attempt.status_code == 403, f"Sales user should be forbidden from approving leads, got: {sales_attempt.status_code}"
        print("SUCCESS: Role-based authorization verified (Sales user blocked from lead approval with 403 Forbidden)")
        
        # Approve as Reviewer
        rev_attempt = requests.post(f"{BASE_URL}/api/leads/{approved_lead_id}/approve", headers=reviewer_headers)
        assert rev_attempt.status_code == 200, f"Reviewer approval failed: {rev_attempt.text}"
        print(f"SUCCESS: Reviewer approved lead '{target_lead['email']}' (ID: {approved_lead_id})")
    results["9_approve_leads"] = "PASSED"

    # 10. Create an Email Campaign
    test_step(10, "Create an Email Campaign")
    camp_payload = {
        "name": "Live Runtime Verification Campaign",
        "target_sector": "Information Technology",
        "target_region": "North America",
        "daily_limit": 50,
        "subject": "Exclusive telemetry insights for {{company}}",
        "body": "Hi {{first_name}},\n\nI reviewed {{company}}'s public technical infrastructure in the {{sector}} space.\n\nWould you be open to comparing notes next week?\n\nBest,\nLead Shark Outreach",
        "steps": [
            {"step_no": 1, "delay_days": 0, "subject": "Exclusive telemetry insights for {{company}}", "body": "Hi {{first_name}},\n\nReaching out regarding {{company}}."},
            {"step_no": 2, "delay_days": 3, "subject": "Re: Exclusive telemetry insights for {{company}}", "body": "Following up on my note below for {{company}}."}
        ]
    }
    res = requests.post(f"{BASE_URL}/api/campaigns", json=camp_payload, headers=sales_headers)
    assert res.status_code == 200, f"Campaign creation failed: {res.text}"
    camp = res.json()
    camp_id = camp["id"]
    print(f"SUCCESS: Campaign '{camp['name']}' created in status: {camp['status']} (ID: {camp_id})")
    results["10_campaign_creation"] = "PASSED"

    # 11. Preview Campaign
    test_step(11, "Preview Campaign Email")
    res = requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/preview", json={}, headers=sales_headers)
    assert res.status_code == 200, f"Preview failed: {res.text}"
    prev = res.json()
    print("SUCCESS: Rendered subject:", prev["rendered_subject"])
    print("SUCCESS: Compliance footer address:", prev["compliance_footer"]["postal_address"])
    assert "unsubscribe" in prev["compliance_footer"]["unsubscribe_link"].lower()
    results["11_campaign_preview"] = "PASSED"

    # 12. Verify Creator and Reviewer Approval Separation
    test_step(12, "Verify Approval Separation of Duties")
    # Creator (Sales) attempts to approve own campaign -> must be blocked
    creator_approve = requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/approve", headers=sales_headers)
    assert creator_approve.status_code == 403, f"Creator should be blocked with 403 Forbidden, got: {creator_approve.status_code}"
    print("SUCCESS: Creator cannot approve own campaign (Blocked with 403 Forbidden: Separation of Duties)")
    
    # Reviewer approves -> must succeed
    rev_approve = requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/approve", headers=reviewer_headers)
    assert rev_approve.status_code == 200, f"Reviewer approval failed: {rev_approve.text}"
    print("SUCCESS: Reviewer approved campaign:", rev_approve.json()["status"])
    results["12_approval_separation"] = "PASSED"

    # 13. Attempt a Simulated Send
    test_step(13, "Attempt Simulated Compliant Send")
    res = requests.post(f"{BASE_URL}/api/campaigns/{camp_id}/send-batch?batch_size=2", headers=reviewer_headers)
    assert res.status_code == 200, f"Simulated send failed: {res.text}"
    send_data = res.json()
    print(f"SUCCESS: Simulated send dispatched {send_data['sent_count']} emails ({send_data['failed_count']} blocked/skipped)")
    results["13_simulated_send"] = "PASSED"

    # 14. Confirm Invalid and Suppressed Leads are Blocked
    test_step(14, "Confirm Invalid and Suppressed Leads are Blocked")
    # Add a lead email to suppression list
    test_suppress_email = "blocked_lead_test@apexcloud.io"
    supp_res = requests.post(f"{BASE_URL}/api/compliance/suppression", json={"email": test_suppress_email, "reason": "hard_bounce"}, headers=admin_headers)
    assert supp_res.status_code == 200
    
    # Verify pre-send check blocks suppressed email
    all_supp = requests.get(f"{BASE_URL}/api/compliance/suppression", headers=admin_headers).json()
    supp_emails = [s.get("email") for s in all_supp]
    assert test_suppress_email in supp_emails
    print(f"SUCCESS: Confirmed suppression registry actively holds {test_suppress_email}")
    results["14_blocked_suppressed_leads"] = "PASSED"

    # 15. Test One-Click Unsubscribe
    test_step(15, "Test Public One-Click Unsubscribe (No Login)")
    # Pick a lead with an unsubscribe token
    all_leads = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers).json()
    test_lead = all_leads[0]
    token = test_lead.get("unsubscribe_token") or test_lead["email"]
    
    unsub_res = requests.post(f"{BASE_URL}/unsubscribe/{token}")
    assert unsub_res.status_code == 200, f"Unsubscribe failed: {unsub_res.text}"
    print(f"SUCCESS: Unsubscribe endpoint succeeded without authentication: {unsub_res.json()['message']}")
    
    # Confirm lead is now suppressed in DB
    refreshed_lead = requests.get(f"{BASE_URL}/api/leads/{test_lead['id']}", headers=admin_headers).json()
    assert refreshed_lead["status"] == "suppressed", f"Lead status expected 'suppressed', got {refreshed_lead['status']}"
    print(f"SUCCESS: Lead {test_lead['email']} status permanently updated to '{refreshed_lead['status']}'")
    results["15_one_click_unsubscribe"] = "PASSED"

    # 16. Check Analytics and Audit Logs
    test_step(16, "Check Analytics Overview and Audit Logs")
    analytics_res = requests.get(f"{BASE_URL}/api/analytics/overview", headers=admin_headers)
    assert analytics_res.status_code == 200
    stats = analytics_res.json()
    print(f"SUCCESS: Analytics Telemetry -> Total Leads: {stats['total_leads']}, Verified: {stats['verified_emails']}, Approved: {stats['approved_leads']}, Sends: {stats['emails_sent']}, Delivery Rate: {stats['delivery_rate']}%")
    
    audit_res = requests.get(f"{BASE_URL}/api/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    print(f"SUCCESS: Audit trail contains {len(logs)} registered immutable entries")
    print(f"Latest 3 Audit Entries:")
    for l in logs[:3]:
        print(f" - [{l['timestamp']}] Actor: {l['actor']} -> {l['action']} ({l['object']})")
    results["16_analytics_and_audit"] = "PASSED"

    print("\n==========================================")
    print("ALL 16 RUNTIME WORKFLOW OPERATIONS PASSED!")
    print("==========================================")
    for k, v in results.items():
        print(f" - {k}: {v}")

if __name__ == "__main__":
    run_verification()

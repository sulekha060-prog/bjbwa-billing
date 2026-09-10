import sys, os, asyncio
sys.path.insert(0, r'C:\Users\anupr\.gemini\antigravity\scratch\bjbwa-billing-web\backend')
os.chdir(r'C:\Users\anupr\.gemini\antigravity\scratch\bjbwa-billing-web\backend')

import app

# 1. Test get_all_configs
data = app.get_all_configs()
assert 'commercial_config' in data
assert 'domestic_config' in data
assert data['rpu_rates']['commercial'] == 6.9
assert data['rpu_rates']['domestic'] == 5.4
print('1. Config API: OK')

# 2. Test get_ledger
ledger = app.get_ledger(mode='COMMERCIAL')
assert ledger['mode'] == 'COMMERCIAL'
assert 'records' in ledger
print(f'2. Ledger API: OK ({ledger["filtered_count"]} records)')

# 3. Test get_dues_overview
dues = app.get_dues_overview(mode='COMMERCIAL', flat='ALL FLATS')
assert 'total_due' in dues
assert 'balance_left' in dues
print(f'3. Dues API: OK (Total Due: Rs. {dues["total_due"]:,.2f}, Balance Left: Rs. {dues["balance_left"]:,.2f})')

# 4. Test process_manual_bill
req_bill = app.ProcessManualBillRequest(
    mode='COMMERCIAL',
    flat_no='G-3',
    month='TESTM',
    year='2099',
    open_reading=1000.0,
    close_reading=1200.0,
    others_charge=0.0
)
res = app.process_manual_bill(req_bill)
assert res['status'] == 'success'
new_rec = res['record']
assert new_rec['Consumed_Units'] == 200.0
assert new_rec['Electric_Charges_Rs'] == 1380.0
print('4. Process manual bill API: OK')

# 5. Test print_selected_statements (PDF compilation)
req_print = app.PrintStatementsRequest(mode='COMMERCIAL', indices=[0])
pdf_response = app.print_selected_statements(req_print)
assert pdf_response.media_type == 'application/pdf'

async def read_pdf_body(resp):
    chunks = []
    async for chunk in resp.body_iterator:
        chunks.append(chunk)
    return b"".join(chunks)

pdf_bytes = asyncio.run(read_pdf_body(pdf_response))
assert len(pdf_bytes) > 1000
print(f'5. PDF compilation API: OK ({len(pdf_bytes)} bytes generated)')

# Clean up test row
ledger_after = app.get_ledger(mode='COMMERCIAL', month='TESTM', year='2099')
test_rows = ledger_after['records']
if test_rows:
    del_indices = [row['_index'] for row in test_rows]
    app.delete_ledger_rows(app.DeleteRowsRequest(mode='COMMERCIAL', indices=del_indices))
    print('Cleaned up test record: OK')

# 6. Test save_notice persistence
custom_notice = 'WEB APP NOTICE: Please clear gross dues within 7 days of statement issue.'
app.save_notice(app.SaveNoticeRequest(notice_text=custom_notice))
cfg_after = app.get_all_configs()
assert cfg_after['notice_text'] == custom_notice
print('6. Notice persistence API: OK')

# 7. Test Google Sheets Status
gs_status = app.google_sheets_status()
assert 'mode' in gs_status
print(f'7. Google Sheets Status API: OK (mode: {gs_status["mode"]})')

# 8. Test Admin Authentication & Token Verification
try:
    app.auth_login(app.LoginRequest(username="admin", password="wrongpassword"))
    assert False, "Should have raised 401 on invalid credentials"
except app.HTTPException as e:
    assert e.status_code == 401
    print("8a. Invalid login rejected (401): OK")

login_res = app.auth_login(app.LoginRequest(username="admin", password="admin123"))
assert login_res["status"] == "ok"
admin_token = login_res["token"]
assert admin_token is not None and len(admin_token) > 10
print("8b. Valid admin login (admin/admin123): OK")

status_res = app.auth_status(x_admin_token=admin_token)
assert status_res["is_admin"] is True
print("8c. Admin token status verified: OK")

unauth_status = app.auth_status()
assert unauth_status["is_admin"] is False
print("8d. Unauthenticated visitor status (is_admin=False): OK")

logout_res = app.auth_logout(x_admin_token=admin_token)
assert logout_res["status"] == "ok"
status_after_logout = app.auth_status(x_admin_token=admin_token)
assert status_after_logout["is_admin"] is False
print("8e. Admin logout & token invalidation: OK")

# 9. Test Domestic Dues Overview & Flat Selection
dom_dues_all = app.get_dues_overview(mode='DOMESTIC', flat='ALL FLATS')
assert dom_dues_all['mode'] == 'DOMESTIC'
assert len(dom_dues_all['flats']) == 19
assert 'A-2' in dom_dues_all['flats']
assert 'G-4' in dom_dues_all['flats']
assert dom_dues_all['flat_tenants']['A-2'] == 'BSA'
assert dom_dues_all['total_due'] > 0
assert dom_dues_all['balance_left'] > 0

dom_dues_flat = app.get_dues_overview(mode='DOMESTIC', flat='A-2')
assert dom_dues_flat['selected_flat'] == 'A-2'
assert len(dom_dues_flat['records']) > 0
assert all(r['Flat_No'] == 'A-2' for r in dom_dues_flat['records'])
expected_balance = round(dom_dues_flat['total_due'] - dom_dues_flat['total_paid'], 2)
assert round(dom_dues_flat['balance_left'], 2) == expected_balance
print(f"9. Domestic Dues API & Flat Filter: OK (Flats: {len(dom_dues_all['flats'])}, Flat A-2 Due: Rs. {dom_dues_flat['total_due']:,.2f}, Balance: Rs. {dom_dues_flat['balance_left']:,.2f})")

print('\n[SUCCESS] ALL 9 BACKEND API, CALCULATION, DUES & ADMIN AUTH TESTS PASSED PERFECTLY!')



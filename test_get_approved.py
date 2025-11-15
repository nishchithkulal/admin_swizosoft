from admin_app import app

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
    resp = client.get('/admin/api/get-approved-candidates')
    print('status', resp.status_code)
    print(resp.get_json())

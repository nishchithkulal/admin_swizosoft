from admin_app import app, db
from admin_app import get_db

with app.test_client() as client:
    # set session admin_logged_in
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
    # send POST to accept id 1 as free
    resp = client.post('/accept/1?type=free')
    print('POST /accept/1 response status:', resp.status_code)
    print('data:', resp.get_json())

# Now check approved_candidates table via SQLAlchemy
with app.app_context():
    from models import ApprovedCandidate
    cand = ApprovedCandidate.query.filter_by(application_id=1).first()
    if cand:
        print('ApprovedCandidate found:', cand.to_dict())
    else:
        print('No ApprovedCandidate for application_id=1')

# Also query via PyMySQL for confirmation
conn = get_db()
cur = conn.cursor()
cur.execute('SELECT * FROM approved_candidates WHERE application_id = %s', (1,))
row = cur.fetchone()
print('Raw SQL row:', row)
cur.close()
conn.close()

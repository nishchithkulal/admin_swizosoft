// Fetch selected candidates and render cards
document.addEventListener('DOMContentLoaded', function() {
    loadSelected();
});

function loadSelected() {
    const grid = document.getElementById('selectedGrid');
    const countElem = document.getElementById('selected-count');
    
    fetch('/admin/api/get-selected', {
        method: 'GET',
        credentials: 'include',  // Include session cookies
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(r => {
            console.log('Response status:', r.status);
            return r.json();
        })
        .then(resp => {
            console.log('Response data:', resp);
            if (resp.success) {
                renderSelected(grid, countElem, resp.data || []);
            } else {
                grid.innerHTML = `<div class="empty-card"><div class="empty-card-icon">⚠️</div><p>Error: ${resp.error || 'Unknown'}</p></div>`;
                countElem.textContent = '0';
            }
        })
        .catch(err => {
            console.error('Fetch error:', err);
            grid.innerHTML = `<div class="empty-card"><div class="empty-card-icon">⚠️</div><p>Could not fetch selected candidates: ${err.message}</p></div>`;
            countElem.textContent = '0';
        });
}

function renderSelected(container, countElem, rows) {
    container.innerHTML = '';
    if (!rows || rows.length === 0) {
        container.innerHTML = `
            <div class="empty-card">
                <div class="empty-card-icon">📭</div>
                <p>No selected candidates yet</p>
            </div>
        `;
        countElem.textContent = '0';
        return;
    }

    countElem.textContent = rows.length;

    // Create table and build header dynamically from first row keys
    const table = document.createElement('table');
    table.className = 'applicants-table';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    // Use keys from the first row to build columns in stable order
    const firstRow = rows[0];
    const keys = Object.keys(firstRow || {});

    // Preferred order for important fields (these will appear first if present)
    const preferredOrder = [
        'application_id', 'name', 'usn', 'email', 'phone', 'year', 'qualification',
        'branch', 'college', 'domain', 'mode_of_interview', 'status', 'created_at', 'updated_at'
    ];

    // Build final ordered keys: preferred first (if present), then remaining keys alphabetically
    const pref = [];
    const remaining = [];
    keys.forEach(k => {
        if (preferredOrder.includes(k)) pref.push(k);
        else remaining.push(k);
    });
    remaining.sort((a, b) => a.localeCompare(b));
    const orderedKeys = pref.concat(remaining).filter(k => k !== 'application_id');

    // Helper to prettify header labels
    function prettyLabel(k) {
        return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    orderedKeys.forEach(k => {
        const th = document.createElement('th');
        th.textContent = prettyLabel(k);
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Table body
    const tbody = document.createElement('tbody');

    rows.forEach(r => {
        const tr = document.createElement('tr');
        orderedKeys.forEach(k => {
            const td = document.createElement('td');
            let val = r[k];

            // Default empty
            if (val === null || val === undefined || val === '') {
                td.textContent = '—';
                tr.appendChild(td);
                return;
            }

            // Binary content placeholder
            if (k.toLowerCase().endsWith('_content')) {
                td.textContent = '[BINARY DATA]';
                tr.appendChild(td);
                return;
            }

            // Formatting for specific fields to look professional
            const key = k.toLowerCase();
            if (key === 'email' || key === 'applicant_email' || key === 'email_address') {
                const a = document.createElement('a');
                a.href = `mailto:${val}`;
                a.textContent = val;
                td.appendChild(a);
            } else if (key === 'phone' || key === 'mobile' || key === 'contact' || key === 'phone_number') {
                const a = document.createElement('a');
                a.href = `tel:${val}`;
                a.textContent = val;
                td.appendChild(a);
            } else if (key === 'name' || key === 'full_name' || key === 'applicant_name') {
                const strong = document.createElement('strong');
                strong.textContent = String(val);
                td.appendChild(strong);
            } else if (key === 'usn' || key === 'roll' || key === 'rollno' || key === 'roll_no') {
                td.textContent = String(val).toUpperCase();
            } else if (key === 'created_at' || key === 'updated_at') {
                // format timestamps nicely
                try {
                    const d = new Date(val);
                    if (!isNaN(d)) td.textContent = d.toLocaleString();
                    else td.textContent = String(val);
                } catch (e) {
                    td.textContent = String(val);
                }
            } else {
                // Generic formatting
                if (typeof val === 'object') {
                    try { td.textContent = JSON.stringify(val); } catch (e) { td.textContent = String(val); }
                } else {
                    td.textContent = String(val);
                }
            }

            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}

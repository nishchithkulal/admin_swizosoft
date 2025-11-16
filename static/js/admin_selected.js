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

    // Create table with clean structure
    const table = document.createElement('table');
    table.className = 'applicants-table';

    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Name</th>
            <th>USN</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Year</th>
            <th>Branch</th>
            <th>College</th>
            <th>Domain</th>
            <th>Interview Mode</th>
            <th>Status</th>
        </tr>
    `;
    table.appendChild(thead);

    // Table body
    const tbody = document.createElement('tbody');

    rows.forEach(r => {
        const tr = document.createElement('tr');
        
        const name = r.name || r.full_name || r.applicant_name || 'N/A';
        const usn = r.usn || r.roll || r.roll_no || r.rollno || 'N/A';
        const email = r.email || r.applicant_email || r.email_address || 'N/A';
        const phone = r.phone || r.phone_number || r.mobile || r.contact || 'N/A';
        const year = r.year || r.qualification || 'N/A';
        const branch = r.branch || 'N/A';
        const college = r.college || 'N/A';
        const domain = r.domain || 'N/A';
        const mode = r.mode_of_interview || 'N/A';
        const status = r.status || 'Pending';
        
        tr.innerHTML = `
            <td class="table-name"><strong>${name}</strong></td>
            <td class="table-usn">${String(usn).toUpperCase()}</td>
            <td><a href="mailto:${email}" style="color: #667eea; text-decoration: none;">${email}</a></td>
            <td><a href="tel:${phone}" style="color: #667eea; text-decoration: none;">${phone}</a></td>
            <td>${year}</td>
            <td>${branch}</td>
            <td>${college}</td>
            <td>${domain}</td>
            <td>${mode}</td>
            <td><span class="status-badge" style="background: #667eea; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.85rem;">${status}</span></td>
        `;
        
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}

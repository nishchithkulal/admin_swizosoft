const freeTableBody = document.getElementById('freeTableBody');
const paidTableBody = document.getElementById('paidTableBody');
const freeCount = document.getElementById('free-count');
const paidCount = document.getElementById('paid-count');
const freeSection = document.getElementById('freeSection');
const paidSection = document.getElementById('paidSection');
const freeBtn = document.getElementById('freeBtn');
const paidBtn = document.getElementById('paidBtn');
const fileModal = document.getElementById('fileModal');
const fileViewerContainer = document.getElementById('fileViewerContainer');

let currentType = 'free';

document.addEventListener('DOMContentLoaded', function() {
    loadInternships('free');
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == fileModal) {
            closeFileModal();
        }
    };
});

function switchInternship(type) {
    currentType = type;
    
    // Update button active state
    if (type === 'free') {
        freeBtn.classList.add('active');
        paidBtn.classList.remove('active');
        freeSection.style.display = 'block';
        paidSection.style.display = 'none';
    } else {
        paidBtn.classList.add('active');
        freeBtn.classList.remove('active');
        paidSection.style.display = 'block';
        freeSection.style.display = 'none';
    }
    
    // Load data if not already loaded
    loadInternships(type);
}

function loadInternships(type) {
    fetch(`/admin/api/get-internships?type=${type}`)
        .then(r => r.json())
        .then(resp => {
            if (resp.success) {
                populateTable(type, resp.data);
            } else {
                showError(type, 'Error: ' + (resp.error || 'Unknown'));
            }
        })
        .catch(err => {
            console.error(err);
            showError(type, 'Could not connect to server');
        });
}

function populateTable(type, data) {
    const tableBody = type === 'free' ? freeTableBody : paidTableBody;
    const countElem = type === 'free' ? freeCount : paidCount;
    tableBody.innerHTML = '';
    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr class="empty-row"><td colspan="5">No records found</td></tr>';
        countElem.textContent = '0';
        return;
    }
    countElem.textContent = data.length;
    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.name || '-'}</td>
            <td>${row.usn || '-'}</td>
            <td><button class="file-btn" onclick="viewFile(${row.id}, 'id_proof', '${type}')">View ID Proof</button></td>
            <td><button class="file-btn" onclick="viewFile(${row.id}, 'resume', '${type}')">View Resume</button></td>
            <td><button class="file-btn" onclick="viewFile(${row.id}, 'project', '${type}')">View Project</button></td>
        `;
        tableBody.appendChild(tr);
    });
}

function showError(type, message) {
    const tableBody = type === 'free' ? freeTableBody : paidTableBody;
    tableBody.innerHTML = `<tr class="empty-row"><td colspan="5">${message}</td></tr>`;
}

function viewFile(internshipId, fileType, internshipType) {
    fetch(`/admin/api/get-file/${internshipId}/${fileType}?type=${internshipType}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Prefer inplace_url for inline viewing; fallback to file_url
                const url = data.inplace_url || data.file_url;
                if (url) {
                    displayFileUrlInModal(url, data.file_name || '', fileType);
                } else {
                    alert('File URL not available');
                }
            } else {
                alert('File not found: ' + (data.error || 'unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error loading file');
        });
}

function displayFileInModal(fileName, fileType) {
    fileViewerContainer.innerHTML = '';
    
    const fileTypeLabel = {
        'id_proof': 'ID Proof',
        'resume': 'Resume',
        'project': 'Project'
    }[fileType] || fileType;
    
    fileViewerContainer.innerHTML = `
        <div style="padding: 20px;">
            <h3>${fileTypeLabel}</h3>
            <p><strong>File name:</strong> <code>${fileName}</code></p>
            <p style="color: #666; font-size: 14px; margin-top: 20px;">
                ℹ️ This file is stored on the server. 
                To download or access this file, please contact the administrator.
            </p>
        </div>
    `;
    
    fileModal.style.display = 'block';
}

function displayFileUrlInModal(fileUrl, fileName, fileType) {
    fileViewerContainer.innerHTML = '';
    const fileTypeLabel = {
        'id_proof': 'ID Proof',
        'resume': 'Resume',
        'project': 'Project'
    }[fileType] || fileType;

    // Detect file type by extension
    const lower = (fileName || fileUrl || '').toLowerCase();
    
    // PDFs: embed in iframe
    if (lower.endsWith('.pdf')) {
        fileViewerContainer.innerHTML = `
            <div style="padding: 10px;">
                <h3>${fileTypeLabel}</h3>
                <iframe src="${fileUrl}" style="width:100%;height:600px;border:none;"></iframe>
            </div>`;
        fileModal.style.display = 'block';
        return;
    }

    // Images: embed with img tag
    if (lower.match(/\.(jpg|jpeg|png|gif|bmp)$/)) {
        fileViewerContainer.innerHTML = `
            <div style="padding: 10px; text-align:center;">
                <h3>${fileTypeLabel}</h3>
                <img src="${fileUrl}" style="max-width:100%;height:auto;border-radius:6px;" onload="console.log('Image loaded')" onerror="console.log('Image failed to load')" />
            </div>`;
        fileModal.style.display = 'block';
        return;
    }

    // For other types (docx, doc, xlsx, etc.), open in new tab
    fileViewerContainer.innerHTML = `
        <div style="padding: 20px;">
            <h3>${fileTypeLabel}</h3>
            <p>Opening <strong>${fileName}</strong> in a new tab...</p>
            <p><a href="${fileUrl}" target="_blank" style="color:#0066cc;">Click here if it doesn't open automatically</a></p>
        </div>`;
    fileModal.style.display = 'block';
    // Auto-open in new tab after a short delay
    setTimeout(() => {
        window.open(fileUrl, '_blank');
    }, 500);
}

function closeFileModal() {
    fileModal.style.display = 'none';
    fileViewerContainer.innerHTML = '';
}

// Optional: refresh every 5 minutes
setInterval(() => { loadInternships(currentType); }, 5 * 60 * 1000);

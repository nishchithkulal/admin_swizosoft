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
    const container = type === 'free' ? freeTableBody : paidTableBody;
    const countElem = type === 'free' ? freeCount : paidCount;
    container.innerHTML = '';
    
    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="empty-card">
                <div class="empty-card-icon">📋</div>
                <p>No applications yet</p>
            </div>
        `;
        countElem.textContent = '0';
        return;
    }
    
    countElem.textContent = data.length;
    
    data.forEach(row => {
        const card = document.createElement('div');
        card.className = 'applicant-card';
        
        let fileButtons = '';
        if (type === 'free') {
            fileButtons = `
                <button class="file-button" onclick="viewFile(${row.id}, 'id_proof', '${type}')">📄 View ID Proof</button>
                <button class="file-button" onclick="viewFile(${row.id}, 'resume', '${type}')">📄 View Resume</button>
                <button class="file-button" onclick="viewFile(${row.id}, 'project', '${type}')">📁 View Project</button>
            `;
        } else {
            fileButtons = `
                <button class="file-button" onclick="viewFile(${row.id}, 'id_proof', '${type}')">📄 View ID Proof</button>
                <button class="file-button" onclick="viewFile(${row.id}, 'resume', '${type}')">📄 View Resume</button>
                <button class="file-button" onclick="viewFile(${row.id}, 'payment', '${type}')">💳 View Payment Screenshot</button>
            `;
        }
        
        const status = row.status ? row.status.toUpperCase() : 'PENDING';
        const statusClass = status === 'ACCEPTED' ? 'accepted' : status === 'REJECTED' ? 'rejected' : 'pending';
        
        card.innerHTML = `
            <div class="card-header">
                <div>
                    <div class="applicant-name">${row.name || 'N/A'}</div>
                    <div class="applicant-usn">USN: ${row.usn || 'N/A'}</div>
                </div>
                <span class="card-status ${statusClass}">${status}</span>
            </div>
            
            <div class="card-content">
                ${fileButtons}
            </div>
            
            <div class="action-buttons">
                <button class="action-btn accept-btn" onclick="updateStatus(${row.id}, 'ACCEPTED', '${type}')">✓ Accept</button>
                <button class="action-btn reject-btn" onclick="updateStatus(${row.id}, 'REJECTED', '${type}')">✕ Reject</button>
            </div>
        `;
        
        container.appendChild(card);
    });
}

function showError(type, message) {
    const container = type === 'free' ? freeTableBody : paidTableBody;
    container.innerHTML = `
        <div class="empty-card">
            <div class="empty-card-icon">⚠️</div>
            <p>${message}</p>
        </div>
    `;
}

function updateStatus(internshipId, status, internshipType) {
    if (!confirm(`Are you sure you want to mark this application as ${status}?`)) {
        return;
    }
    
    fetch(`/admin/api/update-status/${internshipId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            status: status,
            type: internshipType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Application ${status.toLowerCase()}!`);
            // Refresh the table
            loadInternships(currentType);
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error updating status');
    });
}

function viewFile(internshipId, fileType, internshipType) {
    // Special handling for payment screenshots
    if (fileType === 'payment') {
        fetch(`/admin/api/get-payment-screenshots/${internshipId}?type=${internshipType}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayFileUrlInModal(data.inplace_url, data.file_name || '', 'payment');
                } else {
                    alert('Payment screenshot not found: ' + (data.error || 'unknown'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error loading payment screenshot');
            });
        return;
    }
    
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
        'project': 'Project',
        'payment': 'Payment Screenshot'
    }[fileType] || fileType;

    // Detect file type by extension
    const lower = (fileName || fileUrl || '').toLowerCase();
    
    // PDFs: embed in iframe
    if (lower.endsWith('.pdf')) {
        fileViewerContainer.innerHTML = `
            <h3>${fileTypeLabel}</h3>
            <iframe src="${fileUrl}" style="width:100%;height:600px;border:none;"></iframe>`;
        fileModal.classList.add('show');
        return;
    }

    // Images: embed with img tag
    if (lower.match(/\.(jpg|jpeg|png|gif|bmp)$/)) {
        fileViewerContainer.innerHTML = `
            <h3>${fileTypeLabel}</h3>
            <img src="${fileUrl}" style="max-width:100%;height:auto;border-radius:6px;" onload="console.log('Image loaded')" onerror="console.log('Image failed to load')" />`;
        fileModal.classList.add('show');
        return;
    }

    // For other types (docx, doc, xlsx, etc.), open in new tab
    fileViewerContainer.innerHTML = `
        <h3>${fileTypeLabel}</h3>
        <p>Opening <strong>${fileName}</strong> in a new tab...</p>
        <p><a href="${fileUrl}" target="_blank" style="color:#0066cc;">Click here if it doesn't open automatically</a></p>`;
    fileModal.classList.add('show');
    // Auto-open in new tab after a short delay
    setTimeout(() => {
        window.open(fileUrl, '_blank');
    }, 500);
}

function closeFileModal() {
    fileModal.classList.remove('show');
    fileViewerContainer.innerHTML = '';
}

// Optional: refresh every 5 minutes
setInterval(() => { loadInternships(currentType); }, 5 * 60 * 1000);

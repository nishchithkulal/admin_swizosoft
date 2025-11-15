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
    
    // Call the accept/reject endpoints which also send emails
    const endpoint = status === 'ACCEPTED' ? `/accept/${internshipId}?type=${internshipType}` : `/reject/${internshipId}?type=${internshipType}`;
    fetch(endpoint, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || `Application ${status.toLowerCase()}!`);
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
                    // Open viewer page
                    const viewUrl = `/admin/view-file/${internshipId}/${fileType}?type=${internshipType}`;
                    window.open(viewUrl, '_blank');
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
    
    // Open viewer page for all file types
    const viewUrl = `/admin/view-file/${internshipId}/${fileType}?type=${internshipType}`;
    window.open(viewUrl, '_blank');
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
    const fileTitle = document.getElementById('fileTitle');
    const downloadBtn = document.getElementById('downloadBtn');
    const fileViewerContainer = document.getElementById('fileViewerContainer');
    
    fileViewerContainer.innerHTML = '';
    
    const fileTypeLabel = {
        'id_proof': 'ID Proof',
        'resume': 'Resume',
        'project': 'Project',
        'payment': 'Payment Screenshot'
    }[fileType] || fileType;

    // Set title
    fileTitle.textContent = fileTypeLabel;
    
    // Create download URL with download=1 parameter
    const downloadUrl = fileUrl.includes('?') ? fileUrl + '&download=1' : fileUrl + '?download=1';
    downloadBtn.href = downloadUrl;
    // ALWAYS hide initially - will show after content loads
    downloadBtn.style.display = 'none';

    // Detect file type by extension
    const lower = (fileName || fileUrl || '').toLowerCase();
    
    // PDFs: embed in iframe
    if (lower.endsWith('.pdf')) {
        fileViewerContainer.innerHTML = `<iframe id="fileFrame" src="${fileUrl}" style="width:100%;height:550px;border:none;"></iframe>`;
        fileModal.classList.add('show');
        // Show download button after iframe fully loads
        const frame = document.getElementById('fileFrame');
        frame.onload = function() {
            console.log('PDF loaded');
            downloadBtn.style.display = 'inline-flex';
        };
        frame.onerror = function() {
            console.log('PDF load error');
            downloadBtn.style.display = 'inline-flex';
        };
        return;
    }

    // Images: embed with img tag
    if (lower.match(/\.(jpg|jpeg|png|gif|bmp)$/)) {
        fileViewerContainer.innerHTML = `<img id="fileImg" src="${fileUrl}" style="max-width:100%;height:auto;border-radius:6px;" />`;
        fileModal.classList.add('show');
        // Show download button after image loads
        const img = document.getElementById('fileImg');
        img.onload = function() {
            console.log('Image loaded');
            downloadBtn.style.display = 'inline-flex';
        };
        img.onerror = function() {
            console.log('Image load error');
            downloadBtn.style.display = 'inline-flex';
        };
        return;
    }

    // DOCX/DOC files: display using Google Docs Viewer
    if (lower.match(/\.(docx|doc|xlsx|xls|pptx|ppt)$/)) {
        const encodedUrl = encodeURIComponent(fileUrl);
        // Show loading message first
        fileViewerContainer.innerHTML = `<div style="text-align:center;padding:40px;color:#999;"><p>⏳ Loading document...</p></div>`;
        fileViewerContainer.innerHTML += `<iframe id="fileFrame" src="https://docs.google.com/gview?url=${encodedUrl}&embedded=true" style="width:100%;height:550px;border:none;"></iframe>`;
        fileModal.classList.add('show');
        // Show download button after delay (Google Docs Viewer takes time)
        setTimeout(() => {
            console.log('Document ready (timeout)');
            downloadBtn.style.display = 'inline-flex';
        }, 3000);
        return;
    }

    // For other types
    fileViewerContainer.innerHTML = `<p>File type <strong>${fileName}</strong> cannot be previewed.</p><p>Click Download button to get this file.</p>`;
    fileModal.classList.add('show');
    // Show download button immediately
    downloadBtn.style.display = 'inline-flex';
}

function closeFileModal() {
    fileModal.classList.remove('show');
    fileViewerContainer.innerHTML = '';
    document.getElementById('downloadBtn').style.display = 'none';
}

// Optional: refresh every 5 minutes
setInterval(() => { loadInternships(currentType); }, 5 * 60 * 1000);

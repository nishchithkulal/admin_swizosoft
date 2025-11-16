// Fetch approved candidates and render table
document.addEventListener('DOMContentLoaded', function() {
    loadApprovedCandidates();
});

function loadApprovedCandidates() {
    const grid = document.getElementById('approvedGrid');
    const countElem = document.getElementById('approved-count');
    
    fetchWithRetry('/admin/api/get-approved-candidates', 5)
        .then(resp => {
            console.log('Response data:', resp);
            if (resp.success) {
                renderApprovedCandidates(grid, countElem, resp.data || []);
            } else {
                grid.innerHTML = `<div class="empty-card"><div class="empty-card-icon">⚠️</div><p>Error: ${resp.error || 'Unknown'}</p></div>`;
                countElem.textContent = '0';
            }
        })
        .catch(err => {
            console.error('Fetch error:', err);
            grid.innerHTML = `<div class="empty-card"><div class="empty-card-icon">⚠️</div><p>Could not fetch approved candidates: ${err.message}</p></div>`;
            countElem.textContent = '0';
        });
}

// Retry function with exponential backoff
async function fetchWithRetry(url, retries = 5, delay = 100) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                return await response.json();
            } else if (response.status === 500 && i < retries - 1) {
                // Server error, retry after delay
                await new Promise(resolve => setTimeout(resolve, delay));
                delay = Math.min(delay * 1.5, 1000);  // Exponential backoff, max 1s
                continue;
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (err) {
            if (i === retries - 1) {
                throw err;
            }
            // Wait before retrying with exponential backoff
            await new Promise(resolve => setTimeout(resolve, delay));
            delay = Math.min(delay * 1.5, 1000);  // Exponential backoff, max 1s
        }
    }
}

function renderApprovedCandidates(container, countElem, rows) {
    container.innerHTML = '';
    if (!rows || rows.length === 0) {
        container.innerHTML = `
            <div class="empty-card">
                <div class="empty-card-icon">📭</div>
                <p>No approved candidates yet</p>
            </div>
        `;
        countElem.textContent = '0';
        return;
    }

    countElem.textContent = rows.length;

    // Create table
    const table = document.createElement('table');
    table.className = 'applicants-table';
    
    // Table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Name</th>
            <th>USN</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Branch</th>
            <th>College</th>
            <th>Year</th>
            <th>Domain</th>
            <th>Interview Mode</th>
            <th>View Resume</th>
            <th>View ID Proof</th>
            <th>View Project</th>
            <th>Actions</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Table body
    const tbody = document.createElement('tbody');
    
    rows.forEach(r => {
        const tr = document.createElement('tr');
        
        // Extract candidate details - approved_candidates table has consistent column names
        const name = r.name || 'N/A';
        const usn = r.usn || 'N/A';
        const email = r.email || 'N/A';
        const phone = r.phone_number || 'N/A';
        const branch = r.branch || 'N/A';
        const college = r.college || 'N/A';
        const year = r.year || 'N/A';
        const domain = r.domain || 'N/A';
        const mode = r.mode_of_interview || 'N/A';
        const appId = r.application_id || r.id;

        // Build file view buttons based on filename presence (avoid expecting BLOBs in list API)
        const resumeBtn = r.resume_name ? `<button class="table-action-btn table-view-btn" onclick="viewApprovedFile('${usn}', 'resume')">View Resume</button>` : '—';
        const idProofBtn = r.id_proof_name ? `<button class="table-action-btn table-view-btn" onclick="viewApprovedFile('${usn}', 'id_proof')">View ID Proof</button>` : '—';
        const projectBtn = r.project_document_name ? `<button class="table-action-btn table-view-btn" onclick="viewApprovedFile('${usn}', 'project')">View Project</button>` : '—';
        const acceptBtn = `<button class="table-action-btn table-accept-btn" onclick="confirmApprovedAccept(${appId})">Accept</button>`;
        const rejectBtn = `<button class="table-action-btn table-reject-btn" onclick="showApprovedRejectionModal(${appId})">Reject</button>`;

        tr.innerHTML = `
            <td class="table-name">${name}</td>
            <td class="table-usn">${usn}</td>
            <td>${email}</td>
            <td>${phone}</td>
            <td>${branch}</td>
            <td>${college}</td>
            <td>${year}</td>
            <td>${domain}</td>
            <td>${mode}</td>
            <td>${resumeBtn}</td>
            <td>${idProofBtn}</td>
            <td>${projectBtn}</td>
            <td>${acceptBtn} ${rejectBtn}</td>
        `;
        
        tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
}

// View files for approved candidates
function viewApprovedFile(usn, fileType) {
    const fileTitle = {
        'resume': 'Resume',
        'id_proof': 'ID Proof',
        'project': 'Project Document'
    }[fileType] || 'File';
    
    // Fetch the file from the API
    fetch(`/admin/api/get-approved-file/${usn}?type=${fileType}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(r => r.json())
        .then(resp => {
            if (resp.success && resp.file_data) {
                openFileModal(fileTitle, resp.file_data, resp.file_type || fileType, resp.file_name);
            } else {
                alert('Could not load file: ' + (resp.error || 'Unknown error'));
            }
        })
        .catch(err => {
            console.error('Error fetching file:', err);
            alert('Error loading file: ' + err.message);
        });
}

// File modal functions (reused from admin_selected.js)
function openFileModal(title, fileData, fileType, fileName) {
    const modal = document.getElementById('fileModal');
    document.getElementById('fileTitle').textContent = title;
    const container = document.getElementById('fileViewerContainer');
    
    // Detect file type from magic bytes or extension
    const data = atob(fileData);  // Decode base64
    const bytes = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
        bytes[i] = data.charCodeAt(i);
    }
    
    // Detect type
    let detectedType = 'unknown';
    if (bytes[0] === 0xFF && bytes[1] === 0xD8) detectedType = 'image';  // JPEG
    else if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E) detectedType = 'image';  // PNG
    else if (bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44) detectedType = 'pdf';  // PDF
    else if (bytes[0] === 0x50 && bytes[1] === 0x4B && bytes[2] === 0x03 && bytes[3] === 0x04) detectedType = 'office';  // DOCX/XLSX
    
    // Build blob URL
    const blob = new Blob([bytes], { type: getMimeType(detectedType) });
    const url = URL.createObjectURL(blob);
    
    // Set up download button
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = url;
    downloadBtn.download = fileName || `${fileType}.bin`;
    downloadBtn.style.display = 'inline-block';
    
    // Display content
    if (detectedType === 'pdf') {
        container.innerHTML = `<embed src="${url}" type="application/pdf" style="width:100%;height:600px;border:none;" />`;
    } else if (detectedType === 'image') {
        container.innerHTML = `<img src="${url}" style="max-width:100%;height:auto;border:1px solid #ddd;border-radius:4px;" />`;
    } else if (detectedType === 'office') {
        // Use Google Docs Viewer for Office documents
        const googleViewerUrl = `https://docs.google.com/gview?url=${encodeURIComponent(url)}&embedded=true`;
        container.innerHTML = `<iframe src="${googleViewerUrl}" style="width:100%;height:600px;border:none;"></iframe>`;
    } else {
        container.innerHTML = `<p>Preview not available for this file type. Please download to view.</p>`;
    }
    
    modal.style.display = 'block';
}

function closeFileModal() {
    const modal = document.getElementById('fileModal');
    modal.style.display = 'none';
    document.getElementById('fileViewerContainer').innerHTML = '';
}

function getMimeType(type) {
    const mimeTypes = {
        'pdf': 'application/pdf',
        'image': 'image/jpeg',
        'office': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'unknown': 'application/octet-stream'
    };
    return mimeTypes[type] || 'application/octet-stream';
}

// Close modal on background click
window.onclick = function(event) {
    const modal = document.getElementById('fileModal');
    const rejectionModal = document.getElementById('approvedRejectionModal');
    
    if (event.target === modal) {
        closeFileModal();
    }
    if (event.target === rejectionModal) {
        closeApprovedRejectionModal();
    }
};

// Rejection modal for approved candidates
let currentApprovedRejectId = null;

function showApprovedRejectionModal(applicationId) {
    currentApprovedRejectId = applicationId;
    
    // Fetch rejection reasons
    fetch('/admin/api/get-rejection-reasons')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const reasonsList = document.getElementById('approvedRejectionReasonsList');
                reasonsList.innerHTML = '';
                
                data.reasons.forEach(reason => {
                    const div = document.createElement('div');
                    div.className = 'rejection-reason-item';
                    div.textContent = reason;
                    div.onclick = () => confirmApprovedReject(reason);
                    reasonsList.appendChild(div);
                });
                
                document.getElementById('approvedRejectionModal').style.display = 'flex';
            }
        })
        .catch(err => console.error('Error fetching reasons:', err));
}

function closeApprovedRejectionModal() {
    document.getElementById('approvedRejectionModal').style.display = 'none';
    currentApprovedRejectId = null;
}

function confirmApprovedReject(reason) {
    if (!currentApprovedRejectId) return;
    
    const formData = new FormData();
    formData.append('reason', reason);
    
    fetch(`/reject/${currentApprovedRejectId}?type=free`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || 'Candidate rejected!');
            closeApprovedRejectionModal();
            loadApprovedCandidates();
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error rejecting candidate');
    });
}

function confirmApprovedAccept(applicationId) {
    fetch(`/accept/${applicationId}?type=free`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || 'Candidate accepted!');
            loadApprovedCandidates();
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error accepting candidate');
    });
}

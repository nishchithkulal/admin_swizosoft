// Get references to DOM elements
const freeTableBody = document.getElementById('freeTableBody');
const paidTableBody = document.getElementById('paidTableBody');
const freeCount = document.getElementById('free-count');
const paidCount = document.getElementById('paid-count');
const fileModal = document.getElementById('fileModal');
const fileViewerContainer = document.getElementById('fileViewerContainer');
const closeBtn = document.querySelector('.close');

// Close modal when close button is clicked
closeBtn.onclick = function() {
    fileModal.style.display = 'none';
}

// Close modal when clicking outside the modal content
window.onclick = function(event) {
    if (event.target == fileModal) {
        fileModal.style.display = 'none';
    }
}

// Load internship data on page load
document.addEventListener('DOMContentLoaded', function() {
    loadInternships('free');
    loadInternships('paid');
});

/**
 * Load internship data from the server
 */
function loadInternships(type) {
    fetch(`/api/get-internships?type=${type}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateTable(type, data.data);
            } else {
                showError(type, 'Error loading data: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError(type, 'Error connecting to server');
        });
}

/**
 * Populate the table with internship data
 */
function populateTable(type, internships) {
    const tableBody = type === 'free' ? freeTableBody : paidTableBody;
    const countElement = type === 'free' ? freeCount : paidCount;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    if (internships.length === 0) {
        tableBody.innerHTML = '<tr class="empty-row"><td colspan="5">No records found</td></tr>';
        countElement.textContent = '0';
        return;
    }
    
    // Update count
    countElement.textContent = internships.length;
    
    // Populate rows
    internships.forEach(intern => {
        const row = createTableRow(intern, type);
        tableBody.appendChild(row);
    });
}

/**
 * Create a table row for an internship record
 */
function createTableRow(intern, type) {
    const row = document.createElement('tr');
    
    row.innerHTML = `
        <td>${intern.name || '-'}</td>
        <td>${intern.usn || '-'}</td>
        <td>
            <button class="action-btn" onclick="viewFile(${intern.id}, 'resume', '${type}')">
                View Resume
            </button>
        </td>
        <td>
            <button class="action-btn" onclick="viewFile(${intern.id}, 'project', '${type}')">
                View Project
            </button>
        </td>
        <td>
            <button class="action-btn" onclick="viewFile(${intern.id}, 'id_card', '${type}')">
                View ID
            </button>
        </td>
    `;
    
    return row;
}

/**
 * View or download a file
 */
function viewFile(internshipId, fileType, internshipType) {
    const fileTypeLabel = fileType === 'resume' ? 'Resume' : 
                         fileType === 'project' ? 'Project' : 
                         'ID Card';
    
    // Try to view in modal first
    fetch(`/api/view-file/${internshipId}/${fileType}?type=${internshipType}`)
        .then(response => {
            if (!response.ok) {
                // If viewing fails, try downloading
                downloadFile(internshipId, fileType, internshipType);
                return;
            }
            return response.blob();
        })
        .then(blob => {
            if (blob) {
                displayFileInModal(blob, fileType, fileTypeLabel);
            }
        })
        .catch(error => {
            console.error('Error viewing file:', error);
            // Fallback to download
            downloadFile(internshipId, fileType, internshipType);
        });
}

/**
 * Display file in modal
 */
function displayFileInModal(blob, fileType, fileTypeLabel) {
    fileViewerContainer.innerHTML = '';
    
    const url = URL.createObjectURL(blob);
    
    if (fileType === 'id_card') {
        // Display image
        const img = document.createElement('img');
        img.src = url;
        img.alt = fileTypeLabel;
        fileViewerContainer.appendChild(img);
    } else {
        // Display PDF
        const iframe = document.createElement('iframe');
        iframe.src = url;
        fileViewerContainer.appendChild(iframe);
    }
    
    // Show modal
    fileModal.style.display = 'block';
}

/**
 * Download file
 */
function downloadFile(internshipId, fileType, internshipType) {
    const fileTypeLabel = fileType === 'resume' ? 'Resume' : 
                         fileType === 'project' ? 'Project' : 
                         'ID Card';
    
    const link = document.createElement('a');
    link.href = `/api/get-${fileType}/${internshipId}?type=${internshipType}`;
    
    // Determine file extension
    const extension = fileType === 'id_card' ? 'jpg' : 'pdf';
    link.download = `${fileType}_${internshipId}.${extension}`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up the URL
    setTimeout(() => URL.revokeObjectURL(link.href), 100);
}

/**
 * Show error message in table
 */
function showError(type, message) {
    const tableBody = type === 'free' ? freeTableBody : paidTableBody;
    tableBody.innerHTML = `<tr class="empty-row"><td colspan="5">${message}</td></tr>`;
}

// Refresh data every 5 minutes
setInterval(() => {
    loadInternships('free');
    loadInternships('paid');
}, 5 * 60 * 1000);

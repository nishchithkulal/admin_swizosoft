const freeTableBody = document.getElementById("freeTableBody");
const paidTableBody = document.getElementById("paidTableBody");
const freeCount = document.getElementById("free-count");
const paidCount = document.getElementById("paid-count");
const freeSection = document.getElementById("freeSection");
const paidSection = document.getElementById("paidSection");
const freeBtn = document.getElementById("freeBtn");
const paidBtn = document.getElementById("paidBtn");
const fileModal = document.getElementById("fileModal");
const fileViewerContainer = document.getElementById("fileViewerContainer");

let currentType = "free";

document.addEventListener("DOMContentLoaded", function () {
  loadInternships("free");

  // Close modal when clicking outside
  window.onclick = function (event) {
    if (event.target == fileModal) {
      closeFileModal();
    }
  };
});

function switchInternship(type) {
  currentType = type;

  // Update button active state
  if (type === "free") {
    freeBtn.classList.add("active");
    paidBtn.classList.remove("active");
    freeSection.style.display = "block";
    paidSection.style.display = "none";
  } else {
    paidBtn.classList.add("active");
    freeBtn.classList.remove("active");
    paidSection.style.display = "block";
    freeSection.style.display = "none";
  }

  // Load data if not already loaded
  loadInternships(type);
}

function loadInternships(type) {
  fetch(`/admin/api/get-internships?type=${type}`)
    .then((r) => r.json())
    .then((resp) => {
      if (resp.success) {
        populateTable(type, resp.data);
      } else {
        showError(type, "Error: " + (resp.error || "Unknown"));
      }
    })
    .catch((err) => {
      console.error(err);
      showError(type, "Could not connect to server");
    });
}

function populateTable(type, data) {
  const container = type === "free" ? freeTableBody : paidTableBody;
  const countElem = type === "free" ? freeCount : paidCount;
  container.innerHTML = "";

  if (!data || data.length === 0) {
    container.innerHTML = `
            <div class="empty-card">
                <div class="empty-card-icon">📋</div>
                <p>No applications yet</p>
            </div>
        `;
    countElem.textContent = "0";
    return;
  }

  countElem.textContent = data.length;

  // Create table
  const table = document.createElement("table");
  table.className = "applicants-table";

  // Table header
  const thead = document.createElement("thead");
  thead.innerHTML = `
        <tr>
            <th>Name</th>
            <th>USN</th>
            ${type === "free" ? "<th>Resume Score</th>" : ""}
            <th>View ID Proof</th>
            <th>View Resume</th>
            <th>View ${type === "free" ? "Project" : "Payment"}</th>
            <th>Action</th>
        </tr>
    `;
  table.appendChild(thead);

  // Table body
  const tbody = document.createElement("tbody");

  data.forEach((row) => {
    const tr = document.createElement("tr");

    const idProofBtn = `<button class="table-action-btn table-view-btn" onclick="viewFile(${row.id}, 'id_proof', '${type}')">View ID Proof</button>`;
    const resumeBtn = `<button class="table-action-btn table-view-btn" onclick="viewFile(${row.id}, 'resume', '${type}')">View Resume</button>`;
    const projectBtn =
      type === "free"
        ? `<button class="table-action-btn table-view-btn" onclick="viewFile(${row.id}, 'project', '${type}')">View Project</button>`
        : `<button class="table-action-btn table-view-btn" onclick="viewFile(${row.id}, 'payment', '${type}')">View Payment</button>`;

    tr.innerHTML = `
            <td class="table-name">${row.name || "N/A"}</td>
            <td class="table-usn">${row.usn || "N/A"}</td>
            ${
              type === "free"
                ? `<td class="table-score">${
                    row.resume_score !== undefined && row.resume_score !== null
                      ? row.resume_score
                      : "—"
                  }</td>`
                : ""
            }
            <td>${idProofBtn}</td>
            <td>${resumeBtn}</td>
            <td>${projectBtn}</td>
            <td>
                <div class="table-actions">
                    <button class="table-action-btn table-edit-btn" onclick="openEditModal(${
                      row.id
                    }, '${type}')">Edit</button>
                    <button class="table-action-btn table-accept-btn" onclick="updateStatus(${
                      row.id
                    }, 'ACCEPTED', '${type}')">Accept</button>
                    <button class="table-action-btn table-reject-btn" onclick="updateStatus(${
                      row.id
                    }, 'REJECTED', '${type}')">Reject</button>
                </div>
            </td>
        `;

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
}

function showError(type, message) {
  const container = type === "free" ? freeTableBody : paidTableBody;
  container.innerHTML = `
        <div class="empty-card">
            <div class="empty-card-icon">⚠️</div>
            <p>${message}</p>
        </div>
    `;
}

function updateStatus(internshipId, status, internshipType) {
  if (status === "REJECTED") {
    // Show rejection modal instead of confirm dialog
    showRejectionModal(internshipId, internshipType);
    return;
  }

  if (
    !confirm(`Are you sure you want to mark this application as ${status}?`)
  ) {
    return;
  }
  // Call the accept/reject endpoints which also send emails
  const endpoint =
    status === "ACCEPTED"
      ? `/accept/${internshipId}?type=${internshipType}`
      : `/reject/${internshipId}?type=${internshipType}`;
  fetch(endpoint, { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // If server returned selected_inserted flag (for paid type), surface it
        if (
          data.hasOwnProperty("selected_inserted") &&
          data.selected_inserted === false
        ) {
          const err =
            data.selected_insert_error ||
            "Candidate not inserted into Selected (possible duplicate USN)";
          alert(
            (data.message || `Application ${status.toLowerCase()}!`) +
              "\nNote: " +
              err
          );
        } else {
          alert(data.message || `Application ${status.toLowerCase()}!`);
        }
        // Refresh the table
        loadInternships(currentType);
      } else {
        alert("Error: " + (data.error || "Unknown error"));
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error updating status");
    });
}

function viewFile(internshipId, fileType, internshipType) {
  // Special handling for payment screenshots
  if (fileType === "payment") {
    fetch(
      `/admin/api/get-payment-screenshots/${internshipId}?type=${internshipType}`
    )
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Open viewer page
          const viewUrl = `/admin/view-file/${internshipId}/${fileType}?type=${internshipType}`;
          window.open(viewUrl, "_blank");
        } else {
          alert("Payment screenshot not found: " + (data.error || "unknown"));
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("Error loading payment screenshot");
      });
    return;
  }

  // Open viewer page for all file types
  const viewUrl = `/admin/view-file/${internshipId}/${fileType}?type=${internshipType}`;
  window.open(viewUrl, "_blank");
}

function displayFileInModal(fileName, fileType) {
  fileViewerContainer.innerHTML = "";

  const fileTypeLabel =
    {
      id_proof: "ID Proof",
      resume: "Resume",
      project: "Project",
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

  fileModal.style.display = "block";
}

function displayFileUrlInModal(fileUrl, fileName, fileType) {
  const fileTitle = document.getElementById("fileTitle");
  const downloadBtn = document.getElementById("downloadBtn");
  const fileViewerContainer = document.getElementById("fileViewerContainer");

  fileViewerContainer.innerHTML = "";

  const fileTypeLabel =
    {
      id_proof: "ID Proof",
      resume: "Resume",
      project: "Project",
      payment: "Payment Screenshot",
    }[fileType] || fileType;

  // Set title
  fileTitle.textContent = fileTypeLabel;

  // Create download URL with download=1 parameter
  const downloadUrl = fileUrl.includes("?")
    ? fileUrl + "&download=1"
    : fileUrl + "?download=1";
  downloadBtn.href = downloadUrl;
  // ALWAYS hide initially - will show after content loads
  downloadBtn.style.display = "none";

  // Detect file type by extension
  const lower = (fileName || fileUrl || "").toLowerCase();

  // PDFs: embed in iframe
  if (lower.endsWith(".pdf")) {
    fileViewerContainer.innerHTML = `<iframe id="fileFrame" src="${fileUrl}" style="width:100%;height:100%;border:none;"></iframe>`;
    fileModal.classList.add("show");
    // Show download button after iframe fully loads
    const frame = document.getElementById("fileFrame");
    frame.onload = function () {
      console.log("PDF loaded");
      downloadBtn.style.display = "inline-flex";
    };
    frame.onerror = function () {
      console.log("PDF load error");
      downloadBtn.style.display = "inline-flex";
    };
    return;
  }

  // Images: embed with img tag
  if (lower.match(/\.(jpg|jpeg|png|gif|bmp)$/)) {
    fileViewerContainer.innerHTML = `<img id="fileImg" src="${fileUrl}" style="max-width:100%;max-height:100%;object-fit:contain;border-radius:6px;" />`;
    fileModal.classList.add("show");
    // Show download button after image loads
    const img = document.getElementById("fileImg");
    img.onload = function () {
      console.log("Image loaded");
      downloadBtn.style.display = "inline-flex";
    };
    img.onerror = function () {
      console.log("Image load error");
      downloadBtn.style.display = "inline-flex";
    };
    return;
  }

  // DOCX/DOC files: display using Google Docs Viewer
  if (lower.match(/\.(docx|doc|xlsx|xls|pptx|ppt)$/)) {
    const encodedUrl = encodeURIComponent(fileUrl);
    // Show loading message first
    fileViewerContainer.innerHTML = `<div style="text-align:center;padding:40px;color:#999;"><p>⏳ Loading document...</p></div>`;
    fileViewerContainer.innerHTML += `<iframe id="fileFrame" src="https://docs.google.com/gview?url=${encodedUrl}&embedded=true" style="width:100%;height:100%;border:none;"></iframe>`;
    fileModal.classList.add("show");
    // Show download button after delay (Google Docs Viewer takes time)
    setTimeout(() => {
      console.log("Document ready (timeout)");
      downloadBtn.style.display = "inline-flex";
    }, 3000);
    return;
  }

  // For other types
  fileViewerContainer.innerHTML = `<p>File type <strong>${fileName}</strong> cannot be previewed.</p><p>Click Download button to get this file.</p>`;
  fileModal.classList.add("show");
  // Show download button immediately
  downloadBtn.style.display = "inline-flex";
}

function closeFileModal() {
  fileModal.classList.remove("show");
  fileViewerContainer.innerHTML = "";
  document.getElementById("downloadBtn").style.display = "none";
}

function openEditModal(internshipId, internshipType) {
  // Fetch full profile data
  fetch(`/admin/api/get-profile/${internshipId}?type=${internshipType}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showEditModal(internshipId, internshipType, data.data);
      } else {
        alert("Error loading profile: " + (data.error || "Unknown"));
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error loading profile");
    });
}

function showEditModal(internshipId, internshipType, profileData) {
  // Exclude file-related, sensitive, and non-editable columns
  const excludeColumns = [
    "id",
    "id_proof",
    "resume",
    "project_document",
    "payment_screenshot",
    "id_proof_content",
    "resume_content",
    "project_document_content",
    "created_at",
    "updated_at",
    "reason",
    "applicationid",
    "application_id",
    "status",
    "domain",
  ];

  const collegesList = [
    "SRINIVAS INSTITUTE OF TECHNOLOGY",
    "AJ INSTITUTE OF ENGINEERING AND TECHNOLOGY",
    "BEARYS INSTITUTE OF TECHNOLOGY",
    "SAHYADRI COLLEGE OF ENGINEERING AND MANAGEMENT",
    "KVG COLLEGE OF ENGINEERING",
    "CANARA ENGINEERING COLLEGE",
    "MANGALORE INSTITUTE OF TECHNOLOGY & ENGINEERING",
    "ST JOSEPH ENGINEERING COLLEGE",
    "ALVAS INSTITUTE OF ENGINEERING AND TECHNOLOGY",
  ];

  const branchesList = [
    "COMPUTER SCIENCE",
    "INFORMATION TECHNOLOGY",
    "ELECTRONICS AND COMMUNICATION",
    "MECHANICAL ENGINEERING",
    "CIVIL ENGINEERING",
    "ELECTRICAL ENGINEERING",
  ];

  const yearsList = ["1st Year", "2nd Year", "3rd Year", "4th Year"];

  let formHTML = "";
  for (const [key, value] of Object.entries(profileData)) {
    if (!excludeColumns.includes(key.toLowerCase())) {
      const displayKey = key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
      const storedValue = (value || "").toString().trim();

      // Create dropdown for college/institution fields
      if (
        key.toLowerCase().includes("college") ||
        key.toLowerCase().includes("institution") ||
        key.toLowerCase().includes("institute")
      ) {
        formHTML += `
                    <div class="form-group">
                        <label for="field_${key}">${displayKey}</label>
                        <select id="field_${key}" class="form-input">
                            <option value="">-- Select College --</option>
                            ${collegesList
                              .map(
                                (college) =>
                                  `<option value="${college}" ${
                                    storedValue.toUpperCase() ===
                                    college.toUpperCase()
                                      ? "selected"
                                      : ""
                                  }>${college}</option>`
                              )
                              .join("")}
                        </select>
                    </div>
                `;
      }
      // Create dropdown for branch fields
      else if (
        key.toLowerCase().includes("branch") ||
        key.toLowerCase().includes("department") ||
        key.toLowerCase().includes("stream")
      ) {
        formHTML += `
                    <div class="form-group">
                        <label for="field_${key}">${displayKey}</label>
                        <select id="field_${key}" class="form-input">
                            ${branchesList
                              .map(
                                (branch) =>
                                  `<option value="${branch}" ${
                                    storedValue.toUpperCase() ===
                                    branch.toUpperCase()
                                      ? "selected"
                                      : ""
                                  }>${branch}</option>`
                              )
                              .join("")}
                        </select>
                    </div>
                `;
      }
      // Create dropdown for year fields
      else if (
        key.toLowerCase().includes("year") ||
        key.toLowerCase().includes("semester") ||
        key.toLowerCase().includes("sem")
      ) {
        formHTML += `
                    <div class="form-group">
                        <label for="field_${key}">${displayKey}</label>
                        <select id="field_${key}" class="form-input">
                            ${yearsList
                              .map(
                                (year) =>
                                  `<option value="${year}" ${
                                    storedValue === year ? "selected" : ""
                                  }>${year}</option>`
                              )
                              .join("")}
                        </select>
                    </div>
                `;
      } else {
        formHTML += `
                    <div class="form-group">
                        <label for="field_${key}">${displayKey}</label>
                        <input type="text" id="field_${key}" value="${storedValue}" class="form-input">
                    </div>
                `;
      }
    }
  }

  const modalHTML = `
        <div class="edit-modal show" id="editModal">
            <div class="edit-modal-content">
                <div class="edit-modal-header">
                    <h2>Edit Profile</h2>
                    <button class="close-btn" onclick="closeEditModal()">✕</button>
                </div>
                <div class="edit-modal-body">
                    <form id="editForm">
                        ${formHTML}
                    </form>
                </div>
                <div class="edit-modal-footer">
                    <button class="btn-cancel" onclick="closeEditModal()">Cancel</button>
                    <button class="btn-save" onclick="saveProfile(${internshipId}, '${internshipType}')">Save Changes</button>
                </div>
            </div>
        </div>
    `;

  // Remove old modal if exists
  const oldModal = document.getElementById("editModal");
  if (oldModal) oldModal.remove();

  // Add new modal to body
  document.body.insertAdjacentHTML("beforeend", modalHTML);
}

function closeEditModal() {
  const modal = document.getElementById("editModal");
  if (modal) modal.remove();
}

function saveProfile(internshipId, internshipType) {
  const form = document.getElementById("editForm");
  const formData = new FormData(form);

  const updateData = {};
  const inputs = form.querySelectorAll(".form-input");
  inputs.forEach((input) => {
    const fieldName = input.id.replace("field_", "");
    updateData[fieldName] = input.value;
  });

  fetch(`/admin/api/edit-profile/${internshipId}?type=${internshipType}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updateData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert("Profile updated successfully!");
        closeEditModal();
        loadInternships(currentType);
      } else {
        alert("Error: " + (data.error || "Unknown error"));
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error saving profile");
    });
}

// Rejection modal functions
let currentRejectInternshipId = null;
let currentRejectInternshipType = null;

function showRejectionModal(internshipId, internshipType) {
  currentRejectInternshipId = internshipId;
  currentRejectInternshipType = internshipType;

  // Fetch candidate information first
  fetch(`/admin/api/get-profile/${internshipId}?type=${internshipType}`)
    .then((r) => r.json())
    .then((candidateData) => {
      // Populate candidate information in the modal
      const profile = candidateData.data || {};
      document.getElementById("rejectCandidateName").textContent =
        profile.name || profile.full_name || "N/A";
      document.getElementById("rejectCandidateUSN").textContent =
        profile.usn || profile.roll || profile.rollno || "N/A";
      document.getElementById("rejectCandidateEmail").textContent =
        profile.email || profile.applicant_email || "N/A";
    })
    .catch((err) => {
      console.error("Error fetching candidate info:", err);
      document.getElementById("rejectCandidateName").textContent = "N/A";
      document.getElementById("rejectCandidateUSN").textContent = "N/A";
      document.getElementById("rejectCandidateEmail").textContent = "N/A";
    });

  // Fetch rejection reasons
  fetch("/admin/api/get-rejection-reasons")
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        const reasonsList = document.getElementById("rejectionReasonsList");
        reasonsList.innerHTML = "";

        data.reasons.forEach((reason) => {
          const div = document.createElement("div");
          div.className = "rejection-reason-item";
          div.textContent = reason;
          div.onclick = () => performReject(reason);
          reasonsList.appendChild(div);
        });

        document.getElementById("rejectionModal").style.display = "flex";
      }
    })
    .catch((err) => console.error("Error fetching reasons:", err));
}

function closeRejectionModal() {
  document.getElementById("rejectionModal").style.display = "none";
  currentRejectInternshipId = null;
  currentRejectInternshipType = null;
}

function performReject(reason) {
  if (!currentRejectInternshipId || !reason) {
    alert("Please select a reason.");
    return;
  }

  if (
    !confirm(
      "Are you sure? This will delete all applicant data and send rejection email."
    )
  )
    return;

  const formData = new FormData();
  formData.append("reason", reason);

  fetch(
    `/reject/${currentRejectInternshipId}?type=${currentRejectInternshipType}`,
    {
      method: "POST",
      body: formData,
    }
  )
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert(data.message || "Application rejected!");
        closeRejectionModal();
        loadInternships(currentType);
      } else {
        alert("Error: " + (data.error || "Unknown error"));
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error rejecting application");
    });
}

// In your admin_dashboard.js

function acceptApplicant(applicantId, type) {
  fetch(`/accept/${applicantId}?type=${type}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        return response
          .json()
          .then((data) => ({ status: response.status, data: data }));
      }
      return { status: response.status, data: null };
    })
    .then(({ status, data }) => {
      if (status === 409) {
        // Duplicate USN - show professional warning popup
        alert(data.error);
        return;
      }

      if (status === 200) {
        // Success
        alert(data.message);
        location.reload();
      } else if (status === 500) {
        // Server error
        alert(data.error || "An error occurred");
      } else {
        // Other error
        alert(data.error || "Operation failed");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Network error. Please try again.");
    });
}

// Optional: refresh every 5 minutes
setInterval(() => {
  loadInternships(currentType);
}, 5 * 60 * 1000);

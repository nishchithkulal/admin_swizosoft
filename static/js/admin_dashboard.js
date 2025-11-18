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
            <th>View Profile</th>
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
    const profileBtn = `<button class="table-action-btn table-view-btn" onclick="viewProfile(${row.id}, '${type}')">View Profile</button>`;

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
            <td>${profileBtn}</td>
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

  // For ACCEPTED status on PAID internships, show domain selection and offer letter flow
  if (status === "ACCEPTED" && internshipType === "paid") {
    initiatePaidInternshipAccept(internshipId);
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
    .then((response) => {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        return response
          .json()
          .then((data) => ({ status: response.status, data: data }));
      }
      return { status: response.status, data: null };
    })
    .then(({ status: httpStatus, data }) => {
      // Handle 409 Conflict (Duplicate USN)
      if (httpStatus === 409) {
        alert(data.error);
        return;
      }

      // Handle success
      if (data && data.success) {
        alert(data.message || `Application ${status.toLowerCase()}!`);
        loadInternships(currentType);
      }
      // Handle error
      else if (data && data.error) {
        alert("Error: " + data.error);
      }
      // Fallback
      else {
        alert(`Error updating status`);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error updating status");
    });
}

// Store current paid internship data for offer letter flow
let currentPaidInternshipData = null;
let currentOfferLetterData = null;

async function initiatePaidInternshipAccept(applicationId) {
  try {
    console.log("🔄 Initiating paid internship accept for:", applicationId);

    // Fetch the paid internship application data
    const response = await fetch(
      `/admin/api/get-profile/${applicationId}?type=paid`
    );
    if (!response.ok) {
      throw new Error("Could not fetch application data");
    }

    const data = await response.json();
    if (!data.success || !data.data) {
      throw new Error("Application data not found");
    }

    const applicantData = data.data;

    // Store for later use
    currentPaidInternshipData = {
      application_id: applicationId,
      name: applicantData.name || "",
      usn: applicantData.usn || applicantData.roll || `APP${applicationId}`,
      email: applicantData.email || "",
      college: applicantData.college || "",
      domain: applicantData.domain || "",
      mode_of_internship:
        applicantData.mode_of_internship ||
        applicantData.internship_mode ||
        "online",
      year: applicantData.year || "",
      qualification: applicantData.qualification || "",
      branch: applicantData.branch || applicantData.department || "",
      phone:
        applicantData.phone ||
        applicantData.mobile ||
        applicantData.contact_number ||
        "",
      project_description: applicantData.project_description || "",
      project_name:
        applicantData.project_document || applicantData.project_name || "",
      project_title: applicantData.project_title || "",
    };

    // Show domain selection modal (need to create this for dashboard or skip if no domain changes needed)
    // For now, proceed directly with offer letter generation with current domain
    await generateAndShowOfferLetterForPaid(
      currentPaidInternshipData,
      currentPaidInternshipData.domain
    );
  } catch (error) {
    console.error("Error initiating paid internship accept:", error);
    alert("❌ Error: " + error.message);
  }
}

async function generateAndShowOfferLetterForPaid(applicantData, domain) {
  try {
    console.log(
      "🔄 Generating offer letter for paid internship:",
      applicantData.usn
    );

    // Show loading state
    const modal = document.getElementById("offerLetterModal");
    if (modal) {
      modal.classList.add("show");
    }
    document.getElementById("offerLetterContainer").innerHTML =
      "<p>Generating offer letter...</p>";
    document.getElementById("confirmOfferBtn").style.display = "none";

    // Map mode_of_internship to display format
    const modeMapping = {
      online: "remote-based opportunity",
      offline: "on-site based opportunity",
      hybrid: "hybrid-based opportunity",
    };

    // Get the actual mode from applicant data and map it
    const rawMode = applicantData.mode_of_internship || "online";
    const displayMode = modeMapping[rawMode.toLowerCase()] || rawMode;

    // Call the new generate offer letter endpoint
    const generateResponse = await fetch(
      "/admin/api/generate-offer-letter-preview",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: applicantData.application_id,
          source: "paid",
          name: applicantData.name,
          usn: applicantData.usn,
          college: applicantData.college,
          email: applicantData.email,
          domain: domain,
          mode_of_internship: displayMode,
          internship_type: "paid",
          duration: "3 months", // Default for paid internship
        }),
      }
    );

    if (!generateResponse.ok) {
      const errorData = await generateResponse.json();
      throw new Error(errorData.error || "Failed to generate offer letter");
    }

    const generateData = await generateResponse.json();
    if (!generateData.success) {
      throw new Error(generateData.error || "Offer letter generation failed");
    }

    // Store for confirmation
    currentOfferLetterData = {
      candidate_id: applicantData.application_id,
      source: "paid",
      name: applicantData.name,
      usn: applicantData.usn,
      email: applicantData.email,
      college: applicantData.college,
      domain: domain,
      mode_of_internship: displayMode,
      internship_type: "paid",
      duration: 3, // 3 months for paid
      pdf_b64: generateData.pdf_data,
      reference_number: generateData.reference_number,
    };

    // Display the PDF
    document.getElementById(
      "offerLetterTitle"
    ).textContent = `Offer Letter - ${generateData.reference_number}`;
    const container = document.getElementById("offerLetterContainer");
    const iframe = document.createElement("iframe");
    iframe.src = `data:application/pdf;base64,${generateData.pdf_data}`;
    iframe.style.width = "100%";
    iframe.style.height = "100%";
    iframe.style.border = "none";
    iframe.style.borderRadius = "4px";

    container.innerHTML = "";
    container.appendChild(iframe);

    // Show confirm button
    document.getElementById("confirmOfferBtn").style.display = "block";

    console.log(
      "✓ Offer letter displayed for paid internship, waiting for confirmation"
    );
  } catch (error) {
    console.error("Error generating offer letter for paid internship:", error);
    document.getElementById("offerLetterContainer").innerHTML = `
      <div style="color: #d32f2f; padding: 2rem; text-align: center;">
        <p>❌ Error: ${error.message}</p>
        <p style="font-size: 0.9rem; margin-top: 1rem; color: #666;">Please try again.</p>
      </div>
    `;
    document.getElementById("confirmOfferBtn").style.display = "none";
  }
}

function closeOfferLetterModal() {
  const modal = document.getElementById("offerLetterModal");
  if (modal) {
    modal.classList.remove("show");
  }
  currentOfferLetterData = null;
}

async function confirmOfferLetter() {
  if (!currentOfferLetterData) {
    alert("No offer letter data available");
    return;
  }

  try {
    // Save data BEFORE closing modal (which sets currentOfferLetterData to null)
    const candidateData = currentOfferLetterData;
    
    console.log("✓ Processing offer letter workflow...");
    closeOfferLetterModal();

    // For paid internships, use independent endpoints
    if (candidateData.source === "paid") {
      await confirmOfferLetterPaid(candidateData);
    } else {
      // For approved candidates, use the old endpoint
      await confirmOfferLetterApproved(candidateData);
    }

    currentOfferLetterData = null;
  } catch (error) {
    console.error("Error confirming offer letter:", error);
    alert("❌ Error: " + error.message);
  }
}

async function confirmOfferLetterPaid(candidateData) {
  try {
    console.log("✓ Processing PAID internship workflow...");

    const emailData = {
      email: candidateData.email,
      name: candidateData.name,
      pdf_b64: candidateData.pdf_b64,
      reference_number: candidateData.reference_number,
    };

    const transferData = {
      usn: candidateData.usn,
      application_id: candidateData.candidate_id,
      name: candidateData.name,
      email: candidateData.email,
      phone: candidateData.phone || "",
      domain: candidateData.domain,
      college: candidateData.college,
      year: candidateData.year || "",
      qualification: candidateData.qualification || "",
      branch: candidateData.branch || "",
      project_description: candidateData.project_description || "",
      project_name: candidateData.project_name || "",
      project_title: candidateData.project_title || "",
      duration_months: candidateData.duration || 3,
      pdf_b64: candidateData.pdf_b64,
      reference_number: candidateData.reference_number,
    };

    let emailStatus = { success: false, message: "Not attempted" };
    let transferStatus = { success: false, message: "Not attempted" };

    // Step 1: Send email (independent - errors here should not block data transfer)
    console.log("📧 Step 1: Sending offer letter email...");
    try {
      const emailResponse = await fetch("/admin/api/send-paid-offer-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(emailData),
      });

      if (emailResponse.ok) {
        emailStatus = await emailResponse.json();
        console.log("✓ Email step completed:", emailStatus);
      } else {
        const errorData = await emailResponse.json();
        emailStatus = {
          success: false,
          message: errorData.error || "Email send failed",
        };
        console.warn("⚠️ Email send returned error status:", errorData);
      }
    } catch (emailError) {
      emailStatus = {
        success: false,
        message: `Email error: ${emailError.message}`,
      };
      console.warn("⚠️ Email send threw exception:", emailError);
    }

    // Step 2: Transfer data to Selected (independent - should work even if email fails)
    console.log("📦 Step 2: Transferring candidate to Selected table...");
    try {
      const transferResponse = await fetch(
        "/admin/api/transfer-paid-to-selected",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(transferData),
        }
      );

      if (!transferResponse.ok) {
        const errorData = await transferResponse.json();
        throw new Error(errorData.error || "Failed to transfer candidate");
      }

      transferStatus = await transferResponse.json();
      console.log("✓ Transfer step completed:", transferStatus);

      if (!transferStatus.success) {
        throw new Error(transferStatus.error || "Transfer failed");
      }
    } catch (transferError) {
      transferStatus = {
        success: false,
        message: `Transfer error: ${transferError.message}`,
      };
      console.error("❌ Transfer error:", transferError);
      throw transferError; // Transfer is critical - fail if it doesn't work
    }

    // Step 3: Show summary to user
    console.log("✓ Workflow complete!");

    let successMessage = "✓ Success! ";
    let warningMessages = [];

    if (transferStatus.success) {
      successMessage += `Candidate ${candidateData.name} moved to Selected (ID: ${transferStatus.selected_candidate_id}). `;
    }

    if (!emailStatus.success) {
      warningMessages.push(
        `⚠️ Email: ${emailStatus.message}`
      );
    } else {
      successMessage += "Offer letter email sent. ";
    }

    if (warningMessages.length > 0) {
      alert(successMessage + "\n\n" + warningMessages.join("\n"));
    } else {
      alert(successMessage);
    }

    // Reload the table
    loadInternships(currentType);
  } catch (error) {
    console.error("Error in confirmOfferLetterPaid:", error);
    throw error;
  }
}

async function confirmOfferLetterApproved(candidateData) {
  try {
    console.log("✓ Processing APPROVED candidate workflow...");

    // Call the confirm endpoint
    const confirmResponse = await fetch("/admin/api/confirm-offer-letter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(candidateData),
    });

    if (!confirmResponse.ok) {
      const errorData = await confirmResponse.json();
      throw new Error(errorData.error || "Failed to confirm offer letter");
    }

    const confirmData = await confirmResponse.json();
    if (!confirmData.success) {
      throw new Error(confirmData.error || "Confirmation failed");
    }

    console.log(
      "✓ Offer letter confirmed, email sent, candidate moved to Selected"
    );
    alert(
      "✓ Success! Offer letter sent to " +
        candidateData.email +
        " and candidate moved to Selected table."
    );

    // Reload the table
    loadInternships(currentType);
  } catch (error) {
    console.error("Error in confirmOfferLetterApproved:", error);
    throw error;
  }
}

function viewFile(internshipId, fileType, internshipType) {
  // Build the file viewer URL
  const fileViewUrl = `/admin/serve-file-inplace/${internshipId}/${fileType}?type=${internshipType}`;

  // Map file types to display names
  const fileTypeLabels = {
    id_proof: "ID Proof",
    resume: "Resume",
    project: "Project",
    payment: "Payment Screenshot",
  };

  const fileName = fileTypeLabels[fileType] || fileType;

  // Display in modal using the existing displayFileUrlInModal function
  displayFileUrlInModal(fileViewUrl, fileName, fileType);
}

function viewProfile(internshipId, internshipType) {
  // Fetch profile data
  fetch(`/admin/api/get-profile/${internshipId}?type=${internshipType}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProfileModal(data.data);
      } else {
        alert("Error loading profile: " + (data.error || "Unknown"));
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error loading profile");
    });
}

function showProfileModal(profileData) {
  // Create a read-only profile display modal
  const profileContainer = document.createElement("div");
  profileContainer.className = "modal";
  profileContainer.id = "profileViewModal";
  profileContainer.style.display = "block";

  let profileHTML = '<div style="padding: 20px;"><h3>Candidate Profile</h3>';

  // Exclude file-related and non-relevant columns
  const excludeColumns = [
    "id",
    "id_proof",
    "resume",
    "project_document",
    "payment_screenshot",
    "id_proof_content",
    "resume_content",
    "project_document_content",
    "paid_internship_content",
    "free_internship_content",
    "created_at",
    "updated_at",
    "reason",
    "applicationid",
    "application_id",
    "status",
  ];

  profileHTML +=
    '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">';

  for (const [key, value] of Object.entries(profileData)) {
    if (!excludeColumns.includes(key.toLowerCase())) {
      const displayKey = key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
      const displayValue = (value || "N/A").toString().trim();

      profileHTML += `
        <div style="padding: 12px; background: #f5f5f5; border-radius: 6px;">
          <strong style="color: #333; font-size: 13px;">${displayKey}</strong>
          <p style="margin: 8px 0 0 0; color: #666; font-size: 14px;">${displayValue}</p>
        </div>
      `;
    }
  }

  profileHTML += "</div>";
  profileHTML +=
    '<div style="margin-top: 20px;"><button onclick="closeProfileModal()" class="table-action-btn table-edit-btn" style="width: 100%;">Close</button></div>';
  profileHTML += "</div>";

  profileContainer.innerHTML = `
    <div class="modal-content" style="width: 90%; max-width: 800px; max-height: 80vh; overflow-y: auto;">
      <div class="modal-header">
        <h3>Candidate Profile</h3>
        <button class="modal-close" onclick="closeProfileModal()">✕</button>
      </div>
      <div style="padding: 20px; overflow-y: auto;">
        ${profileHTML}
      </div>
    </div>
  `;

  document.body.appendChild(profileContainer);
}

function closeProfileModal() {
  const modal = document.getElementById("profileViewModal");
  if (modal) {
    modal.remove();
  }
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
  downloadBtn.style.display = "inline-flex";

  // Display PDF in iframe
  fileViewerContainer.innerHTML = `<iframe id="fileFrame" src="${fileUrl}" style="width:100%;height:100%;border:none;"></iframe>`;
  fileModal.classList.add("show");
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

/**
 * Frontend Controller for Basant Jamini Bhawan Welfare Association - Automation Hub
 * Manages mode switching, tab routing, file upload, verification modal, ledger editing,
 * FIFO dues allocation, live rate registry, and PDF generation.
 */

// Application State
const state = {
    mode: "COMMERCIAL",
    activeTab: "tabUpload",
    configs: {},
    allLedgerRecords: [],
    ledgerColumns: [],
    ledgerRecords: [],
    selectedLedgerIndices: new Set(),
    selectedFlatIndexForEdit: null,
    extractedUploadData: null,
    currentPdfBlobUrl: null,
    isAdmin: false,
    authToken: localStorage.getItem("bjbwa_admin_token") || null
};

// Initial Load
document.addEventListener("DOMContentLoaded", async () => {
    setupDragAndDrop();
    await checkAdminAuth();
    if (state.isAdmin) {
        await loadInitialConfigs();
        setupEventListeners();
        refreshUIForCurrentMode();
        loadLedgerData();
        loadDuesData();
        checkGoogleSheetsStatus();
    }
});

// ----------------- ADMIN AUTHENTICATION -----------------

async function authFetch(url, options = {}) {
    const headers = options.headers || {};
    if (state.authToken) {
        headers["X-Admin-Token"] = state.authToken;
        headers["Authorization"] = `Bearer ${state.authToken}`;
    }
    options.headers = headers;

    const res = await fetch(url, options);
    if (res.status === 401) {
        state.isAdmin = false;
        state.authToken = null;
        localStorage.removeItem("bjbwa_admin_token");
        renderAdminUI();
        const errBox = document.getElementById("adminPageLoginError");
        if (errBox) {
            errBox.innerText = "🔒 Session expired or login required. Please sign in.";
            errBox.style.display = "block";
        }
        throw new Error("Admin authentication required.");
    }
    return res;
}

async function checkAdminAuth() {
    if (!state.authToken) {
        state.isAdmin = false;
        renderAdminUI();
        return;
    }
    try {
        const res = await fetch("/api/auth/status", {
            headers: { "X-Admin-Token": state.authToken }
        });
        const data = await res.json();
        state.isAdmin = !!data.is_admin;
        if (!state.isAdmin) {
            state.authToken = null;
            localStorage.removeItem("bjbwa_admin_token");
        }
    } catch (e) {
        state.isAdmin = false;
    }
    renderAdminUI();
}

function renderAdminUI() {
    const loginScreen = document.getElementById("adminLoginScreen");
    const workingContainer = document.getElementById("appWorkingContainer");

    if (state.isAdmin) {
        if (loginScreen) loginScreen.style.display = "none";
        if (workingContainer) workingContainer.style.display = "block";
    } else {
        if (workingContainer) workingContainer.style.display = "none";
        if (loginScreen) {
            loginScreen.style.display = "flex";
            setTimeout(() => {
                const pIn = document.getElementById("adminGatePassword");
                if (pIn) pIn.focus();
            }, 100);
        }
    }
}

function openAdminLoginModal(msg = null) {
    state.isAdmin = false;
    renderAdminUI();
    const errBox = document.getElementById("adminPageLoginError");
    if (errBox) {
        if (msg) {
            errBox.innerText = msg;
            errBox.style.display = "block";
        } else {
            errBox.style.display = "none";
        }
    }
}

// ----------------- SYMBOLIC LOADING INDICATOR -----------------

function showLoading(title = "Processing Operation...", subtext = "Please wait while the system completes this action.", symbol = "⚡") {
    const overlay = document.getElementById("globalLoadingOverlay");
    if (!overlay) return;
    const titleElem = document.getElementById("loadingTitle");
    const subtextElem = document.getElementById("loadingSubtext");
    const iconElem = document.getElementById("loadingSymbolIcon");
    if (titleElem) titleElem.innerText = title;
    if (subtextElem) subtextElem.innerText = subtext;
    if (iconElem) iconElem.innerText = symbol;
    overlay.style.display = "flex";
}

function hideLoading() {
    const overlay = document.getElementById("globalLoadingOverlay");
    if (overlay) overlay.style.display = "none";
}

async function handleAdminLoginSubmit(e) {
    if (e) e.preventDefault();
    const uIn = document.getElementById("adminGateUsername");
    const pIn = document.getElementById("adminGatePassword");
    const username = uIn ? uIn.value.trim() : "";
    const password = pIn ? pIn.value : "";
    const errBox = document.getElementById("adminPageLoginError");
    const btnSubmit = document.getElementById("btnAdminGateSubmit");

    if (!username || !password) {
        if (errBox) {
            errBox.innerText = "Please enter both username and password.";
            errBox.style.display = "block";
        }
        return;
    }

    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = "<span>⏳ Authenticating...</span>";
    }

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            const err = await res.json();
            if (errBox) {
                errBox.innerText = err.detail || "Invalid admin username or password.";
                errBox.style.display = "block";
            }
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = "<span>🔓 Log In to Portal</span>";
            }
            return;
        }

        const data = await res.json();
        state.authToken = data.token;
        state.isAdmin = true;
        localStorage.setItem("bjbwa_admin_token", data.token);

        if (errBox) errBox.style.display = "none";
        if (pIn) pIn.value = "";

        renderAdminUI();

        // Load full working data now that user is verified
        await loadInitialConfigs();
        setupEventListeners();
        refreshUIForCurrentMode();
        loadLedgerData();
        loadDuesData();
        checkGoogleSheetsStatus();
    } catch (err) {
        if (errBox) {
            errBox.innerText = "Login connection error: " + err.message;
            errBox.style.display = "block";
        }
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = "<span>🔓 Log In to Portal</span>";
        }
    }
}

async function logoutAdmin() {
    if (state.authToken) {
        try {
            await fetch("/api/auth/logout", {
                method: "POST",
                headers: { "X-Admin-Token": state.authToken }
            });
        } catch (e) {}
    }
    state.authToken = null;
    state.isAdmin = false;
    localStorage.removeItem("bjbwa_admin_token");
    renderAdminUI();
}

async function updateAdminPassword() {
    if (!state.isAdmin) {
        renderAdminUI();
        return;
    }

    const oldP = document.getElementById("adminOldPassInput").value;
    const newP = document.getElementById("adminNewPassInput").value;

    if (!oldP || !newP) {
        alert("Please enter both current and new password.");
        return;
    }

    try {
        const res = await authFetch("/api/auth/change-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password: oldP, new_password: newP })
        });

        const data = await res.json();
        if (res.ok) {
            alert("✅ " + data.message);
            document.getElementById("adminOldPassInput").value = "";
            document.getElementById("adminNewPassInput").value = "";
            logoutAdmin();
            openAdminLoginModal("Password changed. Please log in with your new password.");
        } else {
            alert("❌ Failed: " + (data.detail || "Error changing password"));
        }
    } catch (e) {
        alert("❌ Error: " + e.message);
    }
}

// Setup drag and drop for upload zone
function setupDragAndDrop() {
    const dropzone = document.getElementById("uploadDropzone");
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
        }, false);
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
}

function setupEventListeners() {
    document.getElementById("globalModeSelect").addEventListener("change", (e) => {
        state.mode = e.target.value;
        refreshUIForCurrentMode();
    });

    // Default payment date to today in dues tab
    const todayStr = getTodayFormatted();
    const duesDateInput = document.getElementById("entDuesDatePaid");
    if (duesDateInput) duesDateInput.value = todayStr;
}

function getTodayFormatted() {
    const d = new Date();
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
}

// ----------------- TAB SWITCHING -----------------

function switchTab(tabId) {
    state.activeTab = tabId;
    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));

    const targetPane = document.getElementById(tabId);
    if (targetPane) targetPane.classList.add("active");

    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabMap = {
        tabUpload: 0,
        tabLedger: 1,
        tabDues: 2,
        tabSettings: 3,
        tabNotices: 4
    };
    if (tabButtons[tabMap[tabId]]) {
        tabButtons[tabMap[tabId]].classList.add("active");
    }

    if (tabId === "tabLedger") {
        loadLedgerData();
    } else if (tabId === "tabDues") {
        loadDuesData();
    } else if (tabId === "tabSettings") {
        refreshLiveSettingsGrid();
    }
}

function resetFieldBuffers() {
    document.getElementById("entManualPrev").value = "";
    document.getElementById("entManualCurr").value = "";
    document.getElementById("entManualMisc").value = "0";
    document.getElementById("editOpenReading").value = "";
    document.getElementById("editCloseReading").value = "";
    document.getElementById("entPartialPayment").value = "";
    document.getElementById("filterFlat").value = "";
    document.getElementById("filterMonth").value = "";
    document.getElementById("filterYear").value = "";
    state.selectedLedgerIndices.clear();
    state.selectedFlatIndexForEdit = null;
    loadLedgerData();
    alert("✅ Field buffers reset successfully.");
}

// ----------------- CONFIGURATIONS & MODE SWITCHING -----------------

async function loadInitialConfigs() {
    try {
        const res = await fetch("/api/config");
        const data = await res.json();
        state.configs = data;

        // Set RPU fields
        const rpu = data.rpu_rates || {};
        document.getElementById("entRpuDomestic").value = (rpu.domestic || 5.4).toFixed(2);
        document.getElementById("entRpuCommercial").value = (rpu.commercial || 6.9).toFixed(2);

        // Set Notice text
        document.getElementById("txtGlobalInstructions").value = data.notice_text || "";

        renderFlatsChecklist();
        populateManualFlatDropdown();
    } catch (e) {
        console.error("Error loading configs:", e);
    }
}

function refreshUIForCurrentMode() {
    const isDomestic = (state.mode === "DOMESTIC");

    // Toggle common meter controls
    document.getElementById("domesticCommonMeterGroup").style.display = isDomestic ? "flex" : "none";
    document.getElementById("avgLookupFrame").style.display = isDomestic ? "block" : "none";

    // Template example
    const templateTitle = document.getElementById("templateCardTitle");
    const exampleBox = document.getElementById("lblExampleBox");

    if (isDomestic) {
        templateTitle.innerText = "📋 Required File Formatting Template Example (DOMESTIC)";
        exampleBox.innerText = `Due Month: AUG-2026\nCommon  12450   12810\nA-2     45100   45320\nB-2     38900   39150\nC-2     67200   67450`;
    } else {
        templateTitle.innerText = "📋 Required File Formatting Template Example (COMMERCIAL)";
        exampleBox.innerText = `Due Month: AUG-2026\nG-1   53498   54622\nG-2   69752   75090\nA-1   82446   82907\nF-2   35359   35497`;
    }

    renderFlatsChecklist();
    populateManualFlatDropdown();
    loadLedgerData();
    loadDuesData();
    refreshLiveSettingsGrid();
}

function getCurrentFlatConfig() {
    return (state.mode === "COMMERCIAL")
        ? (state.configs.commercial_config || {})
        : (state.configs.domestic_config || {});
}

function populateManualFlatDropdown() {
    const dropdown = document.getElementById("comboManualFlat");
    dropdown.innerHTML = "";
    const cfg = getCurrentFlatConfig();

    for (const key of Object.keys(cfg)) {
        if (cfg[key].is_common) continue;
        const opt = document.createElement("option");
        opt.value = key;
        opt.innerText = `${key} (${cfg[key].tenant || 'N/A'})`;
        dropdown.appendChild(opt);
    }
}

function renderFlatsChecklist() {
    const container = document.getElementById("flatsChecklist");
    container.innerHTML = "";
    const cfg = getCurrentFlatConfig();

    for (const key of Object.keys(cfg)) {
        if (cfg[key].is_common) continue;

        const label = document.createElement("label");
        label.className = "checklist-item";

        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.value = key;
        chk.className = "flat-chk";
        chk.addEventListener("change", onConfigFieldChanged);

        label.appendChild(chk);
        label.appendChild(document.createTextNode(` Flat ${key} [${cfg[key].tenant || 'N/A'}]`));
        container.appendChild(label);
    }
}

function toggleAllFlats(select) {
    document.querySelectorAll(".flat-chk").forEach(chk => chk.checked = select);
    onConfigFieldChanged();
}

// ----------------- TAB 1: FILE UPLOAD & VERIFICATION -----------------

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

async function uploadFile(file) {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to upload and parse documents.");
        return;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", state.mode);

    showLoading("⚡ Reading & Parsing Meter File...", `Extracting meter readings and month data from ${file.name}...`, "⚡");

    try {
        const res = await authFetch("/api/upload", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ Upload Failed: " + (err.detail || "Error parsing file."));
            return;
        }

        const data = await res.json();
        state.extractedUploadData = data;
        openVerifyModal(data);
    } catch (e) {
        alert("❌ Error during file upload: " + e.message);
    } finally {
        hideLoading();
    }
}

function openVerifyModal(data) {
    const tableBody = document.getElementById("verifyTableBody");
    tableBody.innerHTML = "";

    // Populate Month and Year inputs
    const vMonth = document.getElementById("verifyMonth");
    const vYear = document.getElementById("verifyYear");
    if (vMonth) vMonth.value = data.month || "JAN";
    if (vYear) vYear.value = data.year || String(new Date().getFullYear());

    const metrics = data.extracted_metrics || {};

    for (const [flat, readings] of Object.entries(metrics)) {
        const tr = document.createElement("tr");

        const tdFlat = document.createElement("td");
        tdFlat.style.fontWeight = "bold";
        tdFlat.innerText = flat;
        tr.appendChild(tdFlat);

        const tdOpen = document.createElement("td");
        const inpOpen = document.createElement("input");
        inpOpen.type = "number";
        inpOpen.className = "form-control form-control-sm verify-reading-input";
        inpOpen.style.width = "120px";
        inpOpen.style.textAlign = "center";
        inpOpen.value = readings[0] || 0.0;
        inpOpen.dataset.flat = flat;
        inpOpen.dataset.field = "open";
        tdOpen.appendChild(inpOpen);
        tr.appendChild(tdOpen);

        const tdClose = document.createElement("td");
        const inpClose = document.createElement("input");
        inpClose.type = "number";
        inpClose.className = "form-control form-control-sm verify-reading-input";
        inpClose.style.width = "120px";
        inpClose.style.textAlign = "center";
        inpClose.value = readings[1] || 0.0;
        inpClose.dataset.flat = flat;
        inpClose.dataset.field = "close";
        tdClose.appendChild(inpClose);
        tr.appendChild(tdClose);

        tableBody.appendChild(tr);
    }

    document.getElementById("verifyModal").classList.add("active");
}

function closeVerifyModal() {
    document.getElementById("verifyModal").classList.remove("active");
    state.extractedUploadData = null;
    document.getElementById("fileInput").value = "";
}

async function confirmProcessedBills() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to generate and save bills.");
        return;
    }

    // Read directly from verify modal inputs or fallback to state
    const inputMonth = document.getElementById("verifyMonth")?.value?.trim().toUpperCase();
    const inputYear = document.getElementById("verifyYear")?.value?.trim();
    
    const targetMonth = inputMonth || state.extractedUploadData?.month || "JAN";
    const targetYear = inputYear || state.extractedUploadData?.year || String(new Date().getFullYear());

    // Collect edited readings from modal table
    const updatedMetrics = {};
    document.querySelectorAll(".verify-reading-input").forEach(inp => {
        const flat = inp.dataset.flat;
        const field = inp.dataset.field;
        const val = parseFloat(inp.value.trim()) || 0.0;
        if (!updatedMetrics[flat]) updatedMetrics[flat] = [0.0, 0.0];
        if (field === "open") updatedMetrics[flat][0] = val;
        if (field === "close") updatedMetrics[flat][1] = val;
    });

    if (Object.keys(updatedMetrics).length === 0) {
        alert("⚠️ No readings found to process. Please upload the file again.");
        return;
    }

    // Check for open > close
    for (const [flat, r] of Object.entries(updatedMetrics)) {
        if (r[0] > r[1]) {
            alert(`❌ Error: Opening reading (${r[0]}) cannot exceed closing reading (${r[1]}) at Flat ${flat}!`);
            return;
        }
    }

    const cmOpenElem = document.getElementById("entCmOpen");
    const cmCloseElem = document.getElementById("entCmClose");
    const commonOpen = cmOpenElem ? (parseFloat(cmOpenElem.value) || null) : null;
    const commonClose = cmCloseElem ? (parseFloat(cmCloseElem.value) || null) : null;

    showLoading("⚙️ Processing Bills & Generating Master PDF...", `Saving records and compiling statements for ${targetMonth}-${targetYear}...`, "⚙️");

    try {
        const res = await authFetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                target_month: targetMonth,
                target_year: targetYear,
                extracted_metrics: updatedMetrics,
                common_open: commonOpen,
                common_close: commonClose
            })
        });

        const result = await res.json();
        closeVerifyModal();

        if (result.status === "success") {
            showLoading("📄 Generating PDF Statement for All Flats...", `Compiled bills for ${result.added_count} flat(s). Generating automated PDF...`, "📄");
            await loadLedgerData();

            // Gather all records for targetMonth and targetYear to compile master PDF
            const matchingIndices = state.allLedgerRecords
                .map((r, i) => ({ r, i }))
                .filter(x => String(x.r.Due_Month || "").trim().toUpperCase() === targetMonth.toUpperCase() && String(x.r.Billing_Year || "").trim() === targetYear)
                .map(x => x.i);

            if (matchingIndices.length > 0) {
                try {
                    const printRes = await fetch("/api/print", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            mode: state.mode,
                            indices: matchingIndices
                        })
                    });

                    if (printRes.ok) {
                        const blob = await printRes.blob();
                        if (state.currentPdfBlobUrl) {
                            URL.revokeObjectURL(state.currentPdfBlobUrl);
                        }
                        state.currentPdfBlobUrl = URL.createObjectURL(blob);
                        document.getElementById("pdfViewerFrame").src = state.currentPdfBlobUrl;
                        document.getElementById("pdfModal").classList.add("active");
                    }
                } catch (pdfErr) {
                    console.error("Auto PDF compilation error:", pdfErr);
                }
            }

            hideLoading();
            switchTab("tabLedger");

            let msg = `✅ Successfully created ${result.added_count} bill statement(s) for ${targetMonth}-${targetYear}!\n📄 The automated PDF statements for all flats have been generated and displayed.`;
            if (result.skipped_flats && result.skipped_flats.length > 0) {
                msg += `\n⚠️ Skipped duplicates for: ${result.skipped_flats.join(', ')}`;
            }
            alert(msg);
        } else {
            hideLoading();
            alert("⚠️ Warning: " + (result.message || "Failed to process bills."));
        }
    } catch (e) {
        hideLoading();
        alert("❌ Error processing bills: " + e.message);
    }
}

async function executeLiveAverageLookup() {
    const year = document.getElementById("comboLookupYear").value;
    const month = document.getElementById("comboLookupMonth").value;

    try {
        const res = await fetch(`/api/average-lookup?month=${month}&year=${year}`);
        const data = await res.json();
        document.getElementById("entLookupOutput").value = data.average_units || "0.00 Units";
    } catch (e) {
        console.error(e);
    }
}

async function processManualBill() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to create bills.");
        return;
    }

    const flatNo = document.getElementById("comboManualFlat").value;
    const month = document.getElementById("comboManualMonth").value;
    const year = document.getElementById("comboManualYear").value;
    const openR = parseFloat(document.getElementById("entManualPrev").value);
    const closeR = parseFloat(document.getElementById("entManualCurr").value);
    const misc = parseFloat(document.getElementById("entManualMisc").value) || 0.0;

    if (isNaN(openR) || isNaN(closeR)) {
        alert("❌ Please input valid numeric opening and closing readings.");
        return;
    }
    if (openR > closeR) {
        alert("❌ Opening reading cannot exceed closing reading.");
        return;
    }

    const commonOpen = parseFloat(document.getElementById("entCmOpen").value) || null;
    const commonClose = parseFloat(document.getElementById("entCmClose").value) || null;

    showLoading("📝 Calculating & Saving Manual Bill...", `Computing charges for Flat ${flatNo} (${month}-${year})...`, "📝");

    try {
        const res = await authFetch("/api/process-manual", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                flat_no: flatNo,
                month: month,
                year: year,
                open_reading: openR,
                close_reading: closeR,
                others_charge: misc,
                common_open: commonOpen,
                common_close: commonClose
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ Failed: " + (err.detail || "Error generating manual bill."));
            return;
        }

        alert(`✅ Successfully created bill for Flat ${flatNo} (${month}-${year})!`);
        loadLedgerData();
        switchTab("tabLedger");
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

// ----------------- TAB 2: MASTER LEDGER DATABASE -----------------

async function loadLedgerData(refreshCloud = false) {
    try {
        const url = `/api/ledger?mode=${state.mode}${refreshCloud ? '&refresh=true' : ''}`;
        const res = await fetch(url);
        const data = await res.json();
        state.allLedgerRecords = data.records || [];
        state.ledgerColumns = data.columns || [];
        applyLedgerFilters();
    } catch (e) {
        console.error("Error loading ledger:", e);
    }
}

function applyLedgerFilters() {
    const flatFilter = (document.getElementById("filterFlat")?.value || "").trim().toLowerCase();
    const monthFilter = (document.getElementById("filterMonth")?.value || "").trim().toLowerCase();
    const yearFilter = (document.getElementById("filterYear")?.value || "").trim().toLowerCase();

    if (!flatFilter && !monthFilter && !yearFilter) {
        state.ledgerRecords = state.allLedgerRecords || [];
    } else {
        state.ledgerRecords = (state.allLedgerRecords || []).filter(r => {
            if (flatFilter && !String(r.Flat_No || "").toLowerCase().includes(flatFilter)) return false;
            if (monthFilter && !String(r.Due_Month || "").toLowerCase().includes(monthFilter)) return false;
            if (yearFilter && !String(r.Billing_Year || "").toLowerCase().includes(yearFilter)) return false;
            return true;
        });
    }

    renderLedgerTable(state.ledgerColumns, state.ledgerRecords);
}

function renderLedgerTable(columns, records) {
    const headRow = document.getElementById("ledgerTableHeadRow");
    const body = document.getElementById("ledgerTableBody");

    headRow.innerHTML = "";
    body.innerHTML = "";

    // Selection checkbox column
    const thSelect = document.createElement("th");
    thSelect.style.width = "40px";
    const chkSelectAll = document.createElement("input");
    chkSelectAll.type = "checkbox";
    chkSelectAll.title = "Select All";
    chkSelectAll.onchange = (e) => {
        state.selectedLedgerIndices.clear();
        if (e.target.checked) {
            records.forEach(r => state.selectedLedgerIndices.add(r._index));
        }
        document.querySelectorAll(".ledger-row-chk").forEach(c => c.checked = e.target.checked);
        document.querySelectorAll("#ledgerTableBody tr").forEach(tr => {
            if (e.target.checked) tr.classList.add("selected");
            else tr.classList.remove("selected");
        });
    };
    thSelect.appendChild(chkSelectAll);
    headRow.appendChild(thSelect);

    // Headers
    columns.forEach(col => {
        const th = document.createElement("th");
        th.innerText = col.replace(/_/g, " ");
        headRow.appendChild(th);
    });

    if (records.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = columns.length + 1;
        td.style.padding = "20px";
        td.innerText = "No records found matching current criteria.";
        tr.appendChild(td);
        body.appendChild(tr);
        return;
    }

    records.forEach(r => {
        const tr = document.createElement("tr");
        const idx = r._index;

        if (state.selectedLedgerIndices.has(idx)) {
            tr.classList.add("selected");
        }

        // Click to load for editing
        tr.onclick = (e) => {
            if (e.target.tagName === "INPUT") return;
            selectRowForEditing(r, tr);
        };

        // Selection checkbox cell
        const tdChk = document.createElement("td");
        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.className = "ledger-row-chk";
        chk.checked = state.selectedLedgerIndices.has(idx);
        chk.onchange = (e) => {
            if (e.target.checked) {
                state.selectedLedgerIndices.add(idx);
                tr.classList.add("selected");
            } else {
                state.selectedLedgerIndices.delete(idx);
                tr.classList.remove("selected");
            }
        };
        tdChk.appendChild(chk);
        tr.appendChild(tdChk);

        // Data cells
        columns.forEach(col => {
            const td = document.createElement("td");
            let val = r[col];

            if (typeof val === "number" && (col.includes("Rs") || col.includes("Units") || col.includes("Reading"))) {
                val = val.toFixed(2);
            }

            if (col === "Payment_Status") {
                td.style.fontWeight = "bold";
                td.style.color = (val === "PAID") ? "#047857" : "#dc2626";
            }

            td.innerText = (val !== null && val !== undefined) ? val : "";
            tr.appendChild(td);
        });

        body.appendChild(tr);
    });
}

function selectRowForEditing(record, trElement) {
    state.selectedFlatIndexForEdit = record._index;

    // Highlight row
    document.querySelectorAll("#ledgerTableBody tr").forEach(t => t.style.outline = "none");
    trElement.style.outline = "2px solid var(--color-accent)";

    // Populate editor fields
    document.getElementById("editOpenReading").value = Math.round(record.Open_Meter_Reading || 0);
    document.getElementById("editCloseReading").value = Math.round(record.Closing_Meter_Reading || 0);
    document.getElementById("chkBatchPaid").checked = (record.Payment_Status === "PAID");
    document.getElementById("comboBatchReset").value = String(record.Reset || 0);
    document.getElementById("entPartialPayment").value = record.Actual_Due_Rs || "";
}

async function saveHistoricalRowModification() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to modify records.");
        return;
    }

    if (state.selectedFlatIndexForEdit === null) {
        alert("Please click and select a row in the table first.");
        return;
    }

    const openR = parseFloat(document.getElementById("editOpenReading").value);
    const closeR = parseFloat(document.getElementById("editCloseReading").value);
    const isPaid = document.getElementById("chkBatchPaid").checked;
    const resetVal = parseInt(document.getElementById("comboBatchReset").value) || 0;
    const partialVal = parseFloat(document.getElementById("entPartialPayment").value) || 0.0;

    if (isNaN(openR) || isNaN(closeR) || openR > closeR) {
        alert("❌ Invalid meter readings: opening cannot exceed closing reading.");
        return;
    }

    showLoading("💾 Updating & Recalculating Record...", "Recalculating charges with new meter readings...", "💾");

    try {
        const res = await authFetch(`/api/ledger/row/${state.selectedFlatIndexForEdit}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                index: state.selectedFlatIndexForEdit,
                open_reading: openR,
                close_reading: closeR,
                payment_status: isPaid ? "PAID" : "UNPAID",
                reset: resetVal,
                partial_payment: partialVal
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ Update failed: " + (err.detail || "Error"));
            return;
        }

        alert("✅ Record updated and recalculated successfully.");
        loadLedgerData();
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

async function applyBatchPaymentStatus() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to update payment statuses.");
        return;
    }

    if (state.selectedLedgerIndices.size === 0) {
        alert("Please select at least one row using the checkboxes.");
        return;
    }

    const isPaid = document.getElementById("chkBatchPaid").checked;
    const statusStr = isPaid ? "PAID" : "UNPAID";

    showLoading("⚡ Updating Payment Status...", `Setting status to ${statusStr} for ${state.selectedLedgerIndices.size} selected row(s)...`, "⚡");

    try {
        await authFetch("/api/ledger/batch-status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                indices: Array.from(state.selectedLedgerIndices),
                status: statusStr
            })
        });

        alert(`✅ Updated ${state.selectedLedgerIndices.size} row(s) to ${statusStr}.`);
        loadLedgerData();
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

async function applyBatchResetStatus() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to apply resets.");
        return;
    }

    if (state.selectedLedgerIndices.size === 0) {
        alert("Please select at least one row using the checkboxes.");
        return;
    }

    const resetVal = parseInt(document.getElementById("comboBatchReset").value) || 0;

    showLoading("⚙️ Updating Reset Configuration...", `Applying reset value ${resetVal} to ${state.selectedLedgerIndices.size} selected row(s)...`, "⚙️");

    try {
        await authFetch("/api/ledger/batch-reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                indices: Array.from(state.selectedLedgerIndices),
                reset_val: resetVal
            })
        });

        alert(`✅ Updated Reset value to ${resetVal} for ${state.selectedLedgerIndices.size} row(s).`);
        loadLedgerData();
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

async function applyPartialPayment() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to record payments.");
        return;
    }

    if (state.selectedFlatIndexForEdit === null) {
        alert("Please click and select a row in the table first.");
        return;
    }

    const pAmt = parseFloat(document.getElementById("entPartialPayment").value);
    if (isNaN(pAmt) || pAmt <= 0) {
        alert("Please input a valid positive payment amount.");
        return;
    }

    showLoading("💳 Recording Partial Payment...", `Recording Rs. ${pAmt.toFixed(2)} payment...`, "💳");

    try {
        const res = await authFetch("/api/ledger/partial-pay", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                index: state.selectedFlatIndexForEdit,
                payment_amount: pAmt
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ " + (err.detail || "Partial payment failed."));
            return;
        }

        alert(`✅ Partial payment of Rs. ${pAmt.toFixed(2)} recorded successfully.`);
        loadLedgerData();
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

async function deleteSelectedLedgerRecords() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to delete records.");
        return;
    }

    if (state.selectedLedgerIndices.size === 0) {
        alert("Please select rows using the checkboxes to delete.");
        return;
    }

    if (!confirm(`Are you sure you want to permanently delete ${state.selectedLedgerIndices.size} record(s)?`)) {
        return;
    }

    showLoading("🗑️ Deleting Records...", `Permanently removing ${state.selectedLedgerIndices.size} selected row(s)...`, "🗑️");

    try {
        const res = await authFetch("/api/ledger/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                indices: Array.from(state.selectedLedgerIndices)
            })
        });

        const data = await res.json();
        alert(`✅ Deleted ${data.deleted_count} record(s).`);
        state.selectedLedgerIndices.clear();
        state.selectedFlatIndexForEdit = null;
        loadLedgerData();
    } catch (e) {
        alert("❌ Error deleting records: " + e.message);
    } finally {
        hideLoading();
    }
}

async function handleLedgerImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    alert("💡 To import from Excel or CSV, ensure your file columns match the standard ledger columns.");
    // Can be expanded to upload to an import endpoint
}

// Print Statements
async function printSelectedLedgerStatements() {
    if (state.selectedLedgerIndices.size === 0) {
        alert("Please select at least one row using the checkboxes to print.");
        return;
    }

    showLoading("📄 Generating PDF Statements...", `Compiling formatted invoice statements for ${state.selectedLedgerIndices.size} selected flat(s)...`, "📄");

    try {
        const res = await fetch("/api/print", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                indices: Array.from(state.selectedLedgerIndices)
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ Failed to generate PDF: " + (err.detail || "Error"));
            return;
        }

        const blob = await res.blob();
        if (state.currentPdfBlobUrl) {
            URL.revokeObjectURL(state.currentPdfBlobUrl);
        }
        state.currentPdfBlobUrl = URL.createObjectURL(blob);

        document.getElementById("pdfViewerFrame").src = state.currentPdfBlobUrl;
        document.getElementById("pdfModal").classList.add("active");
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

async function printAllCurrentMonthStatements() {
    const mInput = document.getElementById("filterMonth")?.value?.trim().toUpperCase();
    const yInput = document.getElementById("filterYear")?.value?.trim();

    let targetRows = [];
    if (mInput || yInput) {
        targetRows = state.allLedgerRecords.map((r, i) => ({ r, i })).filter(x => {
            const mMatch = !mInput || String(x.r.Due_Month || "").trim().toUpperCase().includes(mInput);
            const yMatch = !yInput || String(x.r.Billing_Year || "").trim().includes(yInput);
            return mMatch && yMatch;
        });
    } else {
        // If no filter, take all records from the latest month present in the ledger
        if (state.allLedgerRecords.length > 0) {
            const latestRec = state.allLedgerRecords[state.allLedgerRecords.length - 1];
            const latestMonth = String(latestRec.Due_Month || "").trim().toUpperCase();
            const latestYear = String(latestRec.Billing_Year || "").trim();
            targetRows = state.allLedgerRecords.map((r, i) => ({ r, i })).filter(x => {
                return String(x.r.Due_Month || "").trim().toUpperCase() === latestMonth && String(x.r.Billing_Year || "").trim() === latestYear;
            });
        }
    }

    if (targetRows.length === 0) {
        alert("No ledger records found to print.");
        return;
    }

    const indices = targetRows.map(x => x.i);
    showLoading("📄 Generating PDF for All Flats...", `Compiling printable statements for all ${indices.length} flat(s)...`, "📄");

    try {
        const res = await fetch("/api/print", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                indices: indices
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ Failed to generate PDF: " + (err.detail || "Error"));
            return;
        }

        const blob = await res.blob();
        if (state.currentPdfBlobUrl) {
            URL.revokeObjectURL(state.currentPdfBlobUrl);
        }
        state.currentPdfBlobUrl = URL.createObjectURL(blob);

        document.getElementById("pdfViewerFrame").src = state.currentPdfBlobUrl;
        document.getElementById("pdfModal").classList.add("active");
    } catch (e) {
        alert("❌ Error generating PDF: " + e.message);
    } finally {
        hideLoading();
    }
}

function closePdfModal() {
    document.getElementById("pdfModal").classList.remove("active");
}

function downloadCurrentPdf() {
    if (!state.currentPdfBlobUrl) return;
    const a = document.createElement("a");
    a.href = state.currentPdfBlobUrl;
    a.download = `Billing_Statement_${state.mode}_${new Date().toISOString().slice(0, 10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// ----------------- TAB 3: DUES MANAGEMENT -----------------

async function loadDuesData() {
    const flatSelect = document.getElementById("comboDuesFlat");
    const selectedFlat = flatSelect ? flatSelect.value : "ALL FLATS";

    try {
        const res = await fetch(`/api/dues?mode=${state.mode}&flat=${encodeURIComponent(selectedFlat || 'ALL FLATS')}`);
        const data = await res.json();

        // Populate flats dropdown if needed
        if (flatSelect && flatSelect.options.length <= 1) {
            flatSelect.innerHTML = `<option value="ALL FLATS">ALL FLATS</option>`;
            (data.flats || []).forEach(f => {
                const opt = document.createElement("option");
                opt.value = f;
                opt.innerText = f;
                flatSelect.appendChild(opt);
            });
            flatSelect.value = selectedFlat || "ALL FLATS";
        }

        // KPI metrics
        document.getElementById("kpiTotalDue").innerText = `Rs. ${(data.total_due || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById("kpiTotalPaid").innerText = `Rs. ${(data.total_paid || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById("kpiBalanceLeft").innerText = `Rs. ${(data.balance_left || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

        renderDuesTable(data.records || []);
    } catch (e) {
        console.error("Error loading dues:", e);
    }
}

function renderDuesTable(records) {
    const headRow = document.getElementById("duesTableHeadRow");
    const body = document.getElementById("duesTableBody");

    const cols = ["Flat_No", "Tenant_Name", "Due_Month", "Billing_Year", "Total_Amount_Due_Rs", "Partial_Payment_Rs", "Actual_Due_Rs", "Payment_Status"];

    headRow.innerHTML = "";
    body.innerHTML = "";

    cols.forEach(c => {
        const th = document.createElement("th");
        th.innerText = c.replace(/_/g, " ");
        headRow.appendChild(th);
    });

    if (records.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = cols.length;
        td.style.padding = "20px";
        td.innerText = "No pending unpaid records for this flat profile.";
        tr.appendChild(td);
        body.appendChild(tr);
        return;
    }

    records.forEach(r => {
        const tr = document.createElement("tr");
        cols.forEach(col => {
            const td = document.createElement("td");
            let val = r[col];
            if (typeof val === "number") val = `Rs. ${val.toFixed(2)}`;
            if (col === "Payment_Status") {
                td.style.fontWeight = "bold";
                td.style.color = "#dc2626";
            }
            td.innerText = val !== undefined ? val : "";
            tr.appendChild(td);
        });
        body.appendChild(tr);
    });
}

async function applyDuesPaymentAllocation() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to record dues payments.");
        return;
    }

    const flatNo = document.getElementById("comboDuesFlat").value;
    const paymentAmt = parseFloat(document.getElementById("entDuesPaymentAmt").value);
    const datePaid = document.getElementById("entDuesDatePaid").value.trim();

    if (!flatNo || flatNo === "ALL FLATS") {
        alert("Please select a specific Flat No to allocate payment.");
        return;
    }

    if (isNaN(paymentAmt) || paymentAmt <= 0) {
        alert("Please input a valid payment amount.");
        return;
    }

    showLoading("💳 Allocating Payment...", `Applying FIFO dues settlement for Flat ${flatNo}...`, "💳");

    try {
        const res = await authFetch("/api/dues/allocate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                flat_no: flatNo,
                payment_amount: paymentAmt,
                payment_date: datePaid || getTodayFormatted()
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ " + (err.detail || "Payment allocation failed."));
            return;
        }

        const data = await res.json();
        alert(`✅ Successfully allocated payment of Rs. ${paymentAmt.toLocaleString('en-IN', {minimumFractionDigits: 2})} for Flat ${flatNo}!\n• Fully or partially cleared: ${data.cleared_count} month(s).\n• Remaining unallocated: Rs. ${data.unallocated_balance.toFixed(2)}`);

        document.getElementById("entDuesPaymentAmt").value = "";
        loadDuesData();
        loadLedgerData();
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        hideLoading();
    }
}

// ----------------- TAB 4: LIVE RATE SETTINGS -----------------

async function saveRPURates() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to change electricity rates.");
        return;
    }

    const domestic = parseFloat(document.getElementById("entRpuDomestic").value);
    const commercial = parseFloat(document.getElementById("entRpuCommercial").value);

    if (isNaN(domestic) || isNaN(commercial) || domestic < 0 || commercial < 0) {
        alert("❌ Please enter valid positive RPU numbers.");
        return;
    }

    try {
        const res = await authFetch("/api/config/rpu", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domestic, commercial })
        });

        if (res.ok) {
            alert("✅ Successfully updated electricity RPU rates!");
            loadInitialConfigs();
        }
    } catch (e) {
        alert("❌ Error: " + e.message);
    }
}

function onConfigFieldChanged() {
    const selectedChks = Array.from(document.querySelectorAll(".flat-chk:checked"));
    if (selectedChks.length === 0) return;

    const firstFlat = selectedChks[0].value;
    const field = document.getElementById("comboConfigFieldSelect").value;
    const month = document.getElementById("comboConfigStartMonth").value;
    const year = parseInt(document.getElementById("comboConfigStartYear").value);

    const cfg = getCurrentFlatConfig();
    const flatData = cfg[firstFlat] || {};

    let val = 0.0;
    if (field === "fixed") {
        const timeline = flatData.fixed || [];
        val = timeline[0]?.val || 0.0;
    } else {
        val = flatData[field] || 0.0;
    }

    document.getElementById("entConfigFieldValue").value = val.toFixed(2);
    refreshLiveSettingsGrid();
}

async function saveFlatRatesFromFields() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to update flat charges.");
        return;
    }

    const selectedChks = Array.from(document.querySelectorAll(".flat-chk:checked"));
    if (selectedChks.length === 0) {
        alert("Please select at least one Flat from the checklist.");
        return;
    }

    const targetFlats = selectedChks.map(c => c.value);
    const fieldKey = document.getElementById("comboConfigFieldSelect").value;
    const rawVal = document.getElementById("entConfigFieldValue").value.trim();

    if (rawVal === "" || isNaN(parseFloat(rawVal))) {
        alert("❌ Action Blocked: Numeric value field cannot be empty or invalid.");
        return;
    }

    const numVal = parseFloat(rawVal);
    if (numVal < 0) {
        alert("❌ Action Blocked: Negative value detected.");
        return;
    }

    const startMonth = document.getElementById("comboConfigStartMonth").value;
    const startYear = parseInt(document.getElementById("comboConfigStartYear").value);

    try {
        const res = await authFetch("/api/config/rates", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: state.mode,
                target_flats: targetFlats,
                field_key: fieldKey,
                value: numVal,
                start_month: startMonth,
                start_year: startYear
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("❌ " + (err.detail || "Update failed."));
            return;
        }

        alert(`✅ Successfully updated ${fieldKey} to Rs. ${numVal.toFixed(2)} across ${targetFlats.length} flat(s)!`);
        await loadInitialConfigs();
        refreshLiveSettingsGrid();
    } catch (e) {
        alert("❌ Error: " + e.message);
    }
}

function refreshLiveSettingsGrid() {
    const tbody = document.getElementById("liveRatesTableBody");
    tbody.innerHTML = "";
    const cfg = getCurrentFlatConfig();

    for (const [flat, data] of Object.entries(cfg)) {
        if (data.is_common) continue;
        const tr = document.createElement("tr");

        const fixedVal = Array.isArray(data.fixed) ? (data.fixed[0]?.val || 0.0) : (data.fixed || 0.0);

        tr.innerHTML = `
            <td style="font-weight: bold;">${flat}</td>
            <td>${data.tenant || 'N/A'}</td>
            <td>Rs. ${fixedVal.toFixed(2)}</td>
            <td>Rs. ${(data.tax || 0.0).toFixed(2)}</td>
            <td>Rs. ${(data.water || 0.0).toFixed(2)}</td>
            <td>Rs. ${(data.maintenance || 0.0).toFixed(2)}</td>
            <td>Rs. ${(data.lift || 0.0).toFixed(2)}</td>
            <td>Rs. ${(data.others || 0.0).toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
    }
}

// ----------------- TAB 5: INVOICE NOTICES -----------------

async function saveGlobalNoticeText() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to edit invoice notices.");
        return;
    }

    const text = document.getElementById("txtGlobalInstructions").value.trim();

    try {
        const res = await authFetch("/api/config/notices", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notice_text: text })
        });

        if (res.ok) {
            alert("✅ Notice guidelines saved permanently!");
        }
    } catch (e) {
        alert("❌ Error saving notices: " + e.message);
    }
}

// ----------------- GOOGLE SHEETS SETUP & SYNC -----------------

async function checkGoogleSheetsStatus() {
    try {
        const res = await fetch("/api/google-sheets/status");
        const data = await res.json();

        const pillText = document.getElementById("sheetsStatusText");
        const dot = document.getElementById("sheetsDot");

        if (data.is_syncing) {
            pillText.innerText = "Google Sheets: Syncing to Cloud...";
            dot.classList.remove("offline");
        } else if (data.is_connected) {
            const timeStr = data.last_sync_time ? ` (${data.last_sync_time})` : "";
            pillText.innerText = `Google Sheets: Live Cloud${timeStr}`;
            dot.classList.remove("offline");
        } else {
            pillText.innerText = "Google Sheets: Local Mirror Store";
            dot.classList.add("offline");
        }

        const diag = document.getElementById("diagStatusText");
        if (diag) {
            if (data.is_connected) {
                const syncDetail = data.last_sync_time ? `<br><small style="color: #64748b;">Last cloud sync: ${data.last_sync_time}</small>` : "";
                diag.innerHTML = `<span style="color: #047857; font-weight: bold;">Connected (${data.mode})</span>${syncDetail}`;
            } else {
                diag.innerHTML = `<span style="color: #ea580c; font-weight: bold;">Local Mirror Active</span> (${data.connection_error || 'Live Google Sheets disabled in config'})`;
            }
        }

        const inputAppsScript = document.getElementById("cfgAppsScriptUrl");
        if (inputAppsScript) inputAppsScript.value = data.apps_script_url || "";

        document.getElementById("cfgSpreadsheetId").value = data.spreadsheet_id || "";
        document.getElementById("cfgCredentialsFile").value = data.credentials_file || "service_account.json";
        document.getElementById("cfgUseLiveSheets").checked = !!data.use_live_google_sheets;
    } catch (e) {
        console.error("Error checking Google Sheets status:", e);
    }
}

function openSheetsModal() {
    checkGoogleSheetsStatus();
    document.getElementById("sheetsModal").classList.add("active");
}

function closeSheetsModal() {
    document.getElementById("sheetsModal").classList.remove("active");
}

async function copyAppsScriptCode() {
    try {
        const res = await fetch("/api/apps-script-code");
        const data = await res.json();
        if (data.status === "ok" && data.code) {
            await navigator.clipboard.writeText(data.code);
            alert("📋 Google Apps Script code copied to clipboard!\n\nNow open your Google Sheet > Extensions > Apps Script > Paste and Deploy as Web App.");
        } else {
            alert("Could not load script code.");
        }
    } catch (e) {
        alert("Clipboard error: " + e.message);
    }
}

async function saveSheetsConfig() {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to modify Google Sheets settings.");
        return;
    }

    const appsScriptUrl = (document.getElementById("cfgAppsScriptUrl") ? document.getElementById("cfgAppsScriptUrl").value.trim() : "");
    const id = document.getElementById("cfgSpreadsheetId").value.trim();
    const creds = document.getElementById("cfgCredentialsFile").value.trim();
    const useLive = document.getElementById("cfgUseLiveSheets").checked;

    try {
        const res = await authFetch("/api/google-sheets/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                apps_script_url: appsScriptUrl,
                spreadsheet_id: id,
                credentials_file: creds,
                use_live_google_sheets: useLive
            })
        });

        const data = await res.json();
        alert(data.message);
        checkGoogleSheetsStatus();
        loadLedgerData();
    } catch (e) {
        alert("❌ Error saving Google Sheets config: " + e.message);
    }
}

async function syncWithGoogleSheets(action = "push") {
    if (!state.isAdmin) {
        openAdminLoginModal("Admin Login Required: Please log in as Admin to trigger cloud sync.");
        return;
    }

    showLoading("🔄 Syncing with Google Sheets Cloud...", "Connecting and syncing ledger database with Google Cloud...", "🔄");

    try {
        const res = await authFetch("/api/google-sheets/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: action })
        });
        const data = await res.json();
        alert(data.message);
        checkGoogleSheetsStatus();
        loadLedgerData();
    } catch (e) {
        alert("❌ Sync Error: " + e.message);
    } finally {
        hideLoading();
    }
}

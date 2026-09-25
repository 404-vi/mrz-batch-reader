// ---------------------------------------------------------------------
// MRZ Batch Reader - frontend logic (vanilla JS, không phụ thuộc framework)
// ---------------------------------------------------------------------

const CONCURRENCY = 3; // số ảnh xử lý song song tối đa

const state = {
  items: [], // { id, file, thumbUrl, status, data, error }
};

let nextId = 1;

// ---- DOM refs ----
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const browseBtn = document.getElementById("browseBtn");
const queueBody = document.getElementById("queueBody");
const emptyRow = document.getElementById("emptyRow");
const queueCount = document.getElementById("queueCount");
const queueSummary = document.getElementById("queueSummary");
const countSuccess = document.getElementById("countSuccess");
const countWarning = document.getElementById("countWarning");
const countError = document.getElementById("countError");
const processBtn = document.getElementById("processBtn");
const exportBtn = document.getElementById("exportBtn");
const clearBtn = document.getElementById("clearBtn");
const actionbarInfo = document.getElementById("actionbarInfo");

const SEX_LABELS = { M: "Nam", F: "Nữ", X: "Không rõ" };

// ---- File intake ----
browseBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => addFiles(e.target.files));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files);
});

function addFiles(fileList) {
  const files = Array.from(fileList).filter((f) => f.type.startsWith("image/"));
  for (const file of files) {
    const item = {
      id: nextId++,
      file,
      thumbUrl: URL.createObjectURL(file),
      status: "pending", // pending | processing | success | warning | error
      data: null,
      error: null,
    };
    state.items.push(item);
  }
  fileInput.value = "";
  render();
}

// ---- Rendering ----
function statusPillHtml(item) {
  switch (item.status) {
    case "pending":
      return `<span class="status-pill status-pending">Chờ xử lý</span>`;
    case "processing":
      return `<span class="status-pill status-processing"><i class="spinner"></i>Đang xử lý</span>`;
    case "success":
      return `<span class="status-pill status-success">✓ Thành công</span>`;
    case "warning":
      return `<span class="status-pill status-warning">⚠ Cảnh báo</span>`;
    case "error":
      return `<span class="status-pill status-error">✕ Lỗi</span>`;
    default:
      return "";
  }
}

function render() {
  queueCount.textContent = `${state.items.length} ảnh`;

  if (state.items.length === 0) {
    queueBody.innerHTML = "";
    queueBody.appendChild(emptyRow);
    queueSummary.hidden = true;
    processBtn.disabled = true;
    exportBtn.disabled = true;
    actionbarInfo.textContent = "Chưa xử lý ảnh nào";
    return;
  }

  queueBody.innerHTML = state.items
    .map((item, idx) => {
      const d = item.data;
      const name = d ? `${d.surname || ""} ${d.given_names || ""}`.trim() : "";
      const dob = d ? d.birth_date : "";
      const sex = d ? (SEX_LABELS[d.sex] || d.sex) : "";
      const passportNo = d ? d.passport_number : "";
      const country = d ? (d.nationality_name || d.issuing_country_name || "") : "";
      const isEmpty = (v) => !v || v === "";

      return `
        <tr data-id="${item.id}">
          <td class="col-stt">${idx + 1}</td>
          <td>
            <div class="file-cell">
              <img class="file-thumb" src="${item.thumbUrl}" alt="">
              <span class="file-name" title="${escapeHtml(item.file.name)}">${escapeHtml(item.file.name)}</span>
            </div>
          </td>
          <td>${statusPillHtml(item)}</td>
          <td class="${isEmpty(name) ? "cell-muted" : ""}">${escapeHtml(name) || "—"}</td>
          <td class="cell-mono ${isEmpty(dob) ? "cell-muted" : ""}">${escapeHtml(dob) || "—"}</td>
          <td class="${isEmpty(sex) ? "cell-muted" : ""}">${escapeHtml(sex) || "—"}</td>
          <td class="cell-mono ${isEmpty(passportNo) ? "cell-muted" : ""}">${escapeHtml(passportNo) || "—"}</td>
          <td class="${isEmpty(country) ? "cell-muted" : ""}">${escapeHtml(country) || "—"}</td>
          <td>
            <button class="row-remove-btn" data-remove="${item.id}" title="Xóa khỏi danh sách" ${item.status === "processing" ? "disabled" : ""}>✕</button>
          </td>
        </tr>
      `;
    })
    .join("");

  queueBody.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.remove);
      state.items = state.items.filter((it) => it.id !== id);
      render();
    });
  });

  const successCount = state.items.filter((i) => i.status === "success").length;
  const warningCount = state.items.filter((i) => i.status === "warning").length;
  const errorCount = state.items.filter((i) => i.status === "error").length;
  const pendingCount = state.items.filter((i) => i.status === "pending" || i.status === "processing").length;

  const anyProcessed = successCount + warningCount + errorCount > 0;
  queueSummary.hidden = !anyProcessed;
  countSuccess.textContent = successCount;
  countWarning.textContent = warningCount;
  countError.textContent = errorCount;

  processBtn.disabled = pendingCount === 0;
  const isProcessing = state.items.some((i) => i.status === "processing");
  processBtn.disabled = isProcessing || pendingCount === 0;
  processBtn.textContent = isProcessing ? "Đang xử lý…" : "Xử lý tất cả";

  exportBtn.disabled = !anyProcessed || isProcessing;

  if (isProcessing) {
    const completed = successCount + warningCount + errorCount;
    actionbarInfo.textContent = `Đang xử lý ${completed}/${state.items.length}…`;
  } else if (anyProcessed) {
    actionbarInfo.textContent = `Hoàn tất: ${successCount} thành công, ${warningCount} cảnh báo, ${errorCount} lỗi`;
  } else {
    actionbarInfo.textContent = `${state.items.length} ảnh đang chờ xử lý`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---- Processing ----
async function processOne(item) {
  item.status = "processing";
  render();

  const formData = new FormData();
  formData.append("file", item.file);

  try {
    const res = await fetch("/api/read-mrz", { method: "POST", body: formData });
    const json = await res.json();

    if (json.success) {
      item.data = json.data;
      item.status = json.data.all_checks_valid ? "success" : "warning";
    } else {
      item.status = "error";
      item.error = json.error || "Không đọc được MRZ.";
    }
  } catch (err) {
    item.status = "error";
    item.error = `Lỗi kết nối tới server: ${err.message}`;
  }
  render();
}

async function processQueue() {
  const pending = state.items.filter((i) => i.status === "pending");
  let cursor = 0;

  async function worker() {
    while (cursor < pending.length) {
      const item = pending[cursor++];
      await processOne(item);
    }
  }

  const workers = Array.from({ length: Math.min(CONCURRENCY, pending.length) }, () => worker());
  await Promise.all(workers);
}

processBtn.addEventListener("click", () => {
  processBtn.disabled = true;
  processQueue();
});

// ---- Export to Excel ----
exportBtn.addEventListener("click", async () => {
  exportBtn.disabled = true;
  exportBtn.textContent = "Đang tạo file…";

  const payloadItems = state.items
    .filter((i) => i.status !== "pending" && i.status !== "processing")
    .map((i) => ({
      filename: i.file.name,
      success: i.status === "success" || i.status === "warning",
      data: i.data || null,
      error: i.error || null,
    }));

  try {
    const res = await fetch("/api/export-excel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: payloadItems }),
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || `Server trả về lỗi ${res.status}`);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ket_qua_doc_mrz_${payloadItems.length}_anh.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Không xuất được file Excel: ${err.message}`);
  } finally {
    exportBtn.textContent = "Xuất file Excel (.xlsx)";
    render();
  }
});

// ---- Clear ----
clearBtn.addEventListener("click", () => {
  if (state.items.some((i) => i.status === "processing")) return;
  state.items.forEach((i) => URL.revokeObjectURL(i.thumbUrl));
  state.items = [];
  render();
});

render();

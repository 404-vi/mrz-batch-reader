// =====================================================================
// MRZ BATCH READER - PHIÊN BẢN CHẠY 100% TRÊN TRÌNH DUYỆT (CLIENT-SIDE)
// Tích hợp: Cắt ảnh Canvas, Tesseract.js (OCR-B), ICAO 9303 Parser, Bấm giờ
// =====================================================================

const CONCURRENCY = 1; // Bắt buộc là 1 khi chạy OCR trên trình duyệt để không treo máy
const state = { items: [] };
let nextId = 1;
let tesseractWorker = null;

// ---- BẢNG MÃ QUỐC GIA & THUẬT TOÁN ICAO 9303 ----
const COUNTRY_CODES = { "VNM": "Việt Nam", "USA": "Hoa Kỳ", "GBR": "Vương quốc Anh", "FRA": "Pháp", "DEU": "Đức", "D": "Đức", "ITA": "Ý", "ESP": "Tây Ban Nha", "PRT": "Bồ Đào Nha", "NLD": "Hà Lan", "BEL": "Bỉ", "CHE": "Thụy Sĩ", "AUT": "Áo", "SWE": "Thụy Điển", "NOR": "Na Uy", "DNK": "Đan Mạch", "FIN": "Phần Lan", "POL": "Ba Lan", "CZE": "Séc", "SVK": "Slovakia", "HUN": "Hungary", "ROU": "Romania", "BGR": "Bulgaria", "GRC": "Hy Lạp", "TUR": "Thổ Nhĩ Kỳ", "RUS": "Nga", "UKR": "Ukraine", "CHN": "Trung Quốc", "JPN": "Nhật Bản", "KOR": "Hàn Quốc", "PRK": "Triều Tiên", "IND": "Ấn Độ", "PAK": "Pakistan", "BGD": "Bangladesh", "THA": "Thái Lan", "LAO": "Lào", "KHM": "Campuchia", "MMR": "Myanmar", "MYS": "Malaysia", "SGP": "Singapore", "IDN": "Indonesia", "PHL": "Philippines", "AUS": "Úc", "NZL": "New Zealand", "CAN": "Canada", "MEX": "Mexico", "BRA": "Brazil", "ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "PER": "Peru", "VEN": "Venezuela", "CUB": "Cuba", "ZAF": "Nam Phi", "EGY": "Ai Cập", "NGA": "Nigeria", "KEN": "Kenya", "MAR": "Morocco", "DZA": "Algeria", "TUN": "Tunisia", "ETH": "Ethiopia", "SAU": "Ả Rập Xê Út", "ARE": "UAE", "ISR": "Israel", "IRN": "Iran", "IRQ": "Iraq", "QAT": "Qatar", "KWT": "Kuwait", "JOR": "Jordan", "LBN": "Liban", "SYR": "Syria", "YEM": "Yemen", "OMN": "Oman", "BHR": "Bahrain", "AFG": "Afghanistan", "LKA": "Sri Lanka", "NPL": "Nepal", "BTN": "Bhutan", "MDV": "Maldives", "MNG": "Mông Cổ", "KAZ": "Kazakhstan", "UZB": "Uzbekistan", "IRL": "Ireland", "ISL": "Iceland", "LUX": "Luxembourg", "MLT": "Malta", "CYP": "Síp", "EST": "Estonia", "LVA": "Latvia", "LTU": "Lithuania", "SVN": "Slovenia", "HRV": "Croatia", "SRB": "Serbia", "ALB": "Albania", "BLR": "Belarus", "MDA": "Moldova", "GEO": "Georgia", "ARM": "Armenia", "AZE": "Azerbaijan", "TWN": "Đài Loan", "HKG": "Hồng Kông", "MAC": "Ma Cao", "FJI": "Fiji", "PNG": "Papua New Guinea", "UTO": "Utopia (mã ví dụ ICAO)" };
const CHAR_VALUES = { '<': 0 };
"0123456789".split('').forEach((c, i) => CHAR_VALUES[c] = i);
"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split('').forEach((c, i) => CHAR_VALUES[c] = i + 10);
const WEIGHTS = [7, 3, 1];
const DIGIT_TO_ALPHA = { "0": "O", "1": "I", "2": "Z", "5": "S", "6": "G", "8": "B", "7": "Z" };
const ALPHA_TO_DIGIT = { "O": "0", "I": "1", "Z": "2", "S": "5", "G": "6", "B": "8", "L": "1", "D": "0", "T": "7" };
const CONFUSION_CANDIDATES = { "0": ["O", "D"], "O": ["0"], "1": ["I", "L"], "I": ["1"], "L": ["1"], "2": ["Z"], "Z": ["2", "7"], "5": ["S"], "S": ["5"], "6": ["G"], "G": ["6"], "8": ["B"], "B": ["8"], "7": ["Z", "T"], "T": ["7"] };

function forceAlpha(ch) { return (/\d/.test(ch)) ? (DIGIT_TO_ALPHA[ch] || ch) : ch; }
function forceDigit(ch) { return (/[A-Z]/.test(ch)) ? (ALPHA_TO_DIGIT[ch] || ch) : ch; }
function checkDigit(data) {
    let total = 0;
    for (let i = 0; i < data.length; i++) total += (CHAR_VALUES[data[i]] || 0) * WEIGHTS[i % 3];
    return total % 10;
}
function tryFixViaChecksum(data, readCheckDigit) {
    if (!/\d/.test(readCheckDigit)) return { data, fixed: false };
    const target = parseInt(readCheckDigit, 10);
    if (checkDigit(data) === target) return { data, fixed: false };
    let chars = data.split('');
    for (let i = 0; i < chars.length; i++) {
        const alts = CONFUSION_CANDIDATES[chars[i]] || [];
        for (let alt of alts) {
            chars[i] = alt;
            if (checkDigit(chars.join('')) === target) return { data: chars.join(''), fixed: true };
            chars[i] = data[i]; 
        }
    }
    return { data, fixed: false };
}
function formatDob(yymmdd) {
    if (yymmdd.length !== 6 || !/^\d+$/.test(yymmdd)) return yymmdd;
    const yy = yymmdd.substring(0,2), mm = yymmdd.substring(2,4), dd = yymmdd.substring(4,6);
    return `${parseInt(yy) <= 30 ? '20' : '19'}${yy}-${mm}-${dd}`;
}

function parseTd3Client(line1, line2) {
    let l1 = (line1.toUpperCase() + '<'.repeat(44)).slice(0, 44).split('');
    let l2 = (line2.toUpperCase() + '<'.repeat(44)).slice(0, 44).split('');
    
    for (let i = 5; i < 44; i++) l1[i] = forceAlpha(l1[i]);
    l2[9] = forceDigit(l2[9]);
    for (let i = 10; i < 13; i++) l2[i] = forceAlpha(l2[i]);
    for (let i = 13; i < 19; i++) l2[i] = forceDigit(l2[i]);
    l2[19] = forceDigit(l2[19]);
    for (let i = 21; i < 27; i++) l2[i] = forceDigit(l2[i]);
    l2[27] = forceDigit(l2[27]);
    l2[42] = forceDigit(l2[42]);
    l2[43] = forceDigit(l2[43]);

    const strL1 = l1.join(''), strL2 = l2.join('');
    const surname = strL1.substring(5, 44).split('<<')[0].replace(/</g, ' ').replace(/\s+/g, ' ').trim();
    const givenNames = strL1.substring(5, 44).split('<<')[1]?.replace(/</g, ' ').replace(/\s+/g, ' ').trim() || '';
    const countryCode = strL1.substring(2, 5).replace(/</g, '');
    const natCode = strL2.substring(10, 13).replace(/</g, '');
    
    const rawPass = strL2.substring(0, 9), passCheck = strL2[9];
    const rawDob = strL2.substring(13, 19), dobCheck = strL2[19];
    const sex = ["M", "F"].includes(strL2[20]) ? strL2[20] : "X";
    const rawExp = strL2.substring(21, 27), expCheck = strL2[27];
    const rawPersonal = strL2.substring(28, 42), personalCheck = strL2[42], compCheck = strL2[43];

    const fixPass = tryFixViaChecksum(rawPass, passCheck).data;
    const fixDob = tryFixViaChecksum(rawDob, dobCheck).data;
    const fixExp = tryFixViaChecksum(rawExp, expCheck).data;
    const fixPersonal = rawPersonal.replace(/</g, '') !== '' ? tryFixViaChecksum(rawPersonal, personalCheck).data : rawPersonal;

    const isPassOk = checkDigit(fixPass) === parseInt(passCheck) || !/\d/.test(passCheck);
    const isDobOk = checkDigit(fixDob) === parseInt(dobCheck) || !/\d/.test(dobCheck);
    const isExpOk = checkDigit(fixExp) === parseInt(expCheck) || !/\d/.test(expCheck);
    
    const compositeData = fixPass + passCheck + strL2.substring(10, 13) + fixDob + dobCheck + sex + fixExp + expCheck + fixPersonal + personalCheck;
    const isCompOk = checkDigit(compositeData.substring(0, 10) + compositeData.substring(13, 20) + compositeData.substring(21, 43)) === parseInt(compCheck) || !/\d/.test(compCheck);
    
    return {
        surname, given_names: givenNames,
        passport_number: fixPass.replace(/</g, ''),
        birth_date: formatDob(fixDob), sex,
        nationality_name: COUNTRY_CODES[natCode] || "Không xác định",
        issuing_country_name: COUNTRY_CODES[countryCode] || "Không xác định",
        all_checks_valid: isPassOk && isDobOk && isExpOk && isCompOk
    };
}

function findAndParseMrzClient(lines) {
    let cleanLines = lines.map(l => l.toUpperCase().replace(/[^A-Z0-9<]/g, '')).filter(l => l.length >= 20);
    let l1 = cleanLines.find(l => ["P", "V", "I", "A", "C"].includes(l[0]) && l.includes("<<"));
    let l2 = cleanLines.find(l => l !== l1 && l.length >= 28);
    if (l1 && l2) {
        if (l2.length < 44 && l2.length >= 2) l2 = l2.slice(0, -2) + '<'.repeat(44 - l2.length) + l2.slice(-2);
        return parseTd3Client(l1, l2);
    }
    return null;
}

// ---- TESSERACT & XỬ LÝ ẢNH ----
async function getWorker() {
    if (!tesseractWorker) {
        tesseractWorker = await Tesseract.createWorker('ocrb', 1, {
            langPath: window.location.origin + '/tessdata', // Đảm bảo đã có file ocrb.traineddata.gz trong thư mục tessdata
        });
        await tesseractWorker.setParameters({
            tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<',
            tessedit_pageseg_mode: Tesseract.PSM.ASSUME_UNIFORM_BLOCK // Chế độ PSM 6
        });
    }
    return tesseractWorker;
}

async function cropBottomRegion(file) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const cropHeight = Math.floor(img.height * 0.25); // Lấy 25% đáy ảnh
            canvas.width = img.width; canvas.height = cropHeight;
            ctx.drawImage(img, 0, img.height - cropHeight, img.width, cropHeight, 0, 0, img.width, cropHeight);
            resolve(canvas.toDataURL('image/jpeg'));
        };
        img.onerror = reject; img.src = URL.createObjectURL(file);
    });
}

async function processOne(item) {
    item.status = "processing";
    render();
    const startTime = performance.now(); // Bắt đầu đếm giờ
    
    try {
        const worker = await getWorker();
        const base64Img = await cropBottomRegion(item.file);
        const { data: { text } } = await worker.recognize(base64Img);
        
        const lines = text.split('\n').map(l => l.trim());
        const parsed = findAndParseMrzClient(lines);
        
        item.processingTime = ((performance.now() - startTime) / 1000).toFixed(2); // Kết thúc đếm giờ
        
        if (parsed) {
            item.data = parsed;
            item.status = parsed.all_checks_valid ? "success" : "warning";
        } else {
            item.status = "error";
            item.error = "Không tìm thấy MRZ hợp lệ.";
        }
    } catch (err) {
        item.processingTime = ((performance.now() - startTime) / 1000).toFixed(2);
        item.status = "error";
        item.error = "Lỗi nhận diện OCR.";
    }
    render();
}

async function processQueue() {
    const pending = state.items.filter(i => i.status === "pending");
    try {
        actionbarInfo.textContent = "Đang khởi tạo bộ đọc AI...";
        await getWorker(); // Khởi tạo 1 lần trước khi chạy vòng lặp
        for (const item of pending) await processOne(item);
    } catch (e) {
        alert("Không tải được mô hình OCR. Vui lòng kiểm tra lại thư mục tessdata.");
    }
}

// ---- DOM & GIAO DIỆN CHÍNH ----
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const browseBtn = document.getElementById("browseBtn");
const queueBody = document.getElementById("queueBody");
const emptyRow = document.getElementById("emptyRow");
const queueCount = document.getElementById("queueCount");
const statTotal = document.getElementById("statTotal");
const statSuccess = document.getElementById("statSuccess");
const statWarning = document.getElementById("statWarning");
const statError = document.getElementById("statError");
const statAccuracy = document.getElementById("statAccuracy");
const processBtn = document.getElementById("processBtn");
const exportBtn = document.getElementById("exportBtn");
const clearBtn = document.getElementById("clearBtn");
const actionbarInfo = document.getElementById("actionbarInfo");

const SEX_LABELS = { M: "Nam", F: "Nữ", X: "Không rõ" };
const ICON_CHECK = `<svg viewBox="0 0 16 16" fill="none"><path d="M3.5 8.5l3 3 6-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_WARNING = `<svg viewBox="0 0 16 16" fill="none"><path d="M8 6v3.2M8 11.4h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M6.9 2.6 1.4 12a1.2 1.2 0 0 0 1 1.8h11.2a1.2 1.2 0 0 0 1-1.8L9.1 2.6a1.2 1.2 0 0 0-2.2 0Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
const ICON_ERROR = `<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.2" stroke="currentColor" stroke-width="1.5"/><path d="M6 6l4 4M10 6l-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`;

browseBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => addFiles(e.target.files));
["dragenter", "dragover"].forEach(evt => dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add("dragover"); }));
["dragleave", "drop"].forEach(evt => dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove("dragover"); }));
dropzone.addEventListener("drop", e => { if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files); });

function addFiles(fileList) {
    Array.from(fileList).filter(f => f.type.startsWith("image/")).forEach(file => {
        state.items.push({ id: nextId++, file, thumbUrl: URL.createObjectURL(file), status: "pending", data: null, error: null });
    });
    fileInput.value = ""; render();
}

function statusPillHtml(item) {
    if (item.status === "pending") return `<span class="status-pill status-pending">Chờ xử lý</span>`;
    if (item.status === "processing") return `<span class="status-pill status-processing"><i class="spinner"></i>Đang xử lý</span>`;
    if (item.status === "success") return `<span class="status-pill status-success">${ICON_CHECK}Thành công</span>`;
    if (item.status === "warning") return `<span class="status-pill status-warning">${ICON_WARNING}Cảnh báo</span>`;
    if (item.status === "error") return `<span class="status-pill status-error">${ICON_ERROR}Lỗi</span>`;
    return "";
}

function escapeHtml(str) { const div = document.createElement("div"); div.textContent = str ?? ""; return div.innerHTML; }

function render() {
    queueCount.textContent = `${state.items.length} ảnh`;
    const sCount = state.items.filter(i => i.status === "success").length;
    const wCount = state.items.filter(i => i.status === "warning").length;
    const eCount = state.items.filter(i => i.status === "error").length;
    const pCount = state.items.filter(i => i.status === "pending" || i.status === "processing").length;
    const anyProcessed = sCount + wCount + eCount > 0;

    statTotal.textContent = state.items.length; statSuccess.textContent = sCount; statWarning.textContent = wCount; statError.textContent = eCount;
    statAccuracy.textContent = anyProcessed ? `${Math.round(((sCount + wCount) / (sCount + wCount + eCount)) * 100)}%` : "—";

    if (state.items.length === 0) {
        queueBody.innerHTML = ""; queueBody.appendChild(emptyRow);
        processBtn.disabled = true; exportBtn.disabled = true; actionbarInfo.textContent = "Chưa xử lý ảnh nào"; return;
    }

    queueBody.innerHTML = state.items.map((item, idx) => {
        const d = item.data;
        const name = d ? `${d.surname || ""} ${d.given_names || ""}`.trim() : "";
        const isEmpty = (v) => !v || v === "";
        const timeStr = item.processingTime ? `${item.processingTime}s` : "—"; // Cột thời gian

        return `<tr data-id="${item.id}">
            <td class="col-stt">${idx + 1}</td>
            <td><div class="file-cell"><img class="file-thumb" src="${item.thumbUrl}" alt=""><span class="file-name" title="${escapeHtml(item.file.name)}">${escapeHtml(item.file.name)}</span></div></td>
            <td>${statusPillHtml(item)}</td>
            <td class="${isEmpty(name) ? "cell-muted" : ""}">${escapeHtml(name) || "—"}</td>
            <td class="cell-mono ${!d?.birth_date ? "cell-muted" : ""}">${escapeHtml(d?.birth_date) || "—"}</td>
            <td class="${!d?.sex ? "cell-muted" : ""}">${escapeHtml(SEX_LABELS[d?.sex] || d?.sex) || "—"}</td>
            <td class="cell-mono ${!d?.passport_number ? "cell-muted" : ""}">${escapeHtml(d?.passport_number) || "—"}</td>
            <td class="${!d?.nationality_name ? "cell-muted" : ""}">${escapeHtml(d?.nationality_name || d?.issuing_country_name) || "—"}</td>
            <td class="cell-mono">${timeStr}</td>
            <td><button class="row-remove-btn" data-remove="${item.id}" title="Xóa" ${item.status === "processing" ? "disabled" : ""}>✕</button></td>
        </tr>`;
    }).join("");

    queueBody.querySelectorAll("[data-remove]").forEach(btn => btn.addEventListener("click", () => {
        state.items = state.items.filter(it => it.id !== Number(btn.dataset.remove)); render();
    }));

    const isProcessing = state.items.some(i => i.status === "processing");
    processBtn.disabled = isProcessing || pCount === 0;
    processBtn.textContent = isProcessing ? "Đang xử lý…" : "Xử lý tất cả";
    exportBtn.disabled = !anyProcessed || isProcessing;

    if (isProcessing) actionbarInfo.textContent = `Đang xử lý ${sCount + wCount + eCount}/${state.items.length}…`;
    else if (anyProcessed) actionbarInfo.textContent = `Hoàn tất: ${sCount} thành công, ${wCount} cảnh báo, ${eCount} lỗi`;
    else actionbarInfo.textContent = `${state.items.length} ảnh đang chờ xử lý`;
}

processBtn.addEventListener("click", () => { processBtn.disabled = true; processQueue(); });

// Giữ nguyên API xuất file Excel theo backend Python (Nếu bạn tắt server backend, nút này sẽ không gọi được file excel)
exportBtn.addEventListener("click", async () => {
    exportBtn.disabled = true; exportBtn.textContent = "Đang tạo file…";
    const payloadItems = state.items.filter(i => i.status !== "pending" && i.status !== "processing").map(i => ({
        filename: i.file.name, success: i.status === "success" || i.status === "warning", data: i.data || null, error: i.error || null
    }));
    try {
        const res = await fetch("/api/export-excel", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items: payloadItems }) });
        if (!res.ok) throw new Error("Lỗi server");
        const url = URL.createObjectURL(await res.blob());
        const a = document.createElement("a"); a.href = url; a.download = `ket_qua_mrz.xlsx`; document.body.appendChild(a); a.click(); URL.revokeObjectURL(url);
    } catch (err) { alert(`Không xuất được file Excel: ${err.message}`); }
    exportBtn.textContent = "Xuất file Excel (.xlsx)"; render();
});

clearBtn.addEventListener("click", () => {
    if (state.items.some(i => i.status === "processing")) return;
    state.items.forEach(i => URL.revokeObjectURL(i.thumbUrl)); state.items = []; render();
});

render();
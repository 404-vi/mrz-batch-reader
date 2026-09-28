"""
ocr_reader.py
Tiền xử lý ảnh hộ chiếu và dùng Tesseract OCR để trích xuất text vùng MRZ.

QUAN TRỌNG (độ chính xác): dùng model OCR-B chuyên biệt (app/tessdata/ocrb*.traineddata)
thay vì model tiếng Anh mặc định của Tesseract. Model tiếng Anh mặc định "đoán" chữ cái
theo ngữ cảnh ngôn ngữ tự nhiên thay vì đọc đúng từng ký tự, gây sai lệch nghiêm trọng ở
phần họ tên (đặc biệt với dải dấu '<' đệm dài trong MRZ). Model OCR-B theo đánh giá công
khai có tỷ lệ lỗi ký tự ~0% so với ~45% của model mặc định.
Nguồn model: https://github.com/Shreeshrii/tessdata_ocrb

QUAN TRỌNG (tốc độ): ưu tiên dùng thư viện "tesserocr" (gọi thẳng thư viện Tesseract qua
API, KHÔNG qua subprocess) thay vì "pytesseract" (mỗi lần gọi phải khởi động 1 tiến trình
hệ điều hành mới + nạp lại model từ đầu - đo thực tế chiếm ~96% thời gian xử lý 1 ảnh).
Dùng tesserocr với 1 instance API được giữ sẵn trong bộ nhớ (nạp model đúng 1 lần lúc khởi
động server) giúp nhanh hơn ~3-4 lần khi đo thực tế.

tesserocr KHÔNG có sẵn bản cài dựng sẵn (wheel) cho Windows trên PyPI (phải qua Conda hoặc
tự build) - nếu bắt buộc dùng sẽ làm hỏng bước cài đặt trên máy Windows cá nhân. Do đó:
  - Trên Docker/Linux (Render...): cài tesserocr riêng trong Dockerfile -> dùng đường NHANH.
  - Trên máy cá nhân không cài được tesserocr (đặc biệt Windows): tự động dùng lại
    "pytesseract" (đường DỰ PHÒNG, chậm hơn nhưng luôn chạy được, không cần cài thêm gì).
Code tự phát hiện tesserocr có sẵn hay không, KHÔNG cần chỉnh sửa gì thủ công.

Chiến lược tổng thể (tối ưu cả độ chính xác lẫn tốc độ):
1. Đọc ảnh 1 lần, chuyển sang grayscale.
2. Giới hạn kích thước ảnh trong khoảng hợp lý trước khi OCR (không quá nhỏ, không quá
   lớn) - ảnh chụp điện thoại hiện đại xử lý rất chậm mà không giúp OCR chính xác hơn.
3. Chỉ OCR vùng đáy ảnh (nơi MRZ luôn nằm) trước, dùng model "ocrb_int" (nhỏ gọn, nhanh)
   - chỉ khi không ra kết quả hợp lệ mới OCR toàn bộ ảnh bằng model "ocrb" (đầy đủ, chính
   xác cao hơn) làm phương án dự phòng.
"""

import os
import threading
import cv2
import numpy as np
from typing import List

MRZ_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
TESSDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tessdata")

# Kích thước xử lý mục tiêu: đủ lớn để Tesseract đọc rõ chữ, đủ nhỏ để nhanh.
MIN_PROCESS_WIDTH = 1200
MAX_PROCESS_WIDTH = 1600


def load_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không đọc được ảnh - định dạng file không hợp lệ hoặc bị hỏng.")
    return img


def _crop_bottom_region(img: np.ndarray, fraction: float = 0.35) -> np.ndarray:
    """Cắt phần dưới của ảnh (nơi MRZ thường nằm) để giảm nhiễu OCR từ phần ảnh/thông tin khác."""
    h = img.shape[0]
    y0 = int(h * (1 - fraction))
    return img[y0:h, :]


def _preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if w < MIN_PROCESS_WIDTH:
        scale = MIN_PROCESS_WIDTH / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    elif w > MAX_PROCESS_WIDTH:
        scale = MAX_PROCESS_WIDTH / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


# ---------------------------------------------------------------------------
# Backend OCR: tự phát hiện tesserocr, nếu không có thì dùng pytesseract
# ---------------------------------------------------------------------------
try:
    import tesserocr
    from PIL import Image as PILImage

    _BACKEND = "tesserocr"

    # Giữ sẵn 2 API instance trong bộ nhớ suốt vòng đời server - model chỉ nạp 1 lần,
    # không phải nạp lại mỗi lần xử lý ảnh (đây là phần giúp tăng tốc chính).
    _api_fast = tesserocr.PyTessBaseAPI(
        path=TESSDATA_DIR, lang="ocrb_int",
        oem=tesserocr.OEM.LSTM_ONLY, psm=tesserocr.PSM.SINGLE_BLOCK,
    )
    _api_fast.SetVariable("tessedit_char_whitelist", MRZ_WHITELIST)
    _api_fast_lock = threading.Lock()

    _api_accurate = tesserocr.PyTessBaseAPI(
        path=TESSDATA_DIR, lang="ocrb",
        oem=tesserocr.OEM.LSTM_ONLY, psm=tesserocr.PSM.SINGLE_BLOCK,
    )
    _api_accurate.SetVariable("tessedit_char_whitelist", MRZ_WHITELIST)
    _api_accurate_lock = threading.Lock()

    def _ocr_lines_fast(processed_img: np.ndarray) -> List[str]:
        pil_img = PILImage.fromarray(processed_img)
        with _api_fast_lock:
            _api_fast.SetImage(pil_img)
            text = _api_fast.GetUTF8Text()
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    def _ocr_lines_accurate(processed_img: np.ndarray) -> List[str]:
        pil_img = PILImage.fromarray(processed_img)
        with _api_accurate_lock:
            _api_accurate.SetImage(pil_img)
            text = _api_accurate.GetUTF8Text()
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

except ImportError:
    import pytesseract

    _BACKEND = "pytesseract"

    # --- Dành cho người dùng Windows nếu đã cài Tesseract nhưng vẫn báo lỗi
    # "tesseract is not installed or it's not in your PATH" dù đã làm theo hướng dẫn
    # thêm PATH (xem HUONG_DAN_CAI_DAT.md) - bỏ dấu # ở dòng dưới và sửa lại đúng
    # đường dẫn nơi bạn đã cài Tesseract:
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    _CONFIG_FAST = (
        f'--oem 1 --psm 6 -l ocrb_int --tessdata-dir "{TESSDATA_DIR}" '
        f'-c tessedit_char_whitelist={MRZ_WHITELIST}'
    )
    _CONFIG_ACCURATE = (
        f'--oem 1 --psm 6 -l ocrb --tessdata-dir "{TESSDATA_DIR}" '
        f'-c tessedit_char_whitelist={MRZ_WHITELIST}'
    )

    def _ocr_lines_fast(processed_img: np.ndarray) -> List[str]:
        text = pytesseract.image_to_string(processed_img, config=_CONFIG_FAST)
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    def _ocr_lines_accurate(processed_img: np.ndarray) -> List[str]:
        text = pytesseract.image_to_string(processed_img, config=_CONFIG_ACCURATE)
        return [ln.strip() for ln in text.splitlines() if ln.strip()]


def ocr_bottom_crop(img: np.ndarray) -> List[str]:
    """Bước OCR NHANH (mặc định, đủ dùng cho phần lớn ảnh) - chỉ quét vùng đáy ảnh,
    dùng model OCR-B bản nhỏ gọn."""
    bottom = _crop_bottom_region(img, fraction=0.35)
    processed = _preprocess(bottom)
    return _ocr_lines_fast(processed)


def ocr_full_image(img: np.ndarray) -> List[str]:
    """Bước OCR DỰ PHÒNG (chậm hơn, chính xác hơn) - chỉ gọi khi bước đáy ảnh không
    ra kết quả hợp lệ, ví dụ ảnh chụp lệch khung/MRZ không nằm đúng vị trí thường thấy."""
    processed = _preprocess(img)
    return _ocr_lines_accurate(processed)

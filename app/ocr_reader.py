"""
ocr_reader.py
Tiền xử lý ảnh hộ chiếu và dùng Tesseract OCR để trích xuất text vùng MRZ.

Chiến lược:
1. Đọc ảnh, chuyển sang grayscale.
2. Thử phát hiện vùng MRZ bằng cách quét dải ngang có mật độ ký tự cao ở phần dưới ảnh
   (MRZ luôn nằm ở đáy trang thông tin hộ chiếu).
3. Áp threshold thích ứng để tăng độ tương phản chữ (chữ đen trên nền sáng).
4. Chạy Tesseract với whitelist ký tự MRZ (A-Z0-9<) và PSM phù hợp cho text 1 khối.
5. Lọc kết quả OCR để tìm các dòng khớp định dạng MRZ (44 ký tự, đúng charset).
"""

import cv2
import numpy as np
import pytesseract
from typing import List

# --- Dành cho người dùng Windows nếu đã cài Tesseract nhưng vẫn báo lỗi
# "tesseract is not installed or it's not in your PATH" dù đã làm theo hướng dẫn
# thêm PATH (xem HUONG_DAN_CAI_DAT.md) - bỏ dấu # ở dòng dưới và sửa lại đúng
# đường dẫn nơi bạn đã cài Tesseract:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

MRZ_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
TESS_CONFIG = f'--psm 6 -c tessedit_char_whitelist={MRZ_WHITELIST}'


def _load_image(image_bytes: bytes) -> np.ndarray:
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
    # Tăng kích thước nếu ảnh nhỏ, giúp OCR nhận diện tốt hơn
    h, w = gray.shape
    if w < 1200:
        scale = 1200 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    # Khử nhiễu nhẹ + threshold thích ứng (Otsu) để tách chữ khỏi nền
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _ocr_lines(processed_img: np.ndarray) -> List[str]:
    text = pytesseract.image_to_string(processed_img, config=TESS_CONFIG)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines


def extract_mrz_lines(image_bytes: bytes) -> dict:
    """
    Trả về dict:
      - 'lines_full_image': OCR toàn ảnh (fallback)
      - 'lines_bottom_crop': OCR vùng đáy ảnh (ưu tiên chính, ít nhiễu hơn)
    Caller (mrz_parser.find_and_parse_mrz) sẽ thử ghép cặp dòng hợp lệ từ các nguồn này.
    """
    img = _load_image(image_bytes)

    bottom = _crop_bottom_region(img, fraction=0.35)
    processed_bottom = _preprocess(bottom)
    lines_bottom = _ocr_lines(processed_bottom)

    processed_full = _preprocess(img)
    lines_full = _ocr_lines(processed_full)

    return {
        "lines_bottom_crop": lines_bottom,
        "lines_full_image": lines_full,
    }

"""
ocr_reader.py
Tiền xử lý ảnh hộ chiếu và dùng Tesseract OCR để trích xuất text vùng MRZ.

QUAN TRỌNG: dùng model OCR-B chuyên biệt (app/tessdata/ocrb*.traineddata) thay vì
model tiếng Anh mặc định của Tesseract. Model tiếng Anh mặc định được huấn luyện để
đọc chữ viết trong văn bản tự nhiên nên đọc SAI rất nhiều khi gặp chuỗi ký tự lặp lại
(ví dụ dải dấu '<' đệm trong MRZ) - nó cố "đoán" ra các chữ cái hợp lý theo ngữ cảnh
ngôn ngữ thay vì đọc đúng từng ký tự, gây sai lệch nghiêm trọng ở phần họ tên. Model
OCR-B được huấn luyện riêng cho đúng font MRZ (OCR-B), theo đánh giá công khai có tỷ
lệ lỗi ký tự ~0% so với ~45% của model tiếng Anh mặc định.
Nguồn model: https://github.com/Shreeshrii/tessdata_ocrb

Chiến lược (tối ưu cả độ chính xác lẫn tốc độ):
1. Đọc ảnh 1 lần, chuyển sang grayscale.
2. Giới hạn kích thước ảnh trong khoảng hợp lý trước khi OCR (không quá nhỏ, không
   quá lớn) - ảnh chụp điện thoại hiện đại xử lý rất chậm mà không giúp OCR chính
   xác hơn so với ảnh đã thu nhỏ về ~1400px.
3. Chỉ OCR vùng đáy ảnh (nơi MRZ luôn nằm) trước, dùng model "ocrb_int" (nhỏ gọn,
   nhanh) - chỉ khi không ra kết quả hợp lệ mới OCR toàn bộ ảnh bằng model "ocrb"
   (bản đầy đủ, chính xác cao hơn nhưng chậm hơn) làm phương án dự phòng.
"""

import os
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
TESSDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tessdata")

# Bước 1 (nhanh, dùng cho hầu hết ảnh): model OCR-B bản nhỏ gọn/lượng tử hóa.
TESS_CONFIG_FAST = (
    f'--oem 1 --psm 6 -l ocrb_int --tessdata-dir "{TESSDATA_DIR}" '
    f'-c tessedit_char_whitelist={MRZ_WHITELIST}'
)
# Bước 2 (dự phòng, chỉ chạy khi bước 1 thất bại): model OCR-B bản đầy đủ, chính
# xác cao hơn một chút, đánh đổi bằng tốc độ chậm hơn - chấp nhận được vì hiếm khi
# phải chạy tới bước này.
TESS_CONFIG_ACCURATE = (
    f'--oem 1 --psm 6 -l ocrb --tessdata-dir "{TESSDATA_DIR}" '
    f'-c tessedit_char_whitelist={MRZ_WHITELIST}'
)

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
    # Đưa chiều rộng ảnh xử lý về trong khoảng [MIN, MAX] - vừa đảm bảo đủ nét để
    # OCR đọc được (ảnh nhỏ thì phóng to lên), vừa tránh xử lý ảnh khổng lồ không
    # cần thiết (ảnh chụp điện thoại to thì thu nhỏ bớt, chạy nhanh hơn nhiều lần
    # mà độ chính xác OCR gần như không đổi).
    if w < MIN_PROCESS_WIDTH:
        scale = MIN_PROCESS_WIDTH / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    elif w > MAX_PROCESS_WIDTH:
        scale = MAX_PROCESS_WIDTH / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _ocr_lines(processed_img: np.ndarray, config: str) -> List[str]:
    text = pytesseract.image_to_string(processed_img, config=config)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines


def ocr_bottom_crop(img: np.ndarray) -> List[str]:
    """Bước OCR NHANH (mặc định, đủ dùng cho phần lớn ảnh) - chỉ quét vùng đáy ảnh,
    dùng model OCR-B bản nhỏ gọn."""
    bottom = _crop_bottom_region(img, fraction=0.35)
    processed = _preprocess(bottom)
    return _ocr_lines(processed, TESS_CONFIG_FAST)


def ocr_full_image(img: np.ndarray) -> List[str]:
    """Bước OCR DỰ PHÒNG (chậm hơn, chính xác hơn) - chỉ gọi khi bước đáy ảnh không
    ra kết quả hợp lệ, ví dụ ảnh chụp lệch khung/MRZ không nằm đúng vị trí thường thấy."""
    processed = _preprocess(img)
    return _ocr_lines(processed, TESS_CONFIG_ACCURATE)

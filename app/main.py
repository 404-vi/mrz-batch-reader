"""
main.py - FastAPI backend cho hệ thống đọc MRZ hộ chiếu.

Endpoint chính:
  POST /api/read-mrz
    Nhận: file ảnh (multipart/form-data, field name = "file")
    Trả về: JSON gồm các trường MRZ đã parse, trạng thái check digit,
             tên quốc gia cấp/quốc tịch, và dòng MRZ thô OCR được.

Chạy server (dev):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Ghi chú bảo mật: ảnh hộ chiếu được xử lý trong bộ nhớ (RAM), KHÔNG được ghi ra đĩa,
KHÔNG lưu trữ lâu dài. Cần bổ sung HTTPS, xác thực, rate-limit khi triển khai thật.
"""

import asyncio
import dataclasses
import logging

from fastapi import FastAPI, File, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import io

from app.ocr_reader import load_image, ocr_bottom_crop, ocr_full_image
from app.mrz_parser import find_and_parse_mrz
from app.excel_export import generate_excel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mrz_reader")

app = FastAPI(title="MRZ Passport Reader API", version="0.1.0")

# Cho phép gọi từ frontend web (điều chỉnh lại danh sách domain khi deploy thật)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _process_image_sync(image_bytes: bytes):
    """
    Toàn bộ phần xử lý NẶNG (OCR, parse) - chạy trong thread riêng (xem read_mrz)
    để không chặn server khi đang xử lý nhiều ảnh cùng lúc.

    Chiến lược 2 bước để xử lý NHANH hơn: hầu hết ảnh hộ chiếu có MRZ nằm đúng
    vị trí đáy trang, nên chỉ cần OCR vùng đáy ảnh (nhanh) là đủ. Chỉ khi bước
    này không cho ra kết quả hợp lệ mới OCR toàn bộ ảnh (chậm hơn, dùng làm
    phương án dự phòng cho ảnh chụp lệch khung).
    """
    img = load_image(image_bytes)

    lines_bottom = ocr_bottom_crop(img)
    parsed = find_and_parse_mrz(lines_bottom)
    if parsed is not None:
        return parsed, lines_bottom

    lines_full = ocr_full_image(img)
    parsed = find_and_parse_mrz(lines_bottom + lines_full)
    return parsed, lines_bottom + lines_full


@app.post("/api/read-mrz")
async def read_mrz(file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": f"Định dạng file không hỗ trợ: {file.content_type}. Chỉ nhận JPEG/PNG/WEBP."},
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        return JSONResponse(status_code=400, content={"success": False, "error": "File ảnh rỗng."})

    try:
        # Chạy trong thread riêng: đây là phần tốn CPU (OCR), nếu chạy trực tiếp
        # trong hàm async sẽ chặn toàn bộ server, khiến nhiều ảnh gửi lên cùng lúc
        # bị xử lý TUẦN TỰ dù frontend đã gửi song song - chạy trong thread cho
        # phép nhiều ảnh thực sự được xử lý đồng thời khi máy chủ có nhiều lõi CPU.
        parsed, all_candidate_lines = await asyncio.to_thread(_process_image_sync, image_bytes)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        logger.exception("Lỗi xử lý ảnh")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Lỗi xử lý ảnh: {e}"})

    if parsed is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Không tìm thấy vùng MRZ hợp lệ trong ảnh. Hãy thử chụp lại rõ nét hơn, "
                         "đảm bảo 2 dòng MRZ ở đáy trang hộ chiếu không bị che/mờ/nghiêng.",
                "ocr_raw_lines": all_candidate_lines,
            },
        )

    result_dict = dataclasses.asdict(parsed)
    return {
        "success": True,
        "data": result_dict,
    }


@app.post("/api/export-excel")
async def export_excel(payload: dict = Body(...)):
    """
    Nhận kết quả đã xử lý (từ nhiều lần gọi /api/read-mrz ở frontend) và xuất thành
    1 file Excel duy nhất.
    Body: { "items": [ {"filename": str, "success": bool, "data": {...} | None, "error": str | None }, ... ] }
    """
    items = payload.get("items", [])
    if not items:
        return JSONResponse(status_code=400, content={"success": False, "error": "Không có dữ liệu để xuất Excel."})

    try:
        xlsx_bytes = generate_excel(items)
    except Exception as e:
        logger.exception("Lỗi tạo file Excel")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Lỗi tạo file Excel: {e}"})

    filename = f"ket_qua_doc_mrz_{len(items)}_anh.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Phục vụ giao diện web tĩnh (frontend) - đặt SAU các route /api/* để không bị che khuất
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

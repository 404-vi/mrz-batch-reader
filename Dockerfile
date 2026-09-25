# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Dockerfile cho MRZ Batch Reader.
# Đóng gói cả Tesseract OCR (bộ máy đọc chữ từ ảnh, không phải thư viện Python
# thông thường) cùng với ứng dụng FastAPI vào 1 image duy nhất, để triển khai
# lên các nền tảng hỗ trợ Docker như Render.com (gói Free).
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# Cài Tesseract OCR + các thư viện hệ thống mà OpenCV cần để xử lý ảnh
# (opencv-python-headless vẫn cần vài thư viện đồ họa cơ bản của hệ điều hành
# dù không có giao diện, nếu thiếu sẽ báo lỗi "libGL.so.1: cannot open...").
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài thư viện Python trước (tận dụng cache của Docker - chỉ cài lại khi
# requirements.txt thay đổi, giúp các lần build sau nhanh hơn nhiều)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn ứng dụng
COPY app ./app

# Render (và đa số nền tảng PaaS khác) cấp cổng động qua biến môi trường PORT,
# KHÔNG dùng cổng cố định 8000 như khi chạy trên máy cá nhân.
ENV PORT=8000
EXPOSE 8000

# Dùng "sh -c" để biến môi trường ${PORT} được thay thế đúng giá trị lúc chạy
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

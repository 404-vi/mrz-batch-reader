# MRZ Passport Reader — Backend (Nền tảng)

Backend đọc MRZ (Machine Readable Zone) từ ảnh hộ chiếu: nhận ảnh qua API, tự động
tìm vùng MRZ bằng OCR (Tesseract), parse các trường thông tin, kiểm tra check digit
theo chuẩn ICAO Doc 9303, và tự động sửa các lỗi ký tự phổ biến do OCR gây ra
(nhầm lẫn chữ/số như O↔0, Z↔2/7, S↔5, B↔8...).

> **Muốn dùng ngay trên Internet, không cần cài gì lên máy?** Xem
> `HUONG_DAN_TRIEN_KHAI_RENDER.md` — triển khai miễn phí lên Render.com, nhận link
> dạng `https://ten-cua-ban.onrender.com`, ai có link cũng bấm vào dùng được.

> **Muốn tự chạy trên máy tính cá nhân?** Xem `HUONG_DAN_CAI_DAT.md`.

## ⚠️ Bản cập nhật quan trọng: sửa lỗi đọc sai họ tên

**Vấn đề đã phát hiện:** model OCR mặc định của Tesseract (huấn luyện cho văn bản
tiếng Anh thông thường) đọc SAI nghiêm trọng phần họ tên trên ảnh hộ chiếu thật —
nó "đoán" chữ cái theo ngữ cảnh ngôn ngữ tự nhiên thay vì đọc đúng từng ký tự,
đặc biệt sai khi gặp dải dấu `<` đệm dài trong MRZ (đọc nhầm thành hàng loạt chữ
K, O ngẫu nhiên).

**Đã sửa:** chuyển sang dùng model OCR-B chuyên biệt cho đúng font MRZ (nguồn:
https://github.com/Shreeshrii/tessdata_ocrb, đặt tại `app/tessdata/`), theo đánh
giá công khai có tỷ lệ lỗi ký tự ~0% so với ~45% của model mặc định. Đã kiểm chứng
lại bằng 3 ảnh hộ chiếu Trung Quốc thật (không phải ảnh dựng sẵn): đọc đúng 100%
họ tên, ngày sinh, giới tính, số hộ chiếu, quốc gia trên cả 3 ảnh, xử lý dưới 0.6
giây/ảnh.

## Kiến trúc

```
mrz_reader/
├── Dockerfile            # Đóng gói để triển khai lên Render/bất kỳ nền tảng Docker nào
├── .dockerignore
├── render.yaml            # Cấu hình Render Blueprint (gói Free, tự động deploy)
├── app/
│   ├── main.py          # FastAPI server: /api/read-mrz, /api/export-excel, phục vụ giao diện web
│   ├── ocr_reader.py     # Tiền xử lý ảnh (OpenCV) + OCR (Tesseract, dùng model OCR-B)
│   ├── mrz_parser.py     # Parse MRZ, validate & tự sửa check digit
│   ├── excel_export.py   # Tạo file Excel (.xlsx) từ kết quả xử lý hàng loạt
│   ├── tessdata/          # Model OCR-B chuyên biệt cho MRZ (QUAN TRỌNG - xem mục cập nhật ở trên)
│   │   ├── ocrb_int.traineddata   # Bản nhanh, dùng cho bước OCR chính
│   │   └── ocrb.traineddata       # Bản chính xác cao hơn, dùng cho bước dự phòng
│   └── static/           # Giao diện web (HTML/CSS/JS thuần, không cần build)
│       ├── index.html
│       ├── style.css
│       └── app.js
├── test_data/
│   └── generate_test_image.py   # Tạo ảnh mẫu để test (ICAO example + VN example)
└── requirements.txt
```

## Cài đặt

```bash
# 1. Cài Tesseract OCR engine (bắt buộc, không phải package Python)
sudo apt-get install -y tesseract-ocr

# 2. Cài thư viện Python
pip install -r requirements.txt
```

## Chạy server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở trình duyệt tại **http://localhost:8000/** để dùng giao diện web (kéo-thả nhiều ảnh,
xử lý hàng loạt, xuất kết quả ra 1 file Excel duy nhất).

## Test nhanh qua API (không cần giao diện)

```bash
# Tạo ảnh mẫu
python3 test_data/generate_test_image.py

# Gọi API đọc 1 ảnh
curl -X POST http://localhost:8000/api/read-mrz \
  -F "file=@test_data/sample_passport_vn.png;type=image/png"
```

## Kết quả trả về (JSON)

```json
{
  "success": true,
  "data": {
    "document_type": "P",
    "issuing_country_code": "VNM",
    "issuing_country_name": "Việt Nam",
    "surname": "NGUYEN",
    "given_names": "VAN AN",
    "passport_number": "B12345678",
    "nationality_code": "VNM",
    "nationality_name": "Việt Nam",
    "birth_date": "1990-01-01",
    "sex": "M",
    "expiry_date": "2030-01-01",
    "personal_number": "",
    "checks": [ ... chi tiết từng check digit ... ],
    "all_checks_valid": true,
    "raw_line1": "...", "raw_line2": "...",
    "warnings": [ "..." ]
  }
}
```

## Giao diện web (xử lý hàng loạt)

- Kéo-thả hoặc chọn nhiều ảnh hộ chiếu cùng lúc.
- Bấm "Xử lý tất cả" — mỗi ảnh được gửi lên `/api/read-mrz` (tối đa 3 ảnh xử lý song song),
  trạng thái từng ảnh cập nhật trực tiếp trên bảng (Chờ xử lý / Đang xử lý / Thành công /
  Cảnh báo / Lỗi).
- Bấm "Xuất file Excel (.xlsx)" — toàn bộ kết quả (kể cả các dòng lỗi) được gộp thành
  **1 file Excel duy nhất** và tải về máy, với các cột:
  `STT · Tên file ảnh · Họ và tên · Ngày sinh · Giới tính · Số hộ chiếu · Quốc gia · Ghi chú`
  (2 cột "Tên file ảnh" và "Ghi chú" được bổ sung thêm để phục vụ đối soát/truy vết khi xử lý
  hàng loạt — có thể xóa đi nếu không cần, chỉnh trong `app/excel_export.py`).
  - Cột **"Ngày sinh"** ghi dưới dạng **text cố định** `dd/mm/yyyy` (không phải kiểu Date của
    Excel) - tránh bị hiển thị sai lệch do cài đặt vùng miền khác nhau giữa các máy.
  - Cột **"Quốc gia"** hiển thị bằng **tiếng Anh** (ví dụ "China", "Vietnam") theo yêu cầu
    chuẩn hóa dữ liệu - khác với giao diện web (hiển thị tiếng Việt để dễ đọc khi thao tác).
- Dòng bị lỗi OCR (không đọc được MRZ) vẫn xuất hiện trong Excel, tô nền đỏ nhạt kèm mô tả lỗi
  thay vì bị bỏ sót âm thầm.
- Dòng có check digit không khớp (nghi ngờ đọc sai) được tô nền vàng cảnh báo thay vì báo "OK"
  giả.

## Đã tối ưu tốc độ xử lý ảnh

- **Chỉ OCR 1 lần thay vì 2 lần** cho phần lớn ảnh: trước đây luôn quét cả vùng đáy
  ảnh lẫn toàn bộ ảnh; giờ chỉ quét toàn bộ ảnh khi vùng đáy không cho ra kết quả
  hợp lệ (ảnh chụp lệch khung). Đo thực tế: **nhanh hơn ~60-65%** với ảnh MRZ nằm
  đúng vị trí thông thường.
- **Giới hạn kích thước ảnh xử lý** (1200-1600px chiều rộng): ảnh chụp điện thoại
  hiện đại (3000-4000px) được thu nhỏ trước khi OCR - giảm thời gian xử lý đáng kể
  mà không ảnh hưởng độ chính xác (đã kiểm chứng: ảnh giả lập 3200px xử lý trong
  ~0.3s, vẫn đọc đúng 100%).
- **Dùng `--oem 1`** (engine LSTM hiện đại của Tesseract) thay vì mặc định chạy
  cả engine cũ lẫn mới rồi so khớp - nhanh hơn cho chữ in rõ nét như MRZ.
- **Xử lý ảnh trong thread riêng** (`asyncio.to_thread`): trước đây nếu nhiều ảnh
  gửi lên cùng lúc, máy chủ xử lý tuần tự dù frontend gửi song song (vì OCR chặn
  luôn vòng lặp xử lý chính); giờ máy chủ vẫn phản hồi được các yêu cầu khác trong
  lúc đang OCR ảnh nặng.
  ⚠️ **Lưu ý trung thực:** trên máy nhiều lõi CPU, thay đổi này giúp nhiều ảnh xử
  lý thật sự song song, nhanh hơn. Nhưng **gói Free của Render chỉ cấp 0.1 CPU**
  (ít hơn 1 lõi) - trên đó, xử lý song song sẽ KHÔNG nhanh hơn xử lý tuần tự do
  giới hạn phần cứng của nền tảng, không phải do code. Muốn xử lý hàng loạt ảnh
  nhanh hơn thật sự, cần nâng cấp gói trả phí của Render (nhiều CPU hơn).

## Những gì đã được xử lý ở tầng nền tảng này

1. **Nhận diện & phân biệt quốc gia**: đọc mã quốc gia cấp hộ chiếu (issuing state)
   và mã quốc tịch (nationality) riêng biệt theo ISO 3166-1 alpha-3, map sang tên
   quốc gia đầy đủ (bảng `COUNTRY_CODES` trong `mrz_parser.py`, có thể mở rộng thêm).
2. **Validate dữ liệu bằng check digit** theo đúng thuật toán ICAO 9303 (trọng số 7-3-1)
   cho: số hộ chiếu, ngày sinh, ngày hết hạn, số cá nhân, và check digit tổng hợp.
3. **Tự động sửa lỗi ký tự do OCR** (KHÔNG liên quan phiên âm/quốc gia — đây là lỗi
   nhận diện ký tự thuần túy, áp dụng chung cho mọi hộ chiếu):
   - Sửa theo vị trí: các vùng chỉ được là chữ (tên, mã quốc gia) hoặc chỉ được là số
     (ngày tháng, check digit) sẽ được ép về đúng loại nếu OCR đọc nhầm loại.
   - Sửa theo check digit: nếu 1 trường sai check digit, thử hoán đổi các ký tự dễ
     nhầm (O/0, I/1, S/5, B/8, Z/2/7...) để tìm phiên bản khớp lại check digit.
   - Xử lý trường hợp OCR đếm thiếu/thừa ký tự `<` trong vùng đệm (thường xảy ra ở
     trường "số cá nhân" - trường tùy chọn hay để trống).
4. **Chưa khôi phục dấu/phiên âm gốc theo từng quốc gia** (theo lựa chọn hiện tại của
   bạn): tên hiển thị đúng y nguyên như trong MRZ, không dấu. Nếu sau này muốn thêm,
   có thể mở rộng bằng 1 module riêng nhận `issuing_country_code` làm đầu vào để chọn
   bộ quy tắc khôi phục phù hợp (không đụng vào phần lõi đã xây).

## Đã kiểm thử

- MRZ mẫu chuẩn ICAO 9303 (hộ chiếu ví dụ "Utopia") — qua ảnh giả lập có nhiễu.
- MRZ mẫu hộ chiếu Việt Nam (dữ liệu hư cấu, tự tính check digit đúng chuẩn) — qua ảnh
  giả lập có nhiễu.
- Cả 2 test đều: nhận diện đúng quốc gia, đọc đúng toàn bộ trường, tất cả check digit
  hợp lệ sau khi tự động sửa lỗi OCR.

## Giới hạn hiện tại (cần lưu ý)

- OCR dựa trên Tesseract nên độ chính xác phụ thuộc chất lượng ảnh đầu vào (ảnh mờ,
  nghiêng nhiều, thiếu sáng sẽ giảm độ chính xác dù đã có bước tự sửa lỗi).
- Ảnh được xử lý trong bộ nhớ (RAM), không ghi ra đĩa, nhưng CHƯA có xác thực
  (authentication), rate-limiting, hay mã hóa kênh truyền (HTTPS) — cần bổ sung
  trước khi triển khai với dữ liệu thật.
- Mới hỗ trợ định dạng TD3 (hộ chiếu 2 dòng). Chưa hỗ trợ TD1 (căn cước 3 dòng).

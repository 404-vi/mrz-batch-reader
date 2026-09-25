# Hướng dẫn cài đặt MRZ Batch Reader

Tài liệu này hướng dẫn cài đặt phần mềm đọc MRZ hộ chiếu hàng loạt **từ đầu đến khi
chạy được**, dành cho người **chưa từng cài phần mềm lập trình bao giờ**. Làm theo
đúng thứ tự từng bước, không bỏ bước nào.

Phần mềm gồm 2 thành phần bắt buộc phải cài:
1. **Python** — ngôn ngữ lập trình để chạy phần mềm.
2. **Tesseract OCR** — "bộ máy" đọc chữ từ ảnh (không phải thư viện Python, phải cài riêng).

Chọn đúng phần theo hệ điều hành máy bạn đang dùng: **Windows** (phổ biến nhất ở
văn phòng) hoặc **macOS**.

---

## PHẦN A — CÀI ĐẶT TRÊN WINDOWS

### Bước 1: Cài đặt Python

1. Mở trình duyệt, truy cập: **https://www.python.org/downloads/**
2. Bấm nút vàng **"Download Python 3.x.x"** (số phiên bản mới nhất, ví dụ 3.12).
3. Mở file `.exe` vừa tải về.
4. **⚠️ QUAN TRỌNG NHẤT:** Ở màn hình cài đặt đầu tiên, phía dưới cùng có ô vuông
   **"Add python.exe to PATH"** — **phải tích chọn ô này** trước khi bấm "Install Now".
   Đây là bước 90% người mới hay quên, nếu quên thì máy sẽ báo lỗi
   `'python' is not recognized` ở các bước sau.
5. Chờ cài đặt xong, bấm "Close".
6. Kiểm tra lại: mở **Command Prompt** (bấm nút Windows, gõ `cmd`, Enter), gõ lệnh:
   ```
   python --version
   ```
   Nếu hiện ra dòng chữ dạng `Python 3.12.x` → cài đặt thành công.
   Nếu báo lỗi `not recognized` → gỡ Python ra và cài lại, nhớ tích ô ở bước 4.

### Bước 2: Cài đặt Tesseract OCR (bộ máy đọc chữ từ ảnh)

1. Truy cập: **https://github.com/UB-Mannheim/tesseract/wiki**
2. Kéo xuống mục "tesseract-ocr-w64-setup-...", bấm vào file `.exe` mới nhất để tải về
   (đây là bản cài đặt Tesseract dành riêng cho Windows, do nhóm UB Mannheim đóng gói —
   bản phổ biến và ổn định nhất).
3. Mở file `.exe` vừa tải, cứ bấm "Next" theo mặc định.
4. **Ghi nhớ đường dẫn cài đặt** hiện ra trong lúc cài (mặc định là:
   `C:\Program Files\Tesseract-OCR`) — sẽ cần dùng lại ở bước tiếp theo.
5. Bấm "Install", chờ hoàn tất, bấm "Finish".
6. **Thêm Tesseract vào PATH của Windows** (để máy biết "tesseract" nằm ở đâu):
   - Bấm nút Windows, gõ **"Edit the system environment variables"**, Enter.
   - Cửa sổ "System Properties" hiện ra → bấm nút **"Environment Variables..."**.
   - Ở khung **"System variables"** (khung dưới), tìm dòng **"Path"** → bấm **"Edit..."**.
   - Bấm **"New"** → dán vào: `C:\Program Files\Tesseract-OCR`
     (hoặc đúng đường dẫn bạn đã ghi nhớ ở bước 4 nếu cài vào nơi khác).
   - Bấm **OK** ở cả 3 cửa sổ để lưu lại.
7. **Đóng toàn bộ cửa sổ Command Prompt đang mở** (bắt buộc — cửa sổ cũ không tự
   cập nhật PATH mới), mở lại Command Prompt mới, gõ:
   ```
   tesseract --version
   ```
   Nếu hiện ra dòng `tesseract 5.x.x` → thành công.

### Bước 3: Giải nén và mở project

1. Giải nén file `mrz_reader.zip` đã được cung cấp vào một thư mục dễ nhớ,
   ví dụ: `C:\mrz_reader`
2. Mở Command Prompt, di chuyển vào đúng thư mục project (thư mục con bên trong,
   chứa file `requirements.txt`):
   ```
   cd C:\mrz_reader\mrz_reader
   ```

### Bước 4: Tạo môi trường ảo Python (giúp không xung đột với phần mềm khác)

```
python -m venv venv
venv\Scripts\activate
```
Sau lệnh thứ 2, đầu dòng lệnh sẽ hiện chữ `(venv)` — nghĩa là đã bật môi trường ảo
thành công. **Từ giờ về sau, mỗi lần mở Command Prompt mới để chạy phần mềm, phải
chạy lại lệnh `venv\Scripts\activate` này trước.**

### Bước 5: Cài đặt các thư viện Python cần thiết

```
pip install -r requirements.txt
```
Lệnh này cần có Internet, chạy khoảng 2-5 phút tùy tốc độ mạng. Chờ đến khi
Command Prompt hiện lại dấu nhắc lệnh (không còn chạy nữa) là xong.

### Bước 6: Khởi động phần mềm

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Khi thấy dòng chữ:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```
nghĩa là phần mềm đã chạy thành công. **Để nguyên cửa sổ Command Prompt này, KHÔNG
đóng lại** trong suốt quá trình sử dụng phần mềm — đóng cửa sổ này = tắt phần mềm.

### Bước 7: Mở phần mềm để sử dụng

Mở trình duyệt bất kỳ (Chrome, Edge, Cốc Cốc...), gõ vào thanh địa chỉ:
```
http://localhost:8000
```
Giao diện phần mềm sẽ hiện ra.

---

## PHẦN B — CÀI ĐẶT TRÊN macOS

### Bước 1: Cài đặt Homebrew (công cụ cài phần mềm cho Mac, nếu máy chưa có)

Mở **Terminal** (tìm trong Spotlight bằng `Cmd + Space`, gõ "Terminal"), dán lệnh sau
rồi Enter:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Làm theo hướng dẫn hiện trên màn hình (có thể yêu cầu nhập mật khẩu máy Mac).

### Bước 2: Cài Python và Tesseract

```
brew install python tesseract
```

Kiểm tra lại:
```
python3 --version
tesseract --version
```
Cả 2 lệnh đều phải hiện ra số phiên bản.

### Bước 3: Giải nén và mở project

1. Giải nén `mrz_reader.zip` (double-click vào file trong Finder).
2. Trong Terminal, di chuyển vào thư mục project, ví dụ nếu giải nén ra Desktop:
   ```
   cd ~/Desktop/mrz_reader/mrz_reader
   ```

### Bước 4: Tạo môi trường ảo và cài thư viện

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Bước 5: Khởi động phần mềm

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Để nguyên cửa sổ Terminal này, mở trình duyệt truy cập `http://localhost:8000`.

---

## CÁCH SỬ DỤNG PHẦN MỀM (sau khi đã mở được http://localhost:8000)

1. **Kéo-thả** nhiều ảnh hộ chiếu vào khung có sẵn, hoặc bấm **"Chọn ảnh từ máy tính"**
   để chọn nhiều ảnh cùng lúc.
2. Bấm nút **"Xử lý tất cả"**. Từng ảnh sẽ chuyển trạng thái: *Chờ xử lý* →
   *Đang xử lý* → *Thành công* / *Cảnh báo* / *Lỗi*.
3. Sau khi xử lý xong hết, bấm **"Xuất file Excel (.xlsx)"** — file Excel sẽ tự động
   tải về thư mục Downloads của máy bạn, chứa đầy đủ kết quả của toàn bộ ảnh.
4. Muốn xử lý đợt ảnh mới: bấm **"Xóa danh sách"** rồi lặp lại từ bước 1.

## CÁCH DỪNG PHẦN MỀM

Quay lại cửa sổ Command Prompt / Terminal đang chạy phần mềm (dòng chữ
`Uvicorn running...`), bấm tổ hợp phím **Ctrl + C**.

## CÁCH MỞ LẠI PHẦN MỀM LẦN SAU (đã cài đặt xong 1 lần rồi)

Không cần làm lại từ Bước 1. Chỉ cần:
1. Mở Command Prompt / Terminal.
2. `cd` vào đúng thư mục project (giống Bước 3 ở trên).
3. Kích hoạt lại môi trường ảo:
   - Windows: `venv\Scripts\activate`
   - macOS: `source venv/bin/activate`
4. Chạy lại: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Mở trình duyệt vào `http://localhost:8000`

---

## XỬ LÝ LỖI THƯỜNG GẶP

| Lỗi gặp phải | Nguyên nhân & Cách sửa |
|---|---|
| `'python' is not recognized as an internal or external command` | Chưa thêm Python vào PATH lúc cài. Gỡ cài đặt Python, cài lại, **nhớ tích "Add python.exe to PATH"** (xem Bước 1, Phần A). |
| `tesseract is not installed or it's not in your PATH` (hiện khi xử lý ảnh) | Tesseract chưa được thêm vào PATH đúng cách, hoặc đang dùng cửa sổ Command Prompt **cũ** (mở từ trước khi thêm PATH). Mở cửa sổ Command Prompt **mới** và thử lại; nếu vẫn lỗi, làm lại Bước 2 mục 6 (Phần A). |
| `ERROR: Address already in use` / không mở được cổng 8000 | Cổng 8000 đang bị phần mềm khác chiếm. Đổi sang cổng khác: `uvicorn app.main:app --host 0.0.0.0 --port 8080`, rồi truy cập `http://localhost:8080` thay vì 8000. |
| Trang web mở được nhưng bấm "Xử lý tất cả" báo "Lỗi kết nối tới server" | Cửa sổ Command Prompt/Terminal chạy phần mềm đã bị đóng hoặc bị lỗi. Kiểm tra cửa sổ đó còn mở và còn dòng chữ "Uvicorn running..." không. |
| Ảnh xử lý xong nhưng báo "Lỗi: Không tìm thấy vùng MRZ hợp lệ" | Ảnh chụp không đủ rõ nét, bị nghiêng nhiều, thiếu sáng, hoặc 2 dòng MRZ ở đáy trang bị che/mờ. Chụp lại ảnh rõ hơn, đủ sáng, chụp thẳng góc. |
| `pip install` báo lỗi hoặc chạy rất lâu không xong | Kiểm tra lại kết nối Internet. Nếu mạng công ty có tường lửa/proxy chặn, cần hỏi bộ phận IT mở quyền truy cập đến pypi.org. |

---

## GHI CHÚ KỸ THUẬT (không bắt buộc đọc để sử dụng)

- Phần mềm chạy dưới dạng máy chủ nội bộ (server) ngay trên máy bạn — ảnh hộ chiếu
  **không được gửi ra Internet**, toàn bộ xử lý diễn ra trong bộ nhớ máy tính của bạn.
- Nếu muốn nhiều máy tính trong văn phòng cùng truy cập vào 1 máy chủ chung (thay vì
  mỗi máy tự cài), cần cấu hình mạng nội bộ (LAN) và mở cổng 8000 trên máy chủ — phần
  này cần người phụ trách IT hỗ trợ, không nằm trong hướng dẫn cơ bản này.

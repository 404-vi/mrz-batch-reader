# Hướng dẫn triển khai MRZ Batch Reader lên Internet (miễn phí, qua Render.com)

Tài liệu này hướng dẫn đưa phần mềm lên Internet để **máy khác, mạng khác đều bấm
link là dùng được ngay** — không cần máy bạn phải bật 24/7, và **hoàn toàn miễn phí**.

Link nhận được sẽ có dạng: **`https://quethochieu.onrender.com`**
(phần "quethochieu" có thể đổi thành tên khác nếu tên này đã có người dùng trước —
xem ghi chú ở Bước 6).

> **Vì sao không phải `.app`?** Domain kết thúc bằng `.app` riêng (như
> `quethochieu.app`) luôn phải MUA, không có cách nào miễn phí. Còn
> `quethochieu.onrender.com` là subdomain Render cấp miễn phí vĩnh viễn — đúng theo
> lựa chọn "không tốn phí" bạn đã chọn.

## Tổng quan quy trình (2 giai đoạn, khoảng 20 phút)

1. Đưa mã nguồn lên **GitHub** (nơi lưu trữ code, miễn phí) — không cần biết dùng
   Git dòng lệnh, chỉ cần kéo-thả file qua trình duyệt.
2. Kết nối GitHub đó với **Render** (nơi chạy phần mềm, miễn phí) — Render tự đọc
   file `Dockerfile` đã có sẵn trong project để biết cách cài đặt và chạy phần mềm.

---

## GIAI ĐOẠN 1 — Đưa code lên GitHub

### Bước 1: Tạo tài khoản GitHub (bỏ qua nếu đã có)

1. Truy cập **https://github.com/signup**
2. Nhập email, mật khẩu, tên tài khoản theo hướng dẫn trên màn hình, xác nhận email.

### Bước 2: Tạo 1 kho chứa code mới (repository)

1. Sau khi đăng nhập, bấm dấu **"+"** ở góc trên bên phải → **"New repository"**.
2. Đặt tên (ví dụ: `mrz-batch-reader`).
3. Chọn **Public** (bắt buộc để dùng được Render gói Free với Blueprint dễ dàng nhất)
   hoặc **Private** đều được — cả 2 đều dùng được với Render.
4. Bấm **"Create repository"**.

### Bước 3: Tải toàn bộ code lên (không cần cài Git)

1. Ở trang repository vừa tạo, bấm **"uploading an existing file"** (hoặc menu
   **Add file → Upload files**).
2. Giải nén file `mrz_reader.zip` bạn đang có ra một thư mục trên máy.
3. Mở thư mục đó ra, **chọn tất cả file và thư mục con bên trong** (bao gồm
   `Dockerfile`, `render.yaml`, `requirements.txt`, thư mục `app/`...) rồi **kéo-thả**
   toàn bộ vào khung upload trên GitHub.
   ⚠️ Kéo đúng **nội dung bên trong** thư mục `mrz_reader`, không kéo cả thư mục
   `mrz_reader` bọc ngoài — nếu không, Render sẽ không tìm thấy `Dockerfile` ở đúng
   vị trí gốc.
4. Chờ tải lên xong (thanh tiến trình chạy hết), cuộn xuống dưới, bấm
   **"Commit changes"**.

---

## GIAI ĐOẠN 2 — Triển khai trên Render

### Bước 4: Tạo tài khoản Render (miễn phí)

1. Truy cập **https://render.com** → **"Get Started"**.
2. Chọn **"Sign up with GitHub"** — cách này giúp Render tự kết nối với GitHub luôn,
   đỡ phải cấu hình thêm.

### Bước 5: Tạo Web Service mới

1. Trong Render Dashboard, bấm nút **"New +"** (góc trên bên phải) → chọn
   **"Web Service"**.
2. Nếu được hỏi quyền truy cập GitHub, bấm **"Configure account"** và cấp quyền cho
   Render truy cập vào đúng repository `mrz-batch-reader` bạn vừa tạo.
3. Chọn repository đó, bấm **"Connect"**.

### Bước 6: Đặt tên và chọn gói Free

1. Ở ô **Name**, nhập tên bạn muốn làm subdomain, ví dụ: `quethochieu`
   → link sẽ là `https://quethochieu.onrender.com`.
   - Nếu Render báo tên đã có người dùng, thử tên khác, ví dụ `quethochieu-mrz`.
2. Ở mục **Runtime**, Render sẽ tự nhận diện là **Docker** (nhờ có sẵn file
   `Dockerfile`) — không cần chỉnh gì thêm.
3. Ở mục **Instance Type / Plan**, chọn **Free**.
4. Bấm **"Create Web Service"**.

### Bước 7: Chờ build và lấy link

1. Render sẽ tự động tải code, build Docker image (cài Tesseract + thư viện Python)
   — quá trình này mất khoảng **3-5 phút** cho lần đầu tiên, theo dõi tiến trình ở
   tab **"Logs"**.
2. Khi thấy dòng chữ dạng `Uvicorn running on http://0.0.0.0:...` trong Logs và
   trạng thái chuyển sang **"Live"** (chấm xanh) → hoàn tất!
3. Link phần mềm của bạn hiện ở đầu trang, dạng:
   **`https://quethochieu.onrender.com`**
4. Gửi link này cho bất kỳ ai — mở trên máy nào, mạng nào cũng dùng được ngay,
   không cần cài đặt gì cả (khác với cách chạy trên máy cá nhân trước đây).

---

## LƯU Ý QUAN TRỌNG KHI DÙNG GÓI FREE

- **"Ngủ" sau 15 phút không ai dùng:** Render sẽ tạm dừng phần mềm nếu không có ai
  truy cập trong 15 phút. Lượt truy cập **đầu tiên** sau đó sẽ mất khoảng **~1 phút**
  để phần mềm "thức dậy" trước khi trang hiện ra — không phải lỗi, cứ đợi là được.
  Những người dùng sau đó (trong cùng phiên hoạt động) thì tốc độ bình thường.
- **Không có mật khẩu đăng nhập** (theo đúng lựa chọn của bạn): bất kỳ ai có link
  đều dùng được. Nếu sau này muốn giới hạn chỉ người trong tổ chức dùng, có thể yêu
  cầu bổ sung thêm bước xác thực.
- **File tải lên không lưu trữ vĩnh viễn:** ảnh hộ chiếu chỉ xử lý tạm trong bộ nhớ
  rồi bỏ đi ngay (đúng như thiết kế ban đầu), không phải lo mất dữ liệu khi Render
  khởi động lại.

## CẬP NHẬT PHẦN MỀM SAU NÀY (khi cần sửa/thêm tính năng)

Mỗi khi có bản code mới:
1. Vào lại repository trên GitHub → **Add file → Upload files** → tải file đã sửa
   lên đè vào (hoặc kéo-thả lại toàn bộ) → **Commit changes**.
2. Render **tự động phát hiện** có code mới và **tự động build + deploy lại** —
   không cần làm gì thêm bên phía Render.

## XỬ LÝ LỖI THƯỜNG GẶP

| Tình huống | Cách xử lý |
|---|---|
| Build lỗi, tab Logs báo `Dockerfile not found` | Kiểm tra lại Bước 3: có thể bạn đã kéo cả thư mục `mrz_reader` bọc ngoài vào GitHub thay vì kéo nội dung bên trong nó. `Dockerfile` phải nằm ở vị trí gốc của repository. |
| Build lỗi liên quan `tesseract` hoặc `apt-get` | Thường do Render tạm thời lỗi kết nối khi tải gói - bấm **"Manual Deploy" → "Deploy latest commit"** để thử build lại. |
| Trang báo "502 Bad Gateway" ngay sau khi deploy xong | Render vẫn đang cập nhật định tuyến, đợi 1-2 phút rồi tải lại trang. |
| Mở link lần đầu trong ngày rất chậm | Bình thường - phần mềm đang "thức dậy" sau khi ngủ (xem mục Lưu ý ở trên), đợi khoảng 1 phút. |
| Muốn đổi sang domain riêng `quethochieu.app` sau này | Mua domain đó ở bất kỳ nhà đăng ký nào (Namecheap, Porkbun...), vào Render → service → **Settings → Custom Domains** → thêm domain, làm theo hướng dẫn trỏ DNS Render đưa ra. Render tự cấp HTTPS miễn phí cho domain riêng. |

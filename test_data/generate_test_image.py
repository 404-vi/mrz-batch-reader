"""Tạo ảnh giả lập trang thông tin hộ chiếu (có nhiễu nhẹ + vùng MRZ ở đáy)
để kiểm tra pipeline OCR + parser, dùng dữ liệu mẫu chuẩn ICAO 9303."""

from PIL import Image, ImageDraw, ImageFont
import random

W, H = 1600, 1000
img = Image.new("RGB", (W, H), color=(235, 232, 220))  # nền giấy hộ chiếu hơi ngả vàng
draw = ImageDraw.Draw(img)

font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
font_field = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
font_mrz = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 40)

# Giả lập các trường thông tin phía trên (không phải MRZ)
draw.text((60, 40), "PASSPORT / HỘ CHIẾU", font=font_title, fill=(20, 20, 20))
draw.text((60, 120), "Surname / Họ: ERIKSSON", font=font_field, fill=(30, 30, 30))
draw.text((60, 160), "Given names: ANNA MARIA", font=font_field, fill=(30, 30, 30))
draw.text((60, 200), "Passport No: L898902C3", font=font_field, fill=(30, 30, 30))
draw.text((60, 240), "Nationality: UTOPIAN", font=font_field, fill=(30, 30, 30))

# Khung ảnh chân dung giả
draw.rectangle([1200, 100, 1480, 400], outline=(80, 80, 80), width=3)
draw.text((1260, 230), "PHOTO", font=font_field, fill=(150, 150, 150))

# Vùng MRZ (2 dòng, ở đáy trang - đúng theo chuẩn thực tế)
mrz_line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
mrz_line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"

mrz_y1 = H - 150
mrz_y2 = H - 95
draw.text((55, mrz_y1), mrz_line1, font=font_mrz, fill=(10, 10, 10))
draw.text((55, mrz_y2), mrz_line2, font=font_mrz, fill=(10, 10, 10))

# Thêm nhiễu nhẹ giả lập ảnh chụp thực tế (không quá sạch như render thuần)
pixels = img.load()
random.seed(42)
for _ in range(15000):
    x = random.randint(0, W - 1)
    y = random.randint(0, H - 1)
    r, g, b = pixels[x, y]
    noise = random.randint(-12, 12)
    pixels[x, y] = (max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise)))

out_path = "/home/claude/mrz_reader/test_data/sample_passport.png"
img.save(out_path)
print(f"Đã tạo ảnh test: {out_path}")

# ---------------------------------------------------------------------------
# Ảnh test thứ 2: hộ chiếu Việt Nam (dữ liệu hư cấu, check digit tự tính đúng chuẩn)
# ---------------------------------------------------------------------------
img2 = Image.new("RGB", (W, H), color=(230, 235, 225))
draw2 = ImageDraw.Draw(img2)
draw2.text((60, 40), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", font=font_title, fill=(20, 20, 20))
draw2.text((60, 120), "Họ và tên / Full name: NGUYỄN VĂN AN", font=font_field, fill=(30, 30, 30))
draw2.text((60, 160), "Số hộ chiếu / No: B12345678", font=font_field, fill=(30, 30, 30))
draw2.text((60, 200), "Quốc tịch / Nationality: VIỆT NAM", font=font_field, fill=(30, 30, 30))
draw2.rectangle([1200, 100, 1480, 400], outline=(80, 80, 80), width=3)
draw2.text((1260, 230), "PHOTO", font=font_field, fill=(150, 150, 150))

mrz_line1_vn = "P<VNMNGUYEN<<VAN<AN<<<<<<<<<<<<<<<<<<<<<<<<<"[:44]
mrz_line2_vn = "B123456781VNM9001011M3001019<<<<<<<<<<<<<<04"[:44]
draw2.text((55, H - 150), mrz_line1_vn, font=font_mrz, fill=(10, 10, 10))
draw2.text((55, H - 95), mrz_line2_vn, font=font_mrz, fill=(10, 10, 10))

pixels2 = img2.load()
random.seed(7)
for _ in range(15000):
    x = random.randint(0, W - 1)
    y = random.randint(0, H - 1)
    r, g, b = pixels2[x, y]
    noise = random.randint(-12, 12)
    pixels2[x, y] = (max(0, min(255, r + noise)),
                     max(0, min(255, g + noise)),
                     max(0, min(255, b + noise)))

out_path2 = "/home/claude/mrz_reader/test_data/sample_passport_vn.png"
img2.save(out_path2)
print(f"Đã tạo ảnh test: {out_path2}")

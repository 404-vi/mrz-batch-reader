"""
mrz_parser.py
Parse và validate MRZ (Machine Readable Zone) theo chuẩn ICAO Doc 9303.
Hỗ trợ định dạng TD3 (hộ chiếu thông thường - 2 dòng, 44 ký tự/dòng).

Không thực hiện khôi phục phiên âm/dấu theo quốc gia (theo lựa chọn hiện tại):
mọi trường tên/text được trả về đúng như trong MRZ (chỉ chữ hoa A-Z, dấu '<' -> khoảng trắng).
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Bảng mã quốc gia (ISO 3166-1 alpha-3, dùng trong MRZ) -> tên quốc gia
# Đây KHÔNG phải là bộ quy tắc phiên âm - chỉ dùng để hiển thị tên quốc gia
# đầy đủ thay vì mã 3 ký tự, giúp phân biệt rõ hộ chiếu thuộc quốc gia nào.
# ---------------------------------------------------------------------------
COUNTRY_CODES = {
    "VNM": "Việt Nam", "USA": "Hoa Kỳ", "GBR": "Vương quốc Anh", "FRA": "Pháp",
    "DEU": "Đức", "D": "Đức", "ITA": "Ý", "ESP": "Tây Ban Nha", "PRT": "Bồ Đào Nha",
    "NLD": "Hà Lan", "BEL": "Bỉ", "CHE": "Thụy Sĩ", "AUT": "Áo", "SWE": "Thụy Điển",
    "NOR": "Na Uy", "DNK": "Đan Mạch", "FIN": "Phần Lan", "POL": "Ba Lan",
    "CZE": "Séc", "SVK": "Slovakia", "HUN": "Hungary", "ROU": "Romania",
    "BGR": "Bulgaria", "GRC": "Hy Lạp", "TUR": "Thổ Nhĩ Kỳ", "RUS": "Nga",
    "UKR": "Ukraine", "CHN": "Trung Quốc", "JPN": "Nhật Bản", "KOR": "Hàn Quốc",
    "PRK": "Triều Tiên", "IND": "Ấn Độ", "PAK": "Pakistan", "BGD": "Bangladesh",
    "THA": "Thái Lan", "LAO": "Lào", "KHM": "Campuchia", "MMR": "Myanmar",
    "MYS": "Malaysia", "SGP": "Singapore", "IDN": "Indonesia", "PHL": "Philippines",
    "AUS": "Úc", "NZL": "New Zealand", "CAN": "Canada", "MEX": "Mexico",
    "BRA": "Brazil", "ARG": "Argentina", "CHL": "Chile", "COL": "Colombia",
    "ZAF": "Nam Phi", "EGY": "Ai Cập", "NGA": "Nigeria", "KEN": "Kenya",
    "SAU": "Ả Rập Xê Út", "ARE": "UAE", "ISR": "Israel", "IRN": "Iran",
    "IRQ": "Iraq", "UTO": "Utopia (mã ví dụ ICAO)",
}

CHAR_VALUES = {c: i for i, c in enumerate("0123456789")}
CHAR_VALUES.update({c: i + 10 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
CHAR_VALUES["<"] = 0
WEIGHTS = [7, 3, 1]

# ---------------------------------------------------------------------------
# Sửa lỗi OCR phổ biến - KHÔNG liên quan đến ngôn ngữ/quốc gia, đây là lỗi
# nhận diện ký tự thuần túy (chữ và số trông giống nhau: O/0, I/1, S/5, B/8, Z/2, G/6...).
# Áp dụng theo 2 cách:
#   1) Theo VỊ TRÍ: một số vị trí trong MRZ CHỈ được phép là số hoặc CHỈ được phép là chữ
#      (theo đặc tả ICAO 9303) -> ép về đúng loại ký tự nếu OCR đọc sai loại.
#   2) Theo CHECK DIGIT: với các trường có số kiểm tra (passport no, ngày sinh...),
#      nếu check digit không khớp, thử hoán đổi từng ký tự khả nghi (dùng bảng nhầm lẫn)
#      xem có ký tự nào khi sửa lại thì check digit khớp hay không.
# ---------------------------------------------------------------------------
DIGIT_TO_ALPHA = {"0": "O", "1": "I", "2": "Z", "5": "S", "6": "G", "8": "B", "7": "Z"}
ALPHA_TO_DIGIT = {"O": "0", "I": "1", "Z": "2", "S": "5", "G": "6", "B": "8", "L": "1", "D": "0", "T": "7"}
CONFUSION_CANDIDATES = {
    "0": ["O", "D"], "O": ["0"], "1": ["I", "L"], "I": ["1"], "L": ["1"],
    "2": ["Z"], "Z": ["2", "7"], "5": ["S"], "S": ["5"], "6": ["G"], "G": ["6"],
    "8": ["B"], "B": ["8"], "7": ["Z", "T"], "T": ["7"],
}


def _force_alpha(ch: str) -> str:
    """Ép 1 ký tự về dạng chữ cái nếu nó là số dễ nhầm; giữ nguyên nếu đã là chữ/'<' ."""
    if ch.isdigit():
        return DIGIT_TO_ALPHA.get(ch, ch)
    return ch


def _force_digit(ch: str) -> str:
    """Ép 1 ký tự về dạng số nếu nó là chữ dễ nhầm; giữ nguyên nếu đã là số."""
    if ch.isalpha():
        return ALPHA_TO_DIGIT.get(ch, ch)
    return ch


def correct_line1_positions(line1: str) -> str:
    """Vị trí 5-43 (tên) chỉ được là chữ hoặc '<', KHÔNG có số -> ép về chữ."""
    chars = list(line1)
    for i in range(5, 44):
        chars[i] = _force_alpha(chars[i])
    return "".join(chars)


def correct_line2_positions(line2: str) -> str:
    """Ép đúng loại ký tự cho từng vùng cố định theo đặc tả ICAO 9303 TD3 dòng 2."""
    chars = list(line2)
    # 0-8: số hộ chiếu (alphanumeric - không ép)
    chars[9] = _force_digit(chars[9])          # check digit số hộ chiếu
    for i in range(10, 13):                     # 10-12: mã quốc tịch - chỉ chữ
        chars[i] = _force_alpha(chars[i])
    for i in range(13, 19):                     # 13-18: ngày sinh - chỉ số
        chars[i] = _force_digit(chars[i])
    chars[19] = _force_digit(chars[19])          # check digit ngày sinh
    # 20: giới tính (M/F/<) - không ép
    for i in range(21, 27):                      # 21-26: ngày hết hạn - chỉ số
        chars[i] = _force_digit(chars[i])
    chars[27] = _force_digit(chars[27])          # check digit ngày hết hạn
    # 28-41: số cá nhân (alphanumeric - không ép)
    chars[42] = _force_digit(chars[42])          # check digit số cá nhân
    chars[43] = _force_digit(chars[43])          # composite check digit
    return "".join(chars)


def try_fix_via_checksum(data: str, read_check_digit: str):
    """Nếu check digit không khớp, thử hoán đổi từng ký tự khả nghi trong `data`
    (dựa trên bảng nhầm lẫn OCR) để tìm phiên bản khớp check digit đã đọc được.
    Trả về (data_đã_sửa, đã_sửa_hay_không, vị_trí_đã_sửa_hoặc_None)."""
    if not read_check_digit.isdigit():
        return data, False, None
    target = int(read_check_digit)
    if check_digit(data) == target:
        return data, False, None
    for i, ch in enumerate(data):
        for alt in CONFUSION_CANDIDATES.get(ch, []):
            candidate = data[:i] + alt + data[i + 1:]
            if check_digit(candidate) == target:
                return candidate, True, i
    return data, False, None


def check_digit(data: str) -> int:
    """Tính check digit theo thuật toán ICAO 9303 (trọng số lặp 7,3,1)."""
    total = 0
    for i, ch in enumerate(data):
        val = CHAR_VALUES.get(ch, 0)
        total += val * WEIGHTS[i % 3]
    return total % 10


def clean_name_field(raw: str) -> str:
    """Chuyển '<' thành khoảng trắng, gộp khoảng trắng thừa. Không khôi phục dấu."""
    return re.sub(r"\s+", " ", raw.replace("<", " ")).strip()


@dataclass
class FieldCheck:
    """Kết quả kiểm tra 1 check digit: giá trị đọc được, giá trị tính được, có khớp không."""
    field_name: str
    value: str
    read_digit: Optional[str]
    computed_digit: Optional[int]
    valid: Optional[bool]


@dataclass
class MRZResult:
    document_type: str
    issuing_country_code: str
    issuing_country_name: str
    surname: str
    given_names: str
    passport_number: str
    nationality_code: str
    nationality_name: str
    birth_date: str          # YYMMDD -> hiển thị YYYY-MM-DD (giả định thế kỷ)
    sex: str
    expiry_date: str
    personal_number: str
    checks: list = field(default_factory=list)
    all_checks_valid: bool = True
    raw_line1: str = ""
    raw_line2: str = ""
    warnings: list = field(default_factory=list)


def _format_yymmdd(yymmdd: str) -> str:
    """Chuyển YYMMDD -> YYYY-MM-DD. Giả định: YY 00-30 -> 2000s, 31-99 -> 1900s
    (đây là quy ước phổ biến, không phải chuẩn tuyệt đối vì MRZ không lưu thế kỷ)."""
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        return yymmdd
    yy, mm, dd = yymmdd[0:2], yymmdd[2:4], yymmdd[4:6]
    century = "20" if int(yy) <= 30 else "19"
    return f"{century}{yy}-{mm}-{dd}"


def parse_td3(line1: str, line2: str) -> MRZResult:
    """Parse 2 dòng MRZ định dạng TD3 (hộ chiếu). Mỗi dòng phải đúng 44 ký tự."""
    line1 = line1.strip().upper().ljust(44, "<")[:44]
    line2 = line2.strip().upper().ljust(44, "<")[:44]

    warnings = []
    if not re.fullmatch(r"[A-Z0-9<]{44}", line1):
        warnings.append("Dòng 1 chứa ký tự không hợp lệ ngoài A-Z, 0-9, '<'.")
    if not re.fullmatch(r"[A-Z0-9<]{44}", line2):
        warnings.append("Dòng 2 chứa ký tự không hợp lệ ngoài A-Z, 0-9, '<'.")

    # Bước sửa lỗi OCR theo vị trí (ép đúng loại ký tự chữ/số theo đặc tả ICAO)
    line1_fixed = correct_line1_positions(line1)
    line2_fixed = correct_line2_positions(line2)
    if line1_fixed != line1:
        warnings.append("Đã tự động sửa 1 số ký tự dòng 1 (nhầm lẫn chữ/số do OCR, ví dụ O/0).")
    if line2_fixed != line2:
        warnings.append("Đã tự động sửa 1 số ký tự dòng 2 (nhầm lẫn chữ/số do OCR, ví dụ O/0, Z/2).")
    line1, line2 = line1_fixed, line2_fixed

    # ---- Dòng 1 ----
    doc_type = line1[0:2].replace("<", "")
    country_code = line1[2:5].replace("<", "")
    names_field = line1[5:44]
    if "<<" in names_field:
        surname_raw, given_raw = names_field.split("<<", 1)
    else:
        surname_raw, given_raw = names_field, ""
    surname = clean_name_field(surname_raw)
    given_names = clean_name_field(given_raw)

    # ---- Dòng 2 ----
    passport_number = line2[0:9].replace("<", "")
    pn_check = line2[9]
    nationality_code = line2[10:13].replace("<", "")
    birth_date = line2[13:19]
    bd_check = line2[19]
    sex = line2[20] if line2[20] in "MF" else "X"
    expiry_date = line2[21:27]
    ed_check = line2[27]
    personal_number = line2[28:42].replace("<", "")
    pnum_check = line2[42]
    composite_check = line2[43]

    checks = []

    def add_check(name, data, read_ch, allow_autofix=True):
        """Kiểm tra check digit; nếu sai và allow_autofix=True, thử tự sửa 1 ký tự
        khả nghi (nhầm lẫn OCR) để khớp lại check digit đã đọc được."""
        computed = check_digit(data)
        read_val = int(read_ch) if read_ch.isdigit() else None
        valid = (read_val == computed) if read_val is not None else False
        fixed_data = data
        if not valid and allow_autofix and read_val is not None:
            fixed_data, was_fixed, pos = try_fix_via_checksum(data, read_ch)
            if was_fixed:
                warnings.append(
                    f"Trường '{name}': tự động sửa ký tự tại vị trí {pos} "
                    f"('{data[pos]}' -> '{fixed_data[pos]}') để khớp check digit."
                )
                valid = True
                computed = check_digit(fixed_data)
        checks.append(FieldCheck(name, fixed_data, read_ch, computed, valid))
        return valid, fixed_data

    ok1, passport_number_data = add_check("Số hộ chiếu", line2[0:9], pn_check)
    ok2, birth_date_data = add_check("Ngày sinh", line2[13:19], bd_check)
    ok3, expiry_date_data = add_check("Ngày hết hạn", line2[21:27], ed_check)
    # Personal number check digit: theo chuẩn, nếu field toàn '<' thì digit thường là '<' hoặc '0'
    if line2[28:42].strip("<") == "":
        checks.append(FieldCheck("Số cá nhân (rỗng)", line2[28:42], pnum_check, None, True))
        ok4 = True
        personal_number_data = line2[28:42]
    else:
        ok4, personal_number_data = add_check("Số cá nhân", line2[28:42], pnum_check)

    # Dựng lại dòng 2 bằng các trường ĐÃ được tự sửa (passport no, ngày sinh, ngày hết hạn,
    # số cá nhân) trước khi tính composite check digit - nếu không, lỗi OCR ở các trường con
    # (đã fix riêng lẻ) sẽ vẫn còn tồn tại trong composite check và gây báo sai không đáng có.
    line2_rebuilt = (
        passport_number_data + line2[9] + line2[10:13]
        + birth_date_data + line2[19] + line2[20]
        + expiry_date_data + line2[27]
        + personal_number_data + line2[42] + line2[43]
    )
    composite_data_raw = line2_rebuilt[0:10] + line2_rebuilt[13:20] + line2_rebuilt[21:43]
    ok5, _ = add_check("Composite (toàn bộ dòng 2)", composite_data_raw, composite_check, allow_autofix=False)

    all_valid = all([ok1, ok2, ok3, ok4, ok5])

    # Dùng lại dữ liệu đã được auto-fix (nếu có) để hiển thị kết quả cuối cùng
    passport_number = passport_number_data.replace("<", "")
    birth_date = birth_date_data
    expiry_date = expiry_date_data
    personal_number = personal_number_data.replace("<", "")

    return MRZResult(
        document_type=doc_type,
        issuing_country_code=country_code,
        issuing_country_name=COUNTRY_CODES.get(country_code, "Không xác định"),
        surname=surname,
        given_names=given_names,
        passport_number=passport_number,
        nationality_code=nationality_code,
        nationality_name=COUNTRY_CODES.get(nationality_code, "Không xác định"),
        birth_date=_format_yymmdd(birth_date),
        sex=sex,
        expiry_date=_format_yymmdd(expiry_date),
        personal_number=personal_number,
        checks=checks,
        all_checks_valid=all_valid,
        raw_line1=line1,
        raw_line2=line2,
        warnings=warnings,
    )


def _pad_line2(l2: str) -> str:
    """Đệm dòng 2 cho đủ 44 ký tự. Khác với dòng 1, phần bị OCR làm mất ký tự thường
    nằm ở GIỮA dòng (chuỗi '<' dài của trường 'số cá nhân' - trường tùy chọn, thường
    để trống - khiến Tesseract dễ đếm thiếu số lượng '<' liên tiếp giống nhau).
    Sau chuỗi '<' đó luôn là 2 ký tự số có ý nghĩa (check digit số cá nhân + check digit
    tổng), và các ký tự số riêng lẻ này OCR đọc chính xác hơn nhiều so với đếm số lượng
    '<' lặp lại. Do đó nếu dòng bị thiếu ký tự, ta chèn '<' còn thiếu vào TRƯỚC 2 ký tự
    cuối thay vì nối thêm vào cuối cùng - tránh làm lệch vị trí 2 check digit này."""
    if len(l2) >= 44:
        return l2[:44]
    deficit = 44 - len(l2)
    if len(l2) >= 2:
        return l2[:-2] + ("<" * deficit) + l2[-2:]
    return l2.ljust(44, "<")


def find_and_parse_mrz(lines: list[str]) -> Optional[MRZResult]:
    """Nhận 1 danh sách các dòng text (thường là output OCR nhiều nguồn khác nhau),
    xác định đâu là dòng 1 / dòng 2 của MRZ rồi parse.

    Xử lý thực tế quan trọng: Tesseract đôi khi làm mất các ký tự '<' đệm ở cuối dòng
    (do chúng có thể bị coi là khoảng trắng/nhiễu), khiến dòng bị ngắn hơn 44 ký tự.
    Do đó thay vì yêu cầu đúng 44 ký tự, ta chỉ cần nhận diện đúng dòng theo đặc điểm
    cấu trúc (dòng 1 bắt đầu bằng loại giấy tờ + chứa '<<' phân tách họ/tên), sau đó
    đệm thêm '<' cho đủ 44 ký tự."""
    cleaned_lines = []
    for ln in lines:
        cleaned = re.sub(r"[^A-Z0-9<]", "", ln.upper())
        if len(cleaned) >= 20:
            cleaned_lines.append(cleaned)

    line1_candidates = sorted(
        [l for l in cleaned_lines if l[:1] in ("P", "V", "I", "A", "C") and "<<" in l],
        key=len, reverse=True,
    )
    line2_candidates = sorted(
        [l for l in cleaned_lines if l not in line1_candidates and len(l) >= 28],
        key=len, reverse=True,
    )

    if line1_candidates and line2_candidates:
        l1 = line1_candidates[0].ljust(44, "<")[:44]
        l2 = _pad_line2(line2_candidates[0])
        return parse_td3(l1, l2)

    # Fallback: kiểu cũ, dựa thuần vào độ dài gần 44 ký tự
    candidates = [_pad_line2(l) for l in cleaned_lines if 40 <= len(l) <= 44]
    for i in range(len(candidates) - 1):
        l1, l2 = candidates[i], candidates[i + 1]
        if l1[0] in ("P", "V") and re.fullmatch(r"[A-Z0-9<]{44}", l2):
            return parse_td3(l1, l2)
    if len(candidates) >= 2:
        return parse_td3(candidates[0], candidates[1])
    return None

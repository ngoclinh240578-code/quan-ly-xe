import hashlib
import html
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

try:
    import pytesseract
except Exception:  # thiếu thư viện thì vẫn dùng được nhập tay
    pytesseract = None

# ============================ HÀM XỬ LÝ ============================

OCR_CONFIG = "--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHKLMNPRSTUVXYZ0123456789-."
DIGIT_FIX = str.maketrans("OIBSZ", "01852")  # OCR hay nhầm chữ <-> số ở 2 số đầu

KEYS_PLATE = ["biển", "bien", "plate"]
KEYS_NAME = ["tên", "ten", "name"]
KEYS_CLASS = ["lớp", "lop", "class"]
KEYS_CC = ["phân khối", "phan khoi", "dung tích", "dung tich", "cc"]


def norm(text) -> str:
    """Bỏ mọi ký tự ngoài chữ và số: '59-X1 123.45' -> '59X112345'."""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def parse_plate(raw: str):
    """Tìm biển số trong chuỗi, trả về (key, text đẹp) hoặc None."""
    s = norm(raw)
    for i in range(len(s) - 7):
        head = s[i:i + 2].translate(DIGIT_FIX)
        if not head.isdigit():
            continue
        rest = s[i + 2:]
        m = (re.match(r"([A-Z]{2})(\d{5})", rest) or re.match(r"([A-Z]{2})(\d{4})", rest)
             or re.match(r"([A-Z]\d)(\d{5})", rest) or re.match(r"([A-Z]\d)(\d{4})", rest))
        if m:
            seri, num = m.groups()
            tail = f"{num[:3]}.{num[3:]}" if len(num) == 5 else num
            return head + seri + num, f"{head}-{seri} {tail}"
    return None


def pretty(key: str) -> str:
    """Định dạng lại key đã chuẩn hóa thành dạng dễ đọc."""
    p = parse_plate(key)
    return p[1] if p else key


def variants(img: Image.Image):
    img = ImageOps.exif_transpose(img).convert("L")
    if img.width < 900:
        img = img.resize((900, int(img.height * 900 / img.width)))
    auto = ImageOps.autocontrast(img, cutoff=2)
    yield auto
    yield auto.point(lambda p: 255 if p > 140 else 0)
    yield ImageOps.invert(auto)


def read_plate(img: Image.Image):
    """OCR ảnh, trả về (key, text) hoặc None. Ném lỗi nếu thiếu tesseract."""
    if pytesseract is None:
        raise RuntimeError("Chưa cài pytesseract")
    for v in variants(img):
        for psm in (6, 7, 11):
            res = parse_plate(pytesseract.image_to_string(v, config=OCR_CONFIG.format(psm=psm)))
            if res:
                return res
    return None


def find_col(cols, keys, used=()):
    for c in cols:
        if c in used:
            continue
        s = str(c).lower()
        if any(k in s for k in keys):
            return c
    return None


def clean(v) -> str:
    return "" if pd.isna(v) else str(v).strip()


def fmt_cc(v) -> str:
    s = clean(v)
    if not s:
        return "50cc"
    if re.fullmatch(r"\d+(\.0+)?", s):
        return f"{int(float(s))}cc"
    return s


def build_registry(df: pd.DataFrame) -> dict:
    """Từ bảng Excel/CSV tạo dict {biển số chuẩn hóa: thông tin học sinh}."""
    cols = list(df.columns)
    c_plate = find_col(cols, KEYS_PLATE) or cols[0]
    used = [c_plate]
    c_name = find_col(cols, KEYS_NAME, used)
    used.append(c_name)
    c_class = find_col(cols, KEYS_CLASS, used)
    used.append(c_class)
    c_cc = find_col(cols, KEYS_CC, used)
    reg = {}
    for _, row in df.iterrows():
        key = norm(clean(row[c_plate]))
        if len(key) < 6:
            continue
        reg[key] = {
            "name": clean(row[c_name]) if c_name is not None else "",
            "cls": clean(row[c_class]) if c_class is not None else "",
            "cc": fmt_cc(row[c_cc]) if c_cc is not None else "50cc",
        }
    return reg


def read_table(source, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(source, dtype=str, encoding="utf-8-sig")
    return pd.read_excel(source, dtype=str)  # cần openpyxl


def near_match(key: str, reg: dict):
    """Gợi ý biển gần giống (sai 1 ký tự do OCR). Chỉ để tham khảo, không tính là hợp lệ."""
    for k in reg:
        if len(k) == len(key) and sum(a != b for a, b in zip(k, key)) == 1:
            return k
    return None


# ============================ GIAO DIỆN ============================

st.set_page_config(page_title="Kiểm tra xe học sinh", page_icon="🛵", layout="centered")

ss = st.session_state
ss.setdefault("history", [])
ss.setdefault("last", None)
ss.setdefault("registry", {})
ss.setdefault("list_name", "")
ss.setdefault("done_hash", {})
ss.setdefault("autoloaded", False)

# Tự nạp danh sách nếu trong repo có file tên bắt đầu bằng "danh-sach"
if not ss.autoloaded:
    ss.autoloaded = True
    try:
        for p in sorted(Path(__file__).parent.glob("danh-sach*")):
            if p.suffix.lower() in (".csv", ".xlsx"):
                ss.registry = build_registry(read_table(p, p.name))
                ss.list_name = p.name
                break
    except Exception:
        pass

st.title("🛵 Kiểm tra xe học sinh")
st.caption("Chụp hoặc nhập biển số để đối chiếu với danh sách xe 50cc đã đăng ký.")

# ---- Bước 1: danh sách ----
with st.expander("1. Danh sách xe đã đăng ký", expanded=not ss.registry):
    st.write("Tải file **Excel (.xlsx)** hoặc **CSV** có các cột: **Biển số**, Họ tên, Lớp (có thể thêm cột Phân khối).")
    up_list = st.file_uploader("Chọn file danh sách", type=["xlsx", "csv"], key="list_up")
    if up_list is not None:
        h = hashlib.md5(up_list.getvalue()).hexdigest()
        if ss.done_hash.get("list") != h:
            try:
                ss.registry = build_registry(read_table(up_list, up_list.name))
                ss.list_name = up_list.name
                ss.done_hash["list"] = h
            except ImportError:
                st.error("Thiếu thư viện đọc Excel. Hãy thêm `openpyxl` vào requirements.txt, hoặc tải file CSV.")
            except Exception as e:
                st.error(f"Không đọc được file: {e}")
    if ss.registry:
        st.success(f"Đã nạp {len(ss.registry)} xe ({ss.list_name})")

if not ss.registry:
    st.info("Hãy tải danh sách xe đã đăng ký ở trên trước khi kiểm tra.")
    st.stop()


def record(key: str, text: str):
    info = ss.registry.get(key)
    ok = info is not None
    hint = None if ok else near_match(key, ss.registry)
    ss.last = {"text": text, "ok": ok, "info": info, "hint": hint}
    h = ss.history
    if h and h[0]["Biển số"] == text and (datetime.now() - h[0]["_ts"]).seconds < 10:
        return
    h.insert(0, {
        "_ts": datetime.now(),
        "Thời gian": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Biển số": text,
        "Họ tên": info["name"] if ok else "",
        "Lớp": info["cls"] if ok else "",
        "Phân khối": info["cc"] if ok else "Trên 50cc / chưa đăng ký",
        "Kết quả": "Hợp lệ" if ok else "KHÔNG hợp lệ",
    })


def handle_image(file, slot: str):
    h = hashlib.md5(file.getvalue()).hexdigest()
    if ss.done_hash.get(slot) == h:  # ảnh này đã xử lý rồi
        return
    ss.done_hash[slot] = h
    try:
        with st.spinner("Đang đọc biển số…"):
            res = read_plate(Image.open(file))
    except Exception:
        ss.last = None
        st.error("Chưa đọc ảnh được. Hãy kiểm tra file packages.txt có dòng tesseract-ocr, hoặc dùng tab Nhập tay.")
        return
    if res:
        record(*res)
    else:
        ss.last = None
        st.warning("Không đọc được biển số. Hãy chụp gần hơn, đủ sáng, thẳng góc, hoặc nhập tay.")


# ---- Bước 2: kiểm tra ----
st.subheader("2. Kiểm tra biển số")
tab_cam, tab_manual, tab_up = st.tabs(["📷 Chụp ảnh", "⌨️ Nhập tay", "🖼️ Tải ảnh"])

with tab_cam:
    shot = st.camera_input("Đưa biển số vào giữa khung rồi bấm chụp")
    if shot is not None:
        handle_image(shot, "cam")

with tab_manual:
    with st.form("manual_form"):
        txt = st.text_input("Biển số", placeholder="59-AB 123.45")
        go = st.form_submit_button("Kiểm tra")
    if go:
        p = parse_plate(txt)
        if p:
            record(*p)
        elif len(norm(txt)) >= 6:
            record(norm(txt), txt.strip().upper())
        else:
            ss.last = None
            st.warning("Biển số quá ngắn, hãy nhập đầy đủ. Ví dụ: 59-AB 123.45")

with tab_up:
    img_up = st.file_uploader("Chọn ảnh biển số", type=["jpg", "jpeg", "png"], key="img_up")
    if img_up is not None:
        handle_image(img_up, "img")

# ---- Kết quả ----
last = ss.last
if last:
    esc = html.escape
    if last["ok"]:
        i = last["info"]
        st.markdown(
            f"""<div style="background:#1fa85a;color:#fff;padding:24px;border-radius:14px;text-align:center">
            <div style="font-size:22px;font-weight:700">✔ ĐÃ ĐĂNG KÝ - HỢP LỆ</div>
            <div style="font-size:30px;font-weight:700;letter-spacing:.04em;margin:8px 0">{esc(last['text'])}</div>
            <div style="font-size:20px">Học sinh: <b>{esc(i['name'] or 'Chưa có tên')}</b></div>
            <div style="font-size:20px">Lớp: <b>{esc(i['cls'] or '-')}</b></div>
            <div style="font-size:20px">Phân khối: <b>{esc(i['cc'])}</b></div></div>""",
            unsafe_allow_html=True,
        )
    else:
        hint = ""
        if last["hint"]:
            hi = ss.registry[last["hint"]]
            hint = (f'<div style="margin-top:10px;font-size:15px;opacity:.95">Biển giống: {esc(pretty(last["hint"]))} '
                    f'({esc(hi["name"])}). Nếu đọc nhầm, hãy nhập tay lại.</div>')
        st.markdown(
            f"""<div style="background:#d63a3a;color:#fff;padding:24px;border-radius:14px;text-align:center">
            <div style="font-size:22px;font-weight:700">✖ KHÔNG CÓ TRONG DANH SÁCH</div>
            <div style="font-size:30px;font-weight:700;letter-spacing:.04em;margin:8px 0">{esc(last['text'])}</div>
            <div style="font-size:20px;font-weight:700">⚠ CẢNH BÁO: XE TRÊN 50CC</div>
            <div style="font-size:20px;font-weight:700">Yêu cầu học sinh DẮT XE RA NGOÀI</div>{hint}</div>""",
            unsafe_allow_html=True,
        )

# ---- Lịch sử ----
st.divider()
st.subheader(f"Lịch sử kiểm tra ({len(ss.history)})")
if ss.history:
    df = pd.DataFrame(ss.history).drop(columns=["_ts"])
    st.dataframe(df, hide_index=True)
    c1, c2 = st.columns(2)
    csv = df.iloc[::-1].to_csv(index=False).encode("utf-8-sig")
    c1.download_button("⬇️ Xuất Excel (CSV)", csv, file_name=f"kiem-tra-xe-{datetime.now():%Y-%m-%d}.csv", mime="text/csv")
    if c2.button("🗑️ Xóa lịch sử"):
        ss.history = []
        ss.last = None
        st.rerun()
else:
    st.info("Chưa có lượt kiểm tra nào.")

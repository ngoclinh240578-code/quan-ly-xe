import re
from datetime import datetime
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="Quét biển số xe học sinh", page_icon="🛵", layout="centered")

# ---------- Cấu hình ----------
st.sidebar.header("Cài đặt")
LIMIT = st.sidebar.number_input("Hợp lệ khi mã tỉnh nhỏ hơn", min_value=1, max_value=99, value=50, step=1)

if "history" not in st.session_state:
    st.session_state.history = []
if "last" not in st.session_state:
    st.session_state.last = None


# ---------- Xử lý biển số ----------
PLATE_RE = re.compile(r"(\d{2})([A-Z])([A-Z0-9]?)(\d{4,6})")
OCR_CONFIG = "--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHKLMNPRSTUVXYZ0123456789-."


def parse_plate(raw: str):
    """Tìm biển số VN trong chuỗi OCR. Trả về (mã tỉnh, biển số đã định dạng) hoặc None."""
    s = re.sub(r"[^A-Z0-9]", "", raw.upper())
    m = PLATE_RE.search(s)
    if not m:
        return None
    code, series, sub, num = m.groups()
    tail = f"{num[:3]}.{num[3:]}" if len(num) == 5 else num
    return int(code), f"{code}-{series}{sub} {tail}"


def variants(img: Image.Image):
    """Tạo vài phiên bản ảnh để OCR dễ đọc hơn."""
    img = ImageOps.exif_transpose(img).convert("L")
    if img.width < 900:
        ratio = 900 / img.width
        img = img.resize((900, int(img.height * ratio)))
    auto = ImageOps.autocontrast(img, cutoff=2)
    yield auto
    yield auto.point(lambda p: 255 if p > 140 else 0)
    yield ImageOps.invert(auto)  # biển nền tối chữ sáng


def read_plate(img: Image.Image):
    for v in variants(img):
        for psm in (6, 7, 11):
            text = pytesseract.image_to_string(v, config=OCR_CONFIG.format(psm=psm))
            plate = parse_plate(text)
            if plate:
                return plate
    return None


def record(code: int, text: str):
    valid = code < LIMIT
    st.session_state.last = (code, text, valid)
    hist = st.session_state.history
    if hist and hist[0]["Biển số"] == text and (datetime.now() - hist[0]["_ts"]).seconds < 10:
        return
    hist.insert(0, {
        "_ts": datetime.now(),
        "Thời gian": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Biển số": text,
        "Mã tỉnh": code,
        "Kết quả": "Hợp lệ" if valid else "Không hợp lệ",
    })


def show_result():
    last = st.session_state.last
    if not last:
        return
    code, text, valid = last
    color, label, sign = ("#1fa85a", "HỢP LỆ", "<") if valid else ("#d63a3a", "KHÔNG HỢP LỆ", "≥")
    st.markdown(
        f"""
        <div style="background:{color};color:#fff;padding:24px;border-radius:14px;text-align:center">
          <div style="font-size:34px;font-weight:700;letter-spacing:.04em">{text}</div>
          <div style="font-size:22px;font-weight:700;margin-top:6px">{'✔' if valid else '✖'} {label}</div>
<div style="opacity:.85;margin-top:4px">Mã {code} {sign} {LIMIT}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- Giao diện ----------
st.title("🛵 Quét biển số xe học sinh")
st.caption("Chụp biển số, app đọc 2 số đầu (mã tỉnh): nhỏ hơn ngưỡng là xanh, ngược lại là đỏ.")

tab_cam, tab_up, tab_manual = st.tabs(["📷 Chụp ảnh", "🖼️ Tải ảnh lên", "⌨️ Nhập tay"])

with tab_cam:
    shot = st.camera_input("Đưa biển số vào giữa khung rồi bấm chụp")
    if shot is not None:
        with st.spinner("Đang đọc biển số…"):
            res = read_plate(Image.open(shot))
        if res:
            record(*res)
        else:
            st.session_state.last = None
            st.warning("Không đọc được biển số. Thử chụp gần hơn, đủ sáng và thẳng góc.")

with tab_up:
    up = st.file_uploader("Chọn ảnh biển số", type=["jpg", "jpeg", "png"])
    if up is not None:
        with st.spinner("Đang đọc biển số…"):
            res = read_plate(Image.open(up))
        if res:
            record(*res)
        else:
            st.session_state.last = None
            st.warning("Không đọc được biển số trong ảnh này.")

with tab_manual:
    with st.form("manual", clear_on_submit=False):
        txt = st.text_input("Biển số", placeholder="59-X1 123.45")
        if st.form_submit_button("Kiểm tra"):
            res = parse_plate(txt)
            if res:
                record(*res)
            else:
                st.session_state.last = None
                st.warning("Biển số không đúng định dạng. Ví dụ: 59-X1 123.45")

show_result()

# ---------- Lịch sử ----------
st.divider()
st.subheader(f"Lịch sử quét ({len(st.session_state.history)})")
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history).drop(columns=["_ts"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    csv = df.iloc[::-1].to_csv(index=False).encode("utf-8-sig")  # utf-8-sig để Excel đọc đúng tiếng Việt
    c1.download_button("⬇️ Xuất Excel (CSV)", csv,
                       file_name=f"bien-so-{datetime.now():%Y-%m-%d}.csv", mime="text/csv",
                       use_container_width=True)
    if c2.button("🗑️ Xóa lịch sử", use_container_width=True):
        st.session_state.history = []
        st.session_state.last = None
        st.rerun()
else:
    st.info("Chưa có biển số nào được quét.")

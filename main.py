import re
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="Kiểm tra xe dưới 50cc", page_icon="🛵", layout="centered")

if "history" not in st.session_state:
    st.session_state.history = []
if "last" not in st.session_state:
    st.session_state.last = None
if "registered" not in st.session_state:
    st.session_state.registered = {}  # {biển số chuẩn hóa: thông tin học sinh}


# ---------- Đọc & chuẩn hóa biển số ----------
OCR_CONFIG = "--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHKLMNPRSTUVXYZ0123456789-."
DIGIT_FIX = str.maketrans("OIBSZ", "01852")  # OCR hay nhầm chữ <-> số ở 2 số đầu


def norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def parse_plate(raw: str):
    """Trả về dict {key, text, kind} hoặc None.
    kind: 'two_letters' (vd 59-AB 123.45) hoặc 'letter_digit' (vd 59-X1 123.45)."""
    s = norm(raw)
    for i in range(len(s) - 7):
        head = s[i:i + 2].translate(DIGIT_FIX)
        if not head.isdigit():
            continue
        rest = s[i + 2:]
        m = re.match(r"([A-Z]{2})(\d{5})", rest) or re.match(r"([A-Z]{2})(\d{4})", rest)
        kind = "two_letters"
        if not m:
            m = re.match(r"([A-Z]\d)(\d{5})", rest) or re.match(r"([A-Z]\d)(\d{4})", rest)
            kind = "letter_digit"
        if m:
            seri, num = m.groups()
            tail = f"{num[:3]}.{num[3:]}" if len(num) == 5 else num
            return {"key": head + seri + num, "text": f"{head}-{seri} {tail}", "kind": kind}
    return None


def variants(img: Image.Image):
    img = ImageOps.exif_transpose(img).convert("L")
    if img.width < 900:
        img = img.resize((900, int(img.height * 900 / img.width)))
    auto = ImageOps.autocontrast(img, cutoff=2)
    yield auto
    yield auto.point(lambda p: 255 if p > 140 else 0)
    yield ImageOps.invert(auto)


def read_plate(img: Image.Image):
    for v in variants(img):
        for psm in (6, 7, 11):
            text = pytesseract.image_to_string(v, config=OCR_CONFIG.format(psm=psm))
            plate = parse_plate(text)
            if plate:
                return plate
    return None


# ---------- Quyết định hợp lệ / không hợp lệ ----------
def judge(plate: dict, mode: str):
    """Trả về (valid, lý do, thông tin học sinh)."""
    if mode == "list":
        info = st.session_state.registered.get(plate["key"])
        if info is not None:
            return True, "Có trong danh sách xe dưới 50cc đã đăng ký", info
        return False, "Không có trong danh sách xe dưới 50cc", ""
    # Ước lượng theo seri: biển cũ của xe dưới 50cc thường có 2 chữ cái liền nhau
    if plate["kind"] == "two_letters":
        return True, "Seri 2 chữ cái, có thể là xe dưới 50cc (ước lượng)", ""return False, "Seri chữ + số, thường là xe từ 50cc trở lên (ước lượng)", ""


def record(plate: dict, mode: str):
    valid, reason, info = judge(plate, mode)
    st.session_state.last = (plate["text"], valid, reason, info, mode)
    hist = st.session_state.history
    if hist and hist[0]["Biển số"] == plate["text"] and (datetime.now() - hist[0]["_ts"]).total_seconds() < 10:
        return
    hist.insert(0, {
        "_ts": datetime.now(),
        "Thời gian": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Biển số": plate["text"],
        "Học sinh": info,
        "Kết quả": "Hợp lệ" if valid else "Không hợp lệ",
        "Lý do": reason,
    })


def show_result():
    last = st.session_state.last
    if not last:
        return
    text, valid, reason, info, mode = last
    color, label = ("#1fa85a", "✔ HỢP LỆ") if valid else ("#d63a3a", "✖ KHÔNG HỢP LỆ")
    who = f'<div style="font-size:18px;margin-top:4px">{info}</div>' if info else ""
    st.markdown(
        f"""<div style="background:{color};color:#fff;padding:24px;border-radius:14px;text-align:center">
          <div style="font-size:34px;font-weight:700;letter-spacing:.04em">{text}</div>
          <div style="font-size:22px;font-weight:700;margin-top:6px">{label}</div>{who}
          <div style="opacity:.9;margin-top:6px">{reason}</div></div>""",
        unsafe_allow_html=True,
    )


# ---------- Thanh bên: chọn cách kiểm tra ----------
st.sidebar.header("Cách kiểm tra")
mode_label = st.sidebar.radio(
    "Dựa vào",
    ["Danh sách xe đã đăng ký (chính xác)", "Ký hiệu seri trên biển (ước lượng)"],
)
mode = "list" if mode_label.startswith("Danh sách") else "seri"

if mode == "list":
    st.sidebar.caption("Tải file Excel/CSV gồm cột **Biển số** (có thể thêm cột Họ tên, Lớp).")
    f = st.sidebar.file_uploader("Danh sách xe dưới 50cc", type=["csv", "xlsx"])
    if f is not None:
        df_reg = pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f)
        col = next(
            (c for c in df_reg.columns if "biển" in str(c).lower() or "bien" in str(c).lower()),
            df_reg.columns[0],
        )
        others = [c for c in df_reg.columns if c != col]
        reg = {}
        for _, row in df_reg.iterrows():
            k = norm(row[col])
            if k:
                reg[k] = " - ".join(str(row[c]) for c in others if pd.notna(row[c]))
        st.session_state.registered = reg
    st.sidebar.write(f"Đã nạp **{len(st.session_state.registered)}** xe")
else:
    st.sidebar.warning(
        "Từ 15/8/2023 biển số không còn phân loại theo dung tích xi lanh, "
        "nên cách này chỉ là ước lượng và có thể sai."
    )

# ---------- Giao diện chính ----------
st.title("🛵 Kiểm tra xe học sinh dưới 50cc")
st.caption("Chụp biển số: xe dưới 50cc là xanh, từ 50cc trở lên là đỏ.")

if mode == "list" and not st.session_state.registered:
    st.info("Hãy tải danh sách xe dưới 50cc ở thanh bên (mở bằng mũi tên « góc trái trên) trước khi quét.")

tab_cam, tab_up, tab_manual = st.tabs(["📷 Chụp ảnh", "🖼️ Tải ảnh lên", "⌨️ Nhập tay"])


def handle(img):
    with st.spinner("Đang đọc biển số…"):
        p = read_plate(Image.open(img))
    if p:
        record(p, mode)
    else:
        st.session_state.last = None
        st.warning("Không đọc được biển số. Thử chụp gần hơn, đủ sáng và thẳng góc.")


with tab_cam:
    shot = st.camera_input("Đưa biển số vào giữa khung rồi bấm chụp")
    if shot is not None:
        handle(shot)

with tab_up:
    up = st.file_uploader("Chọn ảnh biển số", type=["jpg", "jpeg", "png"])
    if up is not None:
        handle(up)

with tab_manual:
    with st.form("manual"):
        txt = st.text_input("Biển số", placeholder="59-X1 123.45")
        if st.form_submit_button("Kiểm tra"):
            p = parse_plate(txt)
            if p:
                record(p, mode)
            else:
                st.session_state.last = None
                st.warning("Biển số không đúng định dạng. Ví dụ: 59-X1 123.45")

show_result()

# ---------- Lịch sử ----------
st.divider()
st.subheader(f"Lịch sử quét ({len(st.session_state.history)})")
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history).drop(columns=["_ts"])
    st.dataframe(df, hide_index=True)
    c1, c2 = st.columns(2)
    csv = df.iloc[::-1].to_csv(index=False).encode("utf-8-sig")
    c1.download_button(
        "⬇️ Xuất Excel (CSV)",
        csv,
        file_name=f"kiem-tra-xe-{datetime.now():%Y-%m-%d}.csv",
        mime="text/csv",
    )
    if c2.button("🗑️ Xóa lịch sử"):
        st.session_state.history = []
        st.session_state.last = None
        st.rerun()
else:
    st.info("Chưa có biển số nào được quét.")

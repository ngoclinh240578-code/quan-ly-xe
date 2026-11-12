import html
import os
import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="Kiểm tra xe học sinh", page_icon="🛵")

DUNG_TICH_TOI_DA = 50
CAC_FILE = ["hocsinh.xlsx", "hocsinh.csv"]


def chuan_hoa(s):
    """Chỉ giữ chữ và số, viết hoa: 59X1-123.45 -> 59X112345"""
    return re.sub(r"[^0-9A-Z]", "", str(s).upper())


def bo_dau(s):
    s = str(s).replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tim_cot(cac_cot, tu_khoa):
    for c in cac_cot:
        k = bo_dau(c)
        if any(t in k for t in tu_khoa):
            return c
    return None


@st.cache_data
def tai_du_lieu(duong_dan, mtime):
    if duong_dan.endswith(".xlsx"):
        df = pd.read_excel(duong_dan, dtype=str)
    else:
        df = pd.read_csv(duong_dan, dtype=str, encoding="utf-8-sig")
    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    c_bien = tim_cot(df.columns, ["bienso"])
    c_ten = tim_cot(df.columns, ["hoten", "ten"])
    c_cc = tim_cot(df.columns, ["phankhoi", "dungtich", "cc"])
    c_ma = tim_cot(df.columns, ["maso", "mahs"])
    if not (c_bien and c_ten and c_cc):
        raise ValueError("File thiếu cột. Cần có: Họ tên, Biển số, Phân khối")

    out = pd.DataFrame({
        "ho_ten": df[c_ten].str.strip(),
        "ma_so": df[c_ma].str.strip() if c_ma else "",
        "bien_so": df[c_bien].str.strip(),
        "cc": pd.to_numeric(df[c_cc].str.extract(r"(\d+)")[0], errors="coerce"),
    })
    out["key"] = out["bien_so"].map(chuan_hoa)
    return out[out["key"] != ""].reset_index(drop=True)


def tra_cuu_nhap_tay(df, text):
    k = chuan_hoa(text)
    if not k:
        return None
    kq = df[df["key"] == k]
    return kq.iloc[0] if not kq.empty else None


def tra_cuu_tu_anh(df, text_ocr):
    gop = chuan_hoa(text_ocr)
    for _, r in df.iterrows():
        if r["key"] in gop:
            return r
    return None


@st.cache_resource(show_spinner="Đang tải mô hình đọc biển số (lần đầu hơi lâu)...")
def tai_ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def doc_chu_tu_anh(file):
    import cv2
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    if img.width > 1600:
        img = img.resize((1600, int(img.height * 1600 / img.width)))
    elif img.width < 800:
        img = img.resize((img.width * 2, img.height * 2))
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    kq, _ = tai_ocr()(arr)
    if not kq:
        return ""
    return " ".join(str(x[1]) for x in kq)


def khung(mau, noi_dung):
    st.markdown(
        f'<div style="background:{mau};color:white;padding:22px;'
        f'border-radius:12px;margin-top:10px;">{noi_dung}</div>',
        unsafe_allow_html=True,
    )


def hien_thi(hs):
    if hs is not None and pd.notna(hs["cc"]) and hs["cc"] <= DUNG_TICH_TOI_DA:
        khung(
            "#16a34a",
            "<h1 style='margin:0'>✅ XE 50cc – ĐÃ ĐĂNG KÝ</h1>"
            f"<h3>Họ tên: {html.escape(hs['ho_ten'])}</h3>"
            f"<h3>Mã số: {html.escape(hs['ma_so'])}</h3>"
            f"<h3>Biển số: {html.escape(hs['bien_so'])}</h3>",
        )
    elif hs is not None:
        khung(
            "#dc2626",
            "<h1 style='margin:0'>⛔ XE TRÊN 50cc</h1>"
            f"<h3>Biển số: {html.escape(hs['bien_so'])} ({int(hs['cc'])}cc)</h3>"
            "<h2>👉 DẮT XE RA NGOÀI</h2>",
        )
    else:
        khung(
            "#dc2626",
            "<h1 style='margin:0'>⛔ KHÔNG CÓ TRONG DANH SÁCH</h1>"
            "<h3>⚠️ Cảnh báo: đây là xe trên 50cc</h3>"
            "<h2>👉 DẮT XE RA NGOÀI</h2>",
        )


# ---------------- Giao diện ----------------
st.title("🛵 Kiểm tra xe học sinh")

file_data = next((f for f in CAC_FILE if os.path.exists(f)), None)
if file_data is None:
    st.error("Không tìm thấy file hocsinh.xlsx hoặc hocsinh.csv cùng thư mục với main.py")
    st.stop()

try:
    du_lieu = tai_du_lieu(file_data, os.path.getmtime(file_data))
except Exception as e:
    st.error(f"Lỗi đọc file {file_data}: {e}")
    st.stop()

tab1, tab2 = st.tabs(["⌨️ Nhập tay", "📷 Chụp / tải ảnh biển số"])

with tab1:
    with st.form("form_nhap", clear_on_submit=True):
        bien = st.text_input("Nhập biển số xe (ví dụ 70X1-12345):")
        gui = st.form_submit_button("Kiểm tra")
    if gui:
        if bien.strip():
            hien_thi(tra_cuu_nhap_tay(du_lieu, bien))
        else:
            st.warning("Chưa nhập biển số.")

with tab2:
    anh_chup = st.camera_input("Chụp biển số xe")
    anh_tai = st.file_uploader("Hoặc tải ảnh lên", type=["jpg", "jpeg", "png"])
    anh = anh_chup if anh_chup is not None else anh_tai
    if anh is not None:
        with st.spinner("Đang đọc biển số..."):
            try:
                chu = doc_chu_tu_anh(anh)
            except Exception as e:
                chu = ""
                st.error(f"Lỗi đọc ảnh: {e}")
        if chuan_hoa(chu):
            st.caption(f"Chữ đọc được từ ảnh: {chu}")
            hien_thi(tra_cuu_tu_anh(du_lieu, chu))
        else:
            khung(
                "#f59e0b",
                "<h2 style='margin:0'>⚠️ Không đọc được biển số</h2>"
                "<h3>Hãy chụp lại gần hơn, đủ sáng, hoặc dùng tab Nhập tay.</h3>",
            )

with st.expander("📋 Danh sách xe đã đăng ký"):
    st.dataframe(du_lieu[["ho_ten", "ma_so", "bien_so", "cc"]],
                 use_container_width=True, hide_index=True)

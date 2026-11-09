import re
import streamlit as st
import pandas as pd

try:
    import cv2
    import numpy as np
    CO_CAMERA = True
except ImportError:
    CO_CAMERA = False

st.set_page_config(page_title="Kiểm tra xe học sinh", page_icon="🛵")

FILE_DATA = "hocsinh.csv"
DUNG_TICH_TOI_DA = 50


def chuan_hoa(s: str) -> str:
    """Viết hoa, bỏ khoảng trắng, dấu chấm, gạch ngang."""
    return re.sub(r"[\s.\-_]", "", str(s)).upper()


@st.cache_data
def tai_du_lieu(duong_dan: str) -> pd.DataFrame:
    df = pd.read_csv(duong_dan, dtype=str, encoding="utf-8-sig").fillna("")
    df.columns = [c.strip() for c in df.columns]
    df["key_ma"] = df["ma_so"].map(chuan_hoa)
    df["key_bien"] = df["bien_so"].map(chuan_hoa)
    df["cc"] = pd.to_numeric(df["dung_tich"], errors="coerce")
    return df


def tra_cuu(df: pd.DataFrame, ma: str):
    k = chuan_hoa(ma)
    if not k:
        return None
    kq = df[(df["key_ma"] == k) | (df["key_bien"] == k)]
    return kq.iloc[0] if not kq.empty else None


def hien_thi_ket_qua(ma: str, df: pd.DataFrame):
    hs = tra_cuu(df, ma)

    if hs is not None and pd.notna(hs["cc"]) and hs["cc"] <= DUNG_TICH_TOI_DA:
        st.markdown(
            f"""
            <div style="background:#16a34a;color:white;padding:24px;border-radius:12px;">
              <h1 style="margin:0;">✅ XE 50cc – ĐÃ ĐĂNG KÝ</h1>
              <h3>Họ tên: {hs['ho_ten']}</h3>
              <h3>Mã số: {hs['ma_so']}</h3>
              <h3>Biển số: {hs['bien_so']}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif hs is not None:
        st.markdown(
            f"""
            <div style="background:#dc2626;color:white;padding:24px;border-radius:12px;">
              <h1 style="margin:0;">⛔ XE TRÊN 50cc</h1>
              <h3>Biển số: {hs['bien_so']} ({hs['dung_tich']}cc)</h3>
              <h2>👉 HÀNH ĐỘNG: DẮT XE RA NGOÀI</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background:#dc2626;color:white;padding:24px;border-radius:12px;">
              <h1 style="margin:0;">⛔ KHÔNG CÓ TRONG DANH SÁCH</h1>
              <h2>👉 HÀNH ĐỘNG: DẮT XE RA NGOÀI</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.title("🛵 Kiểm tra xe học sinh")

try:
    du_lieu = tai_du_lieu(FILE_DATA)
except FileNotFoundError:
    st.error(f"Không tìm thấy file '{FILE_DATA}'. Hãy đặt file cùng thư mục với app.py.")
    st.stop()
except KeyError as e:
    st.error(f"File CSV thiếu cột: {e}. Cần các cột: ma_so, ho_ten, bien_so, dung_tich")
    st.stop()

tab1, tab2 = st.tabs(["⌨️ Máy quét / Nhập tay", "📷 Camera (QR)"])

with tab1:
    with st.form("form_quet", clear_on_submit=True):
        ma_nhap = st.text_input("Quét hoặc nhập mã số / biển số:")
        gui = st.form_submit_button("Kiểm tra")
    if gui:
        if ma_nhap.strip():
            hien_thi_ket_qua(ma_nhap, du_lieu)
        else:
            st.warning("Chưa có mã để kiểm tra.")

with tab2:
    if not CO_CAMERA:
        st.info("Cần cài thêm: pip install opencv-python-headless numpy")
    else:
        anh = st.camera_input("Chụp mã QR trên xe")
        if anh is not None:
            mang = np.frombuffer(anh.getvalue(), np.uint8)
            hinh = cv2.imdecode(mang, cv2.IMREAD_COLOR)
            noi_dung, _, _ = cv2.QRCodeDetector().detectAndDecode(hinh)
            if noi_dung:
                hien_thi_ket_qua(noi_dung, du_lieu)
            else:
                st.warning("Không đọc được mã QR, hãy chụp lại.")

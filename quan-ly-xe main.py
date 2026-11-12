import re
import unicodedata

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="Kiểm tra xe học sinh", page_icon="🛵", layout="wide")

FILE_DATA = "hocsinh.csv"
DUNG_TICH_TOI_DA = 50
XANH = (22, 163, 74)   # RGB
DO = (220, 38, 38)
CAM = (245, 158, 11)
MAU_NEN = {"XANH": "#bbf7d0", "DO": "#fecaca", "CAM": "#fde68a"}


def chuan_hoa(s) -> str:
    """Viết hoa, bỏ khoảng trắng, dấu chấm, gạch ngang."""
    return re.sub(r"[^0-9A-Z]", "", str(s).upper())


def bo_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


@st.cache_data
def tai_du_lieu(duong_dan: str) -> pd.DataFrame:
    df = pd.read_csv(duong_dan, dtype=str, encoding="utf-8-sig").fillna("")
    df.columns = [c.strip() for c in df.columns]
    df["key_bien"] = df["bien_so"].map(chuan_hoa)
    df["cc"] = pd.to_numeric(df["dung_tich"], errors="coerce")
    return df


@st.cache_resource(show_spinner="Đang tải mô hình nhận diện xe...")
def tai_yolo():
    from ultralytics import YOLO
    return YOLO("yolov8n.pt")


@st.cache_resource(show_spinner="Đang tải mô hình đọc biển số...")
def tai_ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def doc_chu(ocr, crop_rgb: np.ndarray) -> str:
    """OCR toàn bộ chữ trong ảnh cắt của một xe."""
    h, w = crop_rgb.shape[:2]
    if h < 10 or w < 10:
        return ""
    if max(h, w) < 400:
        crop_rgb = cv2.resize(crop_rgb, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    kq, _ = ocr(cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2BGR))
    if not kq:
        return ""
    return " ".join(str(x[1]) for x in kq)


def tim_hoc_sinh(df: pd.DataFrame, chu_doc: str):
    """Tìm học sinh có biển số xuất hiện trong chữ OCR đọc được."""
    gop = chuan_hoa(chu_doc)
    if len(gop) < 5:
        return None
    for _, r in df.iterrows():
        if r["key_bien"] and r["key_bien"] in gop:
            return r
    return None


def ve_khung(img, box, mau, nhan):
    x1, y1, x2, y2 = box
    cv2.rectangle(img, (x1, y1), (x2, y2), mau, 3)
    (tw, th), _ = cv2.getTextSize(nhan, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    ytop = max(y1 - th - 8, 0)
    cv2.rectangle(img, (x1, ytop), (x1 + tw + 8, ytop + th + 8), mau, -1)
    cv2.putText(img, nhan, (x1 + 4, ytop + th + 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def xu_ly(img_rgb: np.ndarray, df: pd.DataFrame):
    yolo = tai_yolo()
    ocr = tai_ocr()

    # YOLO nhận mảng numpy theo kênh BGR
    kq = yolo.predict(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR),
                      conf=0.25, classes=[3], verbose=False)[0]  # 3 = motorcycle
    boxes = kq.boxes.xyxy.cpu().numpy().astype(int).tolist() if kq.boxes is not None else []
    boxes.sort(key=lambda b: (b[0], b[1]))
H, W = img_rgb.shape[:2]
out = img_rgb.copy()
rows = []
for i, (x1, y1, x2, y2) in enumerate(boxes, start=1):
        x1, y1 = max(x1, 0), max(y1, 0)
        x2, y2 = min(x2, W), min(y2, H)
        chu = doc_chu(ocr, img_rgb[y1:y2, x1:x2])
        hs = tim_hoc_sinh(df, chu)

        if hs is not None and pd.notna(hs["cc"]) and hs["cc"] <= DUNG_TICH_TOI_DA:
            mau, nhan, loai = XANH, f"{i}. {bo_dau(hs['ho_ten'])}", "XANH"
            kq_text, hanh_dong = "✅ Xe 50cc đã đăng ký", "Cho qua"
            ten, ma, bien = hs["ho_ten"], hs["ma_so"], hs["bien_so"]
        elif hs is not None:
            mau, nhan, loai = DO, f"{i}. TREN 50cc", "DO"
            kq_text, hanh_dong = f"⛔ Xe trên 50cc ({hs['dung_tich']}cc)", "DẮT XE RA NGOÀI"
            ten, ma, bien = hs["ho_ten"], hs["ma_so"], hs["bien_so"]
        elif chuan_hoa(chu) and len(chuan_hoa(chu)) >= 5:
            mau, nhan, loai = DO, f"{i}. KHONG CO TRONG DS", "DO"
            kq_text, hanh_dong = "⛔ Không có trong danh sách", "DẮT XE RA NGOÀI"
            ten, ma, bien = "", "", chu
        else:
            mau, nhan, loai = CAM, f"{i}. KHONG DOC DUOC BIEN", "CAM"
            kq_text, hanh_dong = "⚠️ Không đọc được biển số", "Kiểm tra thủ công"
            ten, ma, bien = "", "", ""

        ve_khung(out, (x1, y1, x2, y2), mau, nhan)
        rows.append({
            "STT": i, "Kết quả": kq_text, "Họ tên": ten, "Mã số": ma,
            "Biển số": bien, "Hành động": hanh_dong, "_loai": loai,
        })
    
def hien_thi(img_rgb: np.ndarray, df: pd.DataFrame):
    with st.spinner("Đang nhận diện..."):
        try:
            out, bang = xu_ly(img_rgb, df)
        except Exception as e:
            st.error(f"Lỗi khi nhận diện: {e}")
            return

    st.image(out, use_container_width=True)

    if bang.empty:
        st.info("Không phát hiện xe máy nào trong ảnh.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Xanh (đã đăng ký)", int((bang["_loai"] == "XANH").sum()))
    c2.metric("🔴 Đỏ (dắt ra ngoài)", int((bang["_loai"] == "DO").sum()))
    c3.metric("🟠 Kiểm tra thủ công", int((bang["_loai"] == "CAM").sum()))

    hien = bang.drop(columns="_loai")
    mau = bang["_loai"].map(MAU_NEN).tolist()
    styled = hien.style.apply(
        lambda r: [f"background-color:{mau[r.name]};color:#111"] * len(r), axis=1
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


def doc_anh(file) -> np.ndarray:
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    if img.width > 1600:
        img = img.resize((1600, int(img.height * 1600 / img.width)))
    return np.array(img)


# ---------------- Giao diện ----------------
st.title("🛵 Kiểm tra xe học sinh bằng hình ảnh")

try:
    du_lieu = tai_du_lieu(FILE_DATA)
    _ = du_lieu["ma_so"], du_lieu["ho_ten"], du_lieu["bien_so"], du_lieu["dung_tich"]
except FileNotFoundError:
    st.error(f"Không tìm thấy file '{FILE_DATA}'. Hãy đặt file cùng thư mục với main.py.")
    st.stop()
except KeyError as e:
    st.error(f"File CSV thiếu cột: {e}. Cần các cột: ma_so, ho_ten, bien_so, dung_tich")
    st.stop()

tab1, tab2 = st.tabs(["📁 Tải ảnh lên", "📷 Chụp bằng camera"])

with tab1:
    f = st.file_uploader("Chọn ảnh cổng trường", type=["jpg", "jpeg", "png"])
    if f is not None:
        hien_thi(doc_anh(f), du_lieu)

with tab2:
    a = st.camera_input("Chụp xe ở cổng")
    if a is not None:
        hien_thi(doc_anh(a), du_lieu)

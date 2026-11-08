import os
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
import easyocr
import re

# ==========================================
# CẤU HÌNH GIAO DIỆN
# ==========================================
st.set_page_config(page_title="Quản Lý Xe Học Sinh", page_icon="🏫", layout="wide")

st.title("🏫 Hệ Thống Nhận Diện & Quản Lý Xe Học Sinh (AI + CSDL)")

# Tên file cơ sở dữ liệu local
DB_FILE = "database_hoc_sinh.csv"

def init_database():
    """Khởi tạo hoặc tải cơ sở dữ liệu từ file CSV"""
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        # Tạo bảng mẫu nếu chưa có
        df = pd.DataFrame(columns=["Ma_HS", "Ho_Ten", "Lop", "Bien_So", "Dung_Tich"])
        # Thêm vài dữ liệu mẫu để test
        sample_data = [
            {"Ma_HS": "HS001", "Ho_Ten": "Nguyễn Văn A", "Lop": "11A1", "Bien_So": "59A112345", "Dung_Tich": 110},
            {"Ma_HS": "HS002", "Ho_Ten": "Trần Thị B", "Lop": "10B2", "Bien_So": "59FA88888", "Dung_Tich": 49}
        ]
        df = pd.concat([df, pd.DataFrame(sample_data)], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        return df

def save_database(df):
    df.to_csv(DB_FILE, index=False)

df_db = init_database()

# Khởi tạo mô hình OCR (Cache để chạy nhanh)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

with st.spinner("Đang khởi động AI..."):
    reader = load_ocr()

# Tạo giao diện chia tab
tab1, tab2 = st.tabs(["📸 Quét Xe & Đối Chiếu", "📋 Quản Lý CSDL Học Sinh"])

# ==========================================
# TAB 1: QUÉT XE VÀ ĐỐI CHIẾU
# ==========================================
with tab1:
    st.subheader("Quét Ảnh Xe Thực Tế Tại Cổng Trường")
    
    col_input1, col_input2 = st.columns([1, 1])
    
    with col_input1:
        option = st.radio("Chọn phương thức:", ["Tải ảnh xe lên", "Chụp từ Camera"])
        uploaded_file = None
        
        if option == "Tải ảnh xe lên":
            uploaded_file = st.file_uploader("Chọn hình ảnh xe...", type=["jpg", "jpeg", "png"])
        else:
            uploaded_file = st.camera_input("Chụp trực tiếp xe tại cổng")

    with col_input2:
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.markdown("**📷 Hình ảnh xe thực tế:**")
            st.image(image, use_container_width=True)
            
            if st.button("🔍 Tiến hành nhận diện & Đối chiếu", type="primary", use_container_width=True):
                with st.spinner("AI đang xử lý ảnh và quét biển số..."):
                    # Chuyển ảnh PIL sang OpenCV format
                    img_cv = np.array(image)
                    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

# Tiền xử lý & OCR
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    results = reader.readtext(gray)
                    
                    raw_plate = "".join([res[1] for res in results])
                    clean_plate = "".join(filter(str.isalnum, raw_plate)).upper()
                    
                    st.markdown("---")
                    st.markdown(f"**Biển số AI nhận diện được:** `{clean_plate if clean_plate else 'Không rõ'}`")
                    
                    # Cho phép chỉnh sửa tay nếu AI đọc nhầm
                    manual_fix = st.text_input("Nếu biển số chưa đúng, nhập lại chính xác vào đây:", value=clean_plate)
                    if manual_fix:
                        clean_plate = "".join(filter(str.isalnum, manual_fix)).upper()

                    # ĐỐI CHƯỚC VỚI CSDL HỌC SINH
                    if df_db.empty or not clean_plate:
                        st.error("🔴 [CẢNH BÁO ĐỎ]: Xe CHƯA ĐĂNG KÝ hoặc không đọc được biển số!")
                        st.write("👉 **Hành động:** Giữ xe lại kiểm tra giấy tờ.")
                    else:
                        matched = df_db[df_db["Bien_So"].astype(str).str.replace(" ", "") == clean_plate]
                        
                        if matched.empty:
                            st.error("🔴 [CẢNH BÁO ĐỎ]: Xe CHƯA ĐĂNG KÝ trong hệ thống trường!")
                            st.write("👉 **Hành động:** Giữ xe lại kiểm tra.")
                        else:
                            hs = matched.iloc[0]
                            cc = hs["Dung_Tich"]
                            
                            if cc > 50:
                                st.warning(f"🟡 [CẢNH BÁO VÀNG]: Xe đã đăng ký nhưng VI PHẠM PHÂN KHỐI (>50cc)!")
                                st.markdown(f"""
                                - **Học sinh:** {hs['Ho_Ten']}
                                - **Lớp:** {hs['Lop']}
                                - **Mã HS:** {hs['Ma_HS']}
                                - **Dung tích xe:** {cc} cc (Vượt mức cho phép học sinh)
                                """)
                            else:
                                st.success(f"🟢 [AN TOÀN - XANH]: Xe hợp lệ, đúng quy định!")
                                st.markdown(f"""
                                - **Học sinh:** {hs['Ho_Ten']}
                                - **Lớp:** {hs['Lop']}
                                - **Mã HS:** {hs['Ma_HS']}
                                - **Dung tích xe:** {cc} cc (<= 50cc)
                                """)

# ==========================================
# TAB 2: QUẢN LÝ CSDL HỌC SINH
# ==========================================
with tab2:
    st.subheader("Danh Sách Hồ Sơ Học Sinh & Đăng Ký Xe")
    
    # Form thêm học sinh
    with st.expander("➕ Thêm Hồ Sơ Học Sinh / Xe Mới"):
        with st.form("add_form"):
            c1, c2, c3 = st.columns(3)
            ma_hs = c1.text_input("Mã HS")
            ho_ten = c2.text_input("Họ Tên")
            lop = c3.text_input("Lớp")
            
            c4, c5 = st.columns(2)
            bien_so = c4.text_input("Biển Số Xe (viết liền, không dấu)")
            dung_tich = c5.number_input("Dung Tích (cc)", min_value=49, max_value=500, value=50)
            
            submit_btn = st.form_submit_button("Lưu vào CSDL")
            if submit_btn:
                if ma_hs and ho_ten and bien_so:
                    clean_b = "".join(filter(str.isalnum, bien_so)).upper()
                    new_row = pd.DataFrame({
                        "Ma_HS": [ma_hs], "Ho_Ten": [ho_ten], "Lop": [lop],
                        "Bien_So": [clean_b], "Dung_Tich": [int(dung_tich)]
                    })
                    df_db = pd.concat([df_db, new_row], ignore_index=True)
                    save_database(df_db)
                    st.success("Đã thêm học sinh thành công! Hãy tải lại trang nếu cần.")
                else:
                    st.warning("Vui lòng nhập đầy đủ thông tin bắt buộc.")

    # Hiển thị bảng CSDL hiện tại
    st.dataframe(df_db, use_container_width=True)

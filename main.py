import streamlit as st
import pandas as pd
from PIL import Image

st.set_page_config(page_title="App Quản Lý Xe Học Sinh", page_icon="🚗", layout="centered")

@st.cache_data
def load_database():
    data = {
        "Mã HS": ["HS001", "HS002", "HS003", "HS004"],
        "Họ tên": ["Chu Ngọc Phương Linh", "Lê Trần Bảo Ngân", "Huỳnh Lê Bảo Trân", "Lê Vũ Nguyệt Minh"],
        "Lớp": ["11A6", "11A2", "11A3", "11A8"],
        "Biển số xe": ["70HA01125", "70A40523", "61AB88888", "43KA24681"],
        "Dung tích (cc)": [50, 150, 50, 50]
    }
    return pd.DataFrame(data)

df_db = load_database()

st.title("🚗 App Quản Lý & Nhận Diện Xe Học Sinh")

with st.sidebar:
    st.header("📂 Sổ tay Dữ liệu Trường")
    st.dataframe(df_db, use_container_width=True)

st.divider()
st.subheader("📸 Chụp ảnh hoặc Tải ảnh xe tại cổng")

upload_choice = st.radio("Chọn phương thức lấy ảnh:", ["Chụp ảnh trực tiếp từ Camera", "Quét ảnh trực tiếp từ Camera "])

img_file = None
if upload_choice == "Chụp ảnh trực tiếp từ Camera":
    img_file = st.camera_input("Bật camera")
else:
    img_file = st.file_uploader("Quét ảnh trực tiếp từ camera")

if img_file is not None:
    image = Image.open(img_file)
    st.image(image, caption="Hình ảnh xe thực tế", use_column_width=True)
    
    detected_plate = st.text_input("Biển số xe nhận diện được:")
    
    if st.button("🚀 Đối chiếu & Cảnh báo", type="primary"):
        clean_plate = detected_plate.upper().replace(" ", "").replace("-", "").replace(".", "")
        matched_row = df_db[df_db["Biển số xe"].str.replace(" ", "") == clean_plate]
        
        if matched_row.empty:
            st.error("🔴 CẢNH BÁO ĐỎ: Xe CHƯA ĐĂNG KÝ trong hệ thống!")
            st. error("🔴 CẢNH BÁO ĐỎ: Xe TRÊN 50CC")
            st.markdown("* **Hành động:** Giữ xe lại kiểm tra.")
        else:
            hs_info = matched_row.iloc[0]
            cc = hs_info["Dung tích (cc)"]
            
            if cc > 50:
                st.warning("🟡 CẢNH BÁO VÀNG: Đã đăng ký người dùng nhưng VI PHẠM QUY ĐỊNH PHÂN KHỐI (>50cc)!")
                st.markdown(f"* **Học sinh:** {hs_info['Họ tên']} (Lớp: {hs_info['Lớp']})\n* **Dung tích:** {cc}cc")
            else:
                st.success("🟢 AN TOÀN: Xe hợp lệ, đúng quy định!")
                st.markdown(f"* **Học sinh:** {hs_info['Họ tên']} (Lớp: {hs_info['Lớp']})\n* **Dung tích:** {cc}cc")

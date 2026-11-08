import cv2
import numpy as np
import streamlit as st
from PIL import Image
from ultralytics import YOLO

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Nhận Diện Giao Thông AI (YOLOv8)", page_icon="🚦", layout="wide")

st.title("🚦 Hệ Thống Giám Sát & Nhận Diện Phương Tiện Bằng AI (YOLOv8)")
st.markdown("Hệ thống tự động phát hiện, khoanh vùng và đếm phương tiện giao thông.")

# Load mô hình YOLOv8 (Sử dụng cache để không load lại nhiều lần)
@st.cache_resource
def load_yolo_model():
    # Tải model yolov8n.pt (nhỏ, nhẹ, chạy nhanh)
    return YOLO('yolov8n.pt')

with st.spinner("Đang khởi tạo mô hình AI YOLOv8..."):
    model = load_yolo_model()

st.success("Mô hình AI đã sẵn sàng!")

# Chọn phương thức đầu vào
option = st.radio("Chọn nguồn dữ liệu:", ["Tải ảnh lên", "Chụp từ Camera web"])

if option == "Tải ảnh lên":
    uploaded_file = st.file_uploader("Chọn ảnh giao thông (JPG, PNG)...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        img_cv = np.array(image)
        # Chuyển RGB sang BGR cho OpenCV xử lý
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ảnh Gốc")
            st.image(image, use_container_width=True)
            
        with col2:
            st.subheader("Kết Quả AI Nhận Diện")
            if st.button("🚀 Chạy Nhận Diện AI", type="primary"):
                with st.spinner("AI đang quét và phân tích phương tiện..."):
                    # Chạy mô hình YOLOv8 dự đoán
                    results = model(img_cv, conf=0.4)
                    
                    # YOLO hỗ trợ hàm .plot() để tự vẽ bounding box lên ảnh
                    annotated_frame = results[0].plot()
                    
                    # Chuyển đổi lại màu BGR sang RGB để hiển thị trên Streamlit
                    annotated_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                    
                    st.image(annotated_rgb, use_container_width=True)
                    st.success("Đã nhận diện thành công các phương tiện trong ảnh!")

elif option == "Chụp từ Camera web":
    camera_file = st.camera_input("Chụp ảnh trực tiếp từ camera cổng trường")
    
    if camera_file is not None:
        image = Image.open(camera_file)
        img_cv = np.array(image)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
        
        with st.spinner("AI đang phân tích khung hình..."):
            results = model(img_cv, conf=0.4)
            annotated_frame = results[0].plot()
            annotated_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            
            st.image(annotated_rgb, use_container_width=True)

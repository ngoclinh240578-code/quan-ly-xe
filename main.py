import cv2
import numpy as np
from ultralytics import YOLO

def main():
    print("⏳ Đang tải mô hình AI YOLOv8...")
    # Tải mô hình YOLOv8 nano (hoặc yolov8s.pt, yolov8m.pt để độ chính xác cao hơn)
    # Model sẽ tự động tải file trọng số về lần chạy đầu tiên.
    model = YOLO('yolov8n.pt')
    print("✅ Đã sẵn sàng! Đang mở camera...")

    # Mở webcam (hoặc thay bằng đường dẫn video/stream rtsp nếu có)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Không thể mở camera.")
        return

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("❌ Không đọc được khung hình từ camera.")
            break

        # Đưa khung hình qua mô hình YOLOv8 để nhận diện đối tượng
        # conf=0.4 nghĩa là chỉ hiển thị các đối tượng có độ tin cậy từ 40% trở lên
        results = model(frame, conf=0.4, verbose=False)

        # Lấy khung hình đã được YOLO tự động vẽ sẵn các hộp (bounding boxes) và nhãn tên
        annotated_frame = results[0].plot()

        # (Tùy chọn) Bạn có thể vẽ thêm vạch kẻ đường ngang/dọc mô phỏng hệ thống giám sát giao thông
        h, w, _ = annotated_frame.shape
        # Vẽ một đường vạch đỏ ngang đường
        cv2.line(annotated_frame, (0, int(h * 0.7)), (w, int(h * 0.7)), (0, 0, 255), 3)
        # Hiển thị chữ lên góc trái phía trên giống camera giám sát
        cv2.putText(annotated_frame, "CAMERA GIAO THONG - DIEN BIEN PHU", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Hiển thị kết quả lên màn hình
        cv2.imshow("He Thong Giam Sat Giao Thong AI (YOLOv8)", annotated_frame)

        # Bấm phím 'ESC' để thoát chương trình
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

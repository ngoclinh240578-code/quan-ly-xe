return False, "Seri chữ + số, thường là xe từ 50cc trở lên (ước lượng)", ""


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

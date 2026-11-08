st.subheader("Danh Sách Hồ Sơ Học Sinh & Đăng Ký Xe")
    
           
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

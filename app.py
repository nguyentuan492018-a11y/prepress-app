import streamlit as st
from PIL import Image, ImageDraw
import io

st.set_page_config(page_title="Gravure Prepress V3 - Multi-Bag System", layout="wide")

st.title("🖨️ Phần mềm Tự động hóa Chế bản In Ống Đồng (Phiên bản V3 - Đa dạng kiểu túi)")
st.markdown("Hệ thống tự động điều chỉnh thông số kỹ thuật và bố cục theo từng dạng bao bì thực tế.")

# Chia giao diện thành 2 cột
col_input, col_preview = st.columns([1, 1.5])

with col_input:
    st.subheader("1. Chọn quy cách & Dạng túi")
    
    # Bổ sung danh mục các dạng túi thực tế trong in ống đồng
    bag_type = st.selectbox("Chọn dạng túi / Bao bì:", [
        "Túi Lưng Giữa (Center Seal Pouch)", 
        "Túi 3 Biên (3-Side Seal Pouch)", 
        "Túi Đáy Đứng Zipper (Stand-up Pouch)", 
        "Màng Cuộn Tự Động (Flow Wrap / Rollstock)"
    ])
    
    film_type = st.selectbox("Loại màng ghép:", ["PET//PE", "OPP//CPP", "PET//AL//PE"])
    
    col_w, col_h = st.columns(2)
    with col_w:
        width = st.number_input("Chiều rộng (mm):", value=180)
    with col_h:
        height = st.number_input("Chiều cao (mm):", value=110)
        
    st.subheader("2. Nội dung biến đổi")
    product_name = st.text_input("Tên sản phẩm (Mặt trước):", "TRÀ NHUẬN GAN")
    sub_title = st.text_input("Loại sản phẩm:", "Túi lọc")
    
    company_info = st.text_input("Tên công ty / Đơn vị:", "BỆNH VIỆN ĐẠI HỌC Y DƯỢC TP.HCM")
    uses_text = st.text_area("Công dụng:", "Hỗ trợ điều trị các bệnh viêm gan có vàng da, viêm túi mật, ăn uống kém.")
    usage_text = st.text_input("Cách dùng:", "Hãm với 200ml nước sôi, bỏ bã")
    
    barcode = st.text_input("Mã vạch (Barcode):", "8938500123456")
    color_code = st.text_input("Mã màu pha / Hệ màu:", "CMYK + 1 Spot Color")

with col_preview:
    st.subheader(f"3. Maket Kỹ Thuật: {bag_type}")
    
    # Tạo hình ảnh maket canvas
    img_w, img_h = 750, 500
    canvas_img = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas_img)
    
    # Vẽ khung tràn lề (Bleed - màu đỏ)
    bleed_margin = 15
    draw.rectangle([bleed_margin, bleed_margin, img_w - bleed_margin, img_h - bleed_margin - 80], outline="red", width=2)
    
    # Vẽ khung thành phẩm chính (Màu đen)
    box_x1, box_y1, box_x2, box_y2 = 40, 40, img_w - 40, img_h - 120
    draw.rectangle([box_x1, box_y1, box_x2, box_y2], outline="black", width=2)
    
    # Xử lý hiển thị đường phân chia mặt tùy thuộc vào Dạng túi được chọn
    if "Túi Lưng Giữa" in bag_type:
        mid_x = int((box_x1 + box_x2) / 2)
        # Đường hàn lưng ở giữa
        for y_line in range(box_y1, box_y2, 10):
            draw.line([(mid_x, y_line), (mid_x, y_line + 5)], fill="blue", width=1)
        draw.text((mid_x - 50, box_y1 + 5), "[ Mép dán lưng ]", fill="blue")
        
        # Nội dung mặt trước & sau được điều chỉnh né mép dán lưng
        draw.text((mid_x + 30, box_y1 + 40), "Trà", fill="orange")
        draw.text((mid_x + 30, box_y1 + 80), product_name, fill="red")
        
        draw.text((box_x1 + 20, box_y1 + 30), "Công dụng:", fill="brown")
        draw.text((box_x1 + 20, box_y1 + 55), uses_text[:45] + "...", fill="black")
        
    elif "Túi 3 Biên" in bag_type:
        # Túi 3 biên thường thiết kế tràn đều, chừa biên hàn 3 cạnh
        draw.rectangle([box_x1 + 10, box_y1 + 10, box_x2 - 10, box_y2 - 10], outline="gray", width=1)
        draw.text((box_x1 + 40, box_y1 + 40), product_name, fill="red")
        draw.text((box_x1 + 40, box_y1 + 80), f"Quy cách: {bag_type}", fill="black")
        draw.text((box_x1 + 40, box_y1 + 120), f"Công dụng: {uses_text[:50]}...", fill="black")
        
    else:
        # Mặc định cho các loại khác
        mid_x = int((box_x1 + box_x2) / 2)
        for y_line in range(box_y1, box_y2, 10):
            draw.line([(mid_x, y_line), (mid_x, y_line + 5)], fill="gray", width=1)
        draw.text((mid_x + 30, box_y1 + 60), product_name, fill="red")
        draw.text((box_x1 + 20, box_y1 + 40), f"Thông tin: {uses_text[:40]}...", fill="black")

    # --- BẢNG THÔNG TIN KỸ THUẬT DƯỚI ĐÁY ---
    table_y = box_y2 + 10
    draw.rectangle([box_x1, table_y, box_x2, table_y + 60], outline="black", width=1)
    draw.line([(box_x1 + 180, table_y), (box_x1 + 180, table_y + 60)], fill="black", width=1)
    draw.line([(box_x1 + 350, table_y), (box_x1 + 350, table_y + 60)], fill="black", width=1)
    draw.line([(box_x1 + 460, table_y), (box_x1 + 460, table_y + 60)], fill="black", width=1)
    draw.line([(box_x1 + 570, table_y), (box_x1 + 570, table_y + 60)], fill="black", width=1)
    
    draw.text((box_x1 + 10, table_y + 10), f"Kích thước: K{height}*B{width}mm", fill="black")
    draw.text((box_x1 + 10, table_y + 35), f"Loại: {bag_type.split(' ')[0]}", fill="blue")
    draw.text((box_x1 + 190, table_y + 20), "KHÁCH HÀNG KÝ DUYỆT", fill="gray")
    draw.text((box_x1 + 360, table_y + 20), "KINH DOANH", fill="gray")
    draw.text((box_x1 + 480, table_y + 20), "THIẾT KẾ", fill="gray")

    # Hiển thị maket lên web
    st.image(canvas_img, caption=f"Mô phỏng maket kỹ thuật cho dạng: {bag_type}", use_container_width=True)
    st.success(f"⚙️ Đã áp dụng quy chuẩn kỹ thuật dành riêng cho **{bag_type}** thành công!")

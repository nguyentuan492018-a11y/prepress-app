import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os

st.set_page_config(page_title="Gravure Prepress V4 - Colorful Mockup", layout="wide")

st.title("🎨 Phần mềm Thiết kế & Mô phỏng Bao bì Màu sắc (Phiên bản V4)")
st.markdown("Hệ thống tạo maket bao bì trực quan, màu sắc sống động sẵn sàng cho việc kiểm tra mỹ thuật và kỹ thuật.")

# Hàm tải font an toàn tránh lỗi tiếng Việt
def get_font(size):
    font_paths = [
        "DejaVuSans-Bold.ttf", 
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()

col_input, col_preview = st.columns([1, 1.4])

with col_input:
    st.subheader("1. Tùy chọn Quy cách & Bao bì")
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
        
    st.subheader("2. Nội dung & Màu sắc thiết kế")
    product_name = st.text_input("Tên sản phẩm:", "TRÀ NHUẬN GAN")
    sub_title = st.text_input("Loại sản phẩm:", "Thảo dược thiên nhiên 100%")
    company_info = st.text_input("Đơn vị sản xuất:", "BỆNH VIỆN ĐẠI HỌC Y DƯỢC TP.HCM")
    uses_text = st.text_area("Công dụng chính:", "Hỗ trợ thanh nhiệt, giải độc gan, bảo vệ tế bào gan.")
    
    # Chọn chủ đề màu sắc cho bao bì
    color_theme = st.selectbox("Chủ đề màu sắc chủ đạo:", [
        "Xanh Lá Thảo Dược (Eco / Trà)", 
        "Đỏ Vàng Truyền Thống (Dược phẩm)", 
        "Xanh Dương Công Nghệ (Thực phẩm chức năng)",
        "Bạc Metalize (PET//AL)"
    ])
    
    barcode = st.text_input("Mã vạch (Barcode):", "8938500123456")

with col_preview:
    st.subheader(f"3. Maket Trực Quan: {bag_type}")
    
    # Kích thước khung vẽ mô phỏng
    img_w, img_h = 700, 480
    
    # Thiết lập màu sắc theo chủ đề
    if "Xanh Lá" in color_theme:
        bg_color = (235, 247, 238)      # Xanh nhạt nền
        primary_color = (20, 100, 40)   # Xanh đậm
        accent_color = (245, 130, 32)   # Cam điểm nhấn
        banner_color = (34, 139, 34)    # Xanh lá cây
    elif "Đỏ Vàng" in color_theme:
        bg_color = (255, 248, 220)      # Vàng kem
        primary_color = (180, 20, 20)   # Đỏ đậm
        accent_color = (218, 165, 32)   # Vàng đồng
        banner_color = (178, 34, 34)    # Đỏ gạch
    elif "Xanh Dương" in color_theme:
        bg_color = (240, 248, 255)      # Xanh băng
        primary_color = (10, 60, 120)   # Xanh dương đậm
        accent_color = (255, 140, 0)    # Cam
        banner_color = (30, 144, 255)   # Xanh dương sáng
    else:
        bg_color = (220, 224, 230)      # Xám bạc metalize
        primary_color = (50, 50, 50)    # Đen/Xám tối
        accent_color = (0, 102, 204)    # Xanh dương
        banner_color = (100, 110, 120)  # Xám chì

    # Tạo ảnh canvas màu sắc
    canvas_img = Image.new("RGB", (img_w, img_h), color=(240, 240, 240))
    draw = ImageDraw.Draw(canvas_img)
    
    # Vẽ vùng bao bì chính có màu nền chủ đạo
    pkg_x1, pkg_y1, pkg_x2, pkg_y2 = 50, 30, img_w - 50, img_h - 100
    draw.rectangle([pkg_x1, pkg_y1, pkg_x2, pkg_y2], fill=bg_color, outline=primary_color, width=3)
    
    # Font chữ
    font_title = get_font(18)
    font_sub = get_font(12)
    font_body = get_font(11)
    
    # Phân định giao diện theo dạng túi
    if "Túi Lưng Giữa" in bag_type:
        mid_x = int((pkg_x1 + pkg_x2) / 2)
        # Vẽ mép dán lưng ở giữa (mờ dạng sọc chấm)
        for y_line in range(pkg_y1, pkg_y2, 12):
            draw.line([(mid_x, y_line), (mid_x, y_line + 6)], fill=(150, 150, 150), width=2)
        
        # Mặt trước (Bên trái đường hàn lưng)
        draw.rectangle([pkg_x1 + 10, pkg_y1 + 10, mid_x - 10, pkg_y1 + 50], fill=banner_color)
        draw.text((pkg_x1 + 20, pkg_y1 + 15), company_info[:35], fill=(255, 255, 255), font=font_sub)
        
        draw.text((pkg_x1 + 20, pkg_y1 + 70), sub_title, fill=accent_color, font=font_sub)
        draw.text((pkg_x1 + 20, pkg_y1 + 95), product_name, fill=primary_color, font=font_title)
        
        draw.rectangle([pkg_x1 + 15, pkg_y1 + 140, mid_x - 15, pkg_y2 - 20], fill=(255, 255, 255), outline=(200, 200, 200))
        draw.text((pkg_x1 + 25, pkg_y1 + 150), "CÔNG DỤNG CHÍNH:", fill=primary_color, font=font_sub)
        draw.text((pkg_x1 + 25, pkg_y1 + 175), uses_text[:50] + "...", fill=(50, 50, 50), font=font_body)
        
        # Mặt sau (Bên phải đường hàn lưng)
        draw.text((mid_x + 20, pkg_y1 + 30), "THÔNG TIN SẢN PHẨM", fill=primary_color, font=font_sub)
        draw.text((mid_x + 20, pkg_y1 + 70), f"Mã vạch: {barcode}", fill=(50, 50, 50), font=font_body)
        draw.text((mid_x + 20, pkg_y1 + 100), f"Quy cách: {width}x{height}mm", fill=(50, 50, 50), font=font_body)
        draw.text((mid_x + 20, pkg_y1 + 130), f"Màng ghép: {film_type}", fill=(50, 50, 50), font=font_body)
        
    else:
        # Giao diện chung cho các loại túi khác (Túi 3 biên, màng cuộn,...)
        draw.rectangle([pkg_x1, pkg_y1, pkg_x2, pkg_y1 + 60], fill=banner_color)
        draw.text((pkg_x1 + 20, pkg_y1 + 12), company_info, fill=(255, 255, 255), font=font_sub)
        draw.text((pkg_x1 + 20, pkg_y1 + 35), sub_title, fill=(240, 240, 240), font=font_body)
        
        draw.text((pkg_x1 + 30, pkg_y1 + 80), product_name, fill=primary_color, font=font_title)
        
        # Khung chứa nội dung mô tả
        draw.rectangle([pkg_x1 + 20, pkg_y1 + 120, pkg_x2 - 20, pkg_y2 - 20], fill=(255, 255, 255), outline=(210, 210, 210))
        draw.text((pkg_x1 + 35, pkg_y1 + 135), f"Công dụng: {uses_text}", fill=(60, 60, 60), font=font_body)
        draw.text((pkg_x1 + 35, pkg_y1 + 175), f"Barcode chuẩn EAN-13: {barcode}", fill=(60, 60, 60), font=font_body)
        draw.text((pkg_x1 + 35, pkg_y1 + 210), f"Dạng bao bì: {bag_type} | Vật liệu: {film_type}", fill=accent_color, font=font_body)

    # --- BẢNG THÔNG TIN KỸ THUẬT DƯỚI ĐÁY ---
    table_y = pkg_y2 + 10
    draw.rectangle([pkg_x1, table_y, pkg_x2, table_y + 50], fill=(255, 255, 255), outline=(100, 100, 100), width=1)
    
    # Các đường kẻ bảng
    draw.line([(pkg_x1 + 200, table_y), (pkg_x1 + 200, table_y + 50)], fill=(100, 100, 100), width=1)
    draw.line([(pkg_x1 + 380, table_y), (pkg_x1 + 380, table_y + 50)], fill=(100, 100, 100), width=1)
    draw.line([(pkg_x1 + 500, table_y), (pkg_x1 + 500, table_y + 50)], fill=(100, 100, 100), width=1)
    
    draw.text((pkg_x1 + 10, table_y + 10), f"Kích thước: {width} x {height} mm", fill=(0, 0, 0), font=font_body)
    draw.text((pkg_x1 + 10, table_y + 30), f"Loại: {bag_type.split(' ')[0]}", fill=primary_color, font=font_body)
    draw.text((pkg_x1 + 210, table_y + 18), "KHÁCH HÀNG DUYỆT", fill=(100, 100, 100), font=font_body)
    draw.text((pkg_x1 + 390, table_y + 18), "KINH DOANH", fill=(100, 100, 100), font=font_body)
    draw.text((pkg_x1 + 510, table_y + 18), "THIẾT KẾ", fill=(100, 100, 100), font=font_body)

    # Hiển thị ảnh maket màu sắc lên giao diện Streamlit
    st.image(canvas_img, use_container_width=True)
    st.success(f"✨ Đã render thành công maket màu sắc trực quan cho dòng sản phẩm **{product_name}**!")

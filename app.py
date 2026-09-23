# -*- coding: utf-8 -*-
"""
Ung dung Web Tu dong hoa Quy trinh Tien in an (Prepress Automation)
=====================================================================
Doi tuong su dung: Ky thuat vien va nhan vien thiet ke bao bi mang ghep
phuc hop (PET//PE, OPP//CPP) su dung cong nghe in ong dong truc khac
dien tu.

GIAI DOAN 1: Nen tang + Giao dien nhap lieu
---------------------------------------------
O giai doan nay, ung dung tap trung vao viec:
    1. Cau hinh trang va giao dien (tong mau xanh duong, responsive).
    2. Xay dung form nhap lieu day du: loai tui, kich thuoc, thong tin
       bien doi, logo, va khoi cua so trong suot.
    3. Luu du lieu nhap vao st.session_state de cac giai doan sau
       (xu ly nghiep vu, preview, xuat PDF) su dung lai ma khong can
       nguoi dung nhap lai.
    4. Hien thi bang tom tat du lieu da nhap de nguoi dung kiem tra
       nhanh (chua co canh bao nghiep vu - se lam o Giai doan 2).

Cac giai doan tiep theo (se bo sung sau):
    - Giai doan 2: Logic nghiep vu in ong dong (bleed, canh bao EAN-13,
      safe margin, overlap cua so trong suot).
    - Giai doan 3: Preview mockup truc quan bang Pillow.
    - Giai doan 4: Xuat file PDF ky thuat in an bang ReportLab.

Thu vien su dung: streamlit, pillow (PIL), reportlab.
Chi import cac thu vien nay de dam bao on dinh khi trien khai tren
Streamlit Community Cloud.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Optional

import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# HANG SO CAU HINH NGHIEP VU
# ---------------------------------------------------------------------------

# Danh sach 8 loai ket cau tui co dinh (khong cho nguoi dung tu them,
# vi day la danh sach ky thuat da duoc xac nhan voi nha may).
DANH_SACH_LOAI_TUI: list[str] = [
    "Túi dán lưng (Back Seal)",
    "Túi đứng đáy (Stand-up Pouch)",
    "Túi 3 biên",
    "Túi 4 biên",
    "Túi hông (Side Gusset)",
    "Túi đứng đáy có zipper",
    "Sachet (túi gói nhỏ)",
    "Túi cắt hình (Shaped Pouch)",
]

# Danh sach vi tri dat cua so trong suot.
DANH_SACH_VI_TRI_CUA_SO: list[str] = [
    "Giữa mặt trước",
    "Trên mặt trước",
    "Dưới mặt trước",
    "Toàn bộ mặt sau",
    "Tùy chỉnh tọa độ (X, Y)",
]

# Danh sach hinh dang cua so trong suot.
DANH_SACH_HINH_DANG_CUA_SO: list[str] = [
    "Chữ nhật bo góc",
    "Oval",
    "Tròn",
]

# Gioi han kich thuoc hop ly cho tui (mm) - dung de canh bao vuot han muc.
KICH_THUOC_TOI_THIEU_MM: float = 10.0
KICH_THUOC_TOI_DA_MM: float = 2000.0

# Dinh dang anh duoc chap nhan khi upload logo / anh mo phong san pham.
DINH_DANG_ANH_HOP_LE: list[str] = ["png", "jpg", "jpeg"]


# ---------------------------------------------------------------------------
# CAU TRUC DU LIEU (DATA CLASS) LUU THONG TIN NHAP
# ---------------------------------------------------------------------------


@dataclass
class ThongTinCuaSoTrongSuot:
    """Luu thong tin cau hinh cua so trong suot (transparent window).

    Thuoc tinh:
        co_cua_so: Nguoi dung co bat tinh nang cua so trong suot khong.
        vi_tri: Vi tri dat cua so (theo DANH_SACH_VI_TRI_CUA_SO).
        toa_do_x, toa_do_y: Toa do tuy chinh (mm), chi dung khi
            vi_tri = "Tùy chỉnh tọa độ (X, Y)".
        rong_mm, cao_mm: Kich thuoc cua so (mm).
        hinh_dang: Hinh dang cua so (theo DANH_SACH_HINH_DANG_CUA_SO).
        anh_mo_phong: Anh mo phong san pham ben trong (upload tuy chon)
            de hien thi xuyen qua cua so tren preview o Giai doan 3.
    """

    co_cua_so: bool = False
    vi_tri: str = DANH_SACH_VI_TRI_CUA_SO[0]
    toa_do_x: float = 0.0
    toa_do_y: float = 0.0
    rong_mm: float = 30.0
    cao_mm: float = 30.0
    hinh_dang: str = DANH_SACH_HINH_DANG_CUA_SO[0]
    anh_mo_phong: Optional[Image.Image] = None


@dataclass
class ThongTinThietKe:
    """Luu toan bo thong tin nhap lieu cua mot thiet ke tui.

    Day la "single source of truth" duoc luu trong st.session_state,
    cac giai doan sau (logic nghiep vu, preview, xuat PDF) se doc lai
    du lieu tu day thay vi phai nhap lai tu form.
    """

    loai_tui: str = DANH_SACH_LOAI_TUI[0]
    dai_mm: float = 0.0
    rong_mm: float = 0.0
    hong_mm: float = 0.0
    ten_san_pham: str = ""
    slogan: str = ""
    khoi_luong: str = ""
    thanh_phan: str = ""
    ma_vach: str = ""
    logo: Optional[Image.Image] = None
    cua_so_trong_suot: ThongTinCuaSoTrongSuot = field(
        default_factory=ThongTinCuaSoTrongSuot
    )


# ---------------------------------------------------------------------------
# GIAO DIEN: CSS TUY BIEN (TONG MAU XANH DUONG, RESPONSIVE)
# ---------------------------------------------------------------------------


def ap_dung_css_tuy_bien() -> None:
    """Nhung CSS thuan vao trang de dong bo tong mau xanh duong.

    Ly do dung CSS thuan (khong dung Tailwind CDN):
        - Streamlit render cac widget goc (button, input...) trong DOM
          rieng, class Tailwind gan ngoai khong "chui" vao duoc.
        - Tai CDN ngoai co the that bai/cham khi moi truong Cloud han
          che mang ngoai luc build, gay loi giao dien luc khoi dong.
        - CSS thuan nhung truc tiep vao <style> dam bao hoat dong 100%
          offline, on dinh tren Streamlit Community Cloud.
    """
    css = """
    <style>
        /* ===== Bien mau chu dao (tong xanh duong) ===== */
        :root {
            --xanh-duong-nhat: #eff6ff;   /* nen nhat, giong bg-blue-50 */
            --xanh-duong-nhac: #dbeafe;   /* vien nhe, giong bg-blue-100 */
            --xanh-duong-chinh: #2563eb;  /* nut/thanh dieu huong, blue-600 */
            --xanh-duong-dam: #1e3a8a;    /* tieu de, blue-900 */
            --xanh-duong-hover: #1d4ed8;  /* hover nut, blue-700 */
            --nen-trang: #ffffff;
            --chu-xam: #374151;
            --vien-xam: #e5e7eb;
        }

        /* ===== Nen tong the sang, sach ===== */
        .stApp {
            background-color: #f8fafc;
        }

        /* ===== Thanh header tuy bien ===== */
        .header-tuy-bien {
            background: linear-gradient(90deg, var(--xanh-duong-chinh), var(--xanh-duong-dam));
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(30, 58, 138, 0.15);
        }
        .header-tuy-bien h1 {
            color: #ffffff !important;
            margin: 0;
            font-size: 1.6rem;
        }
        .header-tuy-bien p {
            color: #dbeafe !important;
            margin: 0.25rem 0 0 0;
            font-size: 0.95rem;
        }

        /* ===== Tieu de section ===== */
        h2, h3 {
            color: var(--xanh-duong-dam) !important;
        }

        /* ===== Nut bam (button) ===== */
        .stButton > button, .stFormSubmitButton > button {
            background-color: var(--xanh-duong-chinh);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.25rem;
            font-weight: 600;
            transition: background-color 0.2s ease-in-out;
            width: 100%;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background-color: var(--xanh-duong-hover);
            color: #ffffff;
        }

        /* ===== Khung card tom tat ===== */
        .card-tom-tat {
            background-color: var(--nen-trang);
            border: 1px solid var(--vien-xam);
            border-left: 4px solid var(--xanh-duong-chinh);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
        }
        .card-tom-tat .nhan {
            color: #6b7280;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.15rem;
        }
        .card-tom-tat .gia-tri {
            color: var(--chu-xam);
            font-size: 1.05rem;
            font-weight: 600;
        }

        /* ===== Responsive: man hinh nho (mobile/tablet) ===== */
        @media (max-width: 768px) {
            .header-tuy-bien h1 {
                font-size: 1.25rem;
            }
            .header-tuy-bien p {
                font-size: 0.85rem;
            }
            .card-tom-tat {
                padding: 0.75rem 1rem;
            }
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def hien_thi_header() -> None:
    """Hien thi thanh header chinh cua ung dung."""
    st.markdown(
        """
        <div class="header-tuy-bien">
            <h1>🏭 Hệ thống Tự động hóa Tiền in ấn (Prepress)</h1>
            <p>Bao bì màng ghép phức hợp · In ống đồng trục khắc điện tử</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# GIAO DIEN: FORM NHAP LIEU
# ---------------------------------------------------------------------------


def _doc_anh_upload(file_upload) -> Optional[Image.Image]:
    """Chuyen doi file upload tu Streamlit thanh doi tuong PIL.Image.

    Tham so:
        file_upload: Doi tuong UploadedFile tra ve tu st.file_uploader,
            hoac None neu nguoi dung chua chon file.

    Tra ve:
        Doi tuong PIL.Image.Image neu doc thanh cong, nguoc lai None.
        Ham nay khong nem loi ra ngoai - moi loi doc anh (file hong,
        sai dinh dang...) deu duoc bat va bao qua st.error(), tra ve
        None de ung dung khong bi crash.
    """
    if file_upload is None:
        return None
    try:
        du_lieu_anh = file_upload.read()
        anh = Image.open(io.BytesIO(du_lieu_anh))
        # Chuyen ve RGBA de dam bao tuong thich khi ghep lop o Giai doan 3
        # (giu duoc kenh alpha cho logo nen trong suot dang PNG).
        anh = anh.convert("RGBA")
        return anh
    except Exception as loi:  # noqa: BLE001 - can bat moi loi doc anh
        st.error(f"⚠️ Không thể đọc file ảnh vừa tải lên: {loi}")
        return None


def _render_khoi_nhap_kich_thuoc() -> tuple[float, float, float]:
    """Hien thi 3 o nhap kich thuoc Dai / Rong / Hong (mm).

    Su dung st.columns() de tu dong xep 3 o canh nhau tren man hinh
    rong (desktop/tablet) va tu dong xep doc tren man hinh hep
    (mobile) - day la co che responsive mac dinh cua Streamlit.

    Tra ve:
        Tuple (dai_mm, rong_mm, hong_mm).
    """
    cot_dai, cot_rong, cot_hong = st.columns(3)
    with cot_dai:
        dai_mm = st.number_input(
            "Dài (D) - mm",
            min_value=0.0,
            max_value=KICH_THUOC_TOI_DA_MM,
            value=0.0,
            step=1.0,
            help="Chiều dài túi tính bằng milimét, chưa tính tràn lề.",
        )
    with cot_rong:
        rong_mm = st.number_input(
            "Rộng (R) - mm",
            min_value=0.0,
            max_value=KICH_THUOC_TOI_DA_MM,
            value=0.0,
            step=1.0,
            help="Chiều rộng túi tính bằng milimét, chưa tính tràn lề.",
        )
    with cot_hong:
        hong_mm = st.number_input(
            "Hông (H) - mm",
            min_value=0.0,
            max_value=KICH_THUOC_TOI_DA_MM,
            value=0.0,
            step=1.0,
            help="Bề hông túi (dùng cho túi đứng đáy/túi hông). "
            "Nhập 0 nếu loại túi không có hông.",
        )
    return dai_mm, rong_mm, hong_mm


def _render_khoi_thong_tin_bien_doi() -> tuple[str, str, str, str, str]:
    """Hien thi cac o nhap thong tin bien doi theo tung san pham.

    Tra ve:
        Tuple (ten_san_pham, slogan, khoi_luong, thanh_phan, ma_vach).
    """
    ten_san_pham = st.text_input(
        "Tên sản phẩm *",
        placeholder="Ví dụ: Sonet",
        help="Tên hiển thị chính trên bao bì.",
    )
    slogan = st.text_area(
        "Slogan / Mô tả sản phẩm",
        placeholder="Ví dụ: Bánh bông lan ngon ngọt, thơm hấp dẫn",
        height=80,
    )

    cot_khoi_luong, cot_ma_vach = st.columns(2)
    with cot_khoi_luong:
        khoi_luong = st.text_input(
            "Khối lượng tịnh",
            placeholder="Ví dụ: 200g",
        )
    with cot_ma_vach:
        ma_vach = st.text_input(
            "Mã vạch (Barcode)",
            placeholder="Ví dụ: 8938512345678",
            help="Chuẩn EAN-13 sẽ được kiểm tra ở bước xử lý nghiệp vụ.",
        )

    thanh_phan = st.text_area(
        "Thành phần",
        placeholder="Có thể để trống và bổ sung sau...",
        height=100,
    )
    return ten_san_pham, slogan, khoi_luong, thanh_phan, ma_vach


def _render_khoi_cua_so_trong_suot() -> ThongTinCuaSoTrongSuot:
    """Hien thi khoi nhap lieu cho tinh nang cua so trong suot.

    Cac o nhap chi tiet (vi tri, kich thuoc, hinh dang, anh mo phong)
    chi hien ra khi nguoi dung bat checkbox "Có cửa sổ trong suốt",
    giup form gon gang cho cac thiet ke khong can tinh nang nay.

    Tra ve:
        Doi tuong ThongTinCuaSoTrongSuot chua toan bo cau hinh.
    """
    co_cua_so = st.checkbox(
        "🔲 Có cửa sổ trong suốt (nhìn xuyên thấy sản phẩm bên trong)"
    )

    thong_tin = ThongTinCuaSoTrongSuot(co_cua_so=co_cua_so)

    if not co_cua_so:
        return thong_tin

    thong_tin.vi_tri = st.selectbox(
        "Vị trí cửa sổ",
        options=DANH_SACH_VI_TRI_CUA_SO,
    )

    if thong_tin.vi_tri == "Tùy chỉnh tọa độ (X, Y)":
        cot_x, cot_y = st.columns(2)
        with cot_x:
            thong_tin.toa_do_x = st.number_input(
                "Tọa độ X (mm, tính từ mép trái)",
                min_value=0.0,
                value=0.0,
                step=1.0,
            )
        with cot_y:
            thong_tin.toa_do_y = st.number_input(
                "Tọa độ Y (mm, tính từ mép trên)",
                min_value=0.0,
                value=0.0,
                step=1.0,
            )

    cot_rong, cot_cao = st.columns(2)
    with cot_rong:
        thong_tin.rong_mm = st.number_input(
            "Chiều rộng cửa sổ (mm)",
            min_value=1.0,
            max_value=KICH_THUOC_TOI_DA_MM,
            value=30.0,
            step=1.0,
        )
    with cot_cao:
        thong_tin.cao_mm = st.number_input(
            "Chiều cao cửa sổ (mm)",
            min_value=1.0,
            max_value=KICH_THUOC_TOI_DA_MM,
            value=30.0,
            step=1.0,
        )

    thong_tin.hinh_dang = st.selectbox(
        "Hình dạng cửa sổ",
        options=DANH_SACH_HINH_DANG_CUA_SO,
    )

    file_anh_mo_phong = st.file_uploader(
        "Ảnh mô phỏng sản phẩm bên trong (tùy chọn)",
        type=DINH_DANG_ANH_HOP_LE,
        help="Ảnh này sẽ hiển thị xuyên qua cửa sổ trong suốt ở bản xem "
        "trước (preview). Nếu bỏ trống, preview sẽ hiển thị nền trắng "
        "mô phỏng vùng trong suốt.",
        key="upload_anh_mo_phong",
    )
    thong_tin.anh_mo_phong = _doc_anh_upload(file_anh_mo_phong)

    return thong_tin


def render_form_nhap_lieu() -> Optional[ThongTinThietKe]:
    """Hien thi toan bo form nhap lieu chinh cua ung dung.

    Su dung st.form() de gom toan bo input lai va chi xu ly (submit)
    mot lan duy nhat khi nguoi dung bam nut, tranh ung dung bi render
    lai lien tuc gay giat/lag khi go tung ky tu.

    Tra ve:
        Doi tuong ThongTinThietKe neu nguoi dung da bam nut submit,
        nguoc lai tra ve None (form chua duoc gui).
    """
    with st.form(key="form_nhap_lieu_thiet_ke", clear_on_submit=False):
        st.subheader("1️⃣ Loại kết cấu túi")
        loai_tui = st.selectbox("Chọn loại túi *", options=DANH_SACH_LOAI_TUI)

        st.subheader("2️⃣ Kích thước (mm)")
        dai_mm, rong_mm, hong_mm = _render_khoi_nhap_kich_thuoc()

        st.subheader("3️⃣ Thông tin biến đổi")
        (
            ten_san_pham,
            slogan,
            khoi_luong,
            thanh_phan,
            ma_vach,
        ) = _render_khoi_thong_tin_bien_doi()

        st.subheader("4️⃣ Logo thương hiệu")
        file_logo = st.file_uploader(
            "Tải lên logo (không bắt buộc)",
            type=DINH_DANG_ANH_HOP_LE,
            help="Nếu chưa có logo, có thể bỏ trống và bổ sung sau.",
            key="upload_logo",
        )

        st.subheader("5️⃣ Cửa sổ trong suốt")
        cua_so_trong_suot = _render_khoi_cua_so_trong_suot()

        da_gui = st.form_submit_button("✅ Lưu thông tin thiết kế")

    if not da_gui:
        return None

    logo = _doc_anh_upload(file_logo)

    thong_tin_thiet_ke = ThongTinThietKe(
        loai_tui=loai_tui,
        dai_mm=dai_mm,
        rong_mm=rong_mm,
        hong_mm=hong_mm,
        ten_san_pham=ten_san_pham.strip(),
        slogan=slogan.strip(),
        khoi_luong=khoi_luong.strip(),
        thanh_phan=thanh_phan.strip(),
        ma_vach=ma_vach.strip(),
        logo=logo,
        cua_so_trong_suot=cua_so_trong_suot,
    )
    return thong_tin_thiet_ke


# ---------------------------------------------------------------------------
# GIAO DIEN: HIEN THI TOM TAT DU LIEU DA NHAP
# ---------------------------------------------------------------------------


def _hien_thi_the_tom_tat(nhan: str, gia_tri: str) -> None:
    """Hien thi mot the (card) tom tat gom nhan va gia tri.

    Tham so:
        nhan: Ten truong du lieu (vi du "Loại túi").
        gia_tri: Gia tri da nhap, se hien thi "(chưa nhập)" neu rong.
    """
    gia_tri_hien_thi = gia_tri if gia_tri else "(chưa nhập)"
    st.markdown(
        f"""
        <div class="card-tom-tat">
            <div class="nhan">{nhan}</div>
            <div class="gia-tri">{gia_tri_hien_thi}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hien_thi_tom_tat(thong_tin: ThongTinThietKe) -> None:
    """Hien thi bang tom tat toan bo thong tin thiet ke da nhap.

    O Giai doan 1, day chi la buoc hien thi lai du lieu de nguoi dung
    kiem tra nhap dung/du. Cac canh bao nghiep vu (EAN-13, safe
    margin...) se duoc bo sung o Giai doan 2.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe da duoc nguoi dung nhap.
    """
    st.success("Đã lưu thông tin thiết kế vào phiên làm việc hiện tại.")
    st.subheader("📋 Tóm tắt thông tin đã nhập")

    cot_trai, cot_phai = st.columns(2)
    with cot_trai:
        _hien_thi_the_tom_tat("Loại túi", thong_tin.loai_tui)
        _hien_thi_the_tom_tat(
            "Kích thước (D × R × H)",
            f"{thong_tin.dai_mm:.0f} × {thong_tin.rong_mm:.0f} × "
            f"{thong_tin.hong_mm:.0f} mm",
        )
        _hien_thi_the_tom_tat("Tên sản phẩm", thong_tin.ten_san_pham)
        _hien_thi_the_tom_tat("Khối lượng", thong_tin.khoi_luong)
        _hien_thi_the_tom_tat("Mã vạch", thong_tin.ma_vach)

    with cot_phai:
        _hien_thi_the_tom_tat("Slogan / Mô tả", thong_tin.slogan)
        _hien_thi_the_tom_tat("Thành phần", thong_tin.thanh_phan)
        trang_thai_logo = "Đã tải lên" if thong_tin.logo else "Chưa có (bổ sung sau)"
        _hien_thi_the_tom_tat("Logo thương hiệu", trang_thai_logo)

        if thong_tin.cua_so_trong_suot.co_cua_so:
            cua_so = thong_tin.cua_so_trong_suot
            _hien_thi_the_tom_tat(
                "Cửa sổ trong suốt",
                f"{cua_so.vi_tri} · {cua_so.rong_mm:.0f}×{cua_so.cao_mm:.0f} mm "
                f"· {cua_so.hinh_dang}",
            )
        else:
            _hien_thi_the_tom_tat("Cửa sổ trong suốt", "Không sử dụng")

    # Hien thi anh preview logo va anh mo phong (neu co) de nguoi dung
    # xac nhan da upload dung file.
    if thong_tin.logo is not None or (
        thong_tin.cua_so_trong_suot.anh_mo_phong is not None
    ):
        st.markdown("**Xem nhanh ảnh đã tải lên:**")
        cot_anh_1, cot_anh_2 = st.columns(2)
        with cot_anh_1:
            if thong_tin.logo is not None:
                st.image(thong_tin.logo, caption="Logo thương hiệu", width=200)
        with cot_anh_2:
            if thong_tin.cua_so_trong_suot.anh_mo_phong is not None:
                st.image(
                    thong_tin.cua_so_trong_suot.anh_mo_phong,
                    caption="Ảnh mô phỏng sản phẩm (qua cửa sổ trong suốt)",
                    width=200,
                )

    st.info(
        "ℹ️ Đây là bước tóm tắt dữ liệu (Giai đoạn 1). Các cảnh báo kỹ "
        "thuật (mã vạch EAN-13, vùng an toàn chữ, tràn lề, cửa sổ trong "
        "suốt chồng lấn...) sẽ được xử lý ở Giai đoạn 2."
    )


# ---------------------------------------------------------------------------
# HAM CHINH (ENTRY POINT)
# ---------------------------------------------------------------------------


def main() -> None:
    """Ham chinh - dieu phoi toan bo luong chay cua ung dung."""
    st.set_page_config(
        page_title="Prepress Automation - In ống đồng",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    ap_dung_css_tuy_bien()
    hien_thi_header()

    # Khoi tao session_state neu day la lan dau chay ung dung.
    if "thong_tin_thiet_ke" not in st.session_state:
        st.session_state["thong_tin_thiet_ke"] = None

    thong_tin_moi = render_form_nhap_lieu()

    # Chi cap nhat session_state khi nguoi dung thuc su bam nut submit,
    # de du lieu khong bi mat khi Streamlit render lai trang vi cac
    # tuong tac khac (vi du mo/dong checkbox cua so trong suot).
    if thong_tin_moi is not None:
        st.session_state["thong_tin_thiet_ke"] = thong_tin_moi

    thong_tin_hien_tai: Optional[ThongTinThietKe] = st.session_state[
        "thong_tin_thiet_ke"
    ]

    if thong_tin_hien_tai is not None:
        st.divider()
        hien_thi_tom_tat(thong_tin_hien_tai)


if __name__ == "__main__":
    main()

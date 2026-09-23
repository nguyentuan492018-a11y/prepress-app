# -*- coding: utf-8 -*-
"""
Ung dung Web Tu dong hoa Quy trinh Tien in an (Prepress Automation)
=====================================================================
Doi tuong su dung: Ky thuat vien va nhan vien thiet ke bao bi mang ghep
phuc hop (PET//PE, OPP//CPP) su dung cong nghe in ong dong truc khac
dien tu.

GIAI DOAN 1: Nen tang + Giao dien nhap lieu (DA HOAN THANH)
-------------------------------------------------------------
    1. Cau hinh trang va giao dien (tong mau xanh duong, responsive).
    2. Xay dung form nhap lieu day du: loai tui, kich thuoc, thong tin
       bien doi, logo, va khoi cua so trong suot.
    3. Luu du lieu nhap vao st.session_state de cac giai doan sau
       (xu ly nghiep vu, preview, xuat PDF) su dung lai ma khong can
       nguoi dung nhap lai.
    4. Hien thi bang tom tat du lieu da nhap de nguoi dung kiem tra.

GIAI DOAN 2: Logic nghiep vu in ong dong (DA HOAN THANH)
-------------------------------------------------------------
    1. Khoa he mau chuan: CMYK 4 mau co ban + danh sach Pantone spot
       color co dinh (khong cho nhap tay ma chon tu danh sach khoa
       san - tranh sai lech mau khi khac truc).
    2. Tu dong tinh kich thuoc co tran le (bleed +3mm moi canh).
    3. Kiem tra ma vach chuan EAN-13 (du 13 so + dung checksum) va
       kich thuoc toi thieu de ma vach doc duoc bang may quet.
    4. Kiem tra vung an toan (safe margin 5mm tinh tu mep cat) - canh
       bao neu kich thuoc tui qua nho hoac noi dung chu co the vuot
       vung an toan (uoc tinh so bo, se chinh xac hoa o Giai doan 3
       khi ve mockup that).
    5. Kiem tra cua so trong suot co vuot kich thuoc tui hoac lan vao
       vung an toan mep hay khong.

GIAI DOAN 3: Preview mockup truc quan bang Pillow (DA HOAN THANH)
-------------------------------------------------------------
    1. Ve khung tui theo dung ty le kich thuoc that (co tran le), tu
       dong scale de vua hien thi tren man hinh.
    2. Ve duong bleed (net dut do, o mep canvas) va duong safe margin
       (net dut vang, cach mep cat SAFE_MARGIN_MM) - dung chung mot
       he toa do voi logic kiem tra o Giai doan 2.
    3. Ghep logo (neu co) va ve ten san pham/slogan len dung vi tri
       trong vung an toan.
    4. Ve vung cua so trong suot dung vi tri/kich thuoc/hinh dang da
       chon o form - ghep anh mo phong san pham (neu co) qua mask
       theo hinh dang, hoac to nen xanh nhat mo phong kinh trong neu
       chua co anh.

Cac giai doan tiep theo (se bo sung sau):
    - Giai doan 4: Xuat file PDF ky thuat in an bang ReportLab.

Thu vien su dung: streamlit, pillow (PIL), reportlab.
Chi import cac thu vien nay de dam bao on dinh khi trien khai tren
Streamlit Community Cloud.
"""

from __future__ import annotations

import io
import textwrap
from dataclasses import dataclass, field
from typing import Optional

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

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

# ===== HANG SO NGHIEP VU GIAI DOAN 2 =====

# Do tran le (bleed) chuan cho in ong dong - cong them moi canh.
BLEED_MM: float = 3.0

# Vung an toan (safe margin) tinh tu duong cat thanh pham vao trong -
# day la khoang cach toi thieu de chu/logo khong bi cat sat mep khi
# dao dong dao cat trong qua trinh gia cong (chuan pho bien nganh bao
# bi mang ghep: 5mm).
SAFE_MARGIN_MM: float = 5.0

# Kich thuoc vat ly toi thieu cua ma vach EAN-13 de may quet doc on
# dinh (chuan GS1: kich thuoc goc 37.29 x 25.93 mm ở mức phong to
# 100%; muc toi thieu cho phep la phong to 80% ~ 29.83 x 20.73 mm).
EAN13_RONG_TOI_THIEU_MM: float = 29.83
EAN13_CAO_TOI_THIEU_MM: float = 20.73

# Bang mau CMYK tieu chuan (4 mau in ong dong co ban) - hien thi de
# xac nhan he mau da bi khoa, khong cho nguoi dung tu y doi.
BANG_MAU_CMYK_CHUAN: dict[str, str] = {
    "Cyan (C)": "#00AEEF",
    "Magenta (M)": "#EC008C",
    "Yellow (Y)": "#FFF200",
    "Key/Black (K)": "#101010",
}

# Danh sach mau Pantone spot color duoc phep chon them (ngoai 4 mau
# CMYK co ban) - danh sach nay la "khoa cung", nguoi dung chi duoc
# CHON tu day, khong duoc nhap ma Pantone tuy y de tranh sai lech mau
# thuc te khi san xuat hang loat.
DANH_SACH_PANTONE_KHOA: list[str] = [
    "Không dùng thêm Pantone (chỉ CMYK)",
    "Pantone 185 C (Đỏ tươi)",
    "Pantone 286 C (Xanh dương đậm)",
    "Pantone 355 C (Xanh lá)",
    "Pantone 116 C (Vàng cam)",
    "Pantone 877 C (Bạc ánh kim)",
    "Pantone 871 C (Vàng ánh kim)",
]


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
    mau_pantone: str = DANH_SACH_PANTONE_KHOA[0]
    cua_so_trong_suot: ThongTinCuaSoTrongSuot = field(
        default_factory=ThongTinCuaSoTrongSuot
    )


# ---------------------------------------------------------------------------
# LOGIC NGHIEP VU IN ONG DONG (GIAI DOAN 2)
# ---------------------------------------------------------------------------
#
# Quy uoc chung cho cac ham kiem tra (kiem_tra_*) trong khoi nay:
#   - Moi ham tra ve mot list cac tuple (muc_do, thong_diep), trong do
#     muc_do thuoc {"loi", "canh_bao", "thanh_cong"}.
#   - "loi": van de nghiem trong, co the gay hong khuon/truc khac -
#     hien thi bang st.error() (mau do).
#   - "canh_bao": can luu y, nen kiem tra lai truoc khi san xuat -
#     hien thi bang st.warning() (mau vang).
#   - "thanh_cong": da kiem tra va dat yeu cau - hien thi bang
#     st.success() (mau xanh la).
#   - List rong nghia la khong co gi de bao cao (truong hop khong ap
#     dung, vi du chua bat cua so trong suot).


@dataclass
class KichThuocCoBleed:
    """Ket qua tinh kich thuoc sau khi cong tran le (bleed).

    Thuoc tinh:
        dai_mm, rong_mm: Kich thuoc thanh pham goc (chua bleed).
        hong_mm: Be hong goc.
        dai_co_bleed_mm, rong_co_bleed_mm: Kich thuoc file thiet ke
            thuc te (da cong bleed 2 canh doi dien).
        hong_co_bleed_mm: Be hong sau khi cong bleed (chi cong neu
            hong_mm > 0, vi mot so loai tui khong co panel hong).
    """

    dai_mm: float
    rong_mm: float
    hong_mm: float
    dai_co_bleed_mm: float
    rong_co_bleed_mm: float
    hong_co_bleed_mm: float


def tinh_kich_thuoc_co_bleed(
    dai_mm: float, rong_mm: float, hong_mm: float, bleed_mm: float = BLEED_MM
) -> KichThuocCoBleed:
    """Tinh kich thuoc file thiet ke sau khi tu dong cong tran le.

    Nguyen tac in ong dong: moi canh cat thanh pham deu can du mau
    tran ra ngoai duong cat mot khoang bleed_mm, de khi dao cat lech
    nhe trong qua trinh gia cong hang loat van khong lo nen trang.
    Vi bleed duoc cong vao CA HAI canh doi dien cua mot chieu, cong
    thuc la: kich_thuoc_moi = kich_thuoc_goc + 2 * bleed_mm.

    Tham so:
        dai_mm, rong_mm: Kich thuoc thanh pham nguoi dung nhap (mm).
        hong_mm: Be hong (mm), co the bang 0 neu tui khong co hong.
        bleed_mm: Do tran le moi canh (mm), mac dinh la BLEED_MM.

    Tra ve:
        Doi tuong KichThuocCoBleed chua ca kich thuoc goc va kich
        thuoc da cong bleed.
    """
    dai_co_bleed = dai_mm + 2 * bleed_mm
    rong_co_bleed = rong_mm + 2 * bleed_mm
    # Be hong chi cong bleed neu > 0 (tui co panel hong that su),
    # tui khong hong (hong_mm = 0) thi giu nguyen bang 0.
    hong_co_bleed = (hong_mm + 2 * bleed_mm) if hong_mm > 0 else 0.0

    return KichThuocCoBleed(
        dai_mm=dai_mm,
        rong_mm=rong_mm,
        hong_mm=hong_mm,
        dai_co_bleed_mm=dai_co_bleed,
        rong_co_bleed_mm=rong_co_bleed,
        hong_co_bleed_mm=hong_co_bleed,
    )


def _tinh_checksum_ean13(muoi_hai_so_dau: str) -> int:
    """Tinh chu so kiem tra (checksum) chuan EAN-13.

    Thuat toan chuan GS1: nhan cac chu so o vi tri le (tinh tu trai,
    bat dau tu 1) voi he so 1, vi tri chan voi he so 3, cong tong lai,
    lay 10 tru cho phan du cua tong khi chia 10 (neu ket qua la 10 thi
    checksum = 0).

    Tham so:
        muoi_hai_so_dau: Chuoi gom dung 12 chu so dau cua ma EAN-13.

    Tra ve:
        Chu so kiem tra (0-9) duoc tinh toan.
    """
    tong = 0
    for vi_tri, ky_tu in enumerate(muoi_hai_so_dau):
        chu_so = int(ky_tu)
        # Vi tri trong code (0-based): chan (0,2,4..) la vi tri LE
        # theo cach dem 1-based cua chuan GS1 -> he so 1.
        he_so = 1 if vi_tri % 2 == 0 else 3
        tong += chu_so * he_so
    phan_du = tong % 10
    return 0 if phan_du == 0 else 10 - phan_du


def kiem_tra_dinh_dang_ma_vach(ma_vach: str) -> list[tuple[str, str]]:
    """Kiem tra ma vach nguoi dung nhap co dung chuan EAN-13 khong.

    Cac dieu kien kiem tra:
        1. Chuoi phai gom dung 13 ky tu, toan bo la chu so.
        2. Chu so kiem tra (ky tu cuoi) phai khop voi checksum tinh
           tu 12 chu so dau theo thuat toan GS1.

    Neu nguoi dung de trong o ma vach (chua co ma, bo sung sau), ham
    tra ve list rong - khong coi la loi, vi day la truong du lieu
    khong bat buoc o buoc thiet ke so bo.

    Tham so:
        ma_vach: Chuoi ma vach nguoi dung da nhap.

    Tra ve:
        List (muc_do, thong_diep) mo ta ket qua kiem tra.
    """
    ma_vach = ma_vach.strip()
    if not ma_vach:
        return []

    if not ma_vach.isdigit():
        return [
            (
                "loi",
                "Mã vạch chứa ký tự không phải số. Mã EAN-13 chỉ được "
                "gồm các chữ số 0-9.",
            )
        ]

    if len(ma_vach) != 13:
        return [
            (
                "loi",
                f"Mã vạch hiện có {len(ma_vach)} chữ số, chuẩn EAN-13 "
                "yêu cầu đúng 13 chữ số.",
            )
        ]

    checksum_dung = _tinh_checksum_ean13(ma_vach[:12])
    checksum_nhap = int(ma_vach[12])

    if checksum_dung != checksum_nhap:
        return [
            (
                "loi",
                f"Chữ số kiểm tra (checksum) không hợp lệ - theo chuẩn "
                f"GS1, chữ số cuối phải là {checksum_dung}, hiện đang "
                f"là {checksum_nhap}. Vui lòng kiểm tra lại mã vạch.",
            )
        ]

    return [("thanh_cong", "Mã vạch đúng chuẩn EAN-13 (đã kiểm tra checksum).")]


def kiem_tra_kich_thuoc_ma_vach(
    ma_vach: str, rong_mm: float, dai_mm: float
) -> list[tuple[str, str]]:
    """Kiem tra tui co du kich thuoc de dat ma vach chuan hay khong.

    Ma vach EAN-13 can mot vung khong gian toi thieu de may quet doc
    duoc chinh xac. Ham nay chi canh bao so bo dua tren kich thuoc
    tong the cua tui (chua tinh vi tri dat cu the - vi tri chinh xac
    se duoc bo tri khi dan thiet ke that o Giai doan 3).

    Tham so:
        ma_vach: Chuoi ma vach (dung de xac dinh co can kiem tra hay
            khong - neu chua nhap ma vach thi bo qua kiem tra nay).
        rong_mm, dai_mm: Kich thuoc thanh pham (mm).

    Tra ve:
        List (muc_do, thong_diep) mo ta ket qua kiem tra.
    """
    if not ma_vach.strip():
        return []

    if rong_mm < EAN13_RONG_TOI_THIEU_MM or dai_mm < EAN13_CAO_TOI_THIEU_MM:
        return [
            (
                "canh_bao",
                f"Kích thước túi ({rong_mm:.0f}×{dai_mm:.0f} mm) khá nhỏ "
                f"so với vùng tối thiểu để đặt mã vạch EAN-13 đúng chuẩn "
                f"({EAN13_RONG_TOI_THIEU_MM:.1f}×{EAN13_CAO_TOI_THIEU_MM:.1f} mm "
                "ở mức phóng to 100%). Có thể cần thu nhỏ mã vạch xuống "
                "80% hoặc cân nhắc lại vị trí đặt.",
            )
        ]
    return [("thanh_cong", "Kích thước túi đủ để đặt mã vạch EAN-13 chuẩn.")]


def kiem_tra_an_toan_le(thong_tin: "ThongTinThietKe") -> list[tuple[str, str]]:
    """Kiem tra so bo nguy co noi dung vi pham vung an toan (safe margin).

    Day la buoc kiem tra so bo (heuristic) dua tren kich thuoc tui va
    do dai van ban nhap vao - CHUA phai la kiem tra chinh xac theo
    layout that (viec do se duoc thuc hien khi ve mockup that bang
    Pillow o Giai doan 3). Muc dich la canh bao som cho ky thuat vien
    truoc khi sang buoc dan thiet ke chi tiet.

    Logic kiem tra:
        1. Tui phai du lon de chua vung an toan o ca 2 chieu (chieu
           rong va chieu dai phai > 2 * SAFE_MARGIN_MM), neu khong se
           khong con cho nao de dat noi dung an toan -> loi.
        2. Uoc tinh chieu rong noi dung kha dung (da tru 2 ben safe
           margin), so sanh voi do dai chuoi ten san pham/slogan nhan
           voi be rong ky tu trung binh uoc luong -> canh bao neu co
           kha nang vuot qua.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai.

    Tra ve:
        List (muc_do, thong_diep) mo ta ket qua kiem tra.
    """
    ket_qua: list[tuple[str, str]] = []
    rong = thong_tin.rong_mm
    dai = thong_tin.dai_mm

    if rong <= 0 or dai <= 0:
        # Chua nhap kich thuoc - khong co gi de kiem tra.
        return ket_qua

    if rong <= 2 * SAFE_MARGIN_MM or dai <= 2 * SAFE_MARGIN_MM:
        ket_qua.append(
            (
                "loi",
                f"Kích thước túi ({rong:.0f}×{dai:.0f} mm) quá nhỏ so với "
                f"vùng an toàn tiêu chuẩn ({SAFE_MARGIN_MM:.0f}mm mỗi cạnh) "
                "- không còn đủ chỗ để đặt nội dung an toàn cách xa mép cắt.",
            )
        )
        return ket_qua

    # Uoc tinh be rong noi dung kha dung sau khi tru safe margin 2 ben.
    rong_kha_dung_mm = rong - 2 * SAFE_MARGIN_MM

    # He so uoc luong be rong trung binh cua 1 ky tu in hoa co chu lon
    # (ten san pham, don vi mm/ky tu) - day la uoc luong so bo, khong
    # thay the cho viec do dac chinh xac tren mockup that.
    BE_RONG_KY_TU_TEN_SP_MM = 5.5
    if thong_tin.ten_san_pham:
        do_rong_uoc_tinh = len(thong_tin.ten_san_pham) * BE_RONG_KY_TU_TEN_SP_MM
        if do_rong_uoc_tinh > rong_kha_dung_mm:
            ket_qua.append(
                (
                    "canh_bao",
                    f"Tên sản phẩm \"{thong_tin.ten_san_pham}\" khá dài so "
                    f"với bề rộng khả dụng (~{rong_kha_dung_mm:.0f} mm) sau "
                    "khi trừ vùng an toàn. Có thể cần giảm cỡ chữ hoặc rút "
                    "gọn tên khi dàn thiết kế thật.",
                )
            )

    # He so uoc luong be rong trung binh cho slogan (chu nho hon).
    BE_RONG_KY_TU_SLOGAN_MM = 2.5
    if thong_tin.slogan:
        # Uoc tinh tren dong dai nhat cua slogan (tach theo dau xuong dong).
        dong_dai_nhat = max(
            (len(dong) for dong in thong_tin.slogan.splitlines()),
            default=len(thong_tin.slogan),
        )
        do_rong_uoc_tinh = dong_dai_nhat * BE_RONG_KY_TU_SLOGAN_MM
        if do_rong_uoc_tinh > rong_kha_dung_mm:
            ket_qua.append(
                (
                    "canh_bao",
                    "Slogan/mô tả có dòng khá dài, có thể cần xuống dòng "
                    "hoặc giảm cỡ chữ để không phạm vùng an toàn khi dàn "
                    "thiết kế thật.",
                )
            )

    if not ket_qua:
        ket_qua.append(
            ("thanh_cong", "Chưa phát hiện nguy cơ vi phạm vùng an toàn (ước tính sơ bộ).")
        )

    return ket_qua


def kiem_tra_cua_so_trong_suot(
    thong_tin: "ThongTinThietKe",
) -> list[tuple[str, str]]:
    """Kiem tra cau hinh cua so trong suot co hop ly khong.

    Kiem tra 2 nhom van de:
        1. Cua so co vuot qua kich thuoc tong the cua tui khong.
        2. Cua so co lan vao vung an toan mep (SAFE_MARGIN_MM) khong,
           dua tren vi tri uoc tinh theo lua chon cua nguoi dung.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai.

    Tra ve:
        List (muc_do, thong_diep) mo ta ket qua kiem tra.
    """
    cua_so = thong_tin.cua_so_trong_suot
    if not cua_so.co_cua_so:
        return []

    rong_tui = thong_tin.rong_mm
    dai_tui = thong_tin.dai_mm

    if rong_tui <= 0 or dai_tui <= 0:
        return [
            (
                "canh_bao",
                "Chưa nhập kích thước túi nên chưa thể kiểm tra vị trí "
                "cửa sổ trong suốt.",
            )
        ]

    # Truong hop dac biet: cua so phu toan bo mat sau -> khong can
    # kiem tra overlap chi tiet, chi can bao thanh cong dac biet.
    if cua_so.vi_tri == "Toàn bộ mặt sau":
        return [
            (
                "thanh_cong",
                "Cửa sổ trong suốt phủ toàn bộ mặt sau - đã ghi nhận, "
                "không cần kiểm tra chồng lấn vùng an toàn riêng lẻ.",
            )
        ]

    # 1) Kiem tra cua so co vuot kich thuoc tui khong.
    ket_qua: list[tuple[str, str]] = []
    if cua_so.rong_mm > rong_tui or cua_so.cao_mm > dai_tui:
        ket_qua.append(
            (
                "loi",
                f"Kích thước cửa sổ trong suốt ({cua_so.rong_mm:.0f}×"
                f"{cua_so.cao_mm:.0f} mm) lớn hơn kích thước túi "
                f"({rong_tui:.0f}×{dai_tui:.0f} mm) - vui lòng chỉnh lại.",
            )
        )
        return ket_qua

    # 2) Uoc tinh toa do goc tren-trai (x0, y0) cua cua so dua theo
    # vi tri nguoi dung chon, de kiem tra co lan vung an toan khong.
    if cua_so.vi_tri == "Giữa mặt trước":
        x0 = (rong_tui - cua_so.rong_mm) / 2
        y0 = (dai_tui - cua_so.cao_mm) / 2
    elif cua_so.vi_tri == "Trên mặt trước":
        x0 = (rong_tui - cua_so.rong_mm) / 2
        y0 = 0.0
    elif cua_so.vi_tri == "Dưới mặt trước":
        x0 = (rong_tui - cua_so.rong_mm) / 2
        y0 = dai_tui - cua_so.cao_mm
    else:  # "Tùy chỉnh tọa độ (X, Y)"
        x0 = cua_so.toa_do_x
        y0 = cua_so.toa_do_y

    x1 = x0 + cua_so.rong_mm
    y1 = y0 + cua_so.cao_mm

    vi_pham_an_toan = (
        x0 < SAFE_MARGIN_MM
        or y0 < SAFE_MARGIN_MM
        or x1 > (rong_tui - SAFE_MARGIN_MM)
        or y1 > (dai_tui - SAFE_MARGIN_MM)
    )

    if vi_pham_an_toan:
        ket_qua.append(
            (
                "canh_bao",
                f"Cửa sổ trong suốt ở vị trí \"{cua_so.vi_tri}\" có thể "
                f"chạm hoặc vượt vùng an toàn {SAFE_MARGIN_MM:.0f}mm cách "
                "mép cắt. Nên chừa thêm khoảng cách hoặc thu nhỏ cửa sổ.",
            )
        )
    else:
        ket_qua.append(
            (
                "thanh_cong",
                "Vị trí và kích thước cửa sổ trong suốt nằm trong vùng an "
                "toàn (ước tính sơ bộ theo tọa độ đã chọn).",
            )
        )

    return ket_qua


def tinh_toa_do_goc_cua_so_mm(
    cua_so: "ThongTinCuaSoTrongSuot", rong_tui: float, dai_tui: float
) -> Optional[tuple[float, float, float, float]]:
    """Tinh toa do (x0, y0, x1, y1) cua vung cua so trong suot, don vi mm.

    Day la ham DUY NHAT tinh toa do goc cua so - dung chung boi ca
    ham kiem tra nghiep vu (kiem_tra_cua_so_trong_suot) lan ham ve
    mockup (Giai doan 3), de dam bao vi tri hien thi tren preview
    luon khop 100% voi vi tri da duoc kiem tra canh bao an toan.

    Goc toa do (0, 0) la goc tren-trai cua mat tui (KHONG tinh bleed).

    Tham so:
        cua_so: Cau hinh cua so trong suot nguoi dung da nhap.
        rong_tui, dai_tui: Kich thuoc thanh pham cua tui (mm).

    Tra ve:
        Tuple (x0, y0, x1, y1) mm, hoac None neu vi tri la "Toàn bộ
        mặt sau" (khong ap dung toa do mat truoc) hoac chua du du lieu
        de tinh (kich thuoc tui <= 0).
    """
    if rong_tui <= 0 or dai_tui <= 0:
        return None
    if cua_so.vi_tri == "Toàn bộ mặt sau":
        return None

    if cua_so.vi_tri == "Giữa mặt trước":
        x0 = (rong_tui - cua_so.rong_mm) / 2
        y0 = (dai_tui - cua_so.cao_mm) / 2
    elif cua_so.vi_tri == "Trên mặt trước":
        x0 = (rong_tui - cua_so.rong_mm) / 2
        y0 = 0.0
    elif cua_so.vi_tri == "Dưới mặt trước":
        x0 = (rong_tui - cua_so.rong_mm) / 2
        y0 = dai_tui - cua_so.cao_mm
    else:  # "Tùy chỉnh tọa độ (X, Y)"
        x0 = cua_so.toa_do_x
        y0 = cua_so.toa_do_y

    x1 = x0 + cua_so.rong_mm
    y1 = y0 + cua_so.cao_mm
    return (x0, y0, x1, y1)


def tong_hop_ket_qua_kiem_tra(
    thong_tin: "ThongTinThietKe",
) -> dict[str, list[tuple[str, str]]]:
    """Chay toan bo cac ham kiem tra nghiep vu va gom nhom ket qua.

    Day la ham "dieu phoi" (orchestrator) duy nhat ma tang giao dien
    (UI) can goi - giup tach biet ro rang logic nghiep vu (co the unit
    test doc lap) khoi phan hien thi.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai.

    Tra ve:
        Dict anh xa ten nhom kiem tra -> list (muc_do, thong_diep).
    """
    return {
        "Mã vạch EAN-13 (định dạng)": kiem_tra_dinh_dang_ma_vach(thong_tin.ma_vach),
        "Mã vạch EAN-13 (kích thước)": kiem_tra_kich_thuoc_ma_vach(
            thong_tin.ma_vach, thong_tin.rong_mm, thong_tin.dai_mm
        ),
        "Vùng an toàn (Safe Margin)": kiem_tra_an_toan_le(thong_tin),
        "Cửa sổ trong suốt": kiem_tra_cua_so_trong_suot(thong_tin),
    }


# ---------------------------------------------------------------------------
# VE MOCKUP TRUC QUAN BANG PILLOW (GIAI DOAN 3)
# ---------------------------------------------------------------------------
#
# Nguyen tac chung cua khoi nay:
#   - Toan bo phep ve deu lam viec tren mot he toa do px duy nhat, quy
#     doi tu mm sang px bang mot ty le SCALE co dinh cho ca lan ve
#     (tinh boi _tinh_ty_le_px_tren_mm). Nho vay moi thanh phan (bleed,
#     safe margin, logo, chu, cua so...) deu dong bo ty le voi nhau.
#   - Canvas anh preview co KICH THUOC BANG DUNG kich thuoc file thiet
#     ke thuc te (thanh pham + bleed 2 ben), tuc la mep ngoai cung cua
#     anh chinh la duong bleed - giong quy uoc nganh in thuc te.

# Kich thuoc toi da (px) cua canh dai nhat tren anh preview - gioi han
# de anh khong qua nang, nhung van du net de xem tren web.
DO_DAI_CANH_LON_NHAT_PREVIEW_PX: int = 760

# Mau sac dung trong mockup (dong bo tong xanh duong cua giao dien).
MAU_NEN_TUI_MOCKUP: tuple[int, int, int] = (255, 255, 255)
MAU_DUONG_BLEED: tuple[int, int, int] = (220, 38, 38)  # do
MAU_DUONG_SAFE_MARGIN: tuple[int, int, int] = (217, 119, 6)  # vang cam
MAU_VIEN_THANH_PHAM: tuple[int, int, int] = (30, 58, 138)  # xanh duong dam
MAU_NEN_CUA_SO_TRONG: tuple[int, int, int, int] = (191, 219, 254, 175)  # xanh nhat, co alpha
MAU_VIEN_CUA_SO: tuple[int, int, int] = (37, 99, 235)
MAU_CHU_TEN_SAN_PHAM: tuple[int, int, int] = (17, 24, 39)
MAU_CHU_SLOGAN: tuple[int, int, int] = (55, 65, 81)

# Do dai net dut (px) dung chung cho duong bleed va safe margin.
DO_DAI_NET_DUT_PX: int = 6
KHOANG_CACH_NET_DUT_PX: int = 5


def _lay_font(kich_thuoc_px: int, dam: bool = False) -> ImageFont.FreeTypeFont:
    """Tra ve mot font TrueType voi kich thuoc mong muon.

    Thu lan luot mot vai duong dan font pho bien tren cac moi truong
    Linux (bao gom Streamlit Community Cloud) va tren may nguoi dung.
    Neu khong tim thay font TrueType nao, roi ve font mac dinh cua
    Pillow (bitmap) de ung dung khong bi crash, chi giam nhe chat
    luong hien thi chu.

    Tham so:
        kich_thuoc_px: Kich thuoc chu mong muon, tinh bang px.
        dam: True neu can chu dam (bold), vi du cho ten san pham.

    Tra ve:
        Doi tuong font co the dung truc tiep voi ImageDraw.text().
    """
    ten_file_uu_tien = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "Arial Bold.ttf",
        ]
        if dam
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "DejaVuSans.ttf",
            "Arial.ttf",
        ]
    )
    for ten_file in ten_file_uu_tien:
        try:
            return ImageFont.truetype(ten_file, kich_thuoc_px)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=kich_thuoc_px)
    except TypeError:
        # Phien ban Pillow cu khong ho tro tham so size cho load_default.
        return ImageFont.load_default()


def _tinh_ty_le_px_tren_mm(rong_bleed_mm: float, dai_bleed_mm: float) -> float:
    """Tinh ty le quy doi mm -> px sao cho canh dai nhat vua khung preview.

    Tham so:
        rong_bleed_mm, dai_bleed_mm: Kich thuoc file thiet ke (da cong
            bleed), tuc kich thuoc canvas se ve.

    Tra ve:
        So px tuong ung voi 1mm (luon > 0).
    """
    canh_lon_nhat_mm = max(rong_bleed_mm, dai_bleed_mm, 1.0)
    return DO_DAI_CANH_LON_NHAT_PREVIEW_PX / canh_lon_nhat_mm


def _ve_khung_net_dut(
    ve: ImageDraw.ImageDraw,
    hop: tuple[float, float, float, float],
    mau: tuple[int, int, int],
    do_rong_net: int = 2,
) -> None:
    """Ve mot hinh chu nhat vien net dut (khong co san trong Pillow).

    Pillow khong ho tro san kieu net dut cho rectangle, nen ham nay tu
    ve tung doan thang ngan xen ke khoang trong doc theo 4 canh.

    Tham so:
        ve: Doi tuong ImageDraw dang thao tac.
        hop: Toa do (x0, y0, x1, y1) cua hinh chu nhat, don vi px.
        mau: Mau net dut (R, G, B).
        do_rong_net: Do day net ve, tinh bang px.
    """
    x0, y0, x1, y1 = hop
    buoc = DO_DAI_NET_DUT_PX + KHOANG_CACH_NET_DUT_PX

    # Canh tren va canh duoi (di chuyen theo truc X).
    for x_bat_dau in range(int(x0), int(x1), buoc):
        x_ket_thuc = min(x_bat_dau + DO_DAI_NET_DUT_PX, x1)
        ve.line([(x_bat_dau, y0), (x_ket_thuc, y0)], fill=mau, width=do_rong_net)
        ve.line([(x_bat_dau, y1), (x_ket_thuc, y1)], fill=mau, width=do_rong_net)

    # Canh trai va canh phai (di chuyen theo truc Y).
    for y_bat_dau in range(int(y0), int(y1), buoc):
        y_ket_thuc = min(y_bat_dau + DO_DAI_NET_DUT_PX, y1)
        ve.line([(x0, y_bat_dau), (x0, y_ket_thuc)], fill=mau, width=do_rong_net)
        ve.line([(x1, y_bat_dau), (x1, y_ket_thuc)], fill=mau, width=do_rong_net)


def _ve_van_ban_can_giua_co_xuong_dong(
    ve: ImageDraw.ImageDraw,
    tam_x_px: float,
    y_bat_dau_px: float,
    noi_dung: str,
    font: ImageFont.FreeTypeFont,
    mau: tuple[int, int, int],
    rong_toi_da_px: float,
) -> float:
    """Ve van ban can giua, tu dong xuong dong neu vuot be rong cho phep.

    Uoc luong so ky tu toi da tren 1 dong dua tren be rong trung binh
    cua font (do bang bbox chu "M"), roi dung textwrap de ngat dong -
    day la uoc luong don gian, du dung cho muc dich preview truc quan
    (khac voi ban in that se can do chinh xac tung ky tu).

    Tham so:
        ve: Doi tuong ImageDraw dang thao tac.
        tam_x_px: Toa do X tam duong ngang can can giua van ban.
        y_bat_dau_px: Toa do Y bat dau ve dong dau tien.
        noi_dung: Chuoi van ban can ve (co the chua nhieu tu).
        font: Font da tao san boi _lay_font().
        mau: Mau chu (R, G, B).
        rong_toi_da_px: Be rong toi da cho phep (thuong la be rong
            vung an toan) de tinh so ky tu/dong.

    Tra ve:
        Toa do Y ngay duoi dong cuoi cung vua ve (de ve tiep noi dung
        khac ben duoi ma khong bi de).
    """
    if not noi_dung:
        return y_bat_dau_px

    # Uoc luong be rong 1 ky tu trung binh bang bbox chu "M" (ky tu
    # rong nhat pho bien) de tinh so ky tu toi da tren 1 dong.
    bbox_chu_m = ve.textbbox((0, 0), "M", font=font)
    be_rong_ky_tu_uoc_tinh = max(bbox_chu_m[2] - bbox_chu_m[0], 1)
    so_ky_tu_toi_da = max(int(rong_toi_da_px / be_rong_ky_tu_uoc_tinh), 1)

    cac_dong: list[str] = []
    for doan in noi_dung.splitlines():
        cac_dong.extend(textwrap.wrap(doan, width=so_ky_tu_toi_da) or [""])

    y_hien_tai = y_bat_dau_px
    for dong in cac_dong:
        bbox_dong = ve.textbbox((0, 0), dong, font=font)
        chieu_cao_dong = bbox_dong[3] - bbox_dong[1]
        ve.text(
            (tam_x_px, y_hien_tai),
            dong,
            font=font,
            fill=mau,
            anchor="ma",  # middle-ascender: can giua theo truc X
        )
        y_hien_tai += chieu_cao_dong + 4

    return y_hien_tai


def _ve_cua_so_trong_suot(
    canvas: Image.Image,
    thong_tin: "ThongTinThietKe",
    goc_trai_tren_px: tuple[float, float],
    ty_le_px_tren_mm: float,
) -> Optional[str]:
    """Ve vung cua so trong suot len canvas mockup (neu co bat tinh nang).

    Neu nguoi dung da tai anh mo phong san pham, anh se duoc cat/resize
    va ghep vao dung vi tri/hinh dang cua so thong qua mot mask (theo
    hinh chu nhat bo goc, oval, hoac tron). Neu chua co anh, ve mot
    vung mau xanh nhat mo phong be mat kinh trong suot.

    Tham so:
        canvas: Anh nen (mode "RGB") dang duoc ve mockup len.
        thong_tin: Doi tuong ThongTinThietKe hien tai.
        goc_trai_tren_px: Toa do (x, y) px cua goc trai-tren thanh
            pham (tuc vi tri sau khi da tru bleed) tren canvas.
        ty_le_px_tren_mm: Ty le quy doi mm -> px dang dung cho lan ve.

    Tra ve:
        Chuoi ghi chu can hien thi them cho nguoi dung (vi du khi cua
        so o "Toàn bộ mặt sau" khong the ve tren mat truoc), hoac None
        neu khong co ghi chu nao can them.
    """
    cua_so = thong_tin.cua_so_trong_suot
    if not cua_so.co_cua_so:
        return None

    if cua_so.vi_tri == "Toàn bộ mặt sau":
        return (
            "Cửa sổ trong suốt được cấu hình cho **mặt sau** của túi nên "
            "không hiển thị trên bản mockup mặt trước này."
        )

    toa_do_mm = tinh_toa_do_goc_cua_so_mm(
        cua_so, thong_tin.rong_mm, thong_tin.dai_mm
    )
    if toa_do_mm is None:
        return None

    x0_mm, y0_mm, x1_mm, y1_mm = toa_do_mm
    # Ep toa do nam trong pham vi tui, phong truong hop nguoi dung nhap
    # toa do tuy chinh vuot ra ngoai (da co canh bao o Giai doan 2,
    # nhung mockup van khong duoc phep crash).
    x0_mm = max(0.0, min(x0_mm, thong_tin.rong_mm))
    y0_mm = max(0.0, min(y0_mm, thong_tin.dai_mm))
    x1_mm = max(x0_mm, min(x1_mm, thong_tin.rong_mm))
    y1_mm = max(y0_mm, min(y1_mm, thong_tin.dai_mm))

    goc_x_px, goc_y_px = goc_trai_tren_px
    x0_px = goc_x_px + x0_mm * ty_le_px_tren_mm
    y0_px = goc_y_px + y0_mm * ty_le_px_tren_mm
    x1_px = goc_x_px + x1_mm * ty_le_px_tren_mm
    y1_px = goc_y_px + y1_mm * ty_le_px_tren_mm
    rong_px = max(int(x1_px - x0_px), 1)
    cao_px = max(int(y1_px - y0_px), 1)

    # Tao mask theo dung hinh dang da chon - dung chung cho ca truong
    # hop co anh mo phong (paste qua mask) lan truong hop to mau phang.
    mask = Image.new("L", (rong_px, cao_px), 0)
    ve_mask = ImageDraw.Draw(mask)
    if cua_so.hinh_dang == "Chữ nhật bo góc":
        ban_kinh_bo_goc = max(int(min(rong_px, cao_px) * 0.12), 2)
        ve_mask.rounded_rectangle(
            [0, 0, rong_px - 1, cao_px - 1], radius=ban_kinh_bo_goc, fill=255
        )
    else:  # "Oval" hoac "Tròn" - ca hai deu ve bang hinh elip vua khung.
        ve_mask.ellipse([0, 0, rong_px - 1, cao_px - 1], fill=255)

    if cua_so.anh_mo_phong is not None:
        anh_thu_nho = cua_so.anh_mo_phong.convert("RGB").resize((rong_px, cao_px))
        canvas.paste(anh_thu_nho, (int(x0_px), int(y0_px)), mask)
    else:
        lop_phu = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ve_lop_phu = ImageDraw.Draw(lop_phu)
        if cua_so.hinh_dang == "Chữ nhật bo góc":
            ve_lop_phu.rounded_rectangle(
                [x0_px, y0_px, x1_px, y1_px],
                radius=max(int(min(rong_px, cao_px) * 0.12), 2),
                fill=MAU_NEN_CUA_SO_TRONG,
            )
        else:
            ve_lop_phu.ellipse([x0_px, y0_px, x1_px, y1_px], fill=MAU_NEN_CUA_SO_TRONG)
        canvas.paste(lop_phu, (0, 0), lop_phu)

    # Ve them duong vien cua so de de nhan biet ranh gioi tren preview.
    ve_vien = ImageDraw.Draw(canvas)
    if cua_so.hinh_dang == "Chữ nhật bo góc":
        ve_vien.rounded_rectangle(
            [x0_px, y0_px, x1_px, y1_px],
            radius=max(int(min(rong_px, cao_px) * 0.12), 2),
            outline=MAU_VIEN_CUA_SO,
            width=2,
        )
    else:
        ve_vien.ellipse(
            [x0_px, y0_px, x1_px, y1_px], outline=MAU_VIEN_CUA_SO, width=2
        )

    return None


def ve_mockup_tui(
    thong_tin: "ThongTinThietKe",
) -> tuple[Optional[Image.Image], Optional[str]]:
    """Ve anh mockup truc quan cua thiet ke tui dua tren toan bo thong tin da nhap.

    Day la ham chinh cua Giai doan 3 - tong hop tat ca cac buoc ve:
    khung bleed/safe margin, logo, ten san pham/slogan, va cua so
    trong suot - thanh mot anh Pillow duy nhat de hien thi bang
    st.image() o tang giao dien.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai (da co it nhat
            kich thuoc Dai/Rong > 0, neu khong ham se tra ve None).

    Tra ve:
        Tuple (anh_mockup, ghi_chu):
            anh_mockup: Anh Pillow (mode "RGB") san sang de st.image(),
                hoac None neu chua du du lieu kich thuoc de ve.
            ghi_chu: Chuoi ghi chu bo sung can hien thi cho nguoi dung
                (vi du canh bao ve cua so mat sau), hoac None.
    """
    if thong_tin.dai_mm <= 0 or thong_tin.rong_mm <= 0:
        return None, None

    kich_thuoc_bleed = tinh_kich_thuoc_co_bleed(
        thong_tin.dai_mm, thong_tin.rong_mm, thong_tin.hong_mm
    )
    rong_bleed_mm = kich_thuoc_bleed.rong_co_bleed_mm
    dai_bleed_mm = kich_thuoc_bleed.dai_co_bleed_mm

    ty_le = _tinh_ty_le_px_tren_mm(rong_bleed_mm, dai_bleed_mm)
    rong_canvas_px = max(int(round(rong_bleed_mm * ty_le)), 20)
    dai_canvas_px = max(int(round(dai_bleed_mm * ty_le)), 20)

    canvas = Image.new("RGB", (rong_canvas_px, dai_canvas_px), MAU_NEN_TUI_MOCKUP)
    ve = ImageDraw.Draw(canvas)

    # Duong bleed nam ngay o mep canvas (canvas = thanh pham + bleed
    # 2 ben, dung quy uoc file thiet ke thuc te trong nganh in).
    do_lech_bleed_px = BLEED_MM * ty_le
    _ve_khung_net_dut(
        ve,
        (2, 2, rong_canvas_px - 2, dai_canvas_px - 2),
        MAU_DUONG_BLEED,
    )

    # Duong vien thanh pham (duong cat that) - inset dung do_lech_bleed_px.
    x_tp0, y_tp0 = do_lech_bleed_px, do_lech_bleed_px
    x_tp1, y_tp1 = rong_canvas_px - do_lech_bleed_px, dai_canvas_px - do_lech_bleed_px
    ve.rectangle([x_tp0, y_tp0, x_tp1, y_tp1], outline=MAU_VIEN_THANH_PHAM, width=2)

    # Duong safe margin - inset them SAFE_MARGIN_MM tu duong cat.
    do_lech_safe_px = SAFE_MARGIN_MM * ty_le
    x_an0 = x_tp0 + do_lech_safe_px
    y_an0 = y_tp0 + do_lech_safe_px
    x_an1 = x_tp1 - do_lech_safe_px
    y_an1 = y_tp1 - do_lech_safe_px
    if x_an1 > x_an0 and y_an1 > y_an0:
        _ve_khung_net_dut(ve, (x_an0, y_an0, x_an1, y_an1), MAU_DUONG_SAFE_MARGIN)

    # Cua so trong suot duoc ve TRUOC logo/chu, de logo/chu (thuong o
    # phia tren cung) khong bao gio bi cua so de len tren.
    ghi_chu = _ve_cua_so_trong_suot(canvas, thong_tin, (x_tp0, y_tp0), ty_le)
    ve = ImageDraw.Draw(canvas)  # canvas co the da bi paste de, tao lai Draw.

    y_hien_tai = y_an0 + 8
    rong_an_toan_px = max(x_an1 - x_an0, 1)

    # Ghep logo (neu co), can giua theo truc ngang, chieu cao toi da
    # ~18% chieu dai vung an toan de con cho cho ten san pham/slogan.
    if thong_tin.logo is not None:
        chieu_cao_logo_toi_da_px = max(int((y_an1 - y_an0) * 0.18), 24)
        logo = thong_tin.logo.convert("RGBA")
        ty_le_logo = min(
            rong_an_toan_px * 0.6 / logo.width, chieu_cao_logo_toi_da_px / logo.height
        )
        logo_rong = max(int(logo.width * ty_le_logo), 1)
        logo_cao = max(int(logo.height * ty_le_logo), 1)
        logo_resize = logo.resize((logo_rong, logo_cao))
        x_logo = x_an0 + (rong_an_toan_px - logo_rong) / 2
        canvas.paste(logo_resize, (int(x_logo), int(y_hien_tai)), logo_resize)
        y_hien_tai += logo_cao + 10

    tam_x_an_toan = x_an0 + rong_an_toan_px / 2

    # Ten san pham - chu lon, dam, dat ngay duoi logo.
    if thong_tin.ten_san_pham:
        co_chu_ten_sp = max(int(dai_canvas_px * 0.05), 14)
        font_ten_sp = _lay_font(co_chu_ten_sp, dam=True)
        y_hien_tai = _ve_van_ban_can_giua_co_xuong_dong(
            ve,
            tam_x_an_toan,
            y_hien_tai,
            thong_tin.ten_san_pham,
            font_ten_sp,
            MAU_CHU_TEN_SAN_PHAM,
            rong_an_toan_px,
        )
        y_hien_tai += 6

    # Slogan - chu nho hon, thuong, dat duoi ten san pham.
    if thong_tin.slogan:
        co_chu_slogan = max(int(dai_canvas_px * 0.03), 10)
        font_slogan = _lay_font(co_chu_slogan, dam=False)
        _ve_van_ban_can_giua_co_xuong_dong(
            ve,
            tam_x_an_toan,
            y_hien_tai,
            thong_tin.slogan,
            font_slogan,
            MAU_CHU_SLOGAN,
            rong_an_toan_px,
        )

    return canvas, ghi_chu


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


def _render_khoi_he_mau() -> str:
    """Hien thi khoi thong tin he mau in - da khoa chuan CMYK.

    Theo yeu cau nghiep vu, he mau CMYK 4 mau co ban LUON duoc ap
    dung mac dinh cho moi thiet ke va KHONG the tat/doi (chi hien thi
    de xac nhan). Nguoi dung chi duoc phep CHON THEM (khong bat buoc)
    mot mau Pantone spot color tu danh sach co dinh DANH_SACH_PANTONE_
    KHOA - khong co o nhap tu do, tranh sai lech ma mau khi san xuat.

    Tra ve:
        Ten mau Pantone da chon (hoac gia tri mac dinh "Không dùng
        thêm Pantone" neu khong chon).
    """
    st.caption(
        "Hệ màu xử lý (CMYK) — áp dụng cố định cho mọi thiết kế, "
        "không thể chỉnh sửa:"
    )
    cot_mau = st.columns(4)
    for cot, (ten_mau, ma_hex) in zip(cot_mau, BANG_MAU_CMYK_CHUAN.items()):
        with cot:
            st.markdown(
                f"""
                <div style="text-align:center; margin-bottom: 0.5rem;">
                    <div style="background-color:{ma_hex}; height:36px;
                        border-radius:6px; border:1px solid #e5e7eb;"></div>
                    <div style="font-size:0.8rem; color:#374151;
                        margin-top:4px;">{ten_mau}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    mau_pantone = st.selectbox(
        "Chọn thêm màu Pantone chuyên dụng (tùy chọn)",
        options=DANH_SACH_PANTONE_KHOA,
        help="Chỉ được chọn từ danh sách Pantone đã khóa sẵn theo "
        "chuẩn nhà máy, không nhập mã tự do để tránh sai lệch màu "
        "thực tế khi khắc trục.",
    )
    return mau_pantone


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

        st.subheader("5️⃣ Hệ màu in (đã khóa chuẩn)")
        mau_pantone = _render_khoi_he_mau()

        st.subheader("6️⃣ Cửa sổ trong suốt")
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
        mau_pantone=mau_pantone,
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

        _hien_thi_the_tom_tat("Hệ màu", f"CMYK 4 màu + {thong_tin.mau_pantone}")

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


def hien_thi_mockup_preview(thong_tin: "ThongTinThietKe") -> None:
    """Hien thi anh mockup truc quan (Giai doan 3) va chu thich mau sac.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai.
    """
    st.subheader("🖼️ Xem trước thiết kế (Mockup)")

    if thong_tin.dai_mm <= 0 or thong_tin.rong_mm <= 0:
        st.warning(
            "⚠️ Chưa nhập đủ kích thước Dài/Rộng nên chưa thể vẽ bản xem "
            "trước trực quan."
        )
        return

    anh_mockup, ghi_chu = ve_mockup_tui(thong_tin)
    if anh_mockup is None:
        st.warning("⚠️ Chưa thể tạo bản xem trước với dữ liệu hiện tại.")
        return

    cot_anh, cot_chu_thich = st.columns([2, 1])
    with cot_anh:
        st.image(
            anh_mockup,
            caption="Bản xem trước (mô phỏng, chưa phải file in ấn thật)",
            use_container_width=True,
        )
    with cot_chu_thich:
        st.markdown("**Chú thích:**")
        st.markdown("🔴 Nét đứt đỏ — đường tràn lề (bleed)")
        st.markdown("🟦 Viền xanh dương đậm — đường cắt thành phẩm")
        st.markdown("🟡 Nét đứt vàng cam — vùng an toàn (safe margin)")
        st.markdown("🔵 Vùng xanh nhạt/ảnh — cửa sổ trong suốt")
        st.caption(
            "Vị trí chữ và cửa sổ trong suốt được vẽ đúng tỉ lệ kích "
            "thước thật đã nhập, dùng để hình dung bố cục sơ bộ."
        )

    if ghi_chu:
        st.info(ghi_chu)


def hien_thi_kich_thuoc_bleed(thong_tin: "ThongTinThietKe") -> None:
    """Hien thi bang so sanh kich thuoc goc va kich thuoc da cong bleed.

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai.
    """
    if thong_tin.dai_mm <= 0 or thong_tin.rong_mm <= 0:
        st.warning(
            "⚠️ Chưa nhập đủ kích thước Dài/Rộng nên chưa thể tính toán "
            "kích thước tràn lề (bleed)."
        )
        return

    ket_qua_bleed = tinh_kich_thuoc_co_bleed(
        thong_tin.dai_mm, thong_tin.rong_mm, thong_tin.hong_mm
    )

    cot_goc, cot_bleed = st.columns(2)
    with cot_goc:
        _hien_thi_the_tom_tat(
            "Kích thước thành phẩm (chưa bleed)",
            f"{ket_qua_bleed.dai_mm:.0f} × {ket_qua_bleed.rong_mm:.0f} mm"
            + (
                f" × {ket_qua_bleed.hong_mm:.0f} mm hông"
                if ket_qua_bleed.hong_mm > 0
                else ""
            ),
        )
    with cot_bleed:
        _hien_thi_the_tom_tat(
            f"Kích thước file thiết kế (đã +{BLEED_MM:.0f}mm bleed mỗi cạnh)",
            f"{ket_qua_bleed.dai_co_bleed_mm:.0f} × "
            f"{ket_qua_bleed.rong_co_bleed_mm:.0f} mm"
            + (
                f" × {ket_qua_bleed.hong_co_bleed_mm:.0f} mm hông"
                if ket_qua_bleed.hong_co_bleed_mm > 0
                else ""
            ),
        )


def hien_thi_ket_qua_kiem_tra(thong_tin: "ThongTinThietKe") -> None:
    """Hien thi toan bo ket qua kiem tra nghiep vu (Giai doan 2).

    Goi ham tong_hop_ket_qua_kiem_tra() de lay ket qua, sau do render
    tung nhom bang mau sac tuong ung: do (loi), vang (canh bao), xanh
    la (thanh cong).

    Tham so:
        thong_tin: Doi tuong ThongTinThietKe hien tai.
    """
    st.subheader("🛠️ Kết quả kiểm tra kỹ thuật in ống đồng")

    hien_thi_kich_thuoc_bleed(thong_tin)

    st.markdown("**Chi tiết kiểm tra từng hạng mục:**")
    ket_qua_theo_nhom = tong_hop_ket_qua_kiem_tra(thong_tin)

    co_loi_nghiem_trong = False
    tat_ca_trong = True

    for ten_nhom, danh_sach_ket_qua in ket_qua_theo_nhom.items():
        if not danh_sach_ket_qua:
            continue
        tat_ca_trong = False
        with st.expander(f"📌 {ten_nhom}", expanded=True):
            for muc_do, thong_diep in danh_sach_ket_qua:
                if muc_do == "loi":
                    st.error(thong_diep)
                    co_loi_nghiem_trong = True
                elif muc_do == "canh_bao":
                    st.warning(thong_diep)
                else:
                    st.success(thong_diep)

    if tat_ca_trong:
        st.info(
            "ℹ️ Chưa có đủ dữ liệu (mã vạch, kích thước...) để chạy kiểm "
            "tra chi tiết. Hãy nhập đầy đủ thông tin ở form phía trên."
        )
    elif co_loi_nghiem_trong:
        st.error(
            "🚫 Phát hiện lỗi kỹ thuật nghiêm trọng - vui lòng chỉnh sửa "
            "trước khi chuyển sang bước khắc trục ống đồng."
        )
    else:
        st.success(
            "✅ Không phát hiện lỗi nghiêm trọng nào. Vui lòng vẫn xem "
            "kỹ các cảnh báo (nếu có) trước khi sản xuất hàng loạt."
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
        st.divider()
        hien_thi_mockup_preview(thong_tin_hien_tai)
        st.divider()
        hien_thi_ket_qua_kiem_tra(thong_tin_hien_tai)


if __name__ == "__main__":
    main()

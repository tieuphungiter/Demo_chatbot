# ─── Cấu hình chung cho toàn bộ hệ thống Lucky Star AI ──────────────────
DB_PATH = 'data/lucky_star_erp.db'

MATERIALS = [
    {'material_id': 'VL001', 'name': 'Vải cotton trắng',    'unit': 'mét',  'reorder_point': 500,  'lead_time_days': 7},
    {'material_id': 'VL002', 'name': 'Vải thun đen',         'unit': 'mét',  'reorder_point': 400,  'lead_time_days': 5},
    {'material_id': 'VL003', 'name': 'Chỉ may trắng',        'unit': 'cuộn', 'reorder_point': 200,  'lead_time_days': 3},
    {'material_id': 'VL004', 'name': 'Khóa kéo 20cm',        'unit': 'cái',  'reorder_point': 1000, 'lead_time_days': 4},
    {'material_id': 'VL005', 'name': 'Cúc áo nhựa',          'unit': 'túi',  'reorder_point': 300,  'lead_time_days': 3},
    {'material_id': 'VL006', 'name': 'Vải lót polyester',    'unit': 'mét',  'reorder_point': 350,  'lead_time_days': 6},
    {'material_id': 'VL007', 'name': 'Nhãn mác thương hiệu', 'unit': 'cái',  'reorder_point': 2000, 'lead_time_days': 5},
    {'material_id': 'VL008', 'name': 'Bao bì đóng gói',      'unit': 'cái',  'reorder_point': 1500, 'lead_time_days': 4},
]

PRODUCTS = [
    'Áo thun cổ tròn',
    'Quần short kaki',
    'Áo sơ mi công sở',
    'Quần jean slim',
    'Váy đầm dạo phố',
    'Áo khoác nhẹ',
]

FEATURE_COLS = [
    'stock_level', 'reorder_point', 'days_until_reorder',
    'day_of_week', 'month', 'day_of_year', 'is_high_season',
    'consumption_lag1', 'consumption_lag3', 'consumption_lag7', 'consumption_lag14',
    'consumption_ma7', 'consumption_ma14', 'consumption_ma30',
    'consumption_std7', 'consumption_std14',
    'stock_ma7', 'material_code',
]

KNOWLEDGE_BASE = [
    {
        'doc_id': 'SOP_001',
        'title': 'Quy trình nhập kho nguyên liệu',
        'content': (
            'Quy trình nhập kho nguyên liệu tại Lucky Star:\n'
            '1. Bộ phận mua hàng tạo Purchase Order (PO) trên ERP khi tồn kho xuống dưới reorder point.\n'
            '2. Khi hàng về, thủ kho kiểm tra số lượng và chất lượng so với PO.\n'
            '3. Nếu đạt: thực hiện GRN (Goods Receipt Note) trên hệ thống ERP.\n'
            '4. Nếu không đạt: lập biên bản và liên hệ nhà cung cấp trong vòng 24 giờ.\n'
            '5. Cập nhật tồn kho hệ thống trong vòng 2 tiếng sau khi nhập.\n'
            'Mức tồn kho tối thiểu (reorder point): Vải cotton 500m, Vải thun 400m, Chỉ may 200 cuộn.'
        ),
    },
    {
        'doc_id': 'SOP_002',
        'title': 'Quy trình kiểm soát chất lượng (QC)',
        'content': (
            'Tiêu chuẩn QC sản phẩm tại Lucky Star:\n'
            '- Tỷ lệ lỗi cho phép (defect rate): tối đa 2.5% trên tổng sản phẩm.\n'
            '- Kiểm tra 100% lô hàng xuất khẩu, 30% lô hàng nội địa.\n'
            '- Lỗi phân loại: Lỗi A (nghiêm trọng - loại bỏ), Lỗi B (sửa được), Lỗi C (chấp nhận được).\n'
            '- Báo cáo QC gửi trưởng chuyền mỗi 2 tiếng/lần.\n'
            '- Nếu defect rate > 3%: dừng chuyền, báo kỹ thuật ngay lập tức.\n'
            '- Công cụ QC sử dụng: thước dây, máy đo màu, bàn kiểm tra ánh sáng trắng.'
        ),
    },
    {
        'doc_id': 'SOP_003',
        'title': 'KPI và hiệu suất sản xuất',
        'content': (
            'Các chỉ số KPI nhà máy Lucky Star:\n'
            '- OEE (Overall Equipment Effectiveness) mục tiêu: ≥ 80%.\n'
            '- Hiệu suất chuyền (efficiency) mục tiêu: ≥ 90% kế hoạch.\n'
            '- Năng suất trung bình: 800-1000 sản phẩm/chuyền/ngày.\n'
            '- Nhà máy có 5 chuyền may, hoạt động 2 ca (6h-14h và 14h-22h).\n'
            '- Sản phẩm chủ lực: áo thun, quần jean, áo sơ mi, váy đầm.\n'
            '- Tháng cao điểm: tháng 3-5 (hàng hè) và tháng 9-11 (hàng đông).'
        ),
    },
    {
        'doc_id': 'SOP_004',
        'title': 'Hướng dẫn vận hành hệ thống ERP',
        'content': (
            'Hệ thống ERP tại Lucky Star sử dụng Odoo 16:\n'
            '- Module Inventory: quản lý tồn kho nguyên liệu và thành phẩm.\n'
            '- Module Manufacturing: lập kế hoạch và theo dõi lệnh sản xuất.\n'
            '- Module Purchase: quản lý đơn mua hàng và nhà cung cấp.\n'
            '- Module Sales: quản lý đơn hàng khách và xuất kho.\n'
            '- Module Accounting: kế toán và báo cáo tài chính.\n'
            'Đăng nhập: erp.luckystar.vn | Hỗ trợ IT: ext 1001 | Backup dữ liệu: 23h00 hàng ngày.'
        ),
    },
    {
        'doc_id': 'SOP_005',
        'title': 'Nhà cung cấp nguyên liệu chính',
        'content': (
            'Danh sách nhà cung cấp chính Lucky Star:\n'
            '1. Vải Phong Phú (HCM): cung cấp vải cotton, vải thun - lead time 5-7 ngày.\n'
            '2. Chỉ Coats Việt Nam: cung cấp chỉ may các loại - lead time 3-4 ngày.\n'
            '3. Khóa YKK: cung cấp khóa kéo cao cấp - lead time 7-10 ngày.\n'
            '4. Bao bì Tân Tiến: cung cấp bao bì đóng gói - lead time 3-5 ngày.\n'
            'Chính sách: ưu tiên đặt hàng trước 14 ngày để đảm bảo nguồn cung.\n'
            'Liên hệ mua hàng: Ms. Lan - 0901 234 567 | Mr. Hùng - 0912 345 678.'
        ),
    },
    {
        'doc_id': 'RPT_001',
        'title': 'Báo cáo sản xuất tháng 6/2024',
        'content': (
            'Tóm tắt sản xuất tháng 6/2024:\n'
            '- Tổng sản phẩm hoàn thành: 48,250 / kế hoạch 50,000 (đạt 96.5%).\n'
            '- Chuyền hiệu suất cao nhất: Chuyền 2 (97.3%).\n'
            '- Chuyền cần cải thiện: Chuyền 4 (82.1%) - do máy móng tay bị lỗi ngày 15/6.\n'
            '- Defect rate trung bình: 1.8% (dưới ngưỡng 2.5% - đạt).\n'
            '- Tiêu thụ vải cotton: 6,200m; vải thun: 4,800m.\n'
            '- Chi phí nguyên liệu: 1.2 tỷ VNĐ (trong ngân sách).'
        ),
    },
]

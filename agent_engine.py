# -*- coding: utf-8 -*-
"""
AI Agent Engine for Minh An Company - B2B Sales Opportunity Processing.
Implements the 6-step workflow matching the company flowchart.
"""
import re
import json
import datetime
from database import get_connection

def parse_currency(text):
    if not text:
        return 0
    text = str(text).lower().replace(",", "").replace(".", "").replace(" ", "")
    # Check for "tỷ", "triệu", "tr", "k"
    m_ty = re.search(r'(\d+(?:\.\d+)?)\s*(?:tỷ|ty|billion)', text)
    if m_ty:
        return float(m_ty.group(1)) * 1000000000
    m_tr = re.search(r'(\d+(?:\.\d+)?)\s*(?:triệu|trieu|tr|m)', text)
    if m_tr:
        return float(m_tr.group(1)) * 1000000
    m_k = re.search(r'(\d+)\s*(?:k|nghìn|nghin)', text)
    if m_k:
        return float(m_k.group(1)) * 1000
    m_num = re.search(r'(\d{6,})', text)
    if m_num:
        return float(m_num.group(1))
    return 0

def extract_discount(text):
    if not text:
        return 0.0
    match = re.search(r'(?:chiết khấu|giảm giá|discount)\s*(?:là|khoảng|mức)?\s*(\d+(?:\.\d+)?)\s*%', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match2 = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:chiết khấu|giảm giá|discount)', text, re.IGNORECASE)
    if match2:
        return float(match2.group(1))
    return 0.0

def extract_deadline(text):
    if not text:
        return None
    patterns = [
        r'(?:trước ngày|hạn|deadline|hoàn thành trước|giao trước)\s*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
        r'(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
        r'trong vòng\s*(\d+)\s*(?:ngày|tuần|tháng)'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None

def extract_contact_info(text):
    # Extract Email
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    email = email_match.group(0) if email_match else ""

    # Extract Phone
    phone_match = re.search(r'(?:0|\+84)[1-9][0-9\s.-]{8,12}', text)
    phone = phone_match.group(0).strip() if phone_match else ""

    # Extract Name & Company
    name = ""
    company = ""
    lines = text.split("\n")
    for line in lines:
        l = line.strip()
        if not name:
            m_name = re.search(r'(?:tôi là|tên tôi là|người liên hệ|từ|sender:?)\s*[:\-]?\s*([A-ZÀ-Ỹa-zà-ỹ\s]{3,30})', l, re.IGNORECASE)
            if m_name:
                name = m_name.group(1).strip()
        if not company:
            m_comp = re.search(r'(?:công ty|cty|doanh nghiệp|tập đoàn)\s*([A-ZÀ-Ỹ0-9\s\.\-]{3,40})', l, re.IGNORECASE)
            if m_comp:
                company = ("Công ty " + m_comp.group(1).strip()).strip()

    if not name and lines:
        for line in lines[:3]:
            if "anh" in line.lower() or "chị" in line.lower() or "ông" in line.lower() or "bà" in line.lower():
                name = line.strip()
                break

    return {
        "name": name or "Quý Khách Hàng",
        "company": company or "Khách hàng Doanh nghiệp",
        "email": email,
        "phone": phone
    }

def match_products_in_text(text, db_products):
    matched_items = []
    text_lower = text.lower()

    for p in db_products:
        sku = p['sku'].lower()
        name = p['name'].lower()
        # Create search keywords
        keywords = []
        if 'r750' in sku or 'r750' in name:
            keywords = ['r750', 'dell r750', 'server dell', 'máy chủ dell']
        elif 'dl380' in sku or 'dl380' in name:
            keywords = ['dl380', 'hpe dl380', 'server hp', 'máy chủ hpe', 'máy chủ hp']
        elif 'c9200l-24p' in sku or '24 port' in name:
            keywords = ['c9200l-24p', 'switch cisco 24', 'cisco 24 port', 'cisco 24 cổng', 'switch 24p']
        elif 'c9200l-48p' in sku or '48 port' in name:
            keywords = ['c9200l-48p', 'switch cisco 48', 'cisco 48 port', 'cisco 48 cổng', 'switch 48p']
        elif 'forti' in sku or 'fortigate' in name:
            keywords = ['fortigate', 'fortinet', 'firewall', 'tường lửa', '60f']
        elif 'aruba' in sku or 'ap505' in name:
            keywords = ['aruba', 'ap505', 'access point', 'wifi 6', 'wi-fi 6', 'bộ phát wifi']
        elif 'thinkpad' in sku or 'thinkpad' in name:
            keywords = ['thinkpad', 't14', 'lenovo thinkpad', 'laptop thinkpad']
        elif 'lat5440' in sku or 'latitude' in name:
            keywords = ['latitude', '5440', 'dell latitude', 'laptop dell']
        elif 'prodesk' in sku or 'pro400' in name:
            keywords = ['prodesk', 'hp prodesk', 'máy tính bàn', 'pc hp', 'máy bàn hp']
        elif 'apc' in sku or 'ups' in name:
            keywords = ['ups', 'lưu điện', 'apc 3kva', 'smart-ups']
        elif 'ms365' in sku or 'microsoft 365' in name:
            keywords = ['microsoft 365', 'office 365', 'm365', 'bản quyền office', 'ms365']
        elif 'onsite' in sku or 'triển khai' in name:
            keywords = ['triển khai', 'cài đặt', 'onsite', 'dịch vụ lắp đặt', 'đấu nối']

        found = False
        for kw in keywords:
            if kw in text_lower:
                found = True
                break
        
        if found:
            # Find quantity near keyword or in text
            qty = 1
            # Search patterns like: "5 bộ", "10 cái", "2 chiếc", "số lượng 3"
            qty_patterns = [
                rf'(?:số lượng|sl|mua|cần|khoảng)?\s*(\d+)\s*(?:bộ|cái|chiếc|thiết bị|user|gói)?\s*(?:{kw})',
                rf'(?:{kw})\s*[:\-\(]?\s*(\d+)\s*(?:bộ|cái|chiếc|thiết bị|user|gói)?',
                rf'(\d+)\s*(?:bộ|cái|chiếc|thiết bị|user|gói)?\s*(?:{kw})'
            ]
            for qp in qty_patterns:
                m_q = re.search(qp, text_lower)
                if m_q:
                    try:
                        val = int(m_q.group(1))
                        if 1 <= val <= 1000:
                            qty = val
                            break
                    except:
                        pass

            matched_items.append({
                "product": p,
                "quantity": qty,
                "requested_name": p['name']
            })

    return matched_items

def assign_sales_rep(conn, opportunity_size=0):
    cur = conn.cursor()
    # Chọn NVKD có current_leads thấp nhất để cân bằng tải (Workload balancing)
    cur.execute('SELECT * FROM sales_reps ORDER BY current_leads ASC, id ASC LIMIT 1')
    rep = cur.fetchone()
    if rep:
        cur.execute('UPDATE sales_reps SET current_leads = current_leads + 1 WHERE id = ?', (rep['id'],))
        conn.commit()
        return dict(rep)
    return {"id": 1, "name": "Nguyễn Văn Tuấn", "email": "tuan.nv@minhan.vn"}

def run_agent_workflow(raw_request, options=None):
    """
    Main Agent execution matching Minh An's Flowchart:
    1. Bắt đầu: Tiếp nhận yêu cầu
    2. Phân loại & Kiểm tra thông tin -> Có đủ thông tin?
       - Không: Yêu cầu KH làm rõ/bổ sung
       - Có: Tạo Hồ sơ Cơ hội & Gắn người phụ trách
    3. Thẩm định tồn kho & giá
    4. Lập Báo giá & Dự thảo đề xuất
    5. Có vượt thẩm quyền / Cần chiết khấu đặc biệt?
       - Có: Trưởng phòng duyệt
       - Không: Kết thúc: Cập nhật & Theo dõi
    """
    conn = get_connection()
    cur = conn.cursor()

    # Get Master Products
    cur.execute('SELECT * FROM products')
    db_products = [dict(row) for row in cur.fetchall()]

    # Bước 1: Tiếp nhận & Phân tích cấu trúc
    contact = extract_contact_info(raw_request)
    discount_req = extract_discount(raw_request)
    deadline_req = extract_deadline(raw_request)
    
    # Extract Budget
    budget_req = 0
    m_budget = re.search(r'(?:ngân sách|kinh phí|budget|tối đa|dự toán)\s*(?:khoảng|là|tầm)?\s*[:\s]?\s*([0-9\.,\s]+(?:tỷ|ty|triệu|trieu|tr|vnđ|vnd|đ)?)', raw_request, re.IGNORECASE)
    if m_budget:
        budget_req = parse_currency(m_budget.group(1))

    matched_items = match_products_in_text(raw_request, db_products)

    # Bước 2: Kiểm tra Đầy đủ thông tin (Completeness Gate Check)
    missing_fields = []
    if not contact['email'] and not contact['phone']:
        missing_fields.append("Thông tin liên hệ (Email hoặc Số điện thoại để phản hồi)")
    if len(matched_items) == 0:
        missing_fields.append("Danh sách sản phẩm / dịch vụ cụ thể hoặc cấu hình yêu cầu")
    if not deadline_req and ("gấp" in raw_request.lower() or "sớm nhất" in raw_request.lower()):
        missing_fields.append("Thời hạn cụ thể (Deadline) khách hàng mong muốn nghiệm thu")

    is_sufficient = (len(missing_fields) == 0)

    # Sinh mã cơ hội
    now = datetime.datetime.now()
    code = f"OPP-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

    workflow_steps = [
        {"step": 1, "name": "Tiếp nhận yêu cầu", "status": "COMPLETED", "detail": f"Đã tiếp nhận yêu cầu từ {contact['name']} ({contact['company']})"}
    ]

    # Nhánh 1: KHÔNG ĐỦ THÔNG TIN
    if not is_sufficient:
        clarification_email = f"""Kính gửi Anh/Chị {contact['name']},

Công ty Cổ phần Công nghệ Minh An xin chân thành cảm ơn Anh/Chị và Quý công ty {contact['company']} đã quan tâm đến giải pháp và thiết bị của chúng tôi.

Để đội ngũ kỹ sư và kinh doanh của Minh An có thể thẩm định cấu hình, tra cứu tồn kho khả dụng và lập báo giá ưu đãi chính xác nhất cho Quý công ty, chúng tôi kính đề nghị Anh/Chị vui lòng làm rõ/bổ sung thêm một số thông tin sau:

{chr(10).join([f"  • {item}" for item in missing_fields])}

Ngay khi nhận được thông tin bổ sung, Minh An cam kết sẽ gửi Bảng Báo giá và Hồ sơ Giải pháp chi tiết trong vòng 04 giờ làm việc.

Trân trọng cảm ơn,
Bộ phận Kinh doanh B2B - Công ty Cổ phần Công nghệ Minh An
Hotline: 1900 6868 | Email: sales@minhan.vn
"""
        cur.execute('''
        INSERT INTO opportunities (
            code, client_name, client_company, client_email, client_phone,
            raw_request, status, is_info_sufficient, missing_info_notes,
            proposal_email_draft
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code, contact['name'], contact['company'], contact['email'], contact['phone'],
            raw_request, "CLARIFICATION_NEEDED", 0, "; ".join(missing_fields),
            clarification_email
        ))
        opp_id = cur.lastrowid
        conn.commit()
        conn.close()

        workflow_steps.append({"step": 2, "name": "Phân loại & Kiểm tra thông tin", "status": "INSUFFICIENT", "detail": f"Thiếu: {', '.join(missing_fields)}"})
        workflow_steps.append({"step": "2_branch", "name": "Yêu cầu KH làm rõ / bổ sung", "status": "ACTION_REQUIRED", "detail": "Đã tự động tạo bản nháp email gửi khách hàng yêu cầu bổ sung thông tin."})

        return {
            "success": True,
            "opportunity_id": opp_id,
            "code": code,
            "is_sufficient": False,
            "status": "CLARIFICATION_NEEDED",
            "missing_fields": missing_fields,
            "clarification_email": clarification_email,
            "workflow_steps": workflow_steps,
            "client_info": contact
        }

    # Nhánh 2: ĐỦ THÔNG TIN -> Tạo Hồ sơ Cơ hội & Gắn người phụ trách
    rep = assign_sales_rep(conn)
    workflow_steps.append({"step": 2, "name": "Phân loại & Kiểm tra thông tin", "status": "COMPLETED", "detail": "Thông tin đầu vào đầy đủ hợp lệ."})
    workflow_steps.append({"step": 3, "name": "Tạo Hồ sơ Cơ hội & Gán người phụ trách", "status": "COMPLETED", "detail": f"Gán cho NVKD: {rep['name']} ({rep['email']}) - Chuyên môn: {rep['specialty']}"})

    # Bước 3: Thẩm định Tồn kho & Đơn giá (NVKD & Vận hành)
    items_evaluated = []
    total_original = 0
    max_lead_time_days = 2
    stock_issues = []

    for item in matched_items:
        p = item['product']
        qty = item['quantity']
        unit_price = p['unit_price']
        total_p = unit_price * qty
        total_original += total_p

        stock_avail = p['stock_qty']
        is_stock_ok = 1 if (stock_avail >= qty) else 0
        item_lead_time = 2 if is_stock_ok else p['lead_time_days']

        if not is_stock_ok:
            max_lead_time_days = max(max_lead_time_days, p['lead_time_days'])
            stock_issues.append(f"{p['name']} (Cần {qty}, Kho chỉ còn {stock_avail} -> Cần {p['lead_time_days']} ngày nhập hàng)")
        
        items_evaluated.append({
            "product_id": p['id'],
            "sku": p['sku'],
            "name": p['name'],
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": total_p,
            "stock_available": stock_avail,
            "is_stock_sufficient": is_stock_ok,
            "item_lead_time_days": item_lead_time,
            "warranty_months": p['warranty_months']
        })

    # Tính toán thời hạn bàn giao khả thi
    feasible_date = now + datetime.timedelta(days=max_lead_time_days)
    feasible_deadline_str = feasible_date.strftime("%d/%m/%Y")

    deadline_status = "ON_TIME"
    deadline_warning = ""
    if deadline_req:
        deadline_status = "EVALUATED"
        if len(stock_issues) > 0 and ("gấp" in raw_request.lower() or "trong tuần" in raw_request.lower()):
            deadline_status = "DEADLINE_RISK"
            deadline_warning = f"Cảnh báo tiến độ: Khách yêu cầu bàn giao gấp nhưng một số thiết bị cần {max_lead_time_days} ngày để nhập kho."

    workflow_steps.append({
        "step": 4, 
        "name": "Thẩm định tồn kho & giá", 
        "status": "COMPLETED", 
        "detail": f"Khớp {len(items_evaluated)} hạng mục với bảng giá niêm yết hiện hành. " + (f"Tồn kho cảnh báo: {'; '.join(stock_issues)}" if stock_issues else "Tất cả thiết bị đều có sẵn tồn kho khả dụng.")
    })

    # Bước 4: Lập Báo giá & Dự thảo đề xuất
    discount_pct = discount_req
    discount_amount = total_original * (discount_pct / 100.0)
    total_final = total_original - discount_amount

    # Bước 5: Kiểm tra thẩm quyền phê duyệt
    requires_approval = False
    approval_reasons = []

    if discount_pct > 5.0:
        requires_approval = True
        approval_reasons.append(f"Mức chiết khấu yêu cầu ({discount_pct}%) vượt thẩm quyền của NVKD (tối đa 5.0%)")

    if total_final >= 200000000:
        requires_approval = True
        approval_reasons.append(f"Tổng giá trị đơn hàng ({total_final:,.0f} VNĐ) lớn hơn ngưỡng 200 triệu VNĐ")

    if budget_req > 0 and total_final > budget_req * 1.15:
        requires_approval = True
        approval_reasons.append(f"Báo giá ({total_final:,.0f} VNĐ) vượt 15% so với ngân sách dự kiến của khách ({budget_req:,.0f} VNĐ)")

    if deadline_status == "DEADLINE_RISK":
        requires_approval = True
        approval_reasons.append("Tồn kho không đáp ứng ngay hạn giao của khách, cần ý kiến chỉ đạo phương án giao trước 1 phần.")

    approval_status = "PENDING_APPROVAL" if requires_approval else "NOT_REQUIRED"
    status = "PENDING_APPROVAL" if requires_approval else "READY_TO_SEND"

    if requires_approval:
        workflow_steps.append({
            "step": 5, 
            "name": "Kiểm tra thẩm quyền", 
            "status": "APPROVAL_REQUIRED", 
            "detail": f"Yêu cầu Trưởng phòng Kinh doanh phê duyệt do: {'; '.join(approval_reasons)}"
        })
    else:
        workflow_steps.append({
            "step": 5, 
            "name": "Kiểm tra thẩm quyền", 
            "status": "COMPLETED", 
            "detail": "Báo giá nằm hoàn toàn trong hạn mức thẩm quyền của NVKD (Chiết khấu <= 5%). Phê duyệt tự động."
        })

    # Soạn thảo Bản nháp Phản hồi Khách hàng (Proposal Draft)
    item_rows_txt = ""
    for idx, it in enumerate(items_evaluated, 1):
        stock_label = "Sẵn hàng tại kho Minh An" if it['is_stock_sufficient'] else f"Đặt hàng {it['item_lead_time_days']} ngày"
        item_rows_txt += f"  {idx}. {it['name']} | SL: {it['quantity']} | Đơn giá: {it['unit_price']:,.0f} đ | Thành tiền: {it['total_price']:,.0f} đ ({stock_label})\n"

    proposal_email_draft = f"""Kính gửi Anh/Chị {contact['name']} - {contact['company']},

Công ty Cổ phần Công nghệ Minh An xin gửi lời chào trân trọng và lời cảm ơn chân thành tới Quý công ty.
Tôi là {rep['name']} - Chuyên viên Kinh doanh phụ trách trực tiếp yêu cầu của Quý khách.

Căn cứ vào nhu cầu trang bị thiết bị và dịch vụ của Quý công ty, Minh An xin trân trọng gửi Bản tóm tắt Đề xuất & Báo giá kỹ thuật như sau:

--- BẢNG BÁO GIÁ DỰ THẢO (MÃ SỐ: {code}) ---
{item_rows_txt}
• Tổng giá trị trước chiết khấu: {total_original:,.0f} VNĐ
• Chiết khấu áp dụng: {discount_pct}% (-{discount_amount:,.0f} VNĐ)
• TỔNG GIÁ TRỊ THANH TOÁN (Chưa VAT): {total_final:,.0f} VNĐ

--- CAM KẾT VẬN HÀNH & TRIỂN KHAI ---
• Thời gian bàn giao cam kết: {feasible_deadline_str} (Đội ngũ kỹ thuật hỗ trợ tận nơi).
• Tiêu chuẩn bảo hành: Chính hãng theo từng thiết bị (12 - 36 tháng), đổi mới trong 30 ngày nếu phát sinh lỗi phần cứng.
• Phương thức thanh toán: Đặt cọc 30% khi ký hợp đồng, 70% còn lại sau khi bàn giao nghiệm thu.

Anh/Chị vui lòng xem file Báo giá chính thức đính kèm và phản hồi để Minh An giữ tồn kho khả dụng cho đơn hàng của mình.

Rất mong có cơ hội hợp tác cùng Quý công ty!

Trân trọng,
{rep['name']} | Bộ phận Kinh doanh B2B
Công ty Cổ phần Công nghệ Minh An
Điện thoại: {rep['phone']} | Email: {rep['email']}
Địa chỉ: Tầng 5, Tòa nhà Công nghệ, Cầu Giấy, Hà Nội
"""

    # Lưu vào Database
    cur.execute('''
    INSERT INTO opportunities (
        code, client_name, client_company, client_email, client_phone,
        raw_request, status, is_info_sufficient, assigned_rep_id, assigned_rep_name,
        requested_budget, requested_deadline, feasible_deadline, deadline_status,
        total_original_price, requested_discount_pct, approved_discount_pct, total_final_price,
        requires_manager_approval, approval_status, manager_notes, proposal_email_draft
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        code, contact['name'], contact['company'], contact['email'], contact['phone'],
        raw_request, status, 1, rep['id'], rep['name'],
        budget_req, deadline_req or "Tiêu chuẩn", feasible_deadline_str, deadline_status,
        total_original, discount_pct, 0 if requires_approval else discount_pct, total_final,
        1 if requires_approval else 0, approval_status,
        "; ".join(approval_reasons) if requires_approval else "Đã tự động xác thực",
        proposal_email_draft
    ))
    opp_id = cur.lastrowid

    # Lưu chi tiết hạng mục
    for it in items_evaluated:
        cur.execute('''
        INSERT INTO opportunity_items (
            opportunity_id, product_id, matched_sku, matched_name, requested_name,
            quantity, unit_price, total_price, stock_available, is_stock_sufficient, item_lead_time_days
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opp_id, it['product_id'], it['sku'], it['name'], it['name'],
            it['quantity'], it['unit_price'], it['total_price'],
            it['stock_available'], it['is_stock_sufficient'], it['item_lead_time_days']
        ))

    conn.commit()
    conn.close()

    workflow_steps.append({
        "step": 6, 
        "name": "Cập nhật & Theo dõi", 
        "status": "COMPLETED", 
        "detail": f"Đã khởi tạo hồ sơ #{code}, lập xong bản nháp đề xuất và đưa vào pipeline theo dõi."
    })

    return {
        "success": True,
        "opportunity_id": opp_id,
        "code": code,
        "is_sufficient": True,
        "status": status,
        "client_info": contact,
        "assigned_rep": rep,
        "items": items_evaluated,
        "total_original": total_original,
        "discount_pct": discount_pct,
        "discount_amount": discount_amount,
        "total_final": total_final,
        "requested_budget": budget_req,
        "feasible_deadline": feasible_deadline_str,
        "requested_deadline": deadline_req,
        "deadline_status": deadline_status,
        "requires_manager_approval": requires_approval,
        "approval_reasons": approval_reasons,
        "proposal_email_draft": proposal_email_draft,
        "workflow_steps": workflow_steps
    }

def approve_opportunity(opp_id, action, manager_notes=""):
    """
    Trưởng phòng duyệt hoặc từ chối đề xuất vượt quyền
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM opportunities WHERE id = ?', (opp_id,))
    opp = cur.fetchone()
    if not opp:
        conn.close()
        return {"success": False, "error": "Không tìm thấy cơ hội"}

    if action == "APPROVE":
        cur.execute('''
        UPDATE opportunities 
        SET approval_status = 'APPROVED', 
            status = 'READY_TO_SEND',
            approved_discount_pct = requested_discount_pct,
            manager_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (manager_notes or "Trưởng phòng đã phê duyệt mức chiết khấu và đề xuất.", opp_id))
    elif action == "REJECT":
        cur.execute('''
        UPDATE opportunities 
        SET approval_status = 'REJECTED', 
            status = 'REJECTED',
            manager_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (manager_notes or "Trưởng phòng yêu cầu NVKD thương lượng lại điều khoản với khách.", opp_id))

    conn.commit()
    conn.close()
    return {"success": True, "action": action}


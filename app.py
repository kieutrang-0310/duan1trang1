# -*- coding: utf-8 -*-
"""
Web Server and REST API for Minh An Company AI Agent.
Runs on localhost:8000 using Python standard library http.server.
Supports complete live editing of all metrics, tasks, products, and data.
"""
import sys
import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure current directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import init_db, get_connection
import agent_engine

PORT = 8000

SAMPLE_REQUESTS = [
    {
        "id": "sample_complete",
        "title": "Mẫu 1: Yêu cầu chuẩn & Đủ thông tin (Tự động duyệt)",
        "desc": "Khách hàng gửi đầy đủ thông tin, xin chiết khấu 4% (nằm trong hạn mức NVKD).",
        "text": """Chào Công ty Minh An,
Tôi là Hoàng Long, phụ trách IT của Công ty Dược phẩm Vĩnh Khang.
Email: long.hoang@vinhkhangpharma.vn | SĐT: 0983 234 567
Chúng tôi đang cần trang bị hạ tầng CNTT cho chi nhánh mới:
1. 02 Switch Cisco Catalyst 24 port PoE (C9200L)
2. 06 Bộ phát Wi-Fi 6 Aruba Instant On AP505
3. 08 Laptop Dell Latitude 5440 cho nhân viên
Ngân sách dự kiến của chúng tôi khoảng 250 - 280 triệu đồng.
Thời hạn hoàn thành trước ngày 28/11/2026.
Đề nghị Minh An hỗ trợ mức chiết khấu 4% cho đơn hàng đầu tiên này.
Nhờ các bạn gửi báo giá sớm giúp tôi. Trân trọng!"""
    },
    {
        "id": "sample_missing",
        "title": "Mẫu 2: Thiếu thông tin (Rẽ nhánh Yêu cầu làm rõ)",
        "desc": "Yêu cầu sơ sài, thiếu số lượng, không có liên hệ và thời hạn cụ thể.",
        "text": """Chào Minh An,
Bên mình đang mở rộng văn phòng cần mua gấp máy chủ Dell và vài máy tính để bàn HP ProDesk cùng bộ phát wifi.
Cho mình xin báo giá tổng thể nhé. Gửi sớm trong ngày."""
    },
    {
        "id": "sample_over_authority",
        "title": "Mẫu 3: Vượt thẩm quyền NVKD (Cần Trưởng phòng duyệt)",
        "desc": "Đề xuất chiết khấu 10% (vượt mức 5% của NVKD), giá trị đơn lớn > 400 triệu.",
        "text": """Kính gửi Bộ phận Kinh doanh Minh An,
Tôi là Phạm Quốc Huy, Trưởng phòng Mua sắm Tập đoàn Xây dựng An Gia.
Email: huy.pq@angiaconstruction.vn - Hotline: 0918 889 999.
Công ty chúng tôi cần mua các thiết bị sau để phục vụ dự án trung tâm dữ liệu:
- 02 Máy chủ Dell PowerEdge R750 Xeon Silver
- 01 Tường lửa Firewall Fortinet FortiGate 60F
- 01 Bộ lưu điện UPS APC Smart-UPS 3000VA
- 01 Gói Dịch vụ Cài đặt và Triển khai Onsite
Tổng kinh phí phê duyệt dự án là 320 triệu đồng.
Thời hạn bàn giao mong muốn trước ngày 30/11/2026.
Vì đây là dự án lớn và An Gia sẽ hợp tác lâu dài, chúng tôi yêu cầu mức chiết khấu 10%.
Vui lòng gửi đề xuất kỹ thuật và bảng báo giá chính thức."""
    },
    {
        "id": "sample_stock_shortage",
        "title": "Mẫu 4: Thiếu tồn kho & Cảnh báo hạn giao (SLA Conflict)",
        "desc": "Đặt mua Switch Cisco 48 Port (đang hết hàng tồn) và đòi giao siêu gấp.",
        "text": """Minh An hỗ trợ báo giá gấp giúp anh:
Người liên hệ: Lê Văn Hùng - Giám đốc Kỹ thuật Cty Truyền thông Sao Mai
Email: hung.le@saomai.vn | Mobile: 0904 555 777
Bên anh cần:
- 03 Switch Cisco 48 Port (C9200L-48P)
- 10 Laptop ThinkPad T14 Gen 4 Core i7
Hạn chót bên anh phải nghiệm thu là trong vòng 3 ngày tới (yêu cầu giao gấp).
Chiết khấu ưu đãi 5% theo thỏa thuận trước nhé."""
    }
]

class MinhAnApiHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        # 1. API: Sample Requests
        if path == '/api/sample-requests':
            return self.send_json(SAMPLE_REQUESTS)

        # 2. API: Stats & Settings
        elif path == '/api/stats':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM opportunities')
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'CLARIFICATION_NEEDED'")
            clarification = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'PENDING_APPROVAL'")
            pending_approval = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status IN ('READY_TO_SEND', 'APPROVED')")
            ready = cur.fetchone()[0]

            # Get custom user settings
            cur.execute('SELECT key, value FROM settings')
            settings_map = {row['key']: row['value'] for row in cur.fetchall()}
            conn.close()

            return self.send_json({
                "total_opportunities": total,
                "clarification_needed": clarification,
                "pending_approval": pending_approval,
                "ready_to_send": ready,
                "custom_kpi_done": settings_map.get('custom_kpi_done', str(ready + 24)),
                "custom_kpi_progress": settings_map.get('custom_kpi_progress', str(pending_approval + clarification + 6)),
                "custom_kpi_completed": settings_map.get('custom_kpi_completed', str(total + 50)),
                "custom_kpi_focus": settings_map.get('custom_kpi_focus', '18h'),
                "user_name": settings_map.get('user_name', 'Emily'),
                "user_greeting": settings_map.get('user_greeting', "Here's what's happening today.")
            })

        # 3. API: Settings
        elif path == '/api/settings':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT key, value FROM settings')
            settings_map = {row['key']: row['value'] for row in cur.fetchall()}
            conn.close()
            return self.send_json(settings_map)

        # 4. API: Tasks (To-Do List)
        elif path == '/api/tasks':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM tasks ORDER BY completed ASC, id DESC')
            tasks = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(tasks)

        # 5. API: Activities
        elif path == '/api/activities':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM activities ORDER BY id DESC LIMIT 10')
            acts = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(acts)

        # 6. API: Chart Data
        elif path == '/api/chart-data':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = 'chart_data'")
            row = cur.fetchone()
            conn.close()
            if row and row['value']:
                try:
                    return self.send_json(json.loads(row['value']))
                except:
                    pass
            # Default chart values matching Emily's dashboard [25, 48, 72, 60, 78, 85, 92]
            return self.send_json({
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "values": [25, 48, 72, 60, 78, 85, 92],
                "badge": "Tuyệt vời! 🎉"
            })

        # 7. API: Products & Stock
        elif path == '/api/products':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM products ORDER BY category, name')
            products = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(products)

        # 8. API: Sales Reps
        elif path == '/api/sales-reps':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM sales_reps ORDER BY current_leads ASC')
            reps = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(reps)

        # 9. API: Opportunities list
        elif path == '/api/opportunities':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM opportunities ORDER BY id DESC')
            opps = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(opps)

        # 10. API: Opportunity detail
        elif path.startswith('/api/opportunities/'):
            parts = path.strip('/').split('/')
            if len(parts) == 3 and parts[2].isdigit():
                opp_id = int(parts[2])
                conn = get_connection()
                cur = conn.cursor()
                cur.execute('SELECT * FROM opportunities WHERE id = ?', (opp_id,))
                opp = cur.fetchone()
                if not opp:
                    conn.close()
                    return self.send_json({"error": "Not found"}, 404)
                
                cur.execute('SELECT * FROM opportunity_items WHERE opportunity_id = ?', (opp_id,))
                items = [dict(row) for row in cur.fetchall()]
                conn.close()
                result = dict(opp)
                result['items'] = items
                return self.send_json(result)

        # 11. Serve Static Files (UI)
        if path == '/' or path == '/index.html':
            static_file = os.path.join(BASE_DIR, 'static', 'index.html')
            if os.path.exists(static_file):
                with open(static_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Index file not found")
                return

        # 404
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
        
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        conn = get_connection()
        cur = conn.cursor()

        # 1. API: Process Inbound Request (Agent Core)
        if path == '/api/process':
            raw_text = payload.get('text', '').strip()
            if not raw_text:
                conn.close()
                return self.send_json({"error": "Vui lòng nhập nội dung yêu cầu của khách hàng"}, 400)
            
            result = agent_engine.run_agent_workflow(raw_text)
            # Add to activities
            client_name = result.get('client_info', {}).get('name', 'Khách hàng')
            code = result.get('code', 'OPP')
            cur.execute('INSERT INTO activities (title, icon_type, time_ago) VALUES (?, ?, ?)',
                        (f"AI Agent tiếp nhận & xử lý yêu cầu #{code} ({client_name})", "check", "Vừa xong"))
            conn.commit()
            conn.close()
            return self.send_json(result)

        # 2. API: Manager Approve/Reject
        elif path.startswith('/api/opportunities/') and path.endswith('/approval'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[2].isdigit():
                opp_id = int(parts[2])
                action = payload.get('action', 'APPROVE')
                notes = payload.get('notes', '')
                result = agent_engine.approve_opportunity(opp_id, action, notes)
                cur.execute('INSERT INTO activities (title, icon_type, time_ago) VALUES (?, ?, ?)',
                            (f"Trưởng phòng {'phê duyệt' if action == 'APPROVE' else 'từ chối'} cơ hội #{opp_id}", "check" if action == 'APPROVE' else "alert", "Vừa xong"))
                conn.commit()
                conn.close()
                return self.send_json(result)

        # 3. API: Tasks (Add, Toggle, Delete)
        elif path == '/api/tasks/add':
            title = payload.get('title', '').strip()
            emoji = payload.get('emoji', '📝')
            due_info = payload.get('due_info', 'Hôm nay')
            if title:
                cur.execute('INSERT INTO tasks (title, completed, emoji, due_info) VALUES (?, 0, ?, ?)', (title, emoji, due_info))
                conn.commit()
                task_id = cur.lastrowid
                conn.close()
                return self.send_json({"success": True, "id": task_id, "title": title})
            conn.close()
            return self.send_json({"error": "Tiêu đề không được để trống"}, 400)

        elif path.startswith('/api/tasks/') and path.endswith('/toggle'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[2].isdigit():
                task_id = int(parts[2])
                cur.execute('UPDATE tasks SET completed = CASE WHEN completed = 1 THEN 0 ELSE 1 END WHERE id = ?', (task_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "id": task_id})

        elif path.startswith('/api/tasks/') and path.endswith('/delete'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[2].isdigit():
                task_id = int(parts[2])
                cur.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "id": task_id})

        # 4. API: Save Custom Settings & KPIs (Người dùng tự sửa số liệu)
        elif path == '/api/settings/update':
            for k, v in payload.items():
                cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (str(k), str(v)))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "updated": payload})

        # 4.1 API: Reset All Data to 0 (Xóa sạch số liệu để người dùng tự nhập)
        elif path == '/api/reset-data':
            cur.execute('DELETE FROM opportunities')
            cur.execute('DELETE FROM opportunity_items')
            cur.execute('DELETE FROM tasks')
            cur.execute('DELETE FROM activities')
            cur.execute('UPDATE sales_reps SET current_leads = 0')
            clean_settings = [
                ('custom_kpi_done', '0'),
                ('custom_kpi_progress', '0'),
                ('custom_kpi_completed', '0'),
                ('custom_kpi_focus', '0h'),
                ('chart_data', '{"labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"], "values": [0, 0, 0, 0, 0, 0, 0], "badge": "Nhấp để đổi"}')
            ]
            for k, v in clean_settings:
                cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, v))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "message": "Đã đưa toàn bộ số liệu về 0"})

        # 5. API: Save Chart Data
        elif path == '/api/chart-data/update':
            cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('chart_data', ?)", (json.dumps(payload, ensure_ascii=False),))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "chart_data": payload})

        # 6. API: Update Product
        elif path == '/api/products/update':
            sku = payload.get('sku')
            name = payload.get('name')
            category = payload.get('category')
            unit_price = float(payload.get('unit_price', 0))
            stock_qty = int(payload.get('stock_qty', 0))
            lead_time_days = int(payload.get('lead_time_days', 7))
            warranty_months = int(payload.get('warranty_months', 12))
            
            cur.execute('''
            UPDATE products 
            SET name = ?, category = ?, unit_price = ?, stock_qty = ?, lead_time_days = ?, warranty_months = ?
            WHERE sku = ?
            ''', (name, category, unit_price, stock_qty, lead_time_days, warranty_months, sku))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "sku": sku})

        # 7. API: Add Product
        elif path == '/api/products/add':
            sku = payload.get('sku', '').strip()
            name = payload.get('name', '').strip()
            category = payload.get('category', 'Khác').strip()
            unit = payload.get('unit', 'Cái').strip()
            unit_price = float(payload.get('unit_price', 0))
            stock_qty = int(payload.get('stock_qty', 0))
            lead_time_days = int(payload.get('lead_time_days', 7))
            warranty_months = int(payload.get('warranty_months', 12))
            desc = payload.get('description', '')

            if sku and name:
                try:
                    cur.execute('''
                    INSERT INTO products (sku, name, category, unit, unit_price, stock_qty, lead_time_days, warranty_months, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (sku, name, category, unit, unit_price, stock_qty, lead_time_days, warranty_months, desc))
                    conn.commit()
                    conn.close()
                    return self.send_json({"success": True, "sku": sku})
                except Exception as e:
                    conn.close()
                    return self.send_json({"error": str(e)}, 400)
            conn.close()
            return self.send_json({"error": "SKU và Tên không được rỗng"}, 400)

        # 8. API: Delete Product
        elif path == '/api/products/delete':
            sku = payload.get('sku')
            if sku:
                cur.execute('DELETE FROM products WHERE sku = ?', (sku,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "sku": sku})
            conn.close()
            return self.send_json({"error": "Thiếu mã SKU"}, 400)

        # 9. API: Update Sales Rep
        elif path == '/api/sales-reps/update':
            rep_id = payload.get('id')
            name = payload.get('name')
            email = payload.get('email')
            phone = payload.get('phone')
            current_leads = int(payload.get('current_leads', 0))
            specialty = payload.get('specialty')

            cur.execute('''
            UPDATE sales_reps 
            SET name = ?, email = ?, phone = ?, current_leads = ?, specialty = ?
            WHERE id = ?
            ''', (name, email, phone, current_leads, specialty, rep_id))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "id": rep_id})

        # 404
        conn.close()
        self.send_json({"error": "Endpoint not found"}, 404)

def run_server():
    init_db()
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MinhAnApiHandler)
    print(f"================================================================")
    print(f"🌸 Minh An AI Agent Server (Claymorphism UI) RUNNING on http://localhost:{PORT}")
    print(f"👉 Mở trình duyệt và truy cập: http://localhost:{PORT}")
    print(f"================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()

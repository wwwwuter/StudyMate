#!/usr/bin/env python3
"""StudyMate 全阶段数据链路验证脚本。
走通：登录 → 任务CRUD → PDF/Excel导入 → 计时 → 提醒 → 数据分析 → RAG。
"""
import requests, json, time, sys, os

BASE = "http://127.0.0.1:5588/api"
PASS = 0
FAIL = 0

def check(name, ok, detail=""):
    global PASS, FAIL
    status = "✅" if ok else "❌"
    if ok: PASS += 1
    else: FAIL += 1
    print(f"{status} {name}" + (f" — {detail}" if detail else ""))

def req(method, path, **kw):
    url = BASE + path
    kw.setdefault('timeout', 30)
    r = getattr(requests, method)(url, **kw)
    return r

# ── Phase 1: 登录（mock 扫码）──
print("\n═══ Phase 1: 认证（mock 扫码登录）═══")
r = req("post", "/auth/wechat/qr", json={})
ticket = r.json().get("data", {}).get("ticket")
check("获取扫码 ticket", bool(ticket), f"ticket={ticket[:12]}..." if ticket else "无 ticket")

r = req("post", "/auth/wechat/scan", json={"ticket": ticket, "code": "linktest001"})
check("模拟扫码", r.status_code == 200)

r = req("get", f"/auth/wechat/qr/status?ticket={ticket}")
data = r.json().get("data", {})
def find_token(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "access_token" and isinstance(v, str): return v
            r2 = find_token(v)
            if r2: return r2
    return None
TOKEN = find_token(data)
check("获取 JWT token", bool(TOKEN), f"{TOKEN[:20]}..." if TOKEN else "无 token")
H = {"Authorization": f"Bearer {TOKEN}"}

# ── Phase 2: 用户信息 ──
print("\n═══ Phase 2: 用户信息 ═══")
r = req("get", "/auth/me", headers=H)
check("获取当前用户", r.status_code == 200, r.json().get("data", {}).get("username", "") if r.status_code == 200 else r.text[:80])

# ── Phase 3: 学习任务 CRUD ──
print("\n═══ Phase 3: 学习任务 CRUD ═══")
r = req("post", "/tasks", headers=H, json={
    "content": "链路测试-数学复习", "subject": "数学", "date": "2026-07-27",
    "priority": "high", "estimated_minutes": 90, "tags": ["测试", "链路"]
})
task_id = r.json().get("data", {}).get("id") if r.status_code in (200, 201) else None
check("创建任务", bool(task_id), f"id={task_id}")

r = req("get", "/tasks?date=2026-07-27", headers=H)
rdata = r.json().get("data", [])
tasks = rdata if isinstance(rdata, list) else rdata.get("tasks", [])
check("查询任务列表", len(tasks) > 0, f"{len(tasks)} 条")

if task_id:
    r = req("put", f"/tasks/{task_id}", headers=H, json={"status": "done"})
    check("更新任务状态", r.status_code == 200)

# ── Phase 4: PDF/Excel 导入 ──
print("\n═══ Phase 4: PDF/Excel 导入 ═══")
# Excel 导入（构造简单 xlsx）
try:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["日期", "科目", "任务", "开始", "结束"])
    ws.append(["2026-07-28", "英语", "阅读理解", "09:00", "10:30"])
    xlsx_path = "/tmp/sm_link_test.xlsx"
    wb.save(xlsx_path)
    with open(xlsx_path, "rb") as f:
        r = req("post", "/tasks/import/excel", headers=H, files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    check("Excel 导入", r.status_code == 200, f"导入 {r.json().get('data', {}).get('count', '?')} 条")
except Exception as e:
    check("Excel 导入", False, str(e)[:80])

# PDF AI 导入（mock 模式）
try:
    pdf_path = "/tmp/sm_link_test.pdf"
    # 用 reportlab 生成可提取文本的 PDF
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        c = canvas.Canvas(pdf_path, pagesize=A4)
        c.drawString(72, 750, "复习线性代数 7月29日 14:00-16:00")
        c.drawString(72, 730, "做英语阅读理解 7月30日 09:00-10:30")
        c.save()
    except ImportError:
        # 无 reportlab 时用纯文本 PDF
        pdf_text = "BT /F1 12 Tf 72 700 Td (Review Linear Algebra July 29 14:00-16:00) Tj ET"
        pdf_content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length " + str(len(pdf_text.encode())).encode() + b">>stream\n"
            + pdf_text.encode() + b"\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
            b"0000000115 00000 n \n0000000196 00000 n \n"
            b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n290\n%%EOF\n"
        )
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)
    with open(pdf_path, "rb") as f:
        r = req("post", "/tasks/import/pdf/ai", headers=H, files={"file": ("test.pdf", f, "application/pdf")})
    tasks_extracted = r.json().get("data", {}).get("tasks", [])
    check("PDF AI 预览", r.status_code == 200, f"提取 {len(tasks_extracted)} 条")
except Exception as e:
    check("PDF AI 预览", False, str(e)[:80])

# ── Phase 5: 计时系统 ──
print("\n═══ Phase 5: 计时系统 ═══")
r = req("post", "/records", headers=H, json={
    "mode": "pomodoro", "subject": "数学", "task_id": task_id, "planned_duration": 1500
})
record_id = r.json().get("data", {}).get("id") if r.status_code in (200, 201) else None
check("开始计时", bool(record_id), f"record_id={record_id}")

time.sleep(1)
r = req("put", f"/records/{record_id}/stop", headers=H)
check("停止计时", r.status_code == 200, f"时长={r.json().get('data', {}).get('duration', '?')}s")

r = req("get", "/records/history?mode=pomodoro", headers=H)
check("计时历史", r.status_code == 200)

r = req("get", "/records/stats?range=week", headers=H)
check("计时统计", r.status_code == 200, f"总时长={r.json().get('data', {}).get('total_duration', '?')}s")

# ── Phase 6: 提醒系统 ──
print("\n═══ Phase 6: 提醒系统 ═══")
r = req("post", "/reminders/sweep", headers=H)
check("提醒扫描触发", r.status_code == 200, f"生成 {r.json().get('data', {}).get('created', 0)} 条")

r = req("get", "/reminders/pending", headers=H)
check("查询待提醒", r.status_code == 200)

r = req("get", "/reminders/settings", headers=H)
check("查询提醒设置", r.status_code == 200, f"enabled={r.json().get('data', {}).get('enabled')}")

# ── Phase 7: 数据分析 ──
print("\n═══ Phase 7: 数据分析 ═══")
r = req("get", "/analytics/report?range=week", headers=H)
check("学习报告指标", r.status_code == 200, f"总时长={r.json().get('data', {}).get('total_duration', '?')}s")

r = req("post", "/analytics/summary", headers=H, json={"range": "week"})
check("AI 学习报告生成", r.status_code == 200, f"source={r.json().get('data', {}).get('source', '?')}")

# ── Phase 8: RAG 知识库 ──
print("\n═══ Phase 8: RAG 知识库 ═══")
# 先上传一个材料（form-data 方式）
try:
    r = req("post", "/materials", headers=H, data={
        "title": "线性代数笔记",
        "content": "矩阵乘法是线性代数的核心运算，A乘以B得到C。特征值与特征向量描述了矩阵的本质。",
        "source": "text"
    })
    mat_id = r.json().get("data", {}).get("id") if r.status_code in (200, 201) else None
    check("上传材料", bool(mat_id), f"id={mat_id}")
except Exception as e:
    check("上传材料", False, str(e)[:80])

r = req("post", "/rag/index", headers=H, json={})
check("重建 RAG 索引", r.status_code == 200)

r = req("post", "/rag/query", headers=H, json={"question": "矩阵乘法是什么"})
check("RAG 检索问答", r.status_code == 200, f"命中 {len(r.json().get('data', {}).get('results', r.json().get('data', {}).get('sources', [])))} 条")

r = req("get", "/rag/status", headers=H)
check("RAG 状态", r.status_code == 200, f"indexed={r.json().get('data', {}).get('total', r.json().get('data', {}).get('count', '?'))}")

# ── 汇总 ──
print(f"\n{'='*50}")
print(f"总计: ✅ {PASS} 通过, ❌ {FAIL} 失败")
print(f"{'='*50}")
sys.exit(1 if FAIL > 0 else 0)

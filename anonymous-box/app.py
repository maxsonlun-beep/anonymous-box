from flask import Flask, render_template, request, redirect, url_for, session, make_response
import json
import os
import urllib.request
import uuid

app = Flask(__name__)
app.secret_key = 'my_super_secret_key_pineapple'

DB_FILE = 'messages.json'

if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

def get_city_by_ip(ip):
    if ip in ('127.0.0.1', 'localhost', '::1'):
        return '本地测试'
    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == 'success':
                country = data.get('country', '')
                region = data.get('regionName', '')
                city = data.get('city', '')
                return f"{country} {region} {city}".strip()
    except Exception:
        pass
    return "未知城市"

@app.route('/', methods=['GET', 'POST'])
def index():
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    if request.method == 'POST':
        content = request.form.get('content')
        client_token = request.form.get('client_token') # 获取浏览器自带的标识
        
        if content and content.strip():
            if request.headers.get('CF-Connecting-IP'):
                ip = request.headers.get('CF-Connecting-IP')
            elif request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            else:
                ip = request.remote_addr

            location = get_city_by_ip(ip)
            
            # 如果客户端没有 token，帮她生成一个
            if not client_token:
                client_token = uuid.uuid4().hex[:12]

            # 检查数据库里是否已经有这个 token 的留言
            existing_msg = None
            for msg in messages:
                if msg.get('token') == client_token:
                    existing_msg = msg
                    break
            
            if existing_msg:
                # 如果她已经留过言了，这次提交视为“追加或更新留言内容”
                existing_msg['content'] = content.strip()
                existing_msg['ip'] = ip
                existing_msg['location'] = location
            else:
                # 全新留言
                new_msg = {
                    "id": len(messages) + 1,
                    "token": client_token,
                    "content": content.strip(),
                    "ip": ip,
                    "location": location,
                    "reply": ""
                }
                messages.insert(0, new_msg)

            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=4)
            
            # 渲染页面，把 token 带回给前端存入浏览器
            return render_template('index.html', my_msg=existing_msg or new_msg, just_sent=True, token=client_token)

    # 属于 GET 请求（打开网页或刷新）
    # 我们可以通过前端传过来的 cookie 或参数识别，这里在 index.html 里用前端 JS 自动结合后端同步
    return render_template('index.html', my_msg=None, just_sent=False, token="")

@app.route('/check_status', methods=['POST'])
def check_status():
    # 供前端 JS 异步查询自己有没有收到回复
    data = request.get_json() or {}
    token = data.get('token')
    if not token:
        return {"has_msg": False}
        
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        messages = json.load(f)
        
    for msg in messages:
        if msg.get('token') == token:
            return {
                "has_msg": True,
                "content": msg.get('content'),
                "reply": msg.get('reply', '')
            }
    return {"has_msg": False}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '123456':
            session['logged_in'] = True
            return redirect(url_for('admin'))
    return '''
    <body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#0f172a;font-family:sans-serif;">
    <div style="background:#1e293b;padding:35px;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,0.3);text-align:center;color:#f8fafc;width:320px;">
    <h3 style="margin-bottom:20px;font-size:20px;">🍍 菠萝世界后台</h3>
    <form method="post">
    <input type="password" name="password" placeholder="请输入管理密码" style="padding:12px;width:100%;border:1px solid #334155;border-radius:8px;background:#0f172a;color:white;box-sizing:border-box;outline:none;margin-bottom:15px;" required>
    <button type="submit" style="padding:12px;background:#6366f1;color:white;border:none;border-radius:8px;cursor:pointer;width:100%;font-weight:600;">安全登录</button>
    </form>
    </div>
    </body>
    '''

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        messages = json.load(f)
        
    if request.method == 'POST':
        msg_id = int(request.form.get('msg_id'))
        reply_content = request.form.get('reply', '').strip()
        for msg in messages:
            if msg.get('id') == msg_id:
                msg['reply'] = reply_content
                break
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
        return redirect(url_for('admin'))

    return render_template('admin.html', messages=messages)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

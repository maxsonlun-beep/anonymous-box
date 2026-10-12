from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import urllib.request
import uuid

app = Flask(__name__)
app.secret_key = 'my_secret_key_pineapple'

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

    new_token = ""
    if request.method == 'POST':
        content = request.form.get('content')
        if content and content.strip():
            if request.headers.get('CF-Connecting-IP'):
                ip = request.headers.get('CF-Connecting-IP')
            elif request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            else:
                ip = request.remote_addr

            location = get_city_by_ip(ip)
            
            # 每次发送都生成一个全新的独立 token
            token = uuid.uuid4().hex[:12]

            new_msg = {
                "id": len(messages) + 1,
                "token": token,
                "content": content.strip(),
                "ip": ip,
                "location": location,
                "reply": ""
            }
            messages.insert(0, new_msg)

            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=4)
            
            new_token = token

    return render_template('index.html', new_token=new_token)

@app.route('/check_history', methods=['POST'])
def check_history():
    data = request.get_json() or {}
    tokens = data.get('tokens', []) # 接收前端传过来的一组 token 列表
    if not tokens:
        return jsonify({"history": []})
        
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        messages = json.load(f)
        
    user_history = []
    for t in tokens:
        for msg in messages:
            if msg.get('token') == t:
                user_history.append({
                    "content": msg.get('content'),
                    "reply": msg.get('reply', '')
                })
                break
                
    return jsonify({"history": user_history})

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

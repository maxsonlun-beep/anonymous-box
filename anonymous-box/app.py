from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
import urllib.request

app = Flask(__name__)
app.secret_key = 'my_super_secret_key'

DB_FILE = 'messages.json'

if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

def get_city_by_ip(ip):
    # 如果是本地测试或者内网，直接返回本地
    if ip in ('127.0.0.1', 'localhost', '::1'):
        return '本地测试'
    try:
        # 使用免费的 ip-api 查询城市
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
    my_reply = None
    if request.method == 'POST':
        content = request.form.get('content')
        if content and content.strip():
            # 获取访问者的真实 IP
            if request.headers.get('CF-Connecting-IP'):
                ip = request.headers.get('CF-Connecting-IP')
            elif request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            else:
                ip = request.remote_addr

            location = get_city_by_ip(ip)

            with open(DB_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            new_msg = {
                "id": len(messages) + 1,
                "content": content.strip(),
                "ip": ip,
                "location": location,
                "reply": ""
            }
            messages.insert(0, new_msg)
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=4)
            
            return render_template('index.html', success=True, my_reply=None)
        return render_template('index.html', success=False, my_reply=None)
    
    return render_template('index.html', success=False, my_reply=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '123456':
            session['logged_in'] = True
            return redirect(url_for('admin'))
    return '''
    <body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5;font-family:sans-serif;">
    <div style="background:white;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);text-align:center;">
    <h3>🔐 请输入后台查看密码</h3>
    <form method="post">
    <input type="password" name="password" placeholder="默认密码123456" style="padding:10px;width:200px;border:1px solid #ddd;border-radius:6px;outline:none;" required>
    <button type="submit" style="padding:10px 18px;background:#6366f1;color:white;border:none;border-radius:6px;cursor:pointer;margin-left:5px;">登录</button>
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

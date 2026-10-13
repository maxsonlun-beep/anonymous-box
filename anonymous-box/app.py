from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import urllib.request
import uuid

app = Flask(__name__)
app.secret_key = 'pineapple_super_secure_secret_key_2026'

database_url = os.getenv('DATABASE_URL', 'sqlite:///pineapple.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(32), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(20), default='日常')
    is_public = db.Column(db.Boolean, default=True)  # 是否公开到广场
    ip = db.Column(db.String(50), default='未知')
    location = db.Column(db.String(100), default='未知城市')
    reply = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    db.create_all()

def get_city_by_ip(ip):
    if ip in ('127.0.0.1', 'localhost', '::1'):
        return '本地测试'
    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = __import__('json').loads(response.read().decode('utf-8'))
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
    new_token = ""
    if request.method == 'POST':
        content = request.form.get('content')
        tag = request.form.get('tag', '日常')
        is_public = True if request.form.get('is_public') == 'on' else False
        
        if content and content.strip():
            if request.headers.get('CF-Connecting-IP'):
                ip = request.headers.get('CF-Connecting-IP')
            elif request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            else:
                ip = request.remote_addr

            location = get_city_by_ip(ip)
            token = uuid.uuid4().hex[:12]

            new_msg = Message(
                token=token,
                content=content.strip(),
                tag=tag,
                is_public=is_public,
                ip=ip,
                location=location,
                reply=''
            )
            db.session.add(new_msg)
            db.session.commit()
            new_token = token

    # 获取所有公开的留言展示在广场上
    public_messages = Message.query.filter_by(is_public=True).order_by(Message.created_at.desc()).all()
    return render_template('index.html', new_token=new_token, public_messages=public_messages)

@app.route('/check_history', methods=['POST'])
def check_history():
    data = request.get_json() or {}
    tokens = data.get('tokens', [])
    if not tokens:
        return jsonify({"history": []})
        
    messages = Message.query.filter(Message.token.in_(tokens)).all()
    msg_map = {m.token: m for m in messages}
    
    user_history = []
    for t in tokens:
        if t in msg_map:
            m = msg_map[t]
            user_history.append({
                "content": m.content,
                "tag": m.tag,
                "reply": m.reply or '',
                "is_public": m.is_public
            })
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
    <h3 style="margin-bottom:20px;font-size:20px;">🍍 菠萝世界高配后台</h3>
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
        
    if request.method == 'POST':
        msg_id = int(request.form.get('msg_id'))
        reply_content = request.form.get('reply', '').strip()
        msg = Message.query.get(msg_id)
        if msg:
            msg.reply = reply_content
            db.session.commit()
        return redirect(url_for('admin'))

    # 后台可以看到所有的消息（无论是公开的还是私密的）
    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('admin.html', messages=messages)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

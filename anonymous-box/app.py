from flask import Flask, render_template, request, redirect, url_for, session
import json
import os

app = Flask(__name__)
app.secret_key = 'my_super_secret_key'

DB_FILE = 'messages.json'

if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        content = request.form.get('content')
        if content and content.strip():
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            # 每条留言分配一个唯一 ID 和空的回复
            new_msg = {
                "id": len(messages) + 1,
                "content": content.strip(),
                "reply": ""
            }
            messages.insert(0, new_msg)
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=4)
            return render_template('index.html', success=True)
        return render_template('index.html', success=False)
    
    # 首页展示所有留言及博主的回复
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        messages = json.load(f)
    return render_template('index.html', messages=messages, success=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '123456': # 你的后台密码
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

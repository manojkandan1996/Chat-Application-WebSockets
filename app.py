from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit
from models import db, User
from forms import RegisterForm, LoginForm
from config import Config
import redis
import json
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login = LoginManager(app)
login.login_view = 'login'

socketio = SocketIO(app, cors_allowed_origins="*", message_queue=app.config['REDIS_URL'])

redis_client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)

@login.user_loader
def load_user(uid):
    return User.query.get(int(uid))

with app.app_context():
    db.create_all()

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username taken.', 'warning')
        else:
            u = User(username=form.username.data)
            u.set_password(form.password.data)
            db.session.add(u); db.session.commit()
            flash('Account created!', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(username=form.username.data).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            return redirect(url_for('chat'))
        flash('Bad credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', username=current_user.username)

# send last N messages for room
def load_history(room, limit=50):
    key = f"history:{room}"
    msgs = redis_client.lrange(key, -limit, -1)
    return [json.loads(m) for m in msgs]

@socketio.on('join')
@login_required
def on_join(data):
    room = data['room']
    join_room(room)
    # notify others
    emit('system_message', {'msg': f"{current_user.username} has joined {room}"}, room=room)
    # send history to joining user
    history = load_history(room)
    emit('history', history)

@socketio.on('leave')
@login_required
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('system_message', {'msg': f"{current_user.username} has left {room}"}, room=room)

@socketio.on('message')
@login_required
def handle_message(data):
    room = data.get('room')
    text = data.get('msg')
    msg = {'username': current_user.username, 'msg': text}
    # store history
    key = f"history:{room}"
    redis_client.rpush(key, json.dumps(msg))
    redis_client.ltrim(key, -500, -1)  # keep last 500
    emit('message', msg, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)

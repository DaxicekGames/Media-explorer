import os
import json
import io
import zipfile
from waitress import serve
from flask import Flask, render_template, send_from_directory, abort, send_file, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageOps
import cv2
from datetime import datetime

# --- User config ---
PUBLIC_DIRECTORY = 'PUBLIC'
PRIVATE_DIRECTORY = 'PRIVATE'
THUMBNAIL_SIZE = (300, 300)
PAGE_TITLE = "Media explorer"
PORT = 5000


# --- Initilation ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///photobook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access the media."
login_manager.login_message_category = "info"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_PATH = os.path.join(BASE_DIR, PUBLIC_DIRECTORY)
PRIVATE_PATH = os.path.join(BASE_DIR, PRIVATE_DIRECTORY)

# --- Database ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    accesses = db.relationship('FolderAccess', backref='user', lazy=True, cascade="all, delete-orphan")
    group = db.Column(db.String(100), unique=False, nullable=False)

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def set_group(self, group): self.group = group
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class FolderAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

# --- Other functions ---
def is_media_file(filename):
    ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.mkv'}
    return os.path.splitext(filename)[1].lower() in ext

def is_video_file(filename):
    ext = {'.mp4', '.mov', '.mkv', '.webm'}
    return os.path.splitext(filename)[1].lower() in ext

def get_folder_structure(root_path, current_path, is_private=False):
    structure = []
    base_folder_for_relative_path = PRIVATE_PATH if is_private else PUBLIC_PATH
    try:
        for item in sorted(os.listdir(current_path)):
            full_item_path = os.path.join(current_path, item)
            relative_path_prefix = PRIVATE_DIRECTORY if is_private else ''
            relative_item_path = os.path.join(relative_path_prefix, os.path.relpath(full_item_path, base_folder_for_relative_path))
            
            if os.path.isdir(full_item_path):
                sub_folder_data = {'name': item, 'type': 'folder', 'path': relative_item_path, 'children': get_folder_structure(base_folder_for_relative_path, full_item_path, is_private)}
                if sub_folder_data['children']: structure.append(sub_folder_data)
            elif is_media_file(item) and (item[0] != '.' or "!see_hidden" in current_user.group.split(",")):
                mtime = os.path.getmtime(full_item_path)
                structure.append({'name': item, 'type': 'video' if is_video_file(item) else 'image', 'path': relative_item_path.replace('\\', '/'), 'metadata': {'created': datetime.fromtimestamp(mtime).strftime('%d. %m. %Y %H:%M')}})
    except FileNotFoundError: return []
    return structure

    
def get_bg_name() -> str:
    bg_name = current_user.group.split(",")[0]+'.png'
    bg_abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", bg_name)
    return bg_name if os.path.isfile(bg_abs_path) else ''

def get_timestamp() -> str:
    return datetime.now().strftime("%m/%d/%y %H:%M:%S")
def get_client_ip() -> str:
    ip_forwarded = (
    request.headers.get('X-Forwarded-For') or
    request.headers.get('X-Real-IP') or
    request.environ.get('REMOTE_ADDR'))

    if ip_forwarded:
        ip = ip_forwarded.split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip
def log(log_text, IP=True) -> None:
    log_date = f"[{get_timestamp()}]"
    log_ip = get_client_ip() if IP else "server"
    print(f"{log_date} {f'({log_ip})': <18}:", log_text)

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        log(f"    ✅ Login: {current_user.username}")
        return redirect(url_for('index'))
    if request.method == 'POST':
        # log(f"    ➡️ Login try: {request.form.get('username')}")
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user, remember=request.form.get('remember'))
            log(f"    ✅ User {request.form.get('username')} logged in!")
            return redirect(url_for('index'))
        log(f"    ⚠️ User {request.form.get('username')} failed to log in!")
        flash('Invalid username or password.', 'danger')
    else: log(f"    📝 Showing login page")
    return render_template('login.html', title=PAGE_TITLE, now_year=str(datetime.now().year))

@app.route('/logout')
@login_required
def logout():
    log(f"    ❌ User {current_user.username} logged out!")
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username, title=PAGE_TITLE, group=current_user.group.split(",")[0], bg_name=get_bg_name(), now_year=str(datetime.now().year))

# --- API and files ---
@app.route('/api/gallery-data')
@login_required
def gallery_data():
    os.makedirs(PUBLIC_PATH, exist_ok=True)
    os.makedirs(PRIVATE_PATH, exist_ok=True)
    final_structure = []
    
    # Public folders
    final_structure.extend(get_folder_structure(PUBLIC_PATH, PUBLIC_PATH, is_private=False))
            
    # Private folders
    user_accesses = [access.folder_name for access in current_user.accesses]
    for folder_name in sorted(user_accesses):
        full_path = os.path.join(PRIVATE_PATH, folder_name)
        if os.path.isdir(full_path):
            private_folder = {'name': folder_name, 'type': 'folder', 'path': os.path.join(PRIVATE_DIRECTORY, folder_name), 'children': get_folder_structure(PRIVATE_PATH, full_path, is_private=True)}
            if private_folder['children']: final_structure.append(private_folder)
    
    return json.dumps({"structure": final_structure})

def check_access(filepath):
    path_parts = filepath.replace('\\', '/').split('/')
    if path_parts[0] == PRIVATE_DIRECTORY:
        if len(path_parts) < 2: abort(403)
        folder_name = path_parts[1]
        user_accesses = [access.folder_name for access in current_user.accesses]
        if folder_name not in user_accesses: abort(403)

@app.route('/media/<path:filepath>')
@login_required
def serve_media(filepath):
    check_access(filepath)
    root_dir = PRIVATE_PATH if filepath.startswith(PRIVATE_DIRECTORY) else PUBLIC_PATH
    path_to_file = filepath[len(PRIVATE_DIRECTORY)+1:] if filepath.startswith(PRIVATE_DIRECTORY) else filepath
    log(f"🖼️ {current_user.username}: Loading {path_to_file}")
    return send_from_directory(root_dir, path_to_file)

@app.route('/thumbnail/<path:filepath>')
@login_required
def serve_thumbnail(filepath):
    check_access(filepath)
    root_dir = PRIVATE_PATH if filepath.startswith(PRIVATE_DIRECTORY) else PUBLIC_PATH
    path_to_file = filepath[len(PRIVATE_DIRECTORY)+1:] if filepath.startswith(PRIVATE_DIRECTORY) else filepath
    
    full_path = os.path.join(root_dir, path_to_file)
    if not os.path.exists(full_path): abort(404)
    img_io = io.BytesIO()
    try:
        if not is_video_file(filepath):
            with Image.open(full_path) as img:
                img = ImageOps.exif_transpose(img); img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                img = img.convert('RGB'); img.save(img_io, 'JPEG', quality=85)
        else:
            cap = cv2.VideoCapture(full_path); ret, frame = cap.read(); cap.release()
            if not ret: abort(500)
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS); img.save(img_io, 'JPEG', quality=85)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception: abort(500)

@app.route('/download/section/<path:folderpath>')
@login_required
def download_section(folderpath):
    check_access(folderpath)
    root_dir = PRIVATE_PATH if folderpath.startswith(PRIVATE_DIRECTORY) else PUBLIC_PATH
    path_to_folder = folderpath[len(PRIVATE_DIRECTORY)+1:] if folderpath.startswith(PRIVATE_DIRECTORY) else folderpath
    section_path = os.path.join(root_dir, path_to_folder)
    
    log(f"💾 {current_user.username}: Downloading {path_to_folder}")
    if not os.path.isdir(section_path): abort(404)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(section_path):
            for file in files:
                if is_media_file(file): zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), section_path))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{os.path.basename(folderpath)}.zip", as_attachment=True)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    # app.run(host='0.0.0.0', port=5000, debug=False)
    log(f"🚀 Starting server at port {PORT}...", IP=False)
    serve(app, host='0.0.0.0', port=PORT, threads=16)

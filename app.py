# filepath: d:\Kuliah\Tugas Akhir\Kode Program\Latest\app.py
# app.py - Reorganized structure

# ===================================================
# 1. IMPORTS AND CONFIGURATION
# ===================================================
from flask import (Flask, render_template, Response, request, jsonify, 
                  send_file, g, session, redirect, url_for, flash)
import cv2
from ultralytics import YOLO
import sqlite3
from datetime import datetime, timedelta, timedelta
import pandas as pd
import threading
import time
import hashlib
import cv2
import calendar
import argparse
import socket
import os
import zipfile
import shutil
from werkzeug.utils import secure_filename
import tempfile
from fine_tuning_manager import fine_tuning_manager

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Untuk session admin 

# Konfigurasi upload
UPLOAD_FOLDER = 'uploads'
TRAINING_DATA_FOLDER = 'training_data'
ALLOWED_EXTENSIONS = {'zip', 'jpg', 'jpeg', 'png', 'bmp', 'tiff'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB maksimum
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Pastikan folder upload ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRAINING_DATA_FOLDER, exist_ok=True) 

# Load model YOLOv8
model = YOLO('best.pt')

# Variabel global untuk menyimpan nama yang terdeteksi dan waktu terakhir deteksi
detected_name = None
last_detection_time = 0

# Global cache untuk absensi hari ini (untuk menghindari input duplikat)
absen_hari_ini = set()
absen_cache_lock = threading.Lock()

DATABASE = 'absensi.db'


# ===================================================
# 2. DATABASE FUNCTIONS
# ===================================================
def get_db():
    """Create or return existing database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection when app context ends"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables and default values"""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabel absensi: satu baris per guru per hari dengan status tambahan
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS absensi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        arrival_time DATETIME,
        departure_time DATETIME,
        date DATE NOT NULL,
        status_kedatangan TEXT DEFAULT 'Belum Datang',
        status_keberadaan TEXT DEFAULT 'Tidak Ada',
        lama_kerja INTEGER DEFAULT 0,
        status_feedback TEXT DEFAULT NULL
    )
    """)
    
    # Tabel jadwal_bulanan: menyimpan jadwal per tanggal dalam bulan
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jadwal_bulanan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tahun INTEGER NOT NULL,
        bulan INTEGER NOT NULL,
        tanggal INTEGER NOT NULL,
        start_arrival TIME NOT NULL DEFAULT '06:00:00',
        late_arrival TIME NOT NULL DEFAULT '07:00:00',
        departure_time TIME NOT NULL DEFAULT '15:00:00',
        is_holiday BOOLEAN DEFAULT FALSE,
        keterangan TEXT DEFAULT NULL,
        UNIQUE(tahun, bulan, tanggal)
    )
    """)
    
    # Tabel jadwal lama (untuk backward compatibility)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jadwal (
        hari TEXT PRIMARY KEY,
        start_arrival TIME,
        late_arrival TIME,
        departure_time TIME
    )
    """)
    
    # Tabel admin_settings: menyimpan pengaturan admin termasuk password
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_name TEXT UNIQUE NOT NULL,
        setting_value TEXT NOT NULL,
        updated_at DATETIME
    )
    """)
    
    # Tabel master_guru: menyimpan daftar lengkap semua guru
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_guru (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT UNIQUE NOT NULL,
        kelas TEXT,
        status TEXT DEFAULT 'Aktif',
        no_induk TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabel model_training: menyimpan informasi training model dan class mapping
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_training (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        model_path TEXT NOT NULL,
        dataset_path TEXT,
        training_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT FALSE,
        accuracy FLOAT DEFAULT NULL,
        total_classes INTEGER DEFAULT 0,
        description TEXT,
        created_by TEXT DEFAULT 'admin'
    )
    """)
    
    # Tabel class_mapping: mapping antara class_id dalam model dengan guru
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS class_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        guru_id INTEGER NOT NULL,
        class_name TEXT NOT NULL,
        confidence_threshold FLOAT DEFAULT 0.7,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (model_id) REFERENCES model_training (id),
        FOREIGN KEY (guru_id) REFERENCES master_guru (id),
        UNIQUE(model_id, class_id)
    )
    """)
    
    # Tabel training_dataset: track dataset yang digunakan untuk training
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_dataset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_path TEXT NOT NULL,
        dataset_name TEXT NOT NULL,
        guru_id INTEGER,
        images_count INTEGER DEFAULT 0,
        labels_count INTEGER DEFAULT 0,
        upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_used_for_training BOOLEAN DEFAULT FALSE,
        training_model_id INTEGER,
        FOREIGN KEY (guru_id) REFERENCES master_guru (id),
        FOREIGN KEY (training_model_id) REFERENCES model_training (id)
    )
    """)
    
    # Masukkan data default jadwal harian jika belum ada (untuk backward compatibility)
    default_days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    for day in default_days:
        cursor.execute("SELECT 1 FROM jadwal WHERE hari = ?", (day,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO jadwal (hari, start_arrival, late_arrival, departure_time) VALUES (?, ?, ?, ?)",
                           (day, "06:00:00", "07:00:00", "15:00:00"))
    
    # Update kolom absensi yang sudah ada untuk kompatibilitas
    try:
        cursor.execute("ALTER TABLE absensi ADD COLUMN status_kedatangan TEXT DEFAULT 'Belum Datang'")
    except sqlite3.OperationalError:
        pass  # Kolom sudah ada
    
    try:
        cursor.execute("ALTER TABLE absensi ADD COLUMN status_keberadaan TEXT DEFAULT 'Tidak Ada'")
    except sqlite3.OperationalError:
        pass  # Kolom sudah ada
        
    try:
        cursor.execute("ALTER TABLE absensi ADD COLUMN lama_kerja INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Kolom sudah ada
        
    try:
        cursor.execute("ALTER TABLE absensi ADD COLUMN status_feedback TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Kolom sudah ada
    
    # Cek apakah admin password sudah ada, jika belum maka set default
    cursor.execute("SELECT 1 FROM admin_settings WHERE setting_name = ?", ('admin_password',))
    if not cursor.fetchone():
        # Set password default (admin)
        default_password = 'admin'
        # Gunakan SHA-256 untuk hash password
        hashed_password = hashlib.sha256(default_password.encode()).hexdigest()
        
        # Simpan password yang sudah di-hash
        now = datetime.now()
        cursor.execute(
            "INSERT INTO admin_settings (setting_name, setting_value, updated_at) VALUES (?, ?, ?)",
            ('admin_password', hashed_password, now)
        )
        print("Password admin default telah dibuat.")
    
    conn.commit()
    conn.close()

# Initialize database
init_db()


# 3. AUTHENTICATION HELPERS
# ===================================================
def verify_admin_password(password):
    """Verifikasi password admin dari database"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute("SELECT setting_value FROM admin_settings WHERE setting_name = ?", ('admin_password',))
        result = cursor.fetchone()
        
        if result:
            stored_hash = result['setting_value']
            # Hash password input dan bandingkan
            input_hash = hashlib.sha256(password.encode()).hexdigest()
            return input_hash == stored_hash
        else:
            # Fallback ke password hardcoded jika tidak ada di database
            return password == 'admin'
    except:
        # Fallback ke password hardcoded jika ada error
        return password == 'admin'


# ===================================================
# 4. HELPER FUNCTIONS
# ===================================================

def format_datetime_for_display(dt):
    """Format datetime untuk display di template"""
    if not dt:
        return "-"
    
    try:
        if isinstance(dt, str):
            # Parse string datetime
            try:
                dt = datetime.fromisoformat(dt)
            except:
                # Jika format lama HH:MM:SS
                if len(dt) <= 8:
                    return dt  # Return as is
                return dt
        
        return dt.strftime("%H:%M:%S")
    except:
        return str(dt) if dt else "-"

def format_date_for_display(dt):
    """Format date untuk display di template"""
    if not dt:
        return "-"
    
    try:
        if isinstance(dt, str):
            dt = datetime.strptime(dt, '%Y-%m-%d').date()
        elif isinstance(dt, datetime):
            dt = dt.date()
        
        return dt.strftime("%d/%m/%Y")
    except:
        return str(dt) if dt else "-"

# Register template filters
@app.template_filter('datetime_format')
def datetime_format_filter(dt):
    return format_datetime_for_display(dt)

@app.template_filter('date_format')
def date_format_filter(dt):
    return format_date_for_display(dt)

@app.template_filter('time_only')
def time_only_filter(dt):
    """Extract time only from datetime"""
    if not dt:
        return "-"
    
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return dt.strftime("%H:%M")
    except:
        return str(dt) if dt else "-"

def get_day_name():
    """Mengembalikan nama hari (Senin s.d. Minggu) berdasarkan hari saat ini."""
    mapping = {
        0: "Senin",
        1: "Selasa",
        2: "Rabu",
        3: "Kamis",
        4: "Jumat",
        5: "Sabtu",
        6: "Minggu"
    }
    return mapping[datetime.now().weekday()]

def get_schedule_for_today(cursor):
    """Mengembalikan jadwal absensi untuk hari ini dalam bentuk dictionary."""
    today = datetime.now()
    year, month, day = today.year, today.month, today.day
    
    # Coba ambil dari jadwal bulanan dulu
    cursor.execute("""
        SELECT start_arrival, late_arrival, departure_time, is_holiday 
        FROM jadwal_bulanan 
        WHERE tahun = ? AND bulan = ? AND tanggal = ?
    """, (year, month, day))
    row = cursor.fetchone()
    
    if row:
        return {
            "start_arrival": row[0], 
            "late_arrival": row[1], 
            "departure_time": row[2],
            "is_holiday": bool(row[3])
        }
    
    # Fallback ke jadwal harian lama
    hari = get_day_name()
    cursor.execute("SELECT start_arrival, late_arrival, departure_time FROM jadwal WHERE hari = ?", (hari,))
    row = cursor.fetchone()
    if row:
        return {
            "start_arrival": row[0], 
            "late_arrival": row[1], 
            "departure_time": row[2],
            "is_holiday": False
        }
    return None

def get_monthly_schedule(cursor, year, month):
    """Ambil jadwal untuk bulan tertentu"""
    cursor.execute("""
        SELECT tanggal, start_arrival, late_arrival, departure_time, is_holiday, keterangan
        FROM jadwal_bulanan 
        WHERE tahun = ? AND bulan = ?
        ORDER BY tanggal
    """, (year, month))
    return cursor.fetchall()

def save_monthly_schedule(cursor, year, month, schedule_data):
    """Simpan jadwal bulanan"""
    for tanggal, data in schedule_data.items():
        cursor.execute("""
            INSERT OR REPLACE INTO jadwal_bulanan 
            (tahun, bulan, tanggal, start_arrival, late_arrival, departure_time, is_holiday, keterangan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            year, month, tanggal,
            data.get('start_arrival', '06:00:00'),
            data.get('late_arrival', '07:00:00'), 
            data.get('departure_time', '15:00:00'),
            data.get('is_holiday', False),
            data.get('keterangan', None)
        ))

def calculate_work_duration(arrival_time, departure_time):
    """Hitung durasi kerja dalam menit"""
    if not arrival_time or not departure_time:
        return 0
    
    try:
        # Jika input adalah string, parse ke datetime
        if isinstance(arrival_time, str):
            # Jika format HH:MM:SS, tambahkan tanggal hari ini
            if len(arrival_time) <= 8:  # Format HH:MM:SS atau HH:MM
                today = datetime.now().date()
                arrival_time = datetime.combine(today, datetime.strptime(arrival_time, '%H:%M:%S').time())
            else:
                arrival_time = datetime.fromisoformat(arrival_time)
        
        if isinstance(departure_time, str):
            if len(departure_time) <= 8:  # Format HH:MM:SS atau HH:MM
                today = datetime.now().date()
                departure_time = datetime.combine(today, datetime.strptime(departure_time, '%H:%M:%S').time())
            else:
                departure_time = datetime.fromisoformat(departure_time)
        
        # Hitung selisih dalam menit
        duration = (departure_time - arrival_time).total_seconds() / 60
        return int(duration)
    except Exception as e:
        print(f"Error calculating work duration: {e}")
        return 0

def get_feedback_status(arrival_time, departure_time, schedule):
    """Tentukan status feedback berdasarkan waktu kerja"""
    if not arrival_time or not departure_time or not schedule:
        return None
    
    work_duration = calculate_work_duration(arrival_time, departure_time)
    
    # Hitung durasi kerja normal (dalam menit)
    try:
        # Handle berbagai format time
        if isinstance(schedule['start_arrival'], str):
            start_time = datetime.strptime(schedule['start_arrival'], '%H:%M:%S').time()
        else:
            start_time = schedule['start_arrival']
            
        if isinstance(schedule['departure_time'], str):
            end_time = datetime.strptime(schedule['departure_time'], '%H:%M:%S').time()
        else:
            end_time = schedule['departure_time']
        
        # Hitung durasi normal
        start_datetime = datetime.combine(datetime.today(), start_time)
        end_datetime = datetime.combine(datetime.today(), end_time)
        normal_duration = (end_datetime - start_datetime).total_seconds() / 60
        
        # Parse departure time untuk perbandingan
        if isinstance(departure_time, str):
            if len(departure_time) <= 8:  # Format HH:MM:SS
                departure_actual = datetime.strptime(departure_time, '%H:%M:%S').time()
            else:
                departure_actual = datetime.fromisoformat(departure_time).time()
        elif isinstance(departure_time, datetime):
            departure_actual = departure_time.time()
        else:
            departure_actual = departure_time
        
        if departure_actual < end_time:
            return "Pulang Cepat"
        elif work_duration < normal_duration * 0.8:  # Kurang dari 80% jam kerja normal
            return "Durasi Kerja Kurang"
        elif work_duration > normal_duration * 1.2:  # Lebih dari 120% jam kerja normal
            return "Lembur"
        else:
            return "Normal"
    except Exception as e:
        print(f"Error in get_feedback_status: {e}")
        return None


def generate_frames():
    """Generates video frames with face detection and attendance logging"""
    global detected_name, last_detection_time, absen_hari_ini
    local_db = sqlite3.connect(DATABASE, check_same_thread=False)
    local_db.row_factory = sqlite3.Row
    local_cursor = local_db.cursor()
    
    # Load class mapping untuk model aktif
    local_cursor.execute("""
        SELECT cm.class_id, cm.guru_id, cm.class_name, cm.confidence_threshold, mg.nama
        FROM class_mapping cm
        JOIN model_training mt ON cm.model_id = mt.id
        JOIN master_guru mg ON cm.guru_id = mg.id
        WHERE mt.is_active = 1 AND mg.status = 'Aktif'
    """)
    class_mappings = {row['class_id']: {
        'guru_id': row['guru_id'],
        'guru_name': row['nama'],
        'threshold': row['confidence_threshold']
    } for row in local_cursor.fetchall()}
    
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break

        results = model(frame, conf=0.85)
        detected_name_in_frame = None
        for r in results:
            boxes = r.boxes
            if len(boxes) > 0:
                for box in boxes:
                    b = box.xyxy[0]
                    c = int(box.cls.item())
                    conf = float(box.conf.item())
                    cv2.rectangle(frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (255, 0, 0), 2)
                    
                    # Gunakan class mapping jika tersedia
                    if c in class_mappings:
                        mapping = class_mappings[c]
                        if conf >= mapping['threshold']:  # Cek threshold confidence
                            detected_name_in_frame = mapping['guru_name']
                            label = f"{detected_name_in_frame}: {conf:.2f}"
                            cv2.putText(frame, label, (int(b[0]), int(b[1])-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        else:
                            # Confidence terlalu rendah
                            label = f"Unknown: {conf:.2f}"
                            cv2.putText(frame, label, (int(b[0]), int(b[1])-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    elif c < len(r.names):
                        # Fallback ke nama default jika tidak ada mapping
                        detected_name_in_frame = r.names[c]
                        label = f"{detected_name_in_frame}: {conf:.2f}"
                        cv2.putText(frame, label, (int(b[0]), int(b[1])-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                        
        if detected_name_in_frame:
            today_date = datetime.now().strftime('%Y-%m-%d')
            current_time_str = datetime.now().strftime('%H:%M:%S')  # Hanya waktu
            current_hms = datetime.now().strftime('%H:%M:%S')
            
            with absen_cache_lock:
                schedule = get_schedule_for_today(local_cursor)
                
                # Cek apakah hari ini libur
                if schedule and bool(schedule.get('is_holiday', False)):
                    holiday_msg = "Tidak dapat melakukan absensi - hari libur"
                    if schedule.get('keterangan'):
                        holiday_msg += f" ({schedule.get('keterangan')})"
                    print(f"HOLIDAY: {holiday_msg} untuk: {detected_name_in_frame}")
                    continue
                
                local_cursor.execute("SELECT arrival_time, departure_time FROM absensi WHERE nama = ? AND date = ?",
                                     (detected_name_in_frame, today_date))
                row = local_cursor.fetchone()
                if not row:
                    # Validasi waktu mulai
                    if current_hms < schedule['start_arrival']:
                        print(f"Belum waktunya absensi untuk: {detected_name_in_frame}. Mulai {schedule['start_arrival']}")
                    else:
                        # Tentukan status kedatangan
                        status_kedatangan = "Tepat Waktu" if current_hms < schedule['late_arrival'] else "Terlambat"
                        
                        # Catat record absensi dengan status lengkap
                        local_cursor.execute("""
                            INSERT INTO absensi (nama, arrival_time, date, status_kedatangan, status_keberadaan) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (detected_name_in_frame, current_time_str, today_date, status_kedatangan, "Sudah Ada"))
                        local_db.commit()
                        absen_hari_ini.add(detected_name_in_frame)
                        print(f"Absensi kedatangan berhasil untuk: {detected_name_in_frame} ({status_kedatangan})")
                else:
                    # Jika record sudah ada dan departure_time belum diisi, update jika sudah mencapai waktu pulang
                    if row['departure_time'] is None or row['departure_time'] == "":
                        if schedule is not None:
                            current_hms = datetime.now().strftime('%H:%M:%S')
                            if current_hms >= schedule['departure_time']:
                                # Hitung lama kerja
                                lama_kerja = calculate_work_duration(row['arrival_time'], current_time_str)
                                
                                # Tentukan status feedback
                                status_feedback = get_feedback_status(row['arrival_time'], current_time_str, schedule)
                                
                                local_cursor.execute("""
                                    UPDATE absensi 
                                    SET departure_time = ?, lama_kerja = ?, status_feedback = ?, status_keberadaan = ?
                                    WHERE nama = ? AND date = ?
                                """, (current_time_str, lama_kerja, status_feedback, "Tidak Ada", detected_name_in_frame, today_date))
                                local_db.commit()
                                print(f"Absensi pulang berhasil untuk: {detected_name_in_frame} (Lama kerja: {lama_kerja} menit)")
            detected_name = detected_name_in_frame
            last_detection_time = time.time()
        else:
            if time.time() - last_detection_time > 5:
                detected_name = None
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ===================================================
# 5. ROUTE HANDLERS - MAIN PAGES
# ===================================================
@app.route('/')
def index():
    # Tambahkan variabel untuk status autentikasi
    is_authenticated = session.get('authenticated', False)
    
    # Kode yang sudah ada untuk detected_name, dll
    detected_name = None
    absen_status = "Siap untuk absen"
    
    # Cek apakah hari ini adalah hari libur
    db = get_db()
    cursor = db.cursor()
    schedule = get_schedule_for_today(cursor)
    is_holiday = schedule and schedule.get('is_holiday', False)
    
    # Ambil keterangan libur jika ada
    holiday_message = None
    if is_holiday:
        today = datetime.now()
        cursor.execute("""
            SELECT keterangan FROM jadwal_bulanan 
            WHERE tahun = ? AND bulan = ? AND tanggal = ? AND is_holiday = 1
        """, (today.year, today.month, today.day))
        row = cursor.fetchone()
        if row and row[0]:
            holiday_message = row[0]
        else:
            # Default message untuk hari minggu
            if today.weekday() == 6:  # Sunday
                holiday_message = "Hari Minggu"
    
    return render_template('index.html', 
                          detected_name=detected_name, 
                          absen_status=absen_status,
                          authenticated=is_authenticated,
                          is_holiday=is_holiday,
                          holiday_message=holiday_message)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_detected_name', methods=['GET'])
def get_detected_name():
    global detected_name
    today_date = datetime.now().strftime('%Y-%m-%d')
    db = get_db()
    cursor = db.cursor()
    absen_status = False
    if detected_name:
        cursor.execute("SELECT 1 FROM absensi WHERE nama = ? AND date = ?", (detected_name, today_date))
        absen_status = cursor.fetchone() is not None
    return jsonify({
        "detected_name": detected_name or "",
        "absen_status": absen_status
    })

@app.route('/absen_manual', methods=['POST'])
def absen_manual():
    data = request.get_json()
    nama = data.get('nama')
    if nama:
        try:
            today_date = datetime.now().strftime('%Y-%m-%d')
            current_time_str = datetime.now().strftime('%H:%M:%S')  # Hanya waktu
            current_hms = datetime.now().strftime('%H:%M:%S')
            db = get_db()
            cursor = db.cursor()
            schedule = get_schedule_for_today(cursor)
            
            print(f"DEBUG: Processing absen_manual for {nama} at {current_time_str}")
            print(f"DEBUG: Schedule: {schedule}")
            
            if schedule and bool(schedule.get('is_holiday', False)):
                print(f"DEBUG: Holiday detected")
                holiday_message = "Tidak dapat melakukan absensi karena hari ini adalah hari libur"
                if schedule.get('keterangan'):
                    holiday_message += f" ({schedule.get('keterangan')})"
                return jsonify({
                    "message": holiday_message,
                    "is_holiday": True,
                    "status": "holiday"
                })
            
            cursor.execute("SELECT arrival_time, departure_time FROM absensi WHERE nama = ? AND date = ?", (nama, today_date))
            row = cursor.fetchone()
            print(f"DEBUG: Existing record: {row}")
            
            if not row:
                # Validasi waktu mulai
                if current_hms < schedule['start_arrival']:
                    # Format waktu jadi HH:MM untuk tampilan yang lebih baik
                    formatted_time = schedule['start_arrival'][:5]
                    print(f"DEBUG: Too early for attendance")
                    return jsonify({"message": f"Belum waktunya absensi. Absensi dimulai pukul {formatted_time}"})
                
                # Tentukan status kedatangan
                status_kedatangan = "Tepat Waktu" if current_hms < schedule['late_arrival'] else "Terlambat"
                print(f"DEBUG: Inserting new record with status: {status_kedatangan}")
                
                cursor.execute("""
                    INSERT INTO absensi (nama, arrival_time, date, status_kedatangan, status_keberadaan) 
                    VALUES (?, ?, ?, ?, ?)
                """, (nama, current_time_str, today_date, status_kedatangan, "Sudah Ada"))
                
                affected_rows = cursor.rowcount
                print(f"DEBUG: Insert affected rows: {affected_rows}")
                
                db.commit()
                print(f"DEBUG: Database committed")
                
                with absen_cache_lock:
                    absen_hari_ini.add(nama)
                
                message = f"Absensi kedatangan berhasil untuk: {nama} ({status_kedatangan})"
                print(f"DEBUG: Success message: {message}")
                
            else:
                print(f"DEBUG: Record exists, checking departure")
                if row['departure_time'] is None or row['departure_time'] == "":
                    if current_hms >= schedule['departure_time']:
                        # Hitung lama kerja
                        lama_kerja = calculate_work_duration(row['arrival_time'], current_time_str)
                        
                        # Tentukan status feedback
                        status_feedback = get_feedback_status(row['arrival_time'], current_time_str, schedule)
                        
                        print(f"DEBUG: Updating departure with lama_kerja: {lama_kerja}")
                        
                        cursor.execute("""
                            UPDATE absensi 
                            SET departure_time = ?, lama_kerja = ?, status_feedback = ?, status_keberadaan = ?
                            WHERE nama = ? AND date = ?
                        """, (current_time_str, lama_kerja, status_feedback, "Tidak Ada", nama, today_date))
                        
                        affected_rows = cursor.rowcount
                        print(f"DEBUG: Update affected rows: {affected_rows}")
                        
                        db.commit()
                        print(f"DEBUG: Database committed for departure")
                        
                        message = f"Absensi pulang berhasil untuk: {nama} (Lama kerja: {lama_kerja} menit)"
                    else:
                        message = "Belum mencapai waktu pulang."
                        print(f"DEBUG: Too early for departure: {current_hms} < {schedule['departure_time']}")
                else:
                    message = f"{nama} sudah melakukan absensi hari ini."
                    print(f"DEBUG: Already completed attendance")
            
            print(f"DEBUG: Final message: {message}")
            return jsonify({"message": message})
            
        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"message": f"Error: {str(e)}"})
    
    return jsonify({"message": "Data tidak ditemukan."})

# Tampilkan daftar absensi sederhana (tanpa autentikasi)
@app.route('/simple_absensi')
def simple_absensi():
    today_date = datetime.now().strftime('%Y-%m-%d')
    db = get_db()
    cursor = db.cursor()
    
    query = """
    SELECT nama, arrival_time, departure_time, status_kedatangan, 
           status_keberadaan, lama_kerja, status_feedback
    FROM absensi
    WHERE date = ?
    ORDER BY arrival_time
    """
    cursor.execute(query, (today_date,))
    data_absensi = cursor.fetchall()
    
    return render_template('simple_absensi.html', 
                           data_absensi=data_absensi, 
                           today_date=today_date)


# ===================================================
# 6. ROUTE HANDLERS - ADMIN PAGES
# ===================================================
@app.route('/lihat_absensi')
def lihat_absensi():
    # Cek autentikasi
    if not session.get('authenticated'):
        return redirect(url_for('set_schedule'))
        
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    db = get_db()
    cursor = db.cursor()
    if start_date and end_date:
        query = """
        SELECT id, row_number() OVER (PARTITION BY date ORDER BY arrival_time) AS daily_id,
               nama, arrival_time, departure_time, date, status_kedatangan, 
               status_keberadaan, lama_kerja, status_feedback
        FROM absensi
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, daily_id ASC
        """
        cursor.execute(query, (start_date, end_date))
    else:
        query = """ 
        SELECT id, row_number() OVER (PARTITION BY date ORDER BY arrival_time) AS daily_id,
               nama, arrival_time, departure_time, date, status_kedatangan,
               status_keberadaan, lama_kerja, status_feedback
        FROM absensi
        ORDER BY date DESC, daily_id ASC
        """
        cursor.execute(query)
    data_absensi = cursor.fetchall()
    return render_template('lihat_absensi.html', data_absensi=data_absensi, start_date=start_date or '', end_date=end_date or '')

@app.route('/jadwal_bulanan', methods=['GET', 'POST'])
def jadwal_bulanan():
    # Cek autentikasi
    if not session.get('authenticated'):
        return redirect(url_for('set_schedule'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Ambil parameter tahun dan bulan, default ke bulan ini
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Handle POST request untuk pengaturan jadwal umum
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_general_schedule':
            # Update jadwal umum (harian)
            days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']  # Minggu tidak disertakan karena otomatis libur
            
            try:
                for day in days:
                    start_arrival = request.form.get(f"start_arrival_{day}")
                    late_arrival = request.form.get(f"late_arrival_{day}")
                    departure_time = request.form.get(f"departure_time_{day}")
                    
                    # Validasi format waktu
                    if not all([start_arrival, late_arrival, departure_time]):
                        message = f"Harap isi semua waktu untuk hari {day}!"
                        break
                    
                    # Validasi logika waktu
                    if start_arrival >= late_arrival:
                        message = f"Jam mulai absensi harus lebih awal dari batas terlambat untuk hari {day}!"
                        break
                    
                    if late_arrival >= departure_time:
                        message = f"Batas terlambat harus lebih awal dari jam pulang untuk hari {day}!"
                        break
                    
                    cursor.execute("""
                        UPDATE jadwal 
                        SET start_arrival = ?, late_arrival = ?, departure_time = ? 
                        WHERE hari = ?
                    """, (start_arrival, late_arrival, departure_time, day))
                else:
                    # Jika loop berhasil tanpa break
                    db.commit()
                    message = "Jadwal umum berhasil diperbarui!"
            except Exception as e:
                message = f"Terjadi kesalahan saat memperbarui jadwal umum: {str(e)}"
        else:
            message = None
    else:
        message = request.args.get('message')
    
    # Set default minggu sebagai libur untuk bulan ini
    set_default_sunday_holiday(cursor, year, month)
    db.commit()
    
    # Ambil jadwal untuk bulan tersebut
    monthly_schedule = get_monthly_schedule(cursor, year, month)
    
    # Convert ke dictionary untuk mudah diakses di template
    schedule_dict = {}
    for row in monthly_schedule:
        schedule_dict[row[0]] = {
            'start_arrival': row[1],
            'late_arrival': row[2], 
            'departure_time': row[3],
            'is_holiday': row[4],
            'keterangan': row[5]
        }
    
    # Ambil jadwal umum untuk form pengaturan
    cursor.execute("SELECT * FROM jadwal ORDER BY CASE hari WHEN 'Senin' THEN 1 WHEN 'Selasa' THEN 2 WHEN 'Rabu' THEN 3 WHEN 'Kamis' THEN 4 WHEN 'Jumat' THEN 5 WHEN 'Sabtu' THEN 6 WHEN 'Minggu' THEN 7 END")
    jadwal_umum = cursor.fetchall()
    
    # Buat data calendar
    import calendar
    cal = calendar.monthcalendar(year, month)
    
    # Nama bulan dalam bahasa Indonesia
    month_names = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    
    return render_template('jadwal_bulanan.html', 
                          calendar_data=cal,
                          year=year, 
                          month=month,
                          month_name=month_names[month],
                          schedule_dict=schedule_dict,
                          jadwal_umum=jadwal_umum,
                          message=message)

@app.route('/simpan_jadwal_bulanan', methods=['POST'])
def simpan_jadwal_bulanan():
    # Cek autentikasi
    if not session.get('authenticated'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Cek apakah request dalam format form data atau JSON
        if request.is_json:
            data = request.get_json()
            year = data.get('year')
            month = data.get('month')
            schedule_data = data.get('schedule_data', {})
        else:
            # Form data untuk single day update
            year = request.form.get('year', type=int)
            month = request.form.get('month', type=int)
            day = request.form.get('day', type=int)
            
            # Handle special actions
            action = request.form.get('action')
            if action == 'apply_to_all':
                # Apply default schedule to all days in month
                import calendar
                num_days = calendar.monthrange(year, month)[1]
                schedule_data = {}
                
                for d in range(1, num_days + 1):
                    schedule_data[d] = {
                        'start_arrival': '06:00:00',
                        'late_arrival': '07:00:00',
                        'departure_time': '15:00:00',
                        'is_holiday': False,
                        'keterangan': None
                    }
            else:
                # Single day update
                is_holiday = request.form.get('is_holiday') == 'true'
                start_arrival = request.form.get('start_arrival', '06:00') + ':00'
                late_arrival = request.form.get('late_arrival', '07:00') + ':00'
                departure_time = request.form.get('departure_time', '15:00') + ':00'
                keterangan = request.form.get('keterangan', '')
                
                schedule_data = {
                    day: {
                        'start_arrival': start_arrival,
                        'late_arrival': late_arrival,
                        'departure_time': departure_time,
                        'is_holiday': is_holiday,
                        'keterangan': keterangan if keterangan else None
                    }
                }
        
        db = get_db()
        cursor = db.cursor()
        
        save_monthly_schedule(cursor, year, month, schedule_data)
        db.commit()
        
        return jsonify({"success": True, "message": "Jadwal bulanan berhasil disimpan"})
        
    except Exception as e:
        print(f"Error saving monthly schedule: {str(e)}")
        return jsonify({"success": False, "message": f"Gagal menyimpan jadwal: {str(e)}"}), 500

@app.route('/set_schedule', methods=['GET', 'POST'])
def set_schedule():
    if request.method == 'POST':
        # Handle login authentication
        password = request.form.get('password')
        if password and verify_admin_password(password):
            session['authenticated'] = True
            return redirect(url_for('jadwal_bulanan'))
        else:
            # Render login page with error
            return render_template('admin_login.html', error="Password salah!")
    
    # Check if already authenticated
    if session.get('authenticated'):
        return redirect(url_for('jadwal_bulanan'))
    
    # Show login form
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    # Redirect to set_schedule for consistency
    return redirect(url_for('set_schedule'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    # Cek autentikasi
    if not session.get('authenticated'):
        return redirect(url_for('set_schedule'))
        
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validasi input
        if not current_password or not new_password or not confirm_password:
            return render_template('change_password.html', message="Semua field harus diisi", success=False)
            
        if new_password != confirm_password:
            return render_template('change_password.html', message="Password baru tidak cocok dengan konfirmasi", success=False)
            
        # Verifikasi password lama
        if not verify_admin_password(current_password):
            return render_template('change_password.html', message="Password saat ini salah", success=False)
            
        try:
            # Hash password baru
            new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # Update password di database
            db = get_db()
            cursor = db.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "UPDATE admin_settings SET setting_value = ?, updated_at = ? WHERE setting_name = 'admin_password'",
                (new_password_hash, now)
            )
            db.commit()
            
            return render_template('change_password.html', message="Password berhasil diubah!", success=True)
        except Exception as e:
            return render_template('change_password.html', message=f"Gagal mengubah password: {str(e)}", success=False)
    
    return render_template('change_password.html')

@app.route('/atur_jadwal', methods=['GET', 'POST'])
def atur_jadwal():
    # Redirect ke jadwal_bulanan
    return redirect(url_for('jadwal_bulanan'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('authenticated', None)
    return redirect(url_for('index'))


# ===================================================
# 7. ROUTE HANDLERS - DATA MANAGEMENT
# ===================================================
@app.route('/export_excel/<date_range>', methods=['GET'])
def export_excel(date_range):
    # Cek autentikasi
    if not session.get('authenticated'):
        return redirect(url_for('set_schedule'))
    
    start_date, end_date = date_range.split('_')
    
    # Ambil nama file dari parameter query jika ada
    custom_filename = request.args.get('filename', '')
    
    # Format tanggal untuk nama file yang lebih deskriptif
    def format_tanggal_indonesia(date_str):
        # Konversi YYYY-MM-DD ke format DD Bulan YYYY
        bulan_indonesia = {
            '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
            '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
            '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
        }
        year, month, day = date_str.split('-')
        return f"{day} {bulan_indonesia[month]} {year}"
    
    start_date_indo = format_tanggal_indonesia(start_date)
    end_date_indo = format_tanggal_indonesia(end_date)
    
    db = get_db()
    cursor = db.cursor()
    # Query diubah untuk mengambil semua kolom termasuk status baru
    cursor.execute("""
        SELECT nama, arrival_time, departure_time, date, status_kedatangan,
               status_keberadaan, lama_kerja, status_feedback
        FROM absensi 
        WHERE date BETWEEN ? AND ? 
        ORDER BY date, arrival_time
    """, (start_date, end_date))
    rows = cursor.fetchall()
    processed_rows = []
    
    # Gunakan penomoran baru mulai dari 1
    for idx, row in enumerate(rows, 1):
        arrival = row['arrival_time'].split(" ")[1] if row['arrival_time'] and " " in row['arrival_time'] else row['arrival_time']
        departure = row['departure_time'].split(" ")[1] if row['departure_time'] and " " in row['departure_time'] else row['departure_time']
        
        # Format lama kerja
        lama_kerja_formatted = ""
        if row['lama_kerja'] and row['lama_kerja'] > 0:
            hours = row['lama_kerja'] // 60
            minutes = row['lama_kerja'] % 60
            lama_kerja_formatted = f"{hours}j {minutes}m"
        
        processed_rows.append((
            idx, 
            row['nama'], 
            arrival or '-', 
            departure or '-',
            row['status_kedatangan'] or '-',
            row['status_keberadaan'] or '-',
            lama_kerja_formatted or '-',
            row['status_feedback'] or '-',
            row['date']
        ))
    
    # Buat nama file yang lebih deskriptif
    if custom_filename:
        filename = custom_filename
        # Pastikan nama file diakhiri dengan .xlsx
        if not filename.lower().endswith('.xlsx'):
            filename += '.xlsx'
    else:
        file_title = f"Absensi {start_date_indo}"
        if start_date != end_date:
            file_title += f" - {end_date_indo}"
        filename = f"{file_title}.xlsx"
    
    # Gunakan judul kolom yang lebih baik dan tambahkan kolom status baru
    df = pd.DataFrame(processed_rows, columns=[
        'No', 'Nama', 'Jam Kedatangan', 'Jam Pulang', 
        'Status Kedatangan', 'Status Keberadaan', 'Lama Kerja', 'Status Feedback', 'Tanggal'
    ])
    
    # Gunakan xlsxwriter untuk membuat excel lebih rapi
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    
    # Tulis dataframe ke excel dengan offset baris untuk judul
    df.to_excel(writer, index=False, sheet_name='Absensi', startrow=3)
    
    # Dapatkan workbook dan worksheet untuk formatting
    workbook = writer.book
    worksheet = writer.sheets['Absensi']
    
    # Format judul laporan
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # Format subtitle untuk tanggal
    subtitle_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # Format header dengan warna latar dan border
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1,
        'align': 'center'
    })
    
    # Format sel dengan border
    cell_format = workbook.add_format({
        'border': 1
    })
    
    # Tambahkan judul laporan
    worksheet.merge_range('A1:I1', 'REKAP DATA ABSENSI', title_format)
    
    # Tambahkan rentang tanggal sebagai subjudul
    date_range_text = f"Periode: {start_date_indo}"
    if start_date != end_date:
        date_range_text += f" s/d {end_date_indo}"
    worksheet.merge_range('A2:I2', date_range_text, subtitle_format)
    
    # Terapkan format ke header kolom
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(3, col_num, value, header_format)
    
    # Otomatis menyesuaikan lebar kolom
    for i, col in enumerate(df.columns):
        column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
        worksheet.set_column(i, i, column_width)
    
    # Terapkan border ke semua sel dengan data
    for row in range(4, len(df) + 4):
        for col in range(len(df.columns)):
            worksheet.write(row, col, df.iloc[row-4, col], cell_format)
    
    # Tutup writer dan simpan file Excel
    writer.close()
    
    # Set header Content-Disposition untuk memicu dialog Save As di browser
    response = send_file(
        filename, 
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    # Tambahkan header tambahan untuk mendorong dialog Save As
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

@app.route('/delete_absensi', methods=['POST'])
def delete_absensi():
    # Cek autentikasi
    if not session.get('authenticated'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    data = request.get_json()
    date_to_delete = data.get('date')
    date_range = data.get('date_range')
    db = get_db()
    cursor = db.cursor()
    if date_range:
        start, end = date_range.split('_')
        cursor.execute("DELETE FROM absensi WHERE date BETWEEN ? AND ?", (start, end))
        message = "Data absensi untuk rentang tanggal tersebut berhasil dihapus."
    elif date_to_delete:
        cursor.execute("DELETE FROM absensi WHERE date = ?", (date_to_delete,))
        message = f"Data absensi pada tanggal {date_to_delete} berhasil dihapus."
    else:
        message = "Tidak ada filter yang diberikan."
    db.commit()
    with absen_cache_lock:
        absen_hari_ini.clear()
    return jsonify({"status": "success", "message": message})

@app.route('/delete_absensi_all', methods=['POST'])
def delete_absensi_all():
    # Cek autentikasi
    if not session.get('authenticated'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM absensi")
    db.commit()
    with absen_cache_lock:
        absen_hari_ini.clear()
    return jsonify({"status": "success", "message": "Semua data absensi berhasil dihapus."})

@app.route('/delete_selected_absensi', methods=['POST'])
def delete_selected_absensi():
    # Cek autentikasi
    if not session.get('authenticated'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({"status": "error", "message": "Tidak ada data yang dipilih untuk dihapus"})
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Gunakan parameter binding untuk menghindari SQL injection
        placeholders = ', '.join(['?'] * len(ids))
        query = f"DELETE FROM absensi WHERE id IN ({placeholders})"
        cursor.execute(query, ids)
        
        deleted_count = cursor.rowcount
        db.commit()
        
        return jsonify({
            "status": "success", 
            "message": f"{deleted_count} data absensi berhasil dihapus"
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Gagal menghapus data: {str(e)}"
        }), 500

@app.route('/delete_daily_schedule', methods=['POST'])
def delete_daily_schedule():
    if not session.get('authenticated'):
        return jsonify({"success": False, "message": "Tidak terautentikasi"}), 401
    
    try:
        data = request.json
        day = data.get('day')
        year = data.get('year')
        month = data.get('month')
        
        if not all([day, year, month]):
            return jsonify({"success": False, "message": "Data tidak lengkap"}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Delete jadwal khusus untuk tanggal tersebut
        cursor.execute("""
            DELETE FROM jadwal_bulanan 
            WHERE tahun = ? AND bulan = ? AND tanggal = ?
        """, (year, month, day))
        
        db.commit()
        
        # Cek apakah hari tersebut adalah Minggu, jika ya set kembali sebagai libur
        import calendar
        cal = calendar.monthcalendar(year, month)
        
        for week in cal:
            for day_index, calendar_day in enumerate(week):
                if calendar_day == day and day_index == 6:  # Hari Minggu
                    cursor.execute("""
                        INSERT INTO jadwal_bulanan 
                        (tahun, bulan, tanggal, start_arrival, late_arrival, departure_time, is_holiday, keterangan)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (year, month, day, '06:00:00', '07:00:00', '15:00:00', True, 'Hari Minggu'))
                    break
        
        db.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Jadwal tanggal {day} berhasil direset ke default"
        })
        
    except Exception as e:
        print(f"Error deleting daily schedule: {str(e)}")
        return jsonify({"success": False, "message": f"Gagal mereset jadwal: {str(e)}"}), 500

def set_default_sunday_holiday(cursor, year, month):
    """Set semua hari minggu dalam bulan sebagai hari libur secara default"""
    import calendar
    
    # Dapatkan semua tanggal dalam bulan
    cal = calendar.monthcalendar(year, month)
    
    for week in cal:
        for day_index, day in enumerate(week):
            if day != 0 and day_index == 6:  # Hari minggu (index 6)
                # Cek apakah sudah ada setting untuk tanggal ini
                cursor.execute("""
                    SELECT id FROM jadwal_bulanan 
                    WHERE tahun = ? AND bulan = ? AND tanggal = ?
                """, (year, month, day))
                
                if not cursor.fetchone():
                    # Jika belum ada, set sebagai libur default
                    cursor.execute("""
                        INSERT INTO jadwal_bulanan 
                        (tahun, bulan, tanggal, start_arrival, late_arrival, departure_time, is_holiday, keterangan)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (year, month, day, '06:00:00', '07:00:00', '15:00:00', True, 'Hari Minggu'))


# ===================================================
# 8. CAMERA CONTROL ENDPOINTS
# ===================================================
# Endpoints removed - using simple camera implementation

# ===================================================
# 3. HELPER FUNCTIONS - NEW ADDITIONS
# ===================================================

def get_all_teachers():
    """Mendapatkan daftar semua guru dari master_guru (bukan hanya yang pernah absen)"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT nama FROM master_guru WHERE status = 'Aktif' ORDER BY nama")
    return cursor.fetchall()

def get_attendance_status_today():
    """Mendapatkan status kehadiran semua guru untuk hari ini"""
    today_date = datetime.now().strftime('%Y-%m-%d')
    db = get_db()
    cursor = db.cursor()
    
    # Ambil semua guru dari master
    all_teachers = get_all_teachers()
    
    # Ambil data absensi hari ini
    cursor.execute("""
        SELECT nama, arrival_time, departure_time, status_kedatangan, status_keberadaan
        FROM absensi 
        WHERE date = ?
    """, (today_date,))
    
    attendance_data = {}
    for row in cursor.fetchall():
        attendance_data[row[0]] = {
            'nama': row[0],
            'arrival_time': row[1],
            'departure_time': row[2],
            'status_kedatangan': row[3] or 'Belum Datang',
            'status_keberadaan': row[4] or 'Tidak Ada',
            'hadir': True
        }
    
    # Gabungkan dengan data master guru
    result = []
    for teacher_row in all_teachers:
        nama = teacher_row[0]
        
        if nama in attendance_data:
            teacher_data = attendance_data[nama]
            result.append(teacher_data)
        else:
            result.append({
                'nama': nama,
                'arrival_time': None,
                'departure_time': None,
                'status_kedatangan': 'Belum Datang',
                'status_keberadaan': 'Tidak Ada',
                'hadir': False
            })
    
    return result

# API endpoint untuk mendapatkan status kehadiran hari ini
@app.route('/get_attendance_status_today')
def get_attendance_status_today_api():
    """API endpoint untuk mendapatkan status kehadiran hari ini"""
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401
    
    attendance_status = get_attendance_status_today()
    return jsonify({
        "date": datetime.now().strftime('%Y-%m-%d'),
        "day_name": get_day_name(),
        "attendance": attendance_status
    })

@app.route('/edit_attendance_time', methods=['POST'])
def edit_attendance_time():
    """Endpoint untuk mengedit waktu kehadiran"""
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    attendance_id = data.get('id')
    field = data.get('field')  # 'arrival_time' atau 'departure_time'
    new_time = data.get('time')
    
    if not all([attendance_id, field, new_time]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    if field not in ['arrival_time', 'departure_time']:
        return jsonify({"error": "Invalid field"}), 400
    
    try:
        # Validasi format waktu
        datetime.strptime(new_time, '%H:%M:%S')
    except ValueError:
        return jsonify({"error": "Invalid time format"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Ambil data attendance saat ini
        cursor.execute("SELECT nama, date, arrival_time, departure_time FROM absensi WHERE id = ?", (attendance_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({"error": "Attendance record not found"}), 404
        
        nama, date, current_arrival, current_departure = row
        
        # Update field yang diminta
        cursor.execute(f"UPDATE absensi SET {field} = ? WHERE id = ?", (new_time, attendance_id))
        
        # Jika mengupdate arrival_time, recalculate status kedatangan dan status keberadaan
        if field == 'arrival_time':
            # Ambil jadwal untuk tanggal tersebut
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            cursor.execute("""
                SELECT start_arrival, late_arrival FROM jadwal_bulanan 
                WHERE tahun = ? AND bulan = ? AND tanggal = ?
            """, (date_obj.year, date_obj.month, date_obj.day))
            schedule_row = cursor.fetchone()
            
            if not schedule_row:
                # Fallback ke jadwal harian
                day_name = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'][date_obj.weekday()]
                cursor.execute("SELECT start_arrival, late_arrival FROM jadwal WHERE hari = ?", (day_name,))
                schedule_row = cursor.fetchone()
            
            if schedule_row:
                start_arrival, late_arrival = schedule_row
                status_kedatangan = "Tepat Waktu" if new_time < late_arrival else "Terlambat"
                cursor.execute("UPDATE absensi SET status_kedatangan = ?, status_keberadaan = ? WHERE id = ?", 
                              (status_kedatangan, "Sudah Ada", attendance_id))
        
        # Jika mengupdate departure_time, update status keberadaan
        if field == 'departure_time':
            cursor.execute("UPDATE absensi SET status_keberadaan = ? WHERE id = ?", ("Tidak Ada", attendance_id))
        
        # Recalculate lama_kerja dan status_feedback jika keduanya ada
        cursor.execute("SELECT arrival_time, departure_time FROM absensi WHERE id = ?", (attendance_id,))
        updated_row = cursor.fetchone()
        
        if updated_row and updated_row[0] and updated_row[1]:
            arrival_dt = datetime.strptime(f"{date} {updated_row[0]}", '%Y-%m-%d %H:%M:%S')
            departure_dt = datetime.strptime(f"{date} {updated_row[1]}", '%Y-%m-%d %H:%M:%S')
            
            # Handle case jika departure di hari berikutnya
            if departure_dt < arrival_dt:
                departure_dt += timedelta(days=1)
            
            lama_kerja_minutes = int((departure_dt - arrival_dt).total_seconds() / 60)
            
            # Tentukan status feedback
            if lama_kerja_minutes >= 480:  # 8 jam
                if lama_kerja_minutes > 540:  # > 9 jam
                    status_feedback = "Lembur"
                else:
                    status_feedback = "Normal"
            elif lama_kerja_minutes >= 240:  # 4-8 jam
                status_feedback = "Pulang Cepat"
            else:
                status_feedback = "Durasi Kerja Kurang"
            
            # Tentukan status keberadaan berdasarkan kondisi
            if updated_row[1]:  # jika departure_time ada
                status_keberadaan = "Tidak Ada"  # sudah pulang
            else:
                status_keberadaan = "Sudah Ada"  # masih di tempat
            
            cursor.execute("""
                UPDATE absensi 
                SET lama_kerja = ?, status_feedback = ?, status_keberadaan = ?
                WHERE id = ?
            """, (lama_kerja_minutes, status_feedback, status_keberadaan, attendance_id))
        
        db.commit()
        return jsonify({"success": True, "message": "Waktu berhasil diperbarui"})
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/add_attendance_manual', methods=['POST'])
def add_attendance_manual():
    """Endpoint untuk menambahkan data kehadiran manual (untuk yang belum datang)"""
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    nama = data.get('nama')
    date = data.get('date')
    arrival_time = data.get('arrival_time')
    departure_time = data.get('departure_time', None)
    
    if not all([nama, date, arrival_time]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        # Validasi format waktu
        datetime.strptime(arrival_time, '%H:%M:%S')
        if departure_time:
            datetime.strptime(departure_time, '%H:%M:%S')
    except ValueError:
        return jsonify({"error": "Invalid time format"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Cek apakah sudah ada data untuk nama dan tanggal tersebut
        cursor.execute("SELECT id FROM absensi WHERE nama = ? AND date = ?", (nama, date))
        if cursor.fetchone():
            return jsonify({"error": "Attendance record already exists for this person on this date"}), 400
        
        # Ambil jadwal untuk tanggal tersebut
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        cursor.execute("""
            SELECT start_arrival, late_arrival FROM jadwal_bulanan 
            WHERE tahun = ? AND bulan = ? AND tanggal = ?
        """, (date_obj.year, date_obj.month, date_obj.day))
        schedule_row = cursor.fetchone()
        
        if not schedule_row:
            # Fallback ke jadwal harian
            day_name = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'][date_obj.weekday()]
            cursor.execute("SELECT start_arrival, late_arrival FROM jadwal WHERE hari = ?", (day_name,))
            schedule_row = cursor.fetchone()
        
        # Tentukan status kedatangan
        status_kedatangan = "Tepat Waktu"
        if schedule_row:
            start_arrival, late_arrival = schedule_row
            status_kedatangan = "Tepat Waktu" if arrival_time < late_arrival else "Terlambat"
        
        # Hitung lama kerja jika departure time ada
        lama_kerja_minutes = 0
        status_feedback = None
        status_keberadaan = "Tidak Ada" if departure_time else "Sudah Ada"
        
        if departure_time:
            arrival_dt = datetime.strptime(f"{date} {arrival_time}", '%Y-%m-%d %H:%M:%S')
            departure_dt = datetime.strptime(f"{date} {departure_time}", '%Y-%m-%d %H:%M:%S')
            
            # Handle case jika departure di hari berikutnya
            if departure_dt < arrival_dt:
                departure_dt += timedelta(days=1)
            
            lama_kerja_minutes = int((departure_dt - arrival_dt).total_seconds() / 60)
            
            # Tentukan status feedback
            if lama_kerja_minutes >= 480:  # 8 jam
                if lama_kerja_minutes > 540:  # > 9 jam
                    status_feedback = "Lembur"
                else:
                    status_feedback = "Normal"
            elif lama_kerja_minutes >= 240:  # 4-8 jam
                status_feedback = "Pulang Cepat"
            else:
                status_feedback = "Durasi Kerja Kurang"
        
        # Insert data kehadiran
        cursor.execute("""
            INSERT INTO absensi 
            (nama, arrival_time, departure_time, date, status_kedatangan, status_keberadaan, lama_kerja, status_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nama, arrival_time, departure_time, date, status_kedatangan, status_keberadaan, lama_kerja_minutes, status_feedback))
        
        db.commit()
        return jsonify({"success": True, "message": "Data kehadiran berhasil ditambahkan"})
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/daily_attendance')
def daily_attendance():
    """Halaman status kehadiran harian"""
    if not session.get('authenticated'):
        return redirect(url_for('set_schedule'))
    
    return render_template('daily_attendance.html')

@app.route('/check_holiday_status', methods=['GET'])
def check_holiday_status():
    """Endpoint untuk mengecek apakah hari ini libur"""
    db = get_db()
    cursor = db.cursor()
    schedule = get_schedule_for_today(cursor)
    
    if schedule and bool(schedule.get('is_holiday', False)):
        holiday_message = "Hari ini adalah hari libur"
        if schedule.get('keterangan'):
            holiday_message += f" - {schedule.get('keterangan')}"
        
        return jsonify({
            "is_holiday": True,
            "message": holiday_message,
            "keterangan": schedule.get('keterangan', ''),
            "schedule": {
                "start_arrival": schedule.get('start_arrival'),
                "late_arrival": schedule.get('late_arrival'),
                "departure_time": schedule.get('departure_time')
            }
        })
    else:
        return jsonify({
            "is_holiday": False,
            "message": "Hari ini bukan hari libur",
            "schedule": {
                "start_arrival": schedule.get('start_arrival') if schedule else None,
                "late_arrival": schedule.get('late_arrival') if schedule else None,
                "departure_time": schedule.get('departure_time') if schedule else None
            }
        })

@app.route('/manage_teachers', methods=['GET', 'POST'])
def manage_teachers():
    """Halaman untuk mengelola master guru"""
    if not session.get('authenticated'):
        return redirect(url_for('set_schedule'))
    
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            nama = request.form.get('nama')
            kelas = request.form.get('kelas')
            no_induk = request.form.get('no_induk', '')
            
            try:
                cursor.execute("""
                    INSERT INTO master_guru (nama, kelas, no_induk)
                    VALUES (?, ?, ?)
                """, (nama, kelas, no_induk))
                db.commit()
                flash(f"Guru {nama} berhasil ditambahkan", "success")
            except sqlite3.IntegrityError:
                flash(f"Guru {nama} sudah ada dalam database", "error")
        
        elif action == 'delete':
            teacher_id = request.form.get('teacher_id')
            cursor.execute("DELETE FROM master_guru WHERE id = ?", (teacher_id,))
            db.commit()
            flash("Guru berhasil dihapus", "success")
        
        elif action == 'update':
            teacher_id = request.form.get('teacher_id')
            nama = request.form.get('nama')
            kelas = request.form.get('kelas')
            status = request.form.get('status')
            no_induk = request.form.get('no_induk', '')
            
            cursor.execute("""
                UPDATE master_guru 
                SET nama = ?, kelas = ?, status = ?, no_induk = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (nama, kelas, status, no_induk, teacher_id))
            db.commit()
            flash("Data guru berhasil diperbarui", "success")
    
    # Ambil semua data guru
    cursor.execute("SELECT id, nama, kelas, status, no_induk FROM master_guru ORDER BY kelas, nama")
    teachers = cursor.fetchall()
    
    return render_template('manage_teachers.html', teachers=teachers)

@app.route('/init_sample_teachers', methods=['POST'])
def init_sample_teachers():
    """Initialize sample teachers untuk 25 kelas"""
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Data sample guru untuk 25 kelas
    sample_teachers = []
    
    # Buat data sample untuk 25 kelas
    for i in range(1, 26):
        if i <= 6:
            tingkat = "I"
            kelas_detail = f"Kelas {i}"
        elif i <= 12:
            tingkat = "II"
            kelas_detail = f"Kelas {i-6}"
        elif i <= 18:
            tingkat = "III"
            kelas_detail = f"Kelas {i-12}"
        elif i <= 24:
            tingkat = "IV"
            kelas_detail = f"Kelas {i-18}"
        else:
            tingkat = "V"
            kelas_detail = f"Kelas {i-24}"
        
        sample_teachers.extend([
            (f"Guru Kelas {i}A", f"{tingkat}.{kelas_detail}A", f"GTK{i:03d}A"),
            (f"Guru Kelas {i}B", f"{tingkat}.{kelas_detail}B", f"GTK{i:03d}B") if i <= 20 else None
        ])
    
    # Filter None values
    sample_teachers = [t for t in sample_teachers if t is not None]
    
    try:
        cursor.executemany("""
            INSERT OR IGNORE INTO master_guru (nama, kelas, no_induk)
            VALUES (?, ?, ?)
        """, sample_teachers)
        db.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Berhasil menginisialisasi {len(sample_teachers)} data guru untuk 25 kelas",
            "count": len(sample_teachers)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================================================
# 9. MODEL MANAGEMENT ROUTES
# ===================================================

@app.route('/upload_training_data', methods=['GET', 'POST'])
def upload_training_data():
    """Upload data training untuk update model"""
    if not session.get('authenticated'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        # Cek apakah file ada
        if 'file' not in request.files:
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(request.url)
        
        # Validasi file
        if not allowed_file(file.filename):
            flash('Format file tidak didukung. Gunakan ZIP, JPG, JPEG, PNG, BMP, atau TIFF', 'error')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Simpan file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Ambil guru_id dari form jika ada
        guru_id = request.form.get('guru_id')
        guru_id = int(guru_id) if guru_id and guru_id.isdigit() else None
        
        try:
            if filename.lower().endswith('.zip'):
                # Proses file ZIP
                result = process_zip_dataset(file_path, filename, guru_id)
            else:
                # Proses single image
                result = process_single_image(file_path, filename, guru_id)
            
            if result['success']:
                flash(result['message'], 'success')
                if 'warnings' in result and result['warnings']:
                    for warning in result['warnings']:
                        flash(f"Peringatan: {warning}", 'warning')
            else:
                flash(f"Error: {result['message']}", 'error')
                if 'errors' in result and result['errors']:
                    for error in result['errors']:
                        flash(f"Error: {error}", 'error')
                        
        except Exception as e:
            flash(f"Terjadi kesalahan: {str(e)}", 'error')
        finally:
            # Hapus file upload temporary
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return redirect(request.url)
    
    # GET - tampilkan halaman upload dengan daftar guru
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nama, kelas FROM master_guru WHERE status = 'Aktif' ORDER BY nama")
    teachers = cursor.fetchall()
    
    return render_template('upload_training_data.html', teachers=teachers)

def process_zip_dataset(zip_path, filename, guru_id=None):
    """Proses dataset dalam format ZIP"""
    extract_path = os.path.join(TRAINING_DATA_FOLDER, f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    try:
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Validasi struktur dataset
        is_valid, errors, warnings = validate_dataset_structure(extract_path)
        
        if not is_valid:
            shutil.rmtree(extract_path, ignore_errors=True)
            return {
                'success': False,
                'message': 'Struktur dataset tidak valid',
                'errors': errors
            }
        
        # Validasi file-file gambar
        images_path = os.path.join(extract_path, 'images')
        labels_path = os.path.join(extract_path, 'labels')
        
        valid_images = 0
        total_images = 0
        label_errors = []
        
        for image_file in os.listdir(images_path):
            if image_file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                total_images += 1
                image_path = os.path.join(images_path, image_file)
                is_valid_img, msg = validate_image_file(image_path)
                
                if is_valid_img:
                    valid_images += 1
                else:
                    warnings.append(f"Gambar {image_file}: {msg}")
                
                # Cek label corresponding
                label_name = os.path.splitext(image_file)[0] + '.txt'
                label_path = os.path.join(labels_path, label_name)
                
                if os.path.exists(label_path):
                    is_valid_label, label_msg = validate_label_format(label_path)
                    if not is_valid_label:
                        label_errors.append(f"Label {label_name}: {label_msg}")
        
        if valid_images < 5:
            shutil.rmtree(extract_path, ignore_errors=True)
            return {
                'success': False,
                'message': f'Terlalu sedikit gambar valid ({valid_images}). Minimal 5 gambar diperlukan.'
            }
        
        # Ekstrak informasi kelas
        class_ids = extract_class_names_from_labels(labels_path)
        if not class_ids:
            warnings.append("Tidak ada kelas yang terdeteksi dari label")
        
        # Simpan dataset ke folder final
        final_dataset_path = os.path.join(TRAINING_DATA_FOLDER, f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.move(extract_path, final_dataset_path)
        
        # Simpan informasi ke database
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO training_dataset 
            (dataset_path, dataset_name, guru_id, images_count, labels_count, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            final_dataset_path,
            os.path.basename(final_dataset_path),
            guru_id,
            valid_images,
            len([f for f in os.listdir(labels_path) if f.endswith('.txt')]),
            datetime.now()
        ))
        db.commit()
        
        # Buat file classes.txt jika ada kelas
        if class_ids:
            class_names = []
            if guru_id:
                # Jika dataset untuk guru tertentu, gunakan nama guru
                cursor.execute("SELECT nama FROM master_guru WHERE id = ?", (guru_id,))
                guru_row = cursor.fetchone()
                if guru_row:
                    class_names = [guru_row['nama']]
            else:
                # Untuk dataset umum, ambil dari database guru atau buat placeholder
                cursor.execute("SELECT nama FROM master_guru ORDER BY nama")
                guru_names = [row['nama'] for row in cursor.fetchall()]
                
                for class_id in class_ids:
                    if class_id < len(guru_names):
                        class_names.append(guru_names[class_id])
                    else:
                        class_names.append(f"Guru_{class_id}")
            
            if class_names:
                create_classes_file(final_dataset_path, class_names)
        
        result_msg = f"Dataset berhasil diupload! {valid_images}/{total_images} gambar valid. "
        result_msg += f"Dataset disimpan di: {final_dataset_path}"
        
        if guru_id:
            cursor.execute("SELECT nama FROM master_guru WHERE id = ?", (guru_id,))
            guru_row = cursor.fetchone()
            if guru_row:
                result_msg += f" (untuk guru: {guru_row['nama']})"
        
        if label_errors:
            warnings.extend(label_errors[:5])  # Tampilkan max 5 error
        
        return {
            'success': True,
            'message': result_msg,
            'warnings': warnings,
            'dataset_path': final_dataset_path,
            'stats': {
                'total_images': total_images,
                'valid_images': valid_images,
                'classes': len(class_ids),
                'guru_id': guru_id
            }
        }
        
    except zipfile.BadZipFile:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path, ignore_errors=True)
        return {
            'success': False,
            'message': 'File ZIP rusak atau tidak valid'
        }
    except Exception as e:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path, ignore_errors=True)
        return {
            'success': False,
            'message': f'Error processing dataset: {str(e)}'
        }

def process_single_image(image_path, filename, guru_id=None):
    """Proses single image upload"""
    try:
        # Validasi gambar
        is_valid, msg = validate_image_file(image_path)
        
        if not is_valid:
            return {
                'success': False,
                'message': msg
            }
        
        # Simpan ke folder training data
        if guru_id:
            # Buat folder khusus untuk guru
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT nama FROM master_guru WHERE id = ?", (guru_id,))
            guru_row = cursor.fetchone()
            if guru_row:
                guru_folder = secure_filename(guru_row['nama'])
                final_path = os.path.join(TRAINING_DATA_FOLDER, 'single_images', guru_folder)
            else:
                final_path = os.path.join(TRAINING_DATA_FOLDER, 'single_images', 'unknown')
        else:
            final_path = os.path.join(TRAINING_DATA_FOLDER, 'single_images', 'general')
        
        os.makedirs(final_path, exist_ok=True)
        
        # Copy file ke folder final
        final_file_path = os.path.join(final_path, filename)
        shutil.copy2(image_path, final_file_path)
        
        # Simpan informasi ke database
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO training_dataset 
            (dataset_path, dataset_name, guru_id, images_count, labels_count, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            final_path,
            f"single_image_{filename}",
            guru_id,
            1,
            0,
            datetime.now()
        ))
        db.commit()
        
        result_msg = f'Gambar berhasil diupload: {filename}'
        if guru_id:
            cursor.execute("SELECT nama FROM master_guru WHERE id = ?", (guru_id,))
            guru_row = cursor.fetchone()
            if guru_row:
                result_msg += f" (untuk guru: {guru_row['nama']})"
        
        return {
            'success': True,
            'message': result_msg,
            'file_path': final_file_path,
            'guru_id': guru_id
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error processing image: {str(e)}'
        }

@app.route('/view_datasets')
def view_datasets():
    """Lihat dataset yang sudah diupload"""
    if not session.get('authenticated'):
        return redirect(url_for('admin_login'))
    
    datasets = []
    
    if os.path.exists(TRAINING_DATA_FOLDER):
        for item in os.listdir(TRAINING_DATA_FOLDER):
            item_path = os.path.join(TRAINING_DATA_FOLDER, item)
            if os.path.isdir(item_path):
                # Hitung statistik
                stats = get_dataset_statistics(item_path)
                datasets.append({
                    'name': item,
                    'path': item_path,
                    'created': datetime.fromtimestamp(os.path.getctime(item_path)),
                    'stats': stats
                })
    
    # Urutkan berdasarkan tanggal dibuat (terbaru pertama)
    datasets.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('view_datasets.html', datasets=datasets)

def get_dataset_statistics(dataset_path):
    """Hitung statistik dataset"""
    stats = {
        'images': 0,
        'labels': 0,
        'classes': 0,
        'size_mb': 0
    }
    
    try:
        # Hitung ukuran folder
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(dataset_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        
        stats['size_mb'] = round(total_size / (1024 * 1024), 2)
        
        # Hitung jumlah file
        images_path = os.path.join(dataset_path, 'images')
        labels_path = os.path.join(dataset_path, 'labels')
        
        if os.path.exists(images_path):
            stats['images'] = len([f for f in os.listdir(images_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))])
        
        if os.path.exists(labels_path):
            stats['labels'] = len([f for f in os.listdir(labels_path) if f.endswith('.txt')])
            
            # Hitung jumlah kelas unik
            class_ids = extract_class_names_from_labels(labels_path)
            stats['classes'] = len(class_ids)
        
        # Jika single images folder
        if 'single_images' in dataset_path:
            stats['images'] = len([f for f in os.listdir(dataset_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))])
            stats['labels'] = 0
            stats['classes'] = 0
            
    except Exception as e:
        print(f"Error calculating stats for {dataset_path}: {e}")
    
    return stats

@app.route('/delete_dataset', methods=['POST'])
def delete_dataset():
    """Hapus dataset"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    dataset_name = request.form.get('dataset_name')
    if not dataset_name:
        return jsonify({'error': 'Dataset name required'}), 400
    
    dataset_path = os.path.join(TRAINING_DATA_FOLDER, dataset_name)
    
    try:
        if os.path.exists(dataset_path):
            shutil.rmtree(dataset_path)
            return jsonify({'success': True, 'message': f'Dataset {dataset_name} berhasil dihapus'})
        else:
            return jsonify({'error': 'Dataset tidak ditemukan'}), 404
    except Exception as e:
        return jsonify({'error': f'Error menghapus dataset: {str(e)}'}), 500

@app.route('/model_management')
def model_management():
    """Halaman manajemen model dan class mapping"""
    if not session.get('authenticated'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Ambil semua model yang ada
    cursor.execute("""
        SELECT m.*, 
               COUNT(cm.id) as class_count,
               GROUP_CONCAT(g.nama) as mapped_teachers
        FROM model_training m
        LEFT JOIN class_mapping cm ON m.id = cm.model_id
        LEFT JOIN master_guru g ON cm.guru_id = g.id
        GROUP BY m.id
        ORDER BY m.training_date DESC
    """)
    models = cursor.fetchall()
    
    # Ambil model yang aktif
    cursor.execute("SELECT * FROM model_training WHERE is_active = 1")
    active_model = cursor.fetchone()
    
    # Ambil daftar guru untuk mapping
    cursor.execute("SELECT id, nama, kelas FROM master_guru WHERE status = 'Aktif' ORDER BY nama")
    teachers = cursor.fetchall()
    
    # Ambil dataset yang tersedia
    cursor.execute("""
        SELECT td.*, mg.nama as guru_nama
        FROM training_dataset td
        LEFT JOIN master_guru mg ON td.guru_id = mg.id
        ORDER BY td.upload_date DESC
    """)
    datasets_raw = cursor.fetchall()
    
    # Konversi models ke format yang bisa digunakan template
    models_converted = []
    for model in models:
        model_dict = dict(model)
        
        # Konversi training_date string ke datetime jika perlu
        if model_dict.get('training_date'):
            try:
                if isinstance(model_dict['training_date'], str):
                    # Parse string date ke datetime
                    model_dict['training_date'] = datetime.strptime(model_dict['training_date'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                # Jika gagal parse, set ke None
                model_dict['training_date'] = None
        
        models_converted.append(model_dict)
    
    # Konversi active_model ke format yang bisa digunakan template
    active_model_converted = None
    if active_model:
        active_model_converted = dict(active_model)
        
        # Konversi training_date string ke datetime jika perlu
        if active_model_converted.get('training_date'):
            try:
                if isinstance(active_model_converted['training_date'], str):
                    # Parse string date ke datetime
                    active_model_converted['training_date'] = datetime.strptime(active_model_converted['training_date'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                # Jika gagal parse, set ke None
                active_model_converted['training_date'] = None

    # Konversi datasets ke format yang bisa digunakan template
    datasets = []
    for dataset in datasets_raw:
        dataset_dict = dict(dataset)
        
        # Konversi upload_date string ke datetime jika perlu
        if dataset_dict.get('upload_date'):
            try:
                if isinstance(dataset_dict['upload_date'], str):
                    # Parse string date ke datetime
                    dataset_dict['upload_date'] = datetime.strptime(dataset_dict['upload_date'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                # Jika gagal parse, set ke None
                dataset_dict['upload_date'] = None
        
        datasets.append(dataset_dict)
    
    return render_template('model_management.html', 
                         models=models_converted, 
                         active_model=active_model_converted, 
                         teachers=teachers,
                         datasets=datasets)

@app.route('/create_model_mapping', methods=['POST'])
def create_model_mapping():
    """Buat mapping model baru dari dataset"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        model_name = request.form.get('model_name')
        model_path = request.form.get('model_path', 'best.pt')
        dataset_ids = request.form.getlist('dataset_ids')
        description = request.form.get('description', '')
        
        if not model_name or not dataset_ids:
            return jsonify({'error': 'Model name dan dataset harus dipilih'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Buat record model training
        cursor.execute("""
            INSERT INTO model_training 
            (model_name, model_path, description, total_classes, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (model_name, model_path, description, len(dataset_ids), False))
        
        model_id = cursor.lastrowid
        
        # Buat class mapping berdasarkan dataset
        class_id = 0
        for dataset_id in dataset_ids:
            # Ambil info dataset
            cursor.execute("""
                SELECT td.*, mg.nama as guru_nama
                FROM training_dataset td
                LEFT JOIN master_guru mg ON td.guru_id = mg.id
                WHERE td.id = ?
            """, (dataset_id,))
            dataset = cursor.fetchone()
            
            if dataset and dataset['guru_id']:
                # Buat mapping untuk guru
                cursor.execute("""
                    INSERT INTO class_mapping 
                    (model_id, class_id, guru_id, class_name, confidence_threshold)
                    VALUES (?, ?, ?, ?, ?)
                """, (model_id, class_id, dataset['guru_id'], dataset['guru_nama'], 0.7))
                
                # Update dataset untuk menandai sudah digunakan
                cursor.execute("""
                    UPDATE training_dataset 
                    SET is_used_for_training = 1, training_model_id = ?
                    WHERE id = ?
                """, (model_id, dataset_id))
                
                class_id += 1
        
        # Update total classes
        cursor.execute("""
            UPDATE model_training SET total_classes = ? WHERE id = ?
        """, (class_id, model_id))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Model mapping "{model_name}" berhasil dibuat dengan {class_id} kelas',
            'model_id': model_id
        })
        
    except Exception as e:
        return jsonify({'error': f'Error creating model mapping: {str(e)}'}), 500

@app.route('/activate_model', methods=['POST'])
def activate_model():
    """Aktifkan model untuk digunakan dalam deteksi"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        model_id = request.form.get('model_id')
        if not model_id:
            return jsonify({'error': 'Model ID required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Nonaktifkan semua model
        cursor.execute("UPDATE model_training SET is_active = 0")
        
        # Aktifkan model yang dipilih
        cursor.execute("UPDATE model_training SET is_active = 1 WHERE id = ?", (model_id,))
        
        # Ambil info model
        cursor.execute("SELECT model_name, model_path FROM model_training WHERE id = ?", (model_id,))
        model_info = cursor.fetchone()
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Model "{model_info["model_name"]}" berhasil diaktifkan'
        })
        
    except Exception as e:
        return jsonify({'error': f'Error activating model: {str(e)}'}), 500

@app.route('/get_class_mapping/<int:model_id>')
def get_class_mapping(model_id):
    """Ambil class mapping untuk model tertentu"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT cm.*, mg.nama as guru_nama, mg.kelas
        FROM class_mapping cm
        JOIN master_guru mg ON cm.guru_id = mg.id
        WHERE cm.model_id = ?
        ORDER BY cm.class_id
    """, (model_id,))
    
    mappings = cursor.fetchall()
    
    return jsonify({
        'success': True,
        'mappings': [dict(row) for row in mappings]
    })


# ===================================================
# 10. FINE-TUNING ROUTES - FITUR BARU
# ===================================================

@app.route('/add_new_person')
def add_new_person():
    """Halaman untuk menambah orang baru dengan fine-tuning otomatis"""
    if not session.get('authenticated'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nama, kelas FROM master_guru WHERE status = 'Aktif' ORDER BY nama")
    teachers = cursor.fetchall()
    
    return render_template('add_new_person.html', teachers=teachers)

@app.route('/upload_new_person_data', methods=['POST'])
def upload_new_person_data():
    """Upload data untuk orang baru dan trigger fine-tuning"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        person_name = request.form.get('person_name')
        guru_id = request.form.get('guru_id')
        is_new_teacher = request.form.get('is_new_teacher') == 'true'
        
        if not person_name:
            return jsonify({'error': 'Nama orang harus diisi'}), 400
        
        # Validasi file
        if 'images' not in request.files:
            return jsonify({'error': 'Tidak ada file yang diupload'}), 400
        
        files = request.files.getlist('images')
        if len(files) < 15:
            return jsonify({'error': 'Minimal 15 gambar diperlukan untuk fine-tuning'}), 400
        
        # Buat folder untuk menyimpan gambar
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        person_folder = os.path.join('new_person_data', f"{secure_filename(person_name)}_{timestamp}")
        os.makedirs(person_folder, exist_ok=True)
        
        # Simpan gambar
        saved_count = 0
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                # Validasi ukuran dan format gambar
                file_path = os.path.join(person_folder, f"image_{i:03d}.jpg")
                file.save(file_path)
                
                # Validasi gambar
                is_valid, msg = validate_image_file(file_path)
                if is_valid:
                    saved_count += 1
                else:
                    os.remove(file_path)
        
        if saved_count < 15:
            shutil.rmtree(person_folder, ignore_errors=True)
            return jsonify({'error': f'Hanya {saved_count} gambar valid. Minimal 15 gambar diperlukan'}), 400
        
        # Jika guru baru, tambahkan ke database
        if is_new_teacher and guru_id is None:
            kelas = request.form.get('kelas', '')
            no_induk = request.form.get('no_induk', '')
            
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO master_guru (nama, kelas, no_induk)
                VALUES (?, ?, ?)
            """, (person_name, kelas, no_induk))
            guru_id = cursor.lastrowid
            db.commit()
        
        # Trigger fine-tuning
        task_id = fine_tuning_manager.add_new_person_to_queue(
            person_name=person_name,
            image_folder_path=person_folder,
            guru_id=guru_id
        )
        
        return jsonify({
            'success': True,
            'message': f'Data untuk {person_name} berhasil diupload. Fine-tuning dimulai.',
            'task_id': task_id,
            'image_count': saved_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/fine_tuning_status')
def fine_tuning_status():
    """Halaman monitoring status fine-tuning"""
    if not session.get('authenticated'):
        return redirect(url_for('admin_login'))
    
    return render_template('fine_tuning_status.html')

@app.route('/api/fine_tuning_status/<task_id>')
def api_fine_tuning_status(task_id=None):
    """API untuk mendapatkan status fine-tuning"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if task_id:
        status = fine_tuning_manager.get_training_status(task_id)
        if status:
            return jsonify({'success': True, 'status': status})
        else:
            return jsonify({'error': 'Task not found'}), 404
    else:
        # Return overall status
        status = fine_tuning_manager.get_training_status()
        return jsonify({'success': True, 'status': status})

@app.route('/api/fine_tuning_history')
def api_fine_tuning_history():
    """API untuk mendapatkan history fine-tuning"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT fth.*, mg.nama as guru_nama, mg.kelas
            FROM fine_tuning_history fth
            LEFT JOIN master_guru mg ON fth.guru_id = mg.id
            ORDER BY fth.created_at DESC
            LIMIT 50
        """)
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'person_name': row[1],
                'guru_nama': row[11] if row[11] else row[1],
                'kelas': row[12],
                'status': row[3],
                'image_count': row[4],
                'created_at': row[6],
                'started_at': row[7],
                'completed_at': row[8],
                'error_message': row[10]
            })
        
        return jsonify({'success': True, 'history': history})
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/cleanup_fine_tuning')
def api_cleanup_fine_tuning():
    """API untuk membersihkan file temporary"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        fine_tuning_manager.cleanup_temp_files()
        return jsonify({'success': True, 'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

# ===================================================
# HELPER FUNCTIONS UNTUK UPLOAD DAN VALIDASI
# ===================================================

def allowed_file(filename):
    """Cek apakah file yang diupload memiliki ekstensi yang diizinkan"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file(file_path):
    """Validasi apakah file adalah gambar yang valid"""
    try:
        img = cv2.imread(file_path)
        if img is None:
            return False, "File bukan gambar yang valid"
        
        # Cek dimensi minimum
        height, width = img.shape[:2]
        if height < 100 or width < 100:
            return False, "Resolusi gambar terlalu kecil (minimum 100x100 pixel)"
            
        if height > 4000 or width > 4000:
            return False, "Resolusi gambar terlalu besar (maksimum 4000x4000 pixel)"
            
        return True, "Valid"
    except Exception as e:
        return False, f"Error validasi gambar: {str(e)}"

def validate_dataset_structure(extracted_path):
    """Validasi struktur dataset untuk YOLO"""
    required_folders = ['images', 'labels']
    errors = []
    warnings = []
    
    # Cek folder wajib
    for folder in required_folders:
        folder_path = os.path.join(extracted_path, folder)
        if not os.path.exists(folder_path):
            errors.append(f"Folder '{folder}' tidak ditemukan")
    
    if errors:
        return False, errors, warnings
    
    # Cek isi folder images
    images_path = os.path.join(extracted_path, 'images')
    labels_path = os.path.join(extracted_path, 'labels')
    
    image_files = []
    label_files = []
    
    # Scan images
    for file in os.listdir(images_path):
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
            image_files.append(file)
    
    # Scan labels
    for file in os.listdir(labels_path):
        if file.lower().endswith('.txt'):
            label_files.append(file)
    
    if len(image_files) < 10:
        warnings.append(f"Jumlah gambar terlalu sedikit ({len(image_files)}). Disarankan minimal 50 gambar per kelas")
    
    if len(image_files) == 0:
        errors.append("Tidak ada file gambar yang valid ditemukan")
    
    if len(label_files) == 0:
        errors.append("Tidak ada file label (.txt) ditemukan")
    
    # Cek konsistensi nama file
    image_names = {os.path.splitext(f)[0] for f in image_files}
    label_names = {os.path.splitext(f)[0] for f in label_files}
    
    missing_labels = image_names - label_names
    if missing_labels:
        warnings.append(f"Beberapa gambar tidak memiliki label: {list(missing_labels)[:5]}...")
    
    missing_images = label_names - image_names
    if missing_images:
        warnings.append(f"Beberapa label tidak memiliki gambar: {list(missing_images)[:5]}...")
    
    return len(errors) == 0, errors, warnings

def validate_label_format(label_path):
    """Validasi format file label YOLO"""
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) != 5:
                return False, f"Baris {line_num}: Format label salah (harus: class_id x_center y_center width height)"
            
            try:
                class_id = int(parts[0])
                x_center, y_center, width, height = map(float, parts[1:])
                
                # Validasi range koordinat (harus 0-1)
                if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                       0 <= width <= 1 and 0 <= height <= 1):
                    return False, f"Baris {line_num}: Koordinat harus dalam range 0-1"
                    
            except ValueError:
                return False, f"Baris {line_num}: Nilai tidak valid"
        
        return True, "Valid"
    except Exception as e:
        return False, f"Error membaca file: {str(e)}"

def create_classes_file(dataset_path, class_names):
    """Buat file classes.txt berdasarkan nama kelas yang ditemukan"""
    classes_file = os.path.join(dataset_path, 'classes.txt')
    with open(classes_file, 'w') as f:
        for class_name in sorted(class_names):
            f.write(f"{class_name}\n")
    return classes_file

def extract_class_names_from_labels(labels_path):
    """Ekstrak nama kelas dari file label"""
    class_ids = set()
    for label_file in os.listdir(labels_path):
        if label_file.endswith('.txt'):
            label_path = os.path.join(labels_path, label_file)
            try:
                with open(label_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            class_id = int(line.split()[0])
                            class_ids.add(class_id)
            except:
                continue
    return sorted(class_ids)

# ...existing code...
# Run the application
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Aplikasi Absensi')
    parser.add_argument('--host', default='127.0.0.1', help='Host IP to run the server on')
    args = parser.parse_args()
    
    # Tampilkan informasi cara akses
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Server berjalan pada:")
    print(f" - Local: http://{args.host}:5000")
    print(f" - Network: http://{local_ip}:5000")
    
    app.run(debug=False, host=args.host, port=5000)
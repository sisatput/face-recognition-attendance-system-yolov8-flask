# Face Recognition Attendance System with YOLOv8 and Flask

Sistem absensi otomatis berbasis pengenalan wajah menggunakan YOLOv8 dan Flask. Sistem ini dirancang untuk sekolah/institusi yang ingin mengotomatisasi proses pencatatan kehadiran guru dengan teknologi computer vision.

## Features

✅ **Face Recognition Real-time** - Deteksi wajah otomatis menggunakan YOLOv8  
✅ **Web-based Interface** - Interface modern dengan Flask  
✅ **Admin Dashboard** - Kelola jadwal kerja, lihat laporan kehadiran  
✅ **Attendance Reports** - Export data absensi ke Excel  
✅ **Fine-tuning Model** - Latih model dengan dataset khusus  
✅ **Schedule Management** - Atur jadwal kerja harian dan bulanan  
✅ **Holiday Settings** - Pengaturan hari libur dan khusus  
✅ **Manual Attendance** - Input absensi manual jika diperlukan  

## Technology Stack

- **Backend**: Python Flask 2.3.3
- **AI/ML**: YOLOv8 (Ultralytics)
- **Computer Vision**: OpenCV
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **Data Processing**: Pandas, NumPy
- **Model Training**: PyTorch

## Requirements

- Python 3.8+
- Windows/Linux/macOS
- Webcam untuk real-time face detection
- Minimum 4GB RAM

## Installation

### Quick Start (Windows)

1. Clone repository:
```bash
git clone https://github.com/sisatput/face-recognition-attendance-system-yolov8-flask.git
cd face-recognition-attendance-system-yolov8-flask
```

2. Run batch file:
```bash
run.bat
```

Ini akan:
- Membuat virtual environment
- Install dependencies
- Menampilkan URL untuk akses sistem

3. Buka browser ke:
   - **Local**: http://localhost:5000
   - **Network**: http://<your-ip>:5000

### Manual Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py --host=0.0.0.0
```

## Usage

### 1. Access sistem
Buka browser ke http://localhost:5000

### 2. Face Detection (Home Page)
- Sistem akan mendeteksi wajah secara real-time
- Absensi masuk tercatat otomatis saat wajah terdeteksi
- Absensi pulang tercatat saat jam pulang tiba

### 3. Admin Panel
- Login ke http://localhost:5000/set_schedule
- Default password: `admin` (ganti di halaman Change Password)
- Manage jadwal kerja, lihat laporan, export data

### 4. Export Laporan
- Go to "Lihat Absensi" → Pilih tanggal → Export Excel
- Laporan berisi: nama, jam masuk, jam pulang, status kedatangan, durasi kerja

## Default Admin Credentials

- **Username**: (tidak ada)
- **Password**: `admin`

⚠️ **PENTING**: Ubah password default segera di halaman Change Password!

## Project Structure

```
.
├── app.py                      # Main Flask application
├── fine_tuning_manager.py      # Model fine-tuning logic
├── requirements.txt            # Python dependencies
├── best.pt                     # Pre-trained YOLOv8 model
├── run.bat                     # Windows startup script
├── maintenance.py              # Database maintenance utilities
├── static/
│   ├── css/                    # CSS stylesheets
│   ├── images/                 # Logo and images
│   └── js/                     # JavaScript files
├── templates/
│   ├── index.html              # Home page with camera
│   ├── admin_login.html        # Admin login
│   ├── jadwal_bulanan.html     # Monthly schedule
│   ├── lihat_absensi.html      # View attendance reports
│   └── ...                     # Other pages
├── training_data/              # Dataset untuk model training (git ignored)
├── uploads/                    # Upload folder (git ignored)
└── .gitignore                  # Git configuration


## Configuration

### Edit Jadwal Kerja
1. Login sebagai admin
2. Go to "Atur Jadwal" 
3. Set waktu mulai absensi, batas terlambat, dan jam pulang
4. Atur hari libur dan keterangan khusus

### Fine-tuning Model
1. Kumpulkan dataset wajah guru dalam format: `nama-guru.mp4` atau folder images
2. Go to admin panel → "Fine-tuning Model"
3. Upload dataset dan training model
4. Model akan di-train dan di-save secara otomatis

## Troubleshooting

### ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Camera tidak terdeteksi
- Pastikan webcam connect dan tidak digunakan aplikasi lain
- Check permission kamera di Windows Settings
- Coba gunakan device index berbeda di `cv2.VideoCapture(0)`

### Port 5000 sudah digunakan
Ubah port di `app.py`:
```python
app.run(host='0.0.0.0', port=5001)  # Change to 5001
```

## Database

Sistem menggunakan SQLite3:
- Database file: `absensi.db`
- Tables: absensi, jadwal, admin_settings, master_guru, model_training

### Backup Database
```bash
python maintenance.py --backup
```

## Performance Tips

1. **Reduce frame resolution** untuk device lemah
2. **Adjust confidence threshold** di settings untuk deteksi lebih akurat
3. **Use GPU** jika available (set di PyTorch settings)
4. **Clear old attendance data** secara berkala

## Future Enhancements

- [ ] Multi-language support (English, Indonesian, etc)
- [ ] Cloud backup untuk database
- [ ] Mobile app untuk lihat laporan
- [ ] Integrasi dengan sistem payroll
- [ ] Dashboard analytics yang lebih detail
- [ ] Notifikasi real-time untuk keterlambatan

## Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Author

**Satrio Put**
- GitHub: [@sisatput](https://github.com/sisatput)
- Email: satriayuda89@gmail.com

## Disclaimer

Sistem ini dibuat untuk keperluan administrasi pendidikan. Penggunaan teknologi face recognition harus sesuai dengan regulasi privasi data di wilayah Anda.

## Support

Jika ada pertanyaan atau issues:
1. Check existing issues di GitHub
2. Create new issue dengan detail lengkap
3. Include screenshot/logs jika ada error

---

**Last Updated**: April 2026  
**Version**: 1.0.0

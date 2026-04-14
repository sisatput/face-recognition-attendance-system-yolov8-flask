# 📋 Dokumentasi Fitur Upload Data Training untuk Update Model

## 🎯 Tujuan

Fitur ini memungkinkan admin untuk mengunggah data training baru guna memperbarui model deteksi wajah YOLO yang digunakan dalam sistem absensi.

## 🔧 Fitur yang Telah Ditambahkan

### 1. **Upload Data Training** (`/upload_training_data`)

- **Akses**: Hanya admin yang sudah login
- **Fungsi**: Upload dataset untuk training model baru
- **Format Didukung**: ZIP (dataset YOLO), JPG, JPEG, PNG, BMP, TIFF (single image)

### 2. **Lihat Dataset** (`/view_datasets`)

- **Akses**: Hanya admin yang sudah login
- **Fungsi**: Melihat dan mengelola dataset yang sudah diupload
- **Fitur**: Statistik dataset, hapus dataset

### 3. **API Endpoints**

- `POST /delete_dataset`: Hapus dataset tertentu

## 📊 Batasan Upload Data

### 🚫 **Batasan Umum**

| Parameter                | Batasan                        | Keterangan                                    |
| ------------------------ | ------------------------------ | --------------------------------------------- |
| **Ukuran File Maksimum** | 500 MB                         | Per file upload                               |
| **Format File Didukung** | ZIP, JPG, JPEG, PNG, BMP, TIFF | ZIP untuk dataset, gambar untuk single upload |
| **Resolusi Gambar**      | 100x100 - 4000x4000 pixel      | Minimum dan maksimum dimensi                  |

### 📦 **Batasan Dataset ZIP (Format YOLO)**

| Parameter                          | Batasan                 | Keterangan                                           |
| ---------------------------------- | ----------------------- | ---------------------------------------------------- |
| **Struktur Folder Wajib**          | `images/` dan `labels/` | Folder images berisi gambar, labels berisi file .txt |
| **Jumlah Gambar Minimum**          | 10 gambar               | Untuk validasi dasar                                 |
| **Jumlah Gambar Direkomendasikan** | 50+ gambar per kelas    | Untuk hasil training yang optimal                    |
| **Format Label**                   | YOLO (.txt)             | `class_id x_center y_center width height`            |
| **Koordinat Label**                | 0.0 - 1.0               | Normalized coordinates                               |

### 🖼️ **Batasan Single Image**

| Parameter           | Batasan                          | Keterangan                          |
| ------------------- | -------------------------------- | ----------------------------------- |
| **Format Didukung** | JPG, JPEG, PNG, BMP, TIFF        | Format gambar standar               |
| **Validasi Gambar** | Otomatis                         | Cek apakah file adalah gambar valid |
| **Penggunaan**      | Untuk penambahan data individual | Disimpan di folder `single_images/` |

## 🔍 **Validasi Otomatis**

### ✅ **Validasi File ZIP**

1. **Struktur Dataset**: Mengecek keberadaan folder `images/` dan `labels/`
2. **Konsistensi File**: Memastikan setiap gambar memiliki label yang sesuai
3. **Format Label**: Validasi format YOLO (5 nilai per baris)
4. **Range Koordinat**: Memastikan koordinat dalam range 0.0-1.0
5. **Jumlah Minimum**: Minimal 10 gambar valid untuk dataset

### ✅ **Validasi Gambar**

1. **File Integrity**: Cek apakah file bisa dibaca sebagai gambar
2. **Dimensi**: Validasi resolusi dalam range yang diizinkan
3. **Format**: Memastikan format file didukung oleh OpenCV

## 📁 **Organisasi Data**

### 📂 **Struktur Folder**

```
training_data/
├── dataset_20250109_143022/     # Dataset ZIP yang diekstrak
│   ├── images/
│   ├── labels/
│   └── classes.txt              # Auto-generated
├── dataset_20250109_150315/     # Dataset lainnya
└── single_images/               # Single image uploads
    ├── 20250109_143500_image1.jpg
    └── 20250109_143501_image2.png
```

### 🏷️ **Penamaan File**

- **Dataset ZIP**: `dataset_YYYYMMDD_HHMMSS`
- **Single Images**: `YYYYMMDD_HHMMSS_originalname.ext`
- **Classes File**: Auto-generated berdasarkan master_guru

## 🎯 **Kualitas Dataset**

### 🌟 **Kategori Kualitas**

| Kategori   | Jumlah Gambar | Badge              | Rekomendasi                 |
| ---------- | ------------- | ------------------ | --------------------------- |
| **Baik**   | ≥50 gambar    | ⭐ Kualitas Baik   | Siap untuk training         |
| **Sedang** | 20-49 gambar  | ⚠️ Kualitas Sedang | Tambah lebih banyak data    |
| **Rendah** | <20 gambar    | ❌ Kualitas Rendah | Perlu penambahan signifikan |

### 📈 **Tips Dataset Berkualitas**

- **Variasi Pencahayaan**: Gunakan foto dalam berbagai kondisi cahaya
- **Sudut Berbeda**: Ambil foto dari berbagai sudut wajah
- **Ekspresi Beragam**: Sertakan berbagai ekspresi wajah
- **Kualitas Jelas**: Pastikan wajah tidak blur atau kabur
- **Konsistensi**: Gunakan resolusi yang konsisten untuk dataset

## 🛡️ **Keamanan**

### 🔒 **Kontrol Akses**

- **Autentikasi**: Hanya admin yang sudah login dapat mengakses
- **Session Validation**: Pengecekan session pada setiap request
- **Filename Security**: Menggunakan `secure_filename()` untuk keamanan

### 🧹 **Pembersihan Otomatis**

- **Temporary Files**: File upload sementara dihapus setelah diproses
- **Error Handling**: Cleanup otomatis jika terjadi error selama proses
- **Storage Management**: Folder kosong dibersihkan otomatis

## 📊 **Monitoring & Statistik**

### 📈 **Dashboard Statistik**

- **Total Dataset**: Jumlah dataset yang tersimpan
- **Total Gambar**: Agregasi semua gambar dalam sistem
- **Total Label**: Jumlah file label yang tervalidasi
- **Total Storage**: Ukuran penyimpanan yang digunakan

### 📋 **Log Aktivitas**

- **Upload Success**: Log ketika upload berhasil
- **Validation Errors**: Log error validasi untuk debugging
- **Dataset Deletion**: Log penghapusan dataset
- **Storage Cleanup**: Log pembersihan storage

## 🔧 **Penggunaan**

### 👨‍💼 **Untuk Admin**

1. **Login** ke sistem sebagai admin
2. **Akses Menu** "Upload Data Model" di dashboard admin
3. **Pilih File** - drag & drop atau klik untuk browse
4. **Upload** - sistem akan melakukan validasi otomatis
5. **Review** hasil upload dan peringatan jika ada
6. **Kelola Dataset** melalui menu "Lihat Dataset"

### 🔄 **Workflow Update Model**

1. **Persiapan Data**: Siapkan dataset dalam format YOLO
2. **Upload Dataset**: Gunakan fitur upload untuk menambah data
3. **Validasi**: Sistem melakukan validasi otomatis
4. **Review**: Cek statistik dan kualitas dataset
5. **Training**: Gunakan dataset untuk training model baru (manual)
6. **Deployment**: Replace model lama dengan model baru

## ⚠️ **Perhatian Penting**

### 🚨 **Limitasi Sistem**

- **Training Manual**: Sistem hanya menyediakan upload data, training model harus dilakukan manual
- **Model Replacement**: Update model baru memerlukan restart aplikasi
- **Storage Space**: Monitor penggunaan disk space secara berkala
- **Performance**: Upload dataset besar dapat memakan waktu cukup lama

### 💡 **Best Practices**

- **Backup**: Selalu backup dataset penting sebelum menghapus
- **Incremental**: Tambahkan data secara bertahap untuk testing
- **Quality Over Quantity**: Fokus pada kualitas data daripada kuantitas
- **Regular Cleanup**: Hapus dataset lama yang tidak terpakai

## 📞 **Support & Troubleshooting**

### 🐛 **Common Issues**

- **Upload Timeout**: Untuk file besar, pastikan koneksi stabil
- **Format Error**: Periksa kembali struktur folder dataset
- **Storage Full**: Hapus dataset lama untuk mengosongkan ruang
- **Permission Error**: Pastikan folder memiliki permission write

### 🔧 **Technical Requirements**

- **Python**: 3.8+
- **Flask**: 2.3.3
- **OpenCV**: 4.8.1.78
- **Ultralytics**: 8.0.196
- **Storage**: Minimal 2GB free space untuk operasi optimal

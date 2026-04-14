# 🎯 Sistem Recognition Model AI - Panduan Lengkap

## 🔄 Cara Kerja Model Recognition dalam Sistem Absensi

### 📋 **Alur Sistem Recognition**

```
1. Upload Dataset → 2. Mapping dengan Guru → 3. Aktivasi Model → 4. Detection & Recognition
```

### 🎯 **Langkah-langkah Implementasi**

#### **1. 📤 Upload Dataset Training**

- **Akses**: Menu "Upload Data Model" di dashboard admin
- **Format**: ZIP (struktur YOLO) atau gambar individual
- **Pilih Guru**: Setiap dataset dapat dikaitkan dengan guru tertentu
- **Validasi**: Sistem otomatis validasi struktur dan kualitas data

#### **2. 🤖 Buat Model Mapping**

- **Akses**: Menu "Kelola Model AI" di dashboard admin
- **Pilih Dataset**: Pilih dataset yang sudah diupload
- **Auto Mapping**: Sistem otomatis membuat mapping class_id ↔ guru
- **Confidence Threshold**: Atur threshold untuk akurasi detection

#### **3. ✅ Aktivasi Model**

- **Pilih Model**: Pilih model yang akan digunakan untuk detection
- **Aktivasi**: Hanya satu model yang bisa aktif pada satu waktu
- **Class Mapping**: Model aktif menggunakan mapping untuk recognize wajah

#### **4. 🎥 Detection & Recognition**

- **Real-time**: Kamera mendeteksi wajah secara real-time
- **Class Mapping**: Sistem menggunakan mapping untuk identify guru
- **Confidence Check**: Hanya detection dengan confidence ≥ threshold yang diterima
- **Auto Attendance**: Otomatis catat absensi jika guru berhasil dikenali

---

## 🗄️ **Struktur Database**

### **Tabel `model_training`**

```sql
- id: Primary key
- model_name: Nama model (user-defined)
- model_path: Path file model (.pt)
- is_active: Status aktif model (boolean)
- total_classes: Jumlah kelas dalam model
- training_date: Tanggal pembuatan
- description: Deskripsi model
```

### **Tabel `class_mapping`**

```sql
- model_id: Reference ke model_training
- class_id: ID kelas dalam model YOLO (0, 1, 2, ...)
- guru_id: Reference ke master_guru
- class_name: Nama guru
- confidence_threshold: Threshold minimum (default: 0.7)
```

### **Tabel `training_dataset`**

```sql
- dataset_path: Path dataset
- guru_id: Reference ke guru (optional)
- images_count: Jumlah gambar
- is_used_for_training: Status penggunaan
- training_model_id: Model yang menggunakan dataset ini
```

---

## 🎯 **Sistem Recognition dalam Detail**

### **📊 Class ID Mapping**

```
Model YOLO mendeteksi class_id (0, 1, 2, 3, ...)
↓
Sistem lookup di tabel class_mapping
↓
Dapatkan guru_id dan nama guru
↓
Proses absensi dengan nama guru yang dikenali
```

### **🎚️ Confidence Threshold**

- **Default**: 0.7 (70%)
- **Customizable**: Dapat diatur per guru/kelas
- **Function**: Filter false positive detection
- **Color Coding**:
  - 🟢 **Hijau**: Confidence ≥ threshold (recognized)
  - 🔴 **Merah**: Confidence < threshold (unknown)
  - 🟡 **Kuning**: Fallback ke nama default model

### **🔄 Proses Detection**

```python
# Pseudocode
for detected_face in frame:
    class_id = model.predict(face)
    confidence = model.confidence

    if class_id in class_mappings:
        mapping = class_mappings[class_id]
        if confidence >= mapping.threshold:
            guru_name = mapping.guru_name
            process_attendance(guru_name)
        else:
            display_unknown()
    else:
        fallback_to_default_name()
```

---

## 📈 **Keunggulan Sistem**

### **✅ Advantages**

1. **Dynamic Mapping**: Model dapat dipetakan ke guru tanpa retrain
2. **Multiple Models**: Dapat menyimpan multiple model untuk berbagai skenario
3. **Confidence Control**: Kontrol akurasi per guru individual
4. **Audit Trail**: Track dataset usage dan model performance
5. **Flexible**: Guru baru dapat ditambah tanpa mengubah model
6. **Fallback Support**: Sistem tetap berfungsi dengan model default

### **🎯 Use Cases**

- **Scenario 1**: Model umum dengan mapping ke semua guru
- **Scenario 2**: Model spesifik per kelas/departemen
- **Scenario 3**: Model experimental untuk testing
- **Scenario 4**: Model backup untuk reliability

---

## 🛠️ **Penggunaan Praktis**

### **📋 Workflow Admin**

#### **Setup Awal**

1. ✅ Upload dataset untuk setiap guru (min 20 foto/guru)
2. ✅ Buat model mapping dengan pilih dataset
3. ✅ Aktivasi model untuk mulai recognition
4. ✅ Monitor performance dan adjust threshold jika perlu

#### **Penambahan Guru Baru**

1. ✅ Upload dataset guru baru
2. ✅ Buat model mapping baru atau update existing
3. ✅ Aktivasi model updated
4. ✅ Test recognition guru baru

#### **Maintenance Rutin**

1. ✅ Monitor accuracy dan false positive
2. ✅ Update threshold jika diperlukan
3. ✅ Backup model yang performant
4. ✅ Cleanup dataset lama yang tidak terpakai

### **📊 Monitoring & Analytics**

- **Model Performance**: Track accuracy per model
- **Recognition Rate**: Monitor recognition success rate
- **False Positive**: Track unknown detection
- **Attendance Correlation**: Validasi dengan absensi manual

---

## 🚀 **Tips Optimasi**

### **📸 Dataset Quality**

- **Lighting**: Foto dengan berbagai kondisi pencahayaan
- **Angles**: Multiple sudut wajah (frontal, 3/4, profile)
- **Expressions**: Berbagai ekspresi wajah
- **Accessories**: Dengan/tanpa kacamata, masker, dll
- **Background**: Berbagai background

### **⚙️ Model Configuration**

- **Confidence Threshold**:
  - Tinggi (0.8-0.9): Lebih akurat, less detection
  - Sedang (0.6-0.7): Balanced
  - Rendah (0.4-0.5): More detection, less akurat

### **🎯 Best Practices**

1. **Start Small**: Mulai dengan 3-5 guru untuk testing
2. **Iterative**: Tambah guru bertahap dan monitor
3. **Quality over Quantity**: 50 foto berkualitas > 200 foto buruk
4. **Regular Update**: Update dataset secara berkala
5. **Backup Strategy**: Selalu backup model yang sudah optimal

---

## 🔧 **Troubleshooting**

### **❌ Common Issues**

#### **Model tidak mengenali guru**

- ✅ Cek confidence threshold (mungkin terlalu tinggi)
- ✅ Verify class mapping (class_id benar?)
- ✅ Cek kualitas dataset training
- ✅ Ensure model sudah diaktivasi

#### **False positive tinggi**

- ✅ Naikkan confidence threshold
- ✅ Improve dataset quality
- ✅ Tambah negative samples

#### **Performance lambat**

- ✅ Optimize model size
- ✅ Reduce image resolution
- ✅ Check hardware specifications

### **🔍 Debug Commands**

```bash
# Cek model aktif
SELECT * FROM model_training WHERE is_active = 1;

# Cek class mapping
SELECT cm.*, mg.nama FROM class_mapping cm
JOIN master_guru mg ON cm.guru_id = mg.id
WHERE cm.model_id = [MODEL_ID];

# Monitor detection log
tail -f app.log | grep "Detection"
```

---

## 📋 **Summary**

Sistem recognition yang telah diimplementasikan memberikan **fleksibilitas tinggi** dalam manajemen model AI untuk absensi. Admin dapat:

1. **Upload data training** dengan mudah
2. **Mapping dataset ke guru** secara otomatis
3. **Manage multiple models** untuk berbagai skenario
4. **Control accuracy** dengan confidence threshold
5. **Monitor performance** secara real-time

Sistem ini memastikan bahwa **model yang diupload dapat dikenali sebagai anggota dalam proses absensi** melalui mekanisme class mapping yang sophisticated dan user-friendly.

🎯 **Result**: Guru yang ada dalam dataset training akan otomatis dikenali oleh sistem dan absensi mereka akan tercatat secara otomatis saat terdeteksi oleh kamera dengan confidence yang cukup tinggi.

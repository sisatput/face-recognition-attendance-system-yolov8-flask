# Bug Fix: strftime() Error pada Template

## Masalah
Error `'str' object has no attribute 'strftime'` terjadi pada template `model_management.html` ketika mencoba mengformat tanggal menggunakan `strftime()`.

## Penyebab
Data tanggal dari database SQLite dikembalikan sebagai string, bukan objek datetime Python. Template Jinja2 mencoba memanggil method `strftime()` pada string yang menyebabkan error.

## Solusi
Menambahkan konversi string ke objek datetime di fungsi `model_management()` dalam `app.py`:

### Sebelum (Hanya untuk datasets):
```python
# Konversi datasets ke format yang bisa digunakan template
datasets = []
for dataset in datasets_raw:
    dataset_dict = dict(dataset)
    
    # Konversi upload_date string ke datetime jika perlu
    if dataset_dict.get('upload_date'):
        try:
            if isinstance(dataset_dict['upload_date'], str):
                dataset_dict['upload_date'] = datetime.strptime(dataset_dict['upload_date'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            dataset_dict['upload_date'] = None
    
    datasets.append(dataset_dict)
```

### Sesudah (Untuk semua data):
```python
# Konversi models ke format yang bisa digunakan template
models_converted = []
for model in models:
    model_dict = dict(model)
    
    # Konversi training_date string ke datetime jika perlu
    if model_dict.get('training_date'):
        try:
            if isinstance(model_dict['training_date'], str):
                model_dict['training_date'] = datetime.strptime(model_dict['training_date'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
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
                active_model_converted['training_date'] = datetime.strptime(active_model_converted['training_date'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            active_model_converted['training_date'] = None

# Konversi datasets ke format yang bisa digunakan template
datasets = []
for dataset in datasets_raw:
    dataset_dict = dict(dataset)
    
    # Konversi upload_date string ke datetime jika perlu
    if dataset_dict.get('upload_date'):
        try:
            if isinstance(dataset_dict['upload_date'], str):
                dataset_dict['upload_date'] = datetime.strptime(dataset_dict['upload_date'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            dataset_dict['upload_date'] = None
    
    datasets.append(dataset_dict)

return render_template('model_management.html', 
                     models=models_converted, 
                     active_model=active_model_converted, 
                     teachers=teachers,
                     datasets=datasets)
```

## Field yang Diperbaiki
1. `model.training_date` - Tanggal training model
2. `active_model.training_date` - Tanggal training model aktif
3. `dataset.upload_date` - Tanggal upload dataset

## Template yang Terpengaruh
- `model_management.html` - Menggunakan `strftime()` pada 3 lokasi:
  - Line 65: `active_model.training_date.strftime('%d/%m/%Y %H:%M')`
  - Line 109: `dataset.upload_date.strftime('%d/%m/%Y')`
  - Line 153: `model.training_date.strftime('%d/%m/%Y')`

## Hasil
✅ Error `'str' object has no attribute 'strftime'` telah diperbaiki
✅ Template dapat menampilkan tanggal dengan format yang benar
✅ Aplikasi dapat berjalan tanpa error
✅ Test suite berjalan dengan baik

## Catatan
Perbaikan ini memastikan bahwa semua field tanggal dikonversi ke objek datetime Python sebelum dikirim ke template, sehingga method `strftime()` dapat digunakan dengan aman dalam template Jinja2.

# fine_tuning_manager.py
# Sistem Fine-Tuning Terotomatisasi untuk Update Model

import os
import shutil
import sqlite3
import threading
import json
import time
import random
import glob
from datetime import datetime
from ultralytics import YOLO
import yaml
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fine_tuning.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FineTuningManager')

class FineTuningManager:
    def __init__(self, base_model_path='best.pt', database_path='absensi.db'):
        self.base_model_path = base_model_path
        self.database_path = database_path
        self.training_queue = []
        self.is_training = False
        self.current_training_status = {}
        
        # Konfigurasi fine-tuning
        self.fine_tuning_config = {
            'epochs': 20,  # Lebih sedikit dari training full
            'lr0': 0.001,  # Learning rate lebih rendah
            'batch_size': 8,
            'img_size': 640,
            'patience': 10,
            'min_samples_per_class': 15,  # Minimal gambar per orang baru
            'preserve_samples_per_class': 3  # Sample lama yang dipertahankan
        }
    
    def add_new_person_to_queue(self, person_name, image_folder_path, guru_id=None):
        """Tambahkan orang baru ke queue training"""
        training_task = {
            'id': f"ft_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'person_name': person_name,
            'image_folder': image_folder_path,
            'guru_id': guru_id,
            'status': 'queued',
            'created_at': datetime.now(),
            'progress': 0
        }
        
        self.training_queue.append(training_task)
        logger.info(f"Added training task for {person_name} to queue")
        
        # Start training jika tidak ada yang sedang berjalan
        if not self.is_training:
            self._start_training_worker()
        
        return training_task['id']
    
    def _start_training_worker(self):
        """Start background training worker"""
        if self.is_training:
            return
        
        training_thread = threading.Thread(target=self._training_worker)
        training_thread.daemon = True
        training_thread.start()
    
    def _training_worker(self):
        """Background worker untuk menjalankan fine-tuning"""
        self.is_training = True
        
        while self.training_queue:
            task = self.training_queue.pop(0)
            
            try:
                logger.info(f"Starting fine-tuning for {task['person_name']}")
                self.current_training_status = task
                task['status'] = 'training'
                task['started_at'] = datetime.now()
                
                # Jalankan fine-tuning
                success = self._perform_fine_tuning(task)
                
                if success:
                    task['status'] = 'completed'
                    task['progress'] = 100
                    logger.info(f"Fine-tuning completed for {task['person_name']}")
                else:
                    task['status'] = 'failed'
                    logger.error(f"Fine-tuning failed for {task['person_name']}")
                
                task['completed_at'] = datetime.now()
                
                # Update database
                self._update_training_record(task)
                
            except Exception as e:
                logger.error(f"Error in fine-tuning {task['person_name']}: {str(e)}")
                task['status'] = 'failed'
                task['error'] = str(e)
        
        self.is_training = False
        self.current_training_status = {}
        logger.info("Training worker finished")
    
    def _perform_fine_tuning(self, task):
        """Lakukan fine-tuning dengan data baru"""
        try:
            # 1. Validasi data baru
            if not self._validate_new_data(task):
                return False
            
            # 2. Siapkan dataset campuran (baru + sample lama)
            mixed_dataset_path = self._prepare_mixed_dataset(task)
            if not mixed_dataset_path:
                return False
            
            # 3. Buat konfigurasi dataset
            dataset_config = self._create_dataset_config(mixed_dataset_path, task)
            
            # 4. Load model base dan mulai fine-tuning
            model = YOLO(self.base_model_path)
            
            # Update progress
            task['progress'] = 20
            
            # Fine-tuning dengan parameter khusus
            results = model.train(
                data=dataset_config,
                epochs=self.fine_tuning_config['epochs'],
                lr0=self.fine_tuning_config['lr0'],
                batch=self.fine_tuning_config['batch_size'],
                imgsz=self.fine_tuning_config['img_size'],
                patience=self.fine_tuning_config['patience'],
                save=True,
                project='fine_tuning_runs',
                name=f"ft_{task['person_name']}_{task['id']}",
                exist_ok=True,
                verbose=True
            )
            
            task['progress'] = 80
            
            # 5. Backup model lama dan deploy model baru
            if self._deploy_new_model(results, task):
                task['progress'] = 90
                
                # 6. Update class mapping di database
                self._update_class_mapping(task)
                task['progress'] = 100
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in fine-tuning process: {str(e)}")
            return False
    
    def _validate_image_file(self, image_path):
        """Validasi file gambar secara detail"""
        try:
            from PIL import Image
            
            # Buka gambar untuk validasi
            with Image.open(image_path) as img:
                # Check format
                if img.format not in ['JPEG', 'PNG', 'BMP']:
                    return False, f"Format tidak didukung: {img.format}"
                
                # Check dimensi
                width, height = img.size
                if width < 100 or height < 100:
                    return False, f"Gambar terlalu kecil: {width}x{height}"
                
                if width > 4000 or height > 4000:
                    return False, f"Gambar terlalu besar: {width}x{height}"
                
                # Check mode
                if img.mode not in ['RGB', 'L', 'RGBA']:
                    return False, f"Mode gambar tidak didukung: {img.mode}"
                
                return True, "Valid"
                
        except Exception as e:
            return False, f"Error validating image: {str(e)}"
    
    def _validate_new_data(self, task):
        """Validasi data gambar baru"""
        image_folder = task['image_folder']
        
        if not os.path.exists(image_folder):
            logger.error(f"Image folder tidak ditemukan: {image_folder}")
            return False
        
        # Hitung jumlah gambar valid
        valid_images = []
        invalid_images = []
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp']
        
        for file in os.listdir(image_folder):
            if any(file.lower().endswith(fmt) for fmt in supported_formats):
                file_path = os.path.join(image_folder, file)
                
                # Validasi detail
                is_valid, msg = self._validate_image_file(file_path)
                if is_valid:
                    valid_images.append(file)
                else:
                    invalid_images.append((file, msg))
                    logger.warning(f"Invalid image {file}: {msg}")
        
        # Log hasil validasi
        if invalid_images:
            logger.warning(f"Found {len(invalid_images)} invalid images")
            for file, msg in invalid_images:
                logger.warning(f"  - {file}: {msg}")
        
        if len(valid_images) < self.fine_tuning_config['min_samples_per_class']:
            logger.error(f"Jumlah gambar valid tidak mencukupi: {len(valid_images)} < {self.fine_tuning_config['min_samples_per_class']}")
            return False
        
        task['image_count'] = len(valid_images)
        task['valid_images'] = valid_images
        task['invalid_images'] = invalid_images
        
        logger.info(f"Validasi berhasil: {len(valid_images)} gambar valid, {len(invalid_images)} invalid untuk {task['person_name']}")
        return True
    
    def _prepare_mixed_dataset(self, task):
        """Siapkan dataset campuran untuk mencegah catastrophic forgetting"""
        temp_dataset_path = None
        try:
            # Buat folder dataset sementara
            temp_dataset_path = f"temp_ft_dataset_{task['id']}"
            os.makedirs(temp_dataset_path, exist_ok=True)
            
            images_path = os.path.join(temp_dataset_path, 'images')
            labels_path = os.path.join(temp_dataset_path, 'labels')
            os.makedirs(images_path, exist_ok=True)
            os.makedirs(labels_path, exist_ok=True)
            
            # 1. Copy data baru
            new_class_id = self._get_next_class_id()
            logger.info(f"Assigning new class ID: {new_class_id}")
            
            self._copy_new_person_data(task, images_path, labels_path, new_class_id)
            
            # 2. Sample data lama untuk preservasi (optional - tidak gagalkan jika error)
            try:
                self._copy_preserved_samples(images_path, labels_path)
            except Exception as e:
                logger.warning(f"Could not copy preserved samples: {str(e)}")
                logger.info("Continuing with new data only")
            
            # 3. Validasi dataset minimal
            image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            label_files = [f for f in os.listdir(labels_path) if f.lower().endswith('.txt')]
            
            if len(image_files) < self.fine_tuning_config['min_samples_per_class']:
                logger.error(f"Insufficient images in mixed dataset: {len(image_files)} < {self.fine_tuning_config['min_samples_per_class']}")
                return None
            
            logger.info(f"Mixed dataset prepared: {len(image_files)} images, {len(label_files)} labels")
            
            task['mixed_dataset_path'] = temp_dataset_path
            task['new_class_id'] = new_class_id
            
            return temp_dataset_path
            
        except Exception as e:
            logger.error(f"Error preparing mixed dataset: {str(e)}")
            # Cleanup jika ada error
            if temp_dataset_path and os.path.exists(temp_dataset_path):
                try:
                    shutil.rmtree(temp_dataset_path, ignore_errors=True)
                except:
                    pass
            return None
    
    def _copy_new_person_data(self, task, images_path, labels_path, class_id):
        """Copy data orang baru ke dataset"""
        image_folder = task['image_folder']
        person_name = task['person_name']
        
        # Sanitize person name untuk nama file
        safe_person_name = "".join(c for c in person_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_person_name = safe_person_name.replace(' ', '_')
        
        copied_count = 0
        
        try:
            # Gunakan valid_images jika tersedia dari validasi
            images_to_copy = task.get('valid_images', [])
            
            # Jika tidak ada valid_images, ambil semua gambar
            if not images_to_copy:
                all_files = os.listdir(image_folder)
                images_to_copy = [f for f in all_files if any(f.lower().endswith(fmt) for fmt in ['.jpg', '.jpeg', '.png', '.bmp'])]
            
            for i, image_file in enumerate(images_to_copy):
                try:
                    # Copy image
                    src_image = os.path.join(image_folder, image_file)
                    dst_image = os.path.join(images_path, f"{safe_person_name}_{i:03d}.jpg")
                    shutil.copy2(src_image, dst_image)
                    
                    # Buat label (asumsi seluruh gambar adalah wajah)
                    label_file = os.path.join(labels_path, f"{safe_person_name}_{i:03d}.txt")
                    with open(label_file, 'w') as f:
                        # Format YOLO: class_id x_center y_center width height (normalized)
                        # Asumsi wajah di tengah gambar dengan 80% ukuran
                        f.write(f"{class_id} 0.5 0.5 0.8 0.8\n")
                    
                    copied_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error copying image {image_file}: {str(e)}")
                    continue
            
            logger.info(f"Copied {copied_count} images for {person_name} with class_id {class_id}")
            
        except Exception as e:
            logger.error(f"Error in _copy_new_person_data: {str(e)}")
            raise
    
    def _copy_preserved_samples(self, images_path, labels_path):
        """Copy sample dari kelas lama untuk preservasi"""
        try:
            # Ambil daftar kelas yang sudah ada
            existing_classes = self._get_existing_classes()
            
            if not existing_classes:
                logger.info("No existing classes found, skipping preservation")
                return
            
            preserved_count = 0
            for class_info in existing_classes:
                class_id = class_info['class_id']
                guru_name = class_info['guru_name']
                
                # Ambil beberapa sample dari dataset lama
                samples = self._get_class_samples(class_id, self.fine_tuning_config['preserve_samples_per_class'])
                
                for i, sample in enumerate(samples):
                    try:
                        # Copy image jika ada
                        if sample.get('image_path') and os.path.exists(sample['image_path']):
                            # Buat nama file yang safe
                            safe_guru_name = "".join(c for c in guru_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            dst_image = os.path.join(images_path, f"preserved_{safe_guru_name}_{class_id}_{i:03d}.jpg")
                            shutil.copy2(sample['image_path'], dst_image)
                            
                            # Copy atau buat label
                            label_file = os.path.join(labels_path, f"preserved_{safe_guru_name}_{class_id}_{i:03d}.txt")
                            
                            if sample.get('label_path') and os.path.exists(sample['label_path']):
                                # Copy existing label
                                shutil.copy2(sample['label_path'], label_file)
                            else:
                                # Buat label default
                                with open(label_file, 'w') as f:
                                    f.write(f"{class_id} 0.5 0.5 0.8 0.8\n")
                            
                            preserved_count += 1
                            logger.debug(f"Preserved sample for {guru_name}: {os.path.basename(dst_image)}")
                            
                    except Exception as e:
                        logger.warning(f"Error copying sample for {guru_name}: {str(e)}")
                        continue
            
            logger.info(f"Preserved {preserved_count} samples from existing classes")
        
        except Exception as e:
            logger.warning(f"Error copying preserved samples: {str(e)}")
            # Jangan gagalkan seluruh proses jika preservasi gagal
            logger.info("Continuing fine-tuning without preserved samples")
    
    def _get_next_class_id(self):
        """Dapatkan class ID berikutnya"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT MAX(class_id) FROM class_mapping")
            result = cursor.fetchone()
            
            max_class_id = result[0] if result[0] is not None else -1
            conn.close()
            
            return max_class_id + 1
            
        except Exception as e:
            logger.error(f"Error getting next class ID: {str(e)}")
            return 0
    
    def _get_existing_classes(self):
        """Ambil daftar kelas yang sudah ada"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cm.class_id, cm.class_name as guru_name, mg.nama
                FROM class_mapping cm
                JOIN master_guru mg ON cm.guru_id = mg.id
                WHERE cm.model_id = (SELECT id FROM model_training WHERE is_active = 1)
                ORDER BY cm.class_id
            """)
            
            classes = []
            for row in cursor.fetchall():
                classes.append({
                    'class_id': row[0],
                    'guru_name': row[1],
                    'nama': row[2]
                })
            
            conn.close()
            return classes
            
        except Exception as e:
            logger.error(f"Error getting existing classes: {str(e)}")
            return []
    
    def _get_class_samples(self, class_id, num_samples):
        """Ambil sample dari kelas tertentu dari training_data yang ada"""
        samples = []
        
        try:
            # Cari di folder training_data
            training_data_path = 'training_data'
            if not os.path.exists(training_data_path):
                logger.warning("Training data folder not found")
                return samples
            
            # Cari dataset yang ada
            for item in os.listdir(training_data_path):
                item_path = os.path.join(training_data_path, item)
                if os.path.isdir(item_path):
                    images_path = os.path.join(item_path, 'images')
                    labels_path = os.path.join(item_path, 'labels')
                    
                    # Check jika ada folder images dan labels
                    if os.path.exists(images_path) and os.path.exists(labels_path):
                        # Ambil sample dari dataset ini
                        image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                        
                        # Ambil beberapa sample random
                        sample_count = min(num_samples, len(image_files))
                        if sample_count > 0:
                            selected_images = random.sample(image_files, sample_count)
                            
                            for img_file in selected_images:
                                img_path = os.path.join(images_path, img_file)
                                # Cari label file yang sesuai
                                label_file = os.path.splitext(img_file)[0] + '.txt'
                                label_path = os.path.join(labels_path, label_file)
                                
                                samples.append({
                                    'image_path': img_path,
                                    'label_path': label_path
                                })
                                
                                # Batasi total sample
                                if len(samples) >= num_samples:
                                    break
                    
                    # Check juga di single_images folder
                    single_images_path = os.path.join(item_path, 'single_images')
                    if os.path.exists(single_images_path):
                        for teacher_folder in os.listdir(single_images_path):
                            teacher_path = os.path.join(single_images_path, teacher_folder)
                            if os.path.isdir(teacher_path):
                                image_files = [f for f in os.listdir(teacher_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                                
                                sample_count = min(2, len(image_files))  # Ambil max 2 dari single images
                                if sample_count > 0:
                                    selected_images = random.sample(image_files, sample_count)
                                    
                                    for img_file in selected_images:
                                        img_path = os.path.join(teacher_path, img_file)
                                        samples.append({
                                            'image_path': img_path,
                                            'label_path': None  # Single images tidak punya label
                                        })
                                        
                                        if len(samples) >= num_samples:
                                            break
                    
                    if len(samples) >= num_samples:
                        break
            
            logger.info(f"Found {len(samples)} preserved samples for class_id {class_id}")
            return samples[:num_samples]  # Batasi sesuai yang diminta
            
        except Exception as e:
            logger.warning(f"Error getting class samples: {str(e)}")
            return []
    
    def _create_dataset_config(self, dataset_path, task):
        """Buat file konfigurasi dataset untuk YOLO"""
        config = {
            'path': os.path.abspath(dataset_path),
            'train': 'images',
            'val': 'images',  # Untuk fine-tuning, bisa sama dengan train
            'names': {}
        }
        
        # Tambahkan nama kelas
        existing_classes = self._get_existing_classes()
        for class_info in existing_classes:
            config['names'][class_info['class_id']] = class_info['guru_name']
        
        # Tambahkan kelas baru
        config['names'][task['new_class_id']] = task['person_name']
        
        # Simpan konfigurasi
        config_file = os.path.join(dataset_path, 'dataset.yaml')
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        # Buat juga classes.txt untuk referensi
        classes_file = os.path.join(dataset_path, 'classes.txt')
        with open(classes_file, 'w', encoding='utf-8') as f:
            # Sort berdasarkan class_id
            sorted_classes = sorted(config['names'].items())
            for class_id, class_name in sorted_classes:
                f.write(f"{class_id}: {class_name}\n")
        
        logger.info(f"Dataset config created with {len(config['names'])} classes")
        
        return config_file
    
    def _deploy_new_model(self, training_results, task):
        """Deploy model baru yang sudah di-fine-tune"""
        try:
            # Backup model lama
            backup_path = f"model_backups/best_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(self.base_model_path, backup_path)
            
            # Cari model terbaru dari hasil training
            run_dir = training_results.save_dir
            new_model_path = os.path.join(run_dir, 'weights', 'best.pt')
            
            if os.path.exists(new_model_path):
                # Replace model utama
                shutil.copy2(new_model_path, self.base_model_path)
                logger.info(f"Model deployed successfully from {new_model_path}")
                
                # Simpan info backup
                task['backup_model_path'] = backup_path
                task['new_model_path'] = new_model_path
                
                return True
            else:
                logger.error(f"New model not found at {new_model_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying new model: {str(e)}")
            return False
    
    def _update_class_mapping(self, task):
        """Update class mapping di database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Dapatkan model aktif
            cursor.execute("SELECT id FROM model_training WHERE is_active = 1")
            model_result = cursor.fetchone()
            
            if not model_result:
                logger.error("No active model found")
                return False
            
            model_id = model_result[0]
            
            # Tambahkan class mapping baru
            cursor.execute("""
                INSERT INTO class_mapping 
                (model_id, class_id, guru_id, class_name, confidence_threshold)
                VALUES (?, ?, ?, ?, ?)
            """, (
                model_id,
                task['new_class_id'],
                task.get('guru_id'),
                task['person_name'],
                0.7
            ))
            
            # Update total classes di model
            cursor.execute("""
                UPDATE model_training 
                SET total_classes = total_classes + 1
                WHERE id = ?
            """, (model_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Class mapping updated for {task['person_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating class mapping: {str(e)}")
            return False
    
    def _update_training_record(self, task):
        """Update record training di database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Buat tabel jika belum ada
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fine_tuning_history (
                    id TEXT PRIMARY KEY,
                    person_name TEXT,
                    guru_id INTEGER,
                    status TEXT,
                    image_count INTEGER,
                    new_class_id INTEGER,
                    created_at DATETIME,
                    started_at DATETIME,
                    completed_at DATETIME,
                    backup_model_path TEXT,
                    error_message TEXT
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO fine_tuning_history
                (id, person_name, guru_id, status, image_count, new_class_id, 
                 created_at, started_at, completed_at, backup_model_path, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task['id'],
                task['person_name'],
                task.get('guru_id'),
                task['status'],
                task.get('image_count'),
                task.get('new_class_id'),
                task['created_at'],
                task.get('started_at'),
                task.get('completed_at'),
                task.get('backup_model_path'),
                task.get('error')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating training record: {str(e)}")
    
    def get_training_status(self, task_id=None):
        """Dapatkan status training"""
        if task_id:
            # Return status untuk task tertentu
            if self.current_training_status.get('id') == task_id:
                return self.current_training_status
            else:
                # Cek di database untuk history
                try:
                    conn = sqlite3.connect(self.database_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM fine_tuning_history WHERE id = ?", (task_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        return {
                            'id': result[0],
                            'person_name': result[1],
                            'status': result[3],
                            'progress': 100 if result[3] == 'completed' else 0
                        }
                except:
                    pass
                
                return None
        else:
            # Return current training status
            return {
                'is_training': self.is_training,
                'current_task': self.current_training_status,
                'queue_length': len(self.training_queue)
            }
    
    def cleanup_temp_files(self):
        """Bersihkan file temporary"""
        try:
            # Hapus folder dataset temporary yang lebih lama dari 1 hari
            temp_folders = glob.glob('temp_ft_dataset_*')
            current_time = time.time()
            cleaned_count = 0
            
            for folder in temp_folders:
                if os.path.isdir(folder):
                    folder_time = os.path.getctime(folder)
                    if current_time - folder_time > 86400:  # 24 jam
                        try:
                            shutil.rmtree(folder, ignore_errors=True)
                            logger.info(f"Cleaned up temporary folder: {folder}")
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"Could not delete {folder}: {str(e)}")
            
            logger.info(f"Cleanup completed. Removed {cleaned_count} temporary folders.")
            return cleaned_count
                        
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
            return 0

# Singleton instance
fine_tuning_manager = FineTuningManager()

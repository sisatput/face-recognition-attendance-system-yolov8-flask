#!/usr/bin/env python3
# test_fine_tuning.py
# Script untuk test sistem fine-tuning

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add current directory to path
sys.path.append('.')

try:
    from fine_tuning_manager import FineTuningManager
    print("✅ Fine-tuning manager imported successfully")
except ImportError as e:
    print(f"❌ Error importing fine-tuning manager: {e}")
    sys.exit(1)

def create_test_images(count=20):
    """Buat gambar test dummy"""
    try:
        from PIL import Image
        import numpy as np
        
        # Buat folder temporary
        test_folder = tempfile.mkdtemp(prefix='test_person_')
        print(f"📁 Created test folder: {test_folder}")
        
        # Buat gambar dummy
        for i in range(count):
            # Buat gambar RGB random
            img_array = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            
            # Simpan gambar
            img_path = os.path.join(test_folder, f'test_image_{i:03d}.jpg')
            img.save(img_path, 'JPEG')
        
        print(f"✅ Created {count} test images")
        return test_folder
        
    except ImportError:
        print("❌ PIL not available, creating empty files instead")
        
        # Buat folder temporary
        test_folder = tempfile.mkdtemp(prefix='test_person_')
        print(f"📁 Created test folder: {test_folder}")
        
        # Buat file dummy
        for i in range(count):
            file_path = os.path.join(test_folder, f'test_image_{i:03d}.jpg')
            with open(file_path, 'wb') as f:
                # Write minimal JPEG header
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00')
                f.write(b'\x00' * 1000)  # Dummy data
        
        print(f"✅ Created {count} dummy files")
        return test_folder

def test_fine_tuning_manager():
    """Test fungsi-fungsi fine-tuning manager"""
    print("\n🧪 Testing Fine-Tuning Manager...")
    
    # Inisialisasi manager
    manager = FineTuningManager()
    print("✅ Manager initialized")
    
    # Test get next class ID
    try:
        next_id = manager._get_next_class_id()
        print(f"✅ Next class ID: {next_id}")
    except Exception as e:
        print(f"⚠️  Warning getting next class ID: {e}")
    
    # Test get existing classes
    try:
        classes = manager._get_existing_classes()
        print(f"✅ Found {len(classes)} existing classes")
        for cls in classes[:3]:  # Show first 3
            print(f"   - Class {cls['class_id']}: {cls['guru_name']}")
    except Exception as e:
        print(f"⚠️  Warning getting existing classes: {e}")
    
    # Test cleanup
    try:
        cleaned = manager.cleanup_temp_files()
        print(f"✅ Cleanup: removed {cleaned} items")
    except Exception as e:
        print(f"❌ Error in cleanup: {e}")

def test_validation():
    """Test validasi gambar"""
    print("\n🔍 Testing Image Validation...")
    
    # Buat test images
    test_folder = create_test_images(5)
    
    try:
        manager = FineTuningManager()
        
        # Test task dummy
        test_task = {
            'person_name': 'Test Person',
            'image_folder': test_folder,
            'guru_id': None
        }
        
        # Test validasi
        result = manager._validate_new_data(test_task)
        if result:
            print(f"✅ Validation passed: {test_task.get('image_count', 0)} valid images")
        else:
            print("❌ Validation failed")
            
    except Exception as e:
        print(f"❌ Error in validation: {e}")
    
    finally:
        # Cleanup
        if os.path.exists(test_folder):
            shutil.rmtree(test_folder, ignore_errors=True)
            print("🧹 Cleaned up test folder")

def test_database():
    """Test koneksi database"""
    print("\n💾 Testing Database Connection...")
    
    try:
        import sqlite3
        
        conn = sqlite3.connect('absensi.db')
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"✅ Database connected. Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Test fine_tuning_history table
        try:
            cursor.execute("SELECT COUNT(*) FROM fine_tuning_history")
            count = cursor.fetchone()[0]
            print(f"✅ Fine-tuning history table: {count} records")
        except:
            print("⚠️  Fine-tuning history table not found (will be created automatically)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def test_model_file():
    """Test model file"""
    print("\n🤖 Testing Model File...")
    
    model_path = 'best.pt'
    
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"✅ Model file found: {model_path} ({size_mb:.1f} MB)")
        
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            print("✅ Model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
    else:
        print(f"❌ Model file not found: {model_path}")

def main():
    """Run all tests"""
    print("🚀 Fine-Tuning System Test Suite")
    print("=" * 50)
    
    test_database()
    test_model_file()
    test_fine_tuning_manager()
    test_validation()
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")
    print("\n💡 Tips:")
    print("   - Pastikan model best.pt ada di folder utama")
    print("   - Database absensi.db harus readable")
    print("   - Install Pillow untuk validasi gambar optimal: pip install Pillow")

if __name__ == '__main__':
    main()

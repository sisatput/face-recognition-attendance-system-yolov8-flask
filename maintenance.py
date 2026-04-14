#!/usr/bin/env python3
# maintenance.py
# Script untuk maintenance sistem fine-tuning

import os
import shutil
import sqlite3
import argparse
import glob
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Maintenance')

class MaintenanceManager:
    def __init__(self, database_path='absensi.db'):
        self.database_path = database_path
    
    def cleanup_temporary_files(self, days_old=1):
        """Hapus file temporary yang lebih lama dari X hari"""
        logger.info("Starting temporary files cleanup...")
        
        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 60 * 60)
        
        # Cleanup temp dataset folders
        temp_folders = glob.glob('temp_ft_dataset_*')
        deleted_count = 0
        
        for folder in temp_folders:
            if os.path.isdir(folder):
                folder_time = os.path.getctime(folder)
                if folder_time < cutoff_time:
                    try:
                        shutil.rmtree(folder)
                        logger.info(f"Deleted temporary folder: {folder}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting {folder}: {e}")
        
        # Cleanup training runs older than 7 days
        if os.path.exists('fine_tuning_runs'):
            run_folders = glob.glob('fine_tuning_runs/*')
            for folder in run_folders:
                if os.path.isdir(folder):
                    folder_time = os.path.getctime(folder)
                    if folder_time < (current_time - (7 * 24 * 60 * 60)):
                        try:
                            shutil.rmtree(folder)
                            logger.info(f"Deleted old training run: {folder}")
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting {folder}: {e}")
        
        # Cleanup old logs
        log_files = glob.glob('*.log')
        for log_file in log_files:
            if log_file != 'fine_tuning.log':  # Keep main log
                file_time = os.path.getctime(log_file)
                if file_time < (current_time - (30 * 24 * 60 * 60)):  # 30 days
                    try:
                        os.remove(log_file)
                        logger.info(f"Deleted old log: {log_file}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting {log_file}: {e}")
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} items.")
        return deleted_count
    
    def backup_model(self, source_model='best.pt'):
        """Backup model saat ini"""
        if not os.path.exists(source_model):
            logger.error(f"Source model {source_model} not found")
            return False
        
        backup_dir = 'model_backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'manual_backup_{timestamp}.pt')
        
        try:
            shutil.copy2(source_model, backup_path)
            logger.info(f"Model backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Error backing up model: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count=10):
        """Hapus backup lama, simpan hanya N backup terakhir"""
        backup_dir = 'model_backups'
        
        if not os.path.exists(backup_dir):
            logger.info("No backup directory found")
            return 0
        
        # Get all backup files sorted by modification time
        backup_files = []
        for file in os.listdir(backup_dir):
            if file.endswith('.pt'):
                file_path = os.path.join(backup_dir, file)
                backup_files.append((file_path, os.path.getctime(file_path)))
        
        # Sort by creation time (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        deleted_count = 0
        if len(backup_files) > keep_count:
            files_to_delete = backup_files[keep_count:]
            
            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old backup: {os.path.basename(file_path)}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
        
        logger.info(f"Backup cleanup completed. Deleted {deleted_count} old backups.")
        return deleted_count
    
    def database_maintenance(self):
        """Maintenance database"""
        logger.info("Starting database maintenance...")
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Vacuum database
            cursor.execute("VACUUM")
            
            # Get database statistics
            cursor.execute("SELECT COUNT(*) FROM fine_tuning_history")
            ft_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_dataset")
            dataset_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM model_training")
            model_count = cursor.fetchone()[0]
            
            conn.close()
            
            logger.info(f"Database maintenance completed.")
            logger.info(f"Statistics: {ft_count} fine-tuning records, {dataset_count} datasets, {model_count} models")
            
            return {
                'fine_tuning_records': ft_count,
                'datasets': dataset_count,
                'models': model_count
            }
            
        except Exception as e:
            logger.error(f"Error in database maintenance: {e}")
            return None
    
    def system_health_check(self):
        """Check sistem health"""
        logger.info("Starting system health check...")
        
        health_status = {
            'model_exists': os.path.exists('best.pt'),
            'database_exists': os.path.exists(self.database_path),
            'backup_dir_exists': os.path.exists('model_backups'),
            'temp_files_count': len(glob.glob('temp_ft_dataset_*')),
            'log_file_exists': os.path.exists('fine_tuning.log'),
            'disk_space': self._get_disk_space()
        }
        
        # Check permissions
        try:
            test_file = 'test_write_permission.tmp'
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            health_status['write_permissions'] = True
        except:
            health_status['write_permissions'] = False
        
        logger.info("Health check completed:")
        for key, value in health_status.items():
            status = "✅" if value else "❌"
            logger.info(f"  {key}: {status} {value}")
        
        return health_status
    
    def _get_disk_space(self):
        """Get available disk space in GB"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('.')
            return {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2)
            }
        except:
            return None
    
    def generate_report(self):
        """Generate maintenance report"""
        logger.info("Generating maintenance report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'health_check': self.system_health_check(),
            'database_stats': self.database_maintenance(),
        }
        
        # Save report
        report_file = f"maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            import json
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Fine-Tuning System Maintenance')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup temporary files')
    parser.add_argument('--backup', action='store_true', help='Backup current model')
    parser.add_argument('--cleanup-backups', action='store_true', help='Cleanup old backups')
    parser.add_argument('--health-check', action='store_true', help='System health check')
    parser.add_argument('--report', action='store_true', help='Generate maintenance report')
    parser.add_argument('--all', action='store_true', help='Run all maintenance tasks')
    parser.add_argument('--days-old', type=int, default=1, help='Days old for cleanup (default: 1)')
    parser.add_argument('--keep-backups', type=int, default=10, help='Number of backups to keep (default: 10)')
    
    args = parser.parse_args()
    
    if not any([args.cleanup, args.backup, args.cleanup_backups, args.health_check, args.report, args.all]):
        parser.print_help()
        return
    
    maintenance = MaintenanceManager()
    
    if args.all or args.cleanup:
        maintenance.cleanup_temporary_files(args.days_old)
    
    if args.all or args.backup:
        maintenance.backup_model()
    
    if args.all or args.cleanup_backups:
        maintenance.cleanup_old_backups(args.keep_backups)
    
    if args.all or args.health_check:
        maintenance.system_health_check()
    
    if args.all or args.report:
        maintenance.generate_report()
    
    logger.info("Maintenance completed!")

if __name__ == '__main__':
    main()

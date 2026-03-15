from django.db.models.signals import post_save
from django.dispatch import receiver
from achievements.models import Paper
import threading
import subprocess
import sys
from django.conf import settings

def run_sync_neo4j():
    try:
        subprocess.Popen([
            sys.executable,
            'manage.py',
            'sync_neo4j'
        ], cwd=settings.BASE_DIR)
    except Exception as e:
        print(f"[Neo4j Sync Signal] 启动同步失败: {e}")

@receiver(post_save, sender=Paper)
def paper_post_save(sender, instance, **kwargs):
    threading.Thread(target=run_sync_neo4j, daemon=True).start()

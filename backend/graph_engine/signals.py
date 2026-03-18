import subprocess
import sys
import threading

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from achievements.models import Paper


def run_sync_neo4j():
    try:
        subprocess.Popen(
            [
                sys.executable,
                'manage.py',
                'sync_neo4j',
            ],
            cwd=settings.BASE_DIR,
        )
    except Exception as exc:
        print(f'[Neo4j Sync Signal] 启动同步失败: {exc}')


@receiver(post_save, sender=Paper)
def paper_post_save(sender, instance, **kwargs):
    # 第二轮开始默认关闭“论文保存即全量重建 Neo4j”的隐式链路，
    # 图谱写入统一由 achievements.views 中的显式同步入口负责。
    if not getattr(settings, 'GRAPH_SIGNAL_SYNC_ENABLED', False):
        return

    threading.Thread(target=run_sync_neo4j, daemon=True).start()

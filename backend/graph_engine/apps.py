from django.apps import AppConfig


class GraphEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'graph_engine'

    def ready(self):
        import graph_engine.signals

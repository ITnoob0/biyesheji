from __future__ import annotations

from .utils import Neo4jEngine


class AcademicGraphSyncService:
    @staticmethod
    def _execute(action_name, **payload):
        graph = None

        try:
            graph = Neo4jEngine()
            if not graph.enabled:
                return False

            action = getattr(graph, action_name)
            action(**payload)
            return True
        except Exception as exc:
            print(f'[AcademicGraphSyncService] {action_name} failed: {exc}')
            return False
        finally:
            if graph is not None:
                graph.close()

    @classmethod
    def sync_paper(cls, **payload):
        return cls._execute('sync_paper_to_graph', **payload)

    @classmethod
    def delete_paper(cls, paper_id):
        return cls._execute('delete_paper_from_graph', paper_id=paper_id)

    @classmethod
    def sync_project(cls, **payload):
        return cls._execute('sync_project_to_graph', **payload)

    @classmethod
    def delete_project(cls, project_id):
        return cls._execute('delete_project_from_graph', project_id=project_id)

    @classmethod
    def sync_intellectual_property(cls, **payload):
        return cls._execute('sync_intellectual_property_to_graph', **payload)

    @classmethod
    def delete_intellectual_property(cls, ip_id):
        return cls._execute('delete_intellectual_property_from_graph', ip_id=ip_id)

    @classmethod
    def sync_teaching_achievement(cls, **payload):
        return cls._execute('sync_teaching_achievement_to_graph', **payload)

    @classmethod
    def delete_teaching_achievement(cls, teaching_id):
        return cls._execute('delete_teaching_achievement_from_graph', teaching_id=teaching_id)

    @classmethod
    def sync_academic_service(cls, **payload):
        return cls._execute('sync_academic_service_to_graph', **payload)

    @classmethod
    def delete_academic_service(cls, service_id):
        return cls._execute('delete_academic_service_from_graph', service_id=service_id)

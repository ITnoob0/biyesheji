from django.urls import path
from . import views

urlpatterns = [
    path('api/graph/topology/<int:user_id>/', views.AcademicGraphTopologyView.as_view(), name='academic_graph_topology'),
]

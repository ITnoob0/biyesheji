# backend/graph_engine/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 核心修改：去掉 'api/graph/'，只保留业务逻辑路径
    path('topology/<int:user_id>/', views.AcademicGraphTopologyView.as_view(), name='academic_graph_topology'),
]
from django.urls import path
from .views import DocumentViewSet

urlpatterns = [
    path('documents/', DocumentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('documents/<int:pk>/', DocumentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('documents/generate-response/', DocumentViewSet.as_view({
        'post': 'generate_response'
    })),
] 
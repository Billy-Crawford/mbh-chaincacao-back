from django.urls import path
from .views import TransfertListCreateView

urlpatterns = [
    path('', TransfertListCreateView.as_view(), name='transferts'),
]
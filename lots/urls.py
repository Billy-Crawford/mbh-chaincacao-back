from django.urls import path
from .views import LotListCreateView, LotDetailView, VerifierLotView, ExporterLotView, ScannerLotView, ConfirmerReceptionView, CertificatEUDRView

urlpatterns = [
    path('',              LotListCreateView.as_view(), name='lots'),
    path('<uuid:lot_id>/', LotDetailView.as_view(),    name='lot-detail'),
    path('<uuid:lot_id>/verify/', VerifierLotView.as_view(), name='lot-verify'),
    path('<uuid:lot_id>/exporter/', ExporterLotView.as_view(), name='lot-exporter'),

    path('<uuid:lot_id>/scanner/', ScannerLotView.as_view(), name='lot-scanner'),  # ← nouveau

    path('<uuid:lot_id>/confirmer/', ConfirmerReceptionView.as_view(), name='lot-confirmer'),

    path('<uuid:lot_id>/certificat/', CertificatEUDRView.as_view(), name='lot-certificat'),

    # alias
    path('verify/<uuid:lot_id>/', VerifierLotView.as_view(), name='lot-verify-short'),

]




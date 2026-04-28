from django.contrib import admin
from .models import Transfert

@admin.register(Transfert)
class TransfertAdmin(admin.ModelAdmin):
    list_display = ['lot', 'expediteur', 'destinataire', 'etape', 'date_transfert']
    list_filter  = ['etape']
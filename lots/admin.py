from django.contrib import admin
from .models import Lot

@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display  = ['id', 'agriculteur', 'espece', 'poids_kg', 'statut', 'created_at']
    list_filter   = ['espece', 'statut']
    search_fields = ['agriculteur__username']
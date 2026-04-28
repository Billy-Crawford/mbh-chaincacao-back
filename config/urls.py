from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions


from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="ChainCacao API",
      default_version='v1',
      description="API de traçabilité du cacao avec blockchain",
      contact=openapi.Contact(email="contact@chaincacao.com"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/',           admin.site.urls),
    path('api/auth/',        include('users.urls')),
    path('api/lots/',        include('lots.urls')),
    path('api/transferts/',  include('transferts.urls')),



 # Swagger UI
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),

    # Redoc (optionnel)
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),

]
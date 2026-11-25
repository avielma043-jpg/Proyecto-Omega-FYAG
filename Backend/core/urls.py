from django.urls import path
from rest_framework import generics
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Rol
from .permissions import IsAdminOAdministracion
from .serializers import RolSerializer
from .views_lookups import TecnicosLookupAPIView
from .views import CustomTokenObtainPairView, UsuarioDetailAPIView, UsuarioListCreateAPIView

"""
Rutas del módulo de seguridad y autenticación.
"""

app_name = 'core'

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('usuarios/', UsuarioListCreateAPIView.as_view(), name='usuario_list_create'),
    path('usuarios/<int:id_usuario>/', UsuarioDetailAPIView.as_view(), name='usuario_detail'),
    path('roles/', generics.ListAPIView.as_view(queryset=Rol.objects.all(), serializer_class=RolSerializer, permission_classes=[IsAdminOAdministracion]),name='rol_list'),
    path('lookups/tecnicos/', TecnicosLookupAPIView.as_view(), name='lookup_tecnicos'),
]
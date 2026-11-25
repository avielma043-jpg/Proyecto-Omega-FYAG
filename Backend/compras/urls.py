"""
Rutas del módulo de Compras.
"""
from django.urls import path
from .views import ProveedorListCreateAPIView, DocumentoCompraListCreateAPIView, ContactoProveedorListCreateAPIView, ContactoProveedorDetailAPIView

app_name = 'compras'

urlpatterns = [
    path('proveedores/', ProveedorListCreateAPIView.as_view(), name='proveedores_list_create'),
    path('documentos/', DocumentoCompraListCreateAPIView.as_view(), name='documentos_list_create'),
    path('contactos/', ContactoProveedorListCreateAPIView.as_view(), name='contacto_proveedor_list_create'),
    path('contactos/<int:pk>/', ContactoProveedorDetailAPIView.as_view(), name='contacto_proveedor_detail'),
]
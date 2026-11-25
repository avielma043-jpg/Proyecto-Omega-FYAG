"""
Rutas del módulo de Obras y Terreno.
"""
from django.urls import path
from .views import (
    ClienteMandanteListCreateAPIView,
    PresupuestoListCreateAPIView,
    ObraListCreateAPIView,
    ObraDetailAPIView,
    HojaServicioListCreateAPIView,
    HorasTrabajadasListCreateAPIView,
    ContactoClienteListCreateAPIView, 
    ContactoClienteDetailAPIView,
    PresupuestoDetailAPIView
)

from core.views_lookups import ClientesLookupAPIView

app_name = 'obras'

urlpatterns = [
    path('clientes/', ClienteMandanteListCreateAPIView.as_view(), name='clientes_list_create'),
    path('presupuestos/', PresupuestoListCreateAPIView.as_view(), name='presupuestos_list_create'),
    
    path('obras/', ObraListCreateAPIView.as_view(), name='obras_list_create'),
    path('obras/<int:pk>/', ObraDetailAPIView.as_view(), name='obras_detail'),
    
    path('hojas-servicio/', HojaServicioListCreateAPIView.as_view(), name='hojas_servicio_list_create'),
    path('horas-trabajadas/', HorasTrabajadasListCreateAPIView.as_view(), name='horas_trabajadas_list_create'),
    path('contactos-cliente/', ContactoClienteListCreateAPIView.as_view(), name='contacto_cliente_list_create'),
    path('contactos-cliente/<int:pk>/', ContactoClienteDetailAPIView.as_view(), name='contacto_cliente_detail'),
    path('presupuestos/<int:pk>/', PresupuestoDetailAPIView.as_view(), name='presupuesto_detail'),
    path('lookups/clientes/', ClientesLookupAPIView.as_view(), name='lookup_clientes'),
]
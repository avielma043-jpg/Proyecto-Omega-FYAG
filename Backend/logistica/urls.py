from django.urls import path
from .views import ArticuloListCreateAPIView, ArticuloDetailAPIView, CardexListCreateAPIView
from core.views_lookups import ArticulosActivosLookupAPIView
app_name = 'logistica'

urlpatterns = [
    # Catálogo de Artículos
    path('articulos/', ArticuloListCreateAPIView.as_view(), name='articulo_list_create'),
    path('articulos/<int:pk>/', ArticuloDetailAPIView.as_view(), name='articulo_detail'),
    
    # Movimientos del Cardex (Endpoint de solo Inserción y Lectura, Inmutable)
    path('cardex/', CardexListCreateAPIView.as_view(), name='cardex_list_create'),
    path('lookups/articulos-activos/', ArticulosActivosLookupAPIView.as_view(), name='lookup_articulos'),
]
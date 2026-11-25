from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from core.models import Rol, Usuario
from core.serializers import UsuarioSerializer

from logistica.models import Articulo
from logistica.serializers import ArticuloSerializer

from obras.models import ClienteMandante
from obras.serializers import ClienteMandanteSerializer


class TecnicosLookupAPIView(generics.ListAPIView):
    """GET /api/core/lookups/tecnicos/"""
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Usuario.objects.filter(
            estado_activo=True,
            rol__nombre_rol=Rol.TECNICO
        ).order_by('username')


class ArticulosActivosLookupAPIView(generics.ListAPIView):
    """GET /api/logistica/lookups/articulos-activos/"""
    serializer_class = ArticuloSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Articulo.objects.all().order_by('codigo_interno')


class ClientesLookupAPIView(generics.ListAPIView):
    """GET /api/obras/lookups/clientes/"""
    serializer_class = ClienteMandanteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ClienteMandante.objects.all().order_by('razon_social')
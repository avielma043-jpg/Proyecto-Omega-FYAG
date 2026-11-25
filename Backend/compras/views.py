"""
Lógica transaccional para Compras e integración con Inventario.
"""
from django.db import transaction
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .models import Proveedor, DocumentoCompra, ContactoProveedor
from .serializers import ProveedorSerializer, DocumentoCompraSerializer, ContactoProveedorSerializer
from .permissions import CanAccessCompras

from logistica.models import Articulo, Cardex
from core.models import LogAuditoria


class ContactoProveedorListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: Lista contactos (filtrables por ?id_proveedor=X).
    POST: Crea un nuevo contacto.
    Restringido a Administración, Administrador General y Bodega.
    """
    serializer_class = ContactoProveedorSerializer
    permission_classes = [CanAccessCompras]

    def get_queryset(self):
        queryset = ContactoProveedor.objects.all().order_by('id')
        id_proveedor = self.request.query_params.get('id_proveedor')
        if id_proveedor is not None:
            if not id_proveedor.isdigit():
                raise ValidationError(
                    {"id_proveedor": "El parámetro id_proveedor debe ser un entero positivo."}
                )
            queryset = queryset.filter(id_proveedor=int(id_proveedor))
        return queryset


class ContactoProveedorDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT, PATCH, DELETE para un ContactoProveedor específico."""
    queryset = ContactoProveedor.objects.all()
    serializer_class = ContactoProveedorSerializer
    permission_classes = [CanAccessCompras]


class ProveedorListCreateAPIView(generics.ListCreateAPIView):
    queryset = Proveedor.objects.prefetch_related('contactos').all().order_by('id')
    serializer_class = ProveedorSerializer
    permission_classes = [CanAccessCompras]


class DocumentoCompraListCreateAPIView(generics.ListCreateAPIView):
    queryset = DocumentoCompra.objects.prefetch_related('detalles').all().order_by('-fecha_ingreso')
    serializer_class = DocumentoCompraSerializer
    permission_classes = [CanAccessCompras]

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Guarda el documento con sus cálculos backend y afecta al Cardex atómicamente.
        """
        # El save() invoca create() en DocumentoCompraSerializer donde se calculan todos los totales
        documento = serializer.save()
        usuario = self.request.user

        for detalle in documento.detalles.all():
            try:
                # Bloqueo Pesimista (FOR UPDATE)
                articulo = Articulo.objects.select_for_update().get(id=detalle.id_articulo_id)
            except Articulo.DoesNotExist:
                raise ValidationError(
                    {"id_articulo": f"El artículo ID {detalle.id_articulo_id} no existe."}
                )

            # Validar tipo de movimiento: Ingreso o Nota de Crédito (Devolución)
            if documento.tipo_documento == DocumentoCompra.TIPO_NOTA_CREDITO:
                if articulo.stock_disponible < detalle.cantidad:
                    raise ValidationError(
                        {"cantidad": f"Stock insuficiente en '{articulo.nombre}' para procesar Nota de Crédito."}
                    )
                articulo.stock_disponible -= detalle.cantidad
                tipo_mov = Cardex.TIPO_DEVOLUCION
            else:
                articulo.stock_disponible += detalle.cantidad
                tipo_mov = Cardex.TIPO_INGRESO
                
                # Regla de Negocio: Actualiza el último costo solo si es una compra real
                articulo.ultimo_costo = detalle.costo_neto_final

            articulo.save()

            # Insertar movimiento automático inmutable en el Cardex
            movimiento = Cardex.objects.create(
                id_articulo=articulo,
                id_usuario=usuario,
                tipo_movimiento=tipo_mov,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.costo_neto_final
            )

            # Dejar trazabilidad estricta del evento en LogAuditoria
            LogAuditoria.objects.create(
                usuario=usuario,
                tabla_afectada='compras_documento_cardex',
                tipo_operacion=LogAuditoria.OP_INSERT,
                valor_anterior=None,
                valor_nuevo={
                    'id_documento': documento.id,
                    'id_movimiento_cardex': movimiento.id,
                    'id_articulo': articulo.id,
                    'costo_neto_final': detalle.costo_neto_final,
                    'stock_resultante': float(articulo.stock_disponible)
                }
            )
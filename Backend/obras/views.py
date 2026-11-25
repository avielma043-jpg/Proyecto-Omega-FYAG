"""
Vistas de Obras, Presupuestos y Terreno. Incluye la Máquina de Estados de FYAG.
"""
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import ClienteMandante, Presupuesto, Obra, HojaServicio, HorasTrabajadas, ContactoCliente
from .serializers import (
    ClienteMandanteSerializer, PresupuestoSerializer, ObraSerializer,
    HojaServicioSerializer, HorasTrabajadasSerializer, ContactoClienteSerializer
)
from .permissions import CanAccessFinanzasObra, CanManageObras, CanManageTerreno, CanAccessFinanzasObra
from core.models import Rol, LogAuditoria
from logistica.models import Cardex


class ClienteMandanteListCreateAPIView(generics.ListCreateAPIView):
    queryset = ClienteMandante.objects.all().order_by('id')
    serializer_class = ClienteMandanteSerializer
    permission_classes = [CanAccessFinanzasObra]


class PresupuestoListCreateAPIView(generics.ListCreateAPIView):
    queryset = Presupuesto.objects.all().order_by('id')
    serializer_class = PresupuestoSerializer
    permission_classes = [CanAccessFinanzasObra]


class ObraListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ObraSerializer
    permission_classes = [CanManageObras]

    def get_queryset(self):
        """
        Regla de Negocio: Técnicos SOLO ven las obras donde su usuario es el id_tecnico.
        Otros roles operativos ven todo.
        """
        usuario = self.request.user
        if not usuario.is_superuser and usuario.rol and usuario.rol.nombre_rol == Rol.TECNICO:
            return Obra.objects.filter(id_tecnico=usuario).order_by('-fecha_creacion')
        return Obra.objects.all().order_by('-fecha_creacion')


class ObraDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ObraSerializer
    permission_classes = [CanManageObras]

    def get_queryset(self):
        usuario = self.request.user
        if not usuario.is_superuser and usuario.rol and usuario.rol.nombre_rol == Rol.TECNICO:
            return Obra.objects.filter(id_tecnico=usuario)
        return Obra.objects.all()

    def update(self, request, *args, **kwargs):
        """
        Regla de Negocio 1: Máquina de Estados y Bloqueo Financiero.
        Si la obra intenta pasar a 'Finalizada', valida requisitos estrictos. Retorna 422 en caso de fallo.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        nuevo_estado = serializer.validated_data.get('estado')
        
        if nuevo_estado == Obra.ESTADO_FINALIZADA and instance.estado != Obra.ESTADO_FINALIZADA:
            errores = []
            
            # Validación 1: Técnico asignado
            if not instance.id_tecnico:
                errores.append("La obra no tiene un técnico asignado.")
            
            # Validación 2: Hoja de servicio firmada
            if not instance.hojas_servicio.filter(estado_firma=True).exists():
                errores.append("La obra no tiene una hoja de servicio firmada adjunta.")
            
            # Validación 3: Horas trabajadas reportadas
            if not instance.horas_trabajadas.exists():
                errores.append("La obra no tiene registro de horas trabajadas imputadas.")
                
            # Validación 4: Egresos de materiales en Cardex
            tiene_egresos = Cardex.objects.filter(id_obra=instance.id, tipo_movimiento=Cardex.TIPO_EGRESO).exists()
            if not tiene_egresos:
                errores.append("La obra carece de egresos de materiales registrados en el Cardex de Bodega.")

            # Si falla el workflow, rechazar la transacción con HTTP 422 Unprocessable Entity
            if errores:
                return Response({"errores": errores}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        self.perform_update(serializer)
        return Response(serializer.data)


class HojaServicioListCreateAPIView(generics.ListCreateAPIView):
    queryset = HojaServicio.objects.all().order_by('-fecha_servicio')
    serializer_class = HojaServicioSerializer
    permission_classes = [CanManageTerreno]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_uuid = serializer.validated_data.get('client_uuid')
        if client_uuid:
            existente = HojaServicio.objects.filter(client_uuid=client_uuid).first()
            if existente:
                return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            if client_uuid:
                existente = HojaServicio.objects.get(client_uuid=client_uuid)
                return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)
            raise

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class HorasTrabajadasListCreateAPIView(generics.ListCreateAPIView):
    queryset = HorasTrabajadas.objects.all().order_by('-id')
    serializer_class = HorasTrabajadasSerializer
    permission_classes = [CanManageTerreno]


class ContactoClienteListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: Lista contactos (filtrables por ?id_cliente=X).
    POST: Crea nuevo contacto.
    Bloqueado para Técnicos.
    """
    serializer_class = ContactoClienteSerializer
    permission_classes = [CanAccessFinanzasObra]

    def get_queryset(self):
        queryset = ContactoCliente.objects.all().order_by('id')
        id_cliente = self.request.query_params.get('id_cliente')
        if id_cliente is not None:
            if not id_cliente.isdigit():
                raise ValidationError(
                    {"id_cliente": "El parámetro id_cliente debe ser un entero positivo."}
                )
            queryset = queryset.filter(id_cliente=int(id_cliente))
        return queryset


class ContactoClienteDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT, PATCH, DELETE para un ContactoCliente específico."""
    queryset = ContactoCliente.objects.all()
    serializer_class = ContactoClienteSerializer
    permission_classes = [CanAccessFinanzasObra]


class PresupuestoDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    GET, PUT, PATCH para modificar el estado y monto del presupuesto.
    Audita cambios de estado en core.models.LogAuditoria.
    """
    queryset = Presupuesto.objects.all()
    serializer_class = PresupuestoSerializer
    permission_classes = [CanAccessFinanzasObra]

    def perform_update(self, serializer):
        instancia_previa = self.get_object()
        estado_anterior = instancia_previa.estado
        
        # Validar regla de negocio de estados
        nuevo_estado = serializer.validated_data.get('estado', estado_anterior)
        if estado_anterior == Presupuesto.ESTADO_APROBADO and nuevo_estado == Presupuesto.ESTADO_PENDIENTE:
            raise ValidationError(
                {"estado": "Un presupuesto 'Aprobado' no puede retroceder al estado 'Pendiente'."}
            )

        presupuesto_actualizado = serializer.save()

        # Si el estado cambió, generar traza de auditoría
        if estado_anterior != nuevo_estado:
            LogAuditoria.objects.create(
                usuario=self.request.user,
                tabla_afectada='obras_presupuesto',
                tipo_operacion=LogAuditoria.OP_UPDATE,
                valor_anterior={'estado': estado_anterior},
                valor_nuevo={
                    'estado': nuevo_estado,
                    'monto_total': presupuesto_actualizado.monto_total
                }
            )
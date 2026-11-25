from decimal import Decimal
import uuid

from django.db import DatabaseError
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import LogAuditoria, Rol, Usuario
from logistica.models import Articulo, Cardex
from obras.models import ClienteMandante, Obra, Presupuesto


class LogisticaBaseMixin:
    def setUp(self):
        super().setUp()

        # Roles
        self.rol_admin_gral = Rol.objects.create(nombre_rol=Rol.ADMIN_GENERAL)
        self.rol_admin = Rol.objects.create(nombre_rol=Rol.ADMINISTRACION)
        self.rol_bodega = Rol.objects.create(nombre_rol=Rol.BODEGA)
        self.rol_tecnico = Rol.objects.create(nombre_rol=Rol.TECNICO)
        self.rol_consulta = Rol.objects.create(nombre_rol=Rol.CONSULTA)

        # Usuarios
        self.admin_gral = Usuario.objects.create_user(
            username='admin_gral', rut='111-1', password='pass', rol=self.rol_admin_gral
        )
        self.admin = Usuario.objects.create_user(
            username='admin', rut='222-2', password='pass', rol=self.rol_admin
        )
        self.bodega = Usuario.objects.create_user(
            username='bodega', rut='333-3', password='pass', rol=self.rol_bodega
        )
        self.tecnico1 = Usuario.objects.create_user(
            username='tecnico1', rut='444-4', password='pass', rol=self.rol_tecnico
        )
        self.tecnico2 = Usuario.objects.create_user(
            username='tecnico2', rut='555-5', password='pass', rol=self.rol_tecnico
        )
        self.consulta = Usuario.objects.create_user(
            username='consulta', rut='666-6', password='pass', rol=self.rol_consulta
        )

        # Obras (dependencias para id_obra en Cardex)
        self.cliente = ClienteMandante.objects.create(
            rut='777-7',
            razon_social='Cliente Test',
        )
        self.presupuesto = Presupuesto.objects.create(
            id_cliente=self.cliente,
            estado='Pendiente',
            monto_total=100000,
        )
        self.obra_tec1 = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            id_tecnico=self.tecnico1,
            tipo_servicio='Instalación',
            estado='En proceso',
        )
        self.obra_tec2 = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            id_tecnico=self.tecnico2,
            tipo_servicio='Instalación',
            estado='En proceso',
        )

        # Artículos
        self.articulo1 = Articulo.objects.create(
            codigo_interno='ART-001',
            nombre='Tubo Cobre',
            categoria='Gas',
            unidad_medida='Metro',
            stock_disponible=Decimal('10.00'),
            stock_minimo=Decimal('5.00'),
            precio_lista_vigente=5000,
        )
        self.articulo_sin_stock = Articulo.objects.create(
            codigo_interno='ART-002',
            nombre='Tuerca',
            categoria='Fijaciones',
            unidad_medida='Unidad',
            stock_disponible=Decimal('0.00'),
            stock_minimo=Decimal('10.00'),
            precio_lista_vigente=100,
        )

        # URLs
        self.articulos_url = reverse('logistica:articulo_list_create')
        self.cardex_url = reverse('logistica:cardex_list_create')

    def _create_mov_ingreso(self, articulo, cantidad=Decimal('10.00'), user=None):
        return Cardex.objects.create(
            id_articulo=articulo,
            id_usuario=user or self.admin_gral,
            tipo_movimiento=Cardex.TIPO_INGRESO,
            cantidad=cantidad,
            precio_unitario=articulo.precio_lista_vigente,
        )


class LogisticaFuncionalTests(LogisticaBaseMixin, APITestCase):

    def test_a01_rbac_articulos_escritura(self):
        """A01:2025 - Bodega puede crear artículos, Consulta no"""
        payload = {
            'codigo_interno': 'ART-NEW',
            'nombre': 'Test',
            'categoria': 'C',
            'unidad_medida': 'U',
        }

        self.client.force_authenticate(user=self.bodega)
        self.assertEqual(
            self.client.post(self.articulos_url, payload).status_code,
            status.HTTP_201_CREATED,
        )

        self.client.force_authenticate(user=self.consulta)
        self.assertEqual(
            self.client.post(self.articulos_url, payload).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_a01_bodega_no_puede_cambiar_precio_lista(self):
        """A01:2025 - Bodega recibe 403 al intentar cambiar precio_lista_vigente"""
        self.client.force_authenticate(user=self.bodega)
        url = reverse('logistica:articulo_detail', kwargs={'pk': self.articulo1.id})
        res = self.client.patch(url, {'precio_lista_vigente': 9999})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_a01_tecnico_solo_egreso_en_su_obra(self):
        """A01:2025 - Técnico solo puede registrar 'Egreso' en su propia obra"""
        self.client.force_authenticate(user=self.tecnico1)

        payload_ingreso = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_INGRESO,
            'cantidad': '1.00',
            'precio_unitario': 100,
        }
        self.assertEqual(
            self.client.post(self.cardex_url, payload_ingreso).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        payload_egreso_ajeno = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra_tec2.id,
            'cantidad': '1.00',
            'precio_unitario': 100,
        }
        self.assertEqual(
            self.client.post(self.cardex_url, payload_egreso_ajeno).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        payload_egreso_propio = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra_tec1.id,
            'cantidad': '1.00',
            'precio_unitario': 100,
        }
        self.assertEqual(
            self.client.post(self.cardex_url, payload_egreso_propio).status_code,
            status.HTTP_201_CREATED,
        )

    def test_a01_solo_admin_general_hace_reversa(self):
        """A01:2025 - Solo Admin General puede hacer Reversas"""
        mov = self._create_mov_ingreso(self.articulo1)
        payload_reversa = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_REVERSA,
            'cantidad': '1.00',
            'precio_unitario': 5000,
            'id_movimiento_original': mov.id,
            'motivo_reversa': 'Error de digitacion',
        }

        self.client.force_authenticate(user=self.admin)
        self.assertEqual(
            self.client.post(self.cardex_url, payload_reversa).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(user=self.admin_gral)
        self.assertEqual(
            self.client.post(self.cardex_url, payload_reversa).status_code,
            status.HTTP_201_CREATED,
        )

    def test_a06_egreso_sin_obra(self):
        """A06:2025 - Egreso sin id_obra falla"""
        self.client.force_authenticate(user=self.bodega)
        payload = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'cantidad': '1.00',
            'precio_unitario': 100,
        }
        res = self.client.post(self.cardex_url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id_obra', res.data)

    def test_a06_egreso_forzar_precio_lista(self):
        """A06:2025 - Egreso usa precio_lista_vigente ignorando el request"""
        self.client.force_authenticate(user=self.tecnico1)
        precio_real = self.articulo1.precio_lista_vigente

        payload = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra_tec1.id,
            'cantidad': '1.00',
            'precio_unitario': 1,
        }
        res = self.client.post(self.cardex_url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['precio_unitario'], precio_real)

    def test_a06_stock_insuficiente(self):
        """A06:2025 - Egreso falla por stock insuficiente y no descuenta"""
        self.client.force_authenticate(user=self.bodega)
        payload = {
            'id_articulo': self.articulo_sin_stock.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra_tec1.id,
            'cantidad': '5.00',
            'precio_unitario': 100,
        }
        res = self.client.post(self.cardex_url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        self.articulo_sin_stock.refresh_from_db()
        self.assertEqual(self.articulo_sin_stock.stock_disponible, Decimal('0.00'))

    def test_a08_idempotencia_offline(self):
        """A08:2025 - Idempotencia offline con client_uuid (201 -> 200 sin duplicar)"""
        self.client.force_authenticate(user=self.tecnico1)
        uid = str(uuid.uuid4())
        payload = {
            'client_uuid': uid,
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra_tec1.id,
            'cantidad': '2.00',
            'precio_unitario': 5000,
        }

        res1 = self.client.post(self.cardex_url, payload)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        self.articulo1.refresh_from_db()
        self.assertEqual(self.articulo1.stock_disponible, Decimal('8.00'))

        res2 = self.client.post(self.cardex_url, payload)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        self.articulo1.refresh_from_db()
        self.assertEqual(self.articulo1.stock_disponible, Decimal('8.00'))
        self.assertEqual(Cardex.objects.filter(client_uuid=uid).count(), 1)

    def test_a09_logging_cardex(self):
        """A09:2025 - Snapshot JSON en LogAuditoria tras movimiento"""
        self.client.force_authenticate(user=self.tecnico1)
        payload = {
            'id_articulo': self.articulo1.id,
            'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra_tec1.id,
            'cantidad': '1.00',
            'precio_unitario': 5000,
        }

        self.client.post(self.cardex_url, payload)

        log = LogAuditoria.objects.filter(tabla_afectada='logistica_cardex').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.tipo_operacion, LogAuditoria.OP_INSERT)
        self.assertEqual(log.valor_nuevo['tipo_movimiento'], Cardex.TIPO_EGRESO)
        self.assertEqual(log.valor_nuevo['cantidad'], 1.0)
        self.assertEqual(log.valor_nuevo['id_obra'], self.obra_tec1.id)


class LogisticaTransactionTests(LogisticaBaseMixin, TransactionTestCase):

    def test_a08_inmutabilidad_put_patch_delete(self):
        """A08:2025 - Bloqueo (403/405) de PUT, PATCH y DELETE en Cardex API"""
        self._create_mov_ingreso(self.articulo1)
        token = str(RefreshToken.for_user(self.admin_gral).access_token)
        auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        bloqueados = [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED]

        self.assertIn(self.client.put(self.cardex_url, **auth_headers).status_code, bloqueados)
        self.assertIn(self.client.patch(self.cardex_url, **auth_headers).status_code, bloqueados)
        self.assertIn(self.client.delete(self.cardex_url, **auth_headers).status_code, bloqueados)

    def test_a08_trigger_postgres_impide_update_delete(self):
        """A08:2025 - Trigger PostgreSQL rechaza update/delete a nivel ORM/SQL"""
        mov = self._create_mov_ingreso(self.articulo1)

        with self.assertRaises(DatabaseError):
            mov.delete()

        with self.assertRaises(DatabaseError):
            Cardex.objects.filter(id=mov.id).update(cantidad=99)
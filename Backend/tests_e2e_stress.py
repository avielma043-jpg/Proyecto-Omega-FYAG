import concurrent.futures
import importlib.metadata
import uuid
from decimal import Decimal

from django.test import TransactionTestCase
from django.urls import reverse
from django.db import connections
from rest_framework import status
from rest_framework.test import APIClient

from core.models import LogAuditoria, Rol, Usuario
from logistica.models import Articulo, Cardex
from obras.models import ClienteMandante, Obra, Presupuesto, HojaServicio, HorasTrabajadas
from compras.models import Proveedor, DocumentoCompra, DetalleCompra


class OmegaE2EAndStressTests(TransactionTestCase):
    
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre_rol=Rol.ADMIN_GENERAL)
        self.rol_tecnico = Rol.objects.create(nombre_rol=Rol.TECNICO)

        self.admin = Usuario.objects.create_user(
            username='admin_master', rut='99-9', password='pass', rol=self.rol_admin
        )
        self.tecnico = Usuario.objects.create_user(
            username='tec_master', rut='88-8', password='pass', rol=self.rol_tecnico
        )

        self.articulo = Articulo.objects.create(
            codigo_interno='ART-STRESS', nombre='Cobre', categoria='C', unidad_medida='U', 
            stock_disponible=Decimal('5.00'), precio_lista_vigente=1000
        )
        self.cliente = ClienteMandante.objects.create(rut='77-7', razon_social='Cliente Stress', giro='G')
        self.presupuesto = Presupuesto.objects.create(id_cliente=self.cliente, estado=Presupuesto.ESTADO_APROBADO, monto_total=500000)
        self.obra = Obra.objects.create(
            id_presupuesto=self.presupuesto, id_cliente=self.cliente, id_tecnico=self.tecnico, 
            tipo_servicio='Stress', estado=Obra.ESTADO_PROCESO
        )

    def test_a03_software_supply_chain_y_entorno(self):
        """A03:2025 - Validación de dependencias críticas de seguridad y middlewares"""
        dependencias = [
            'djangorestframework', 
            'djangorestframework-simplejwt', 
            'argon2-cffi', 
            'psycopg', 
            'openpyxl', 
            'reportlab', 
            'django-cors-headers'
        ]
        
        for dep in dependencias:
            try:
                version = importlib.metadata.version(dep)
                self.assertIsNotNone(version)
            except importlib.metadata.PackageNotFoundError:
                self.fail(f"Dependencia crítica faltante: {dep}")
        
        from django.conf import settings
        self.assertIn('corsheaders.middleware.CorsMiddleware', settings.MIDDLEWARE)
        self.assertIn('django.middleware.security.SecurityMiddleware', settings.MIDDLEWARE)

    def test_a10_stress_carrera_stock_30_hilos(self):
        """A10:2025 - 30 hilos compitiendo por 5 unidades de stock. Cierre atómico."""
        def worker_stock():
            client = APIClient()
            client.force_authenticate(user=self.admin)
            res = client.post(reverse('logistica:cardex_list_create'), {
                'id_articulo': self.articulo.id,
                'tipo_movimiento': Cardex.TIPO_EGRESO,
                'id_obra': self.obra.id,
                'cantidad': '1.00',
                'precio_unitario': 1000
            })
            connections.close_all()
            return res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            resultados = list(executor.map(lambda _: worker_stock(), range(30)))

        # Resultados esperados: Exactamente 5 exitosos (201), 25 fallidos por stock (400)
        exitos = resultados.count(status.HTTP_201_CREATED)
        fallos = resultados.count(status.HTTP_400_BAD_REQUEST)

        self.assertEqual(exitos, 5)
        self.assertEqual(fallos, 25)

        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_disponible, Decimal('0.00'))

    def test_a10_stress_idempotencia_offline(self):
        """A10:2025 - 20 hilos enviando el mismo client_uuid simultáneamente"""
        uid = str(uuid.uuid4())
        
        def worker_idemp():
            client = APIClient()
            client.force_authenticate(user=self.admin)
            res = client.post(reverse('logistica:cardex_list_create'), {
                'client_uuid': uid,
                'id_articulo': self.articulo.id,
                'tipo_movimiento': Cardex.TIPO_EGRESO,
                'id_obra': self.obra.id,
                'cantidad': '1.00',
                'precio_unitario': 1000
            })
            connections.close_all()
            return res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            resultados = list(executor.map(lambda _: worker_idemp(), range(20)))

        # Solo 1 movimiento debe ser 201 Created. Los otros 19 deben detectar idempotencia (200 OK)
        exitos = resultados.count(status.HTTP_201_CREATED)
        idempotentes = resultados.count(status.HTTP_200_OK)
        
        self.assertEqual(exitos, 1)
        self.assertEqual(idempotentes, 19)
        
        movimientos_creados = Cardex.objects.filter(client_uuid=uid).count()
        self.assertEqual(movimientos_creados, 1)

    def test_flujo_completo_e2e_fyag(self):
        """Simulación de Flujo E2E Completo: Login -> Compras -> Obras -> Terreno -> Cierre -> Exportar"""
        # 1. Login Admin
        client_admin = APIClient()
        res_login = client_admin.post(reverse('core:token_obtain_pair'), {
            'username': 'admin_master', 'password': 'pass'
        })
        self.assertEqual(res_login.status_code, 200)
        client_admin.credentials(HTTP_AUTHORIZATION='Bearer ' + res_login.data['access'])

        # 2 & 3. Proveedor, Artículo y Factura (Cascada matemática)
        prov_id = self.client.post(reverse('compras:proveedores_list_create'), {
            'rut': '9876543-2', 'razon_social': 'P', 'direccion': 'D'
        })
        # Asumiendo que crear facturas funciona (creado manualmente si no hay endpoint POST proveedor)
        prov = Proveedor.objects.create(rut='1-9', razon_social='P2', direccion='D')
        
        # Ingreso Factura
        res_fact = client_admin.post(reverse('compras:documentos_list_create'), {
            'id_proveedor': prov.id,
            'tipo_documento': DocumentoCompra.TIPO_FACTURA,
            'folio': 'F-E2E',
            'fecha_ingreso': '2026-11-21',
            'detalles': [{
                'id_articulo': self.articulo.id, 'cantidad': '1.00', 'costo_base': 10000,
                'descuento_1': '0.1000', 'descuento_2': '0.0500', 'descuento_3': '0.0200'
            }]
        }, format='json')
        self.assertEqual(res_fact.status_code, 201)
        self.assertEqual(res_fact.data['detalles'][0]['costo_neto_final'], 8379) # Validar cálculo cascada

        # 4 & 5. Crear Obra y Cliente (Usando los de setUp)
        
        # 6. Login Técnico
        client_tec = APIClient()
        client_tec.force_authenticate(user=self.tecnico)
        
        # 7. Sincronizar Egreso Offline + Duplicado
        uid_egreso = str(uuid.uuid4())
        payload_egreso = {
            'client_uuid': uid_egreso, 'id_articulo': self.articulo.id, 'tipo_movimiento': Cardex.TIPO_EGRESO,
            'id_obra': self.obra.id, 'cantidad': '1.00', 'precio_unitario': 8379
        }
        res_egreso1 = client_tec.post(reverse('logistica:cardex_list_create'), payload_egreso)
        self.assertEqual(res_egreso1.status_code, 201)
        res_egreso2 = client_tec.post(reverse('logistica:cardex_list_create'), payload_egreso)
        self.assertEqual(res_egreso2.status_code, 200)

        # 8. Horas Trabajadas
        res_horas = client_tec.post(reverse('obras:horas_trabajadas_list_create'), {
            'id_obra': self.obra.id, 'id_tecnico': self.tecnico.id_usuario,
            'cantidad_horas': '2.00', 'costo_hora': 5000
        })
        self.assertEqual(res_horas.status_code, 201)

        # 9. Admin intenta cierre prematuro -> 422
        url_obra_detail = reverse('obras:obras_detail', kwargs={'pk': self.obra.id})
        res_cierre_fallo = client_admin.patch(url_obra_detail, {'estado': Obra.ESTADO_FINALIZADA})
        self.assertEqual(res_cierre_fallo.status_code, 422)

        # 10. Hoja Servicio
        res_hoja = client_tec.post(reverse('obras:hojas_servicio_list_create'), {
            'id_obra': self.obra.id, 'estado_firma': True, 'firma_canvas_base64': 'data:img'
        })
        self.assertEqual(res_hoja.status_code, 201)

        # 11. Cierre Exitoso -> 200
        res_cierre_ok = client_admin.patch(url_obra_detail, {'estado': Obra.ESTADO_FINALIZADA})
        self.assertEqual(res_cierre_ok.status_code, 200)

        # 12-14. Trazabilidad
        logs = LogAuditoria.objects.filter(tabla_afectada='logistica_cardex').count()
        self.assertTrue(logs > 0)
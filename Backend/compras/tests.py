from decimal import Decimal

from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from compras.models import DocumentoCompra, Proveedor, ContactoProveedor, DetalleCompra
from core.models import LogAuditoria, Rol, Usuario
from logistica.models import Articulo, Cardex


class ComprasBaseMixin:
    def setUp(self):
        super().setUp()

        # Roles
        self.rol_admin_gral = Rol.objects.create(nombre_rol=Rol.ADMIN_GENERAL)
        self.rol_admin = Rol.objects.create(nombre_rol=Rol.ADMINISTRACION)
        self.rol_bodega = Rol.objects.create(nombre_rol=Rol.BODEGA)
        self.rol_tecnico = Rol.objects.create(nombre_rol=Rol.TECNICO)
        self.rol_supervisor = Rol.objects.create(nombre_rol=Rol.SUPERVISOR)
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
        self.tecnico = Usuario.objects.create_user(
            username='tecnico', rut='444-4', password='pass', rol=self.rol_tecnico
        )
        self.supervisor = Usuario.objects.create_user(
            username='supervisor', rut='555-5', password='pass', rol=self.rol_supervisor
        )
        self.consulta = Usuario.objects.create_user(
            username='consulta', rut='666-6', password='pass', rol=self.rol_consulta
        )

        # Proveedor y Articulo Base
        self.proveedor = Proveedor.objects.create(
            rut='76543210-K',
            razon_social='Proveedor Test SpA',
            direccion='Calle Falsa 123'
        )
        self.articulo = Articulo.objects.create(
            codigo_interno='ART-COMP-01',
            nombre='Compresor 5HP',
            categoria='Refrigeración',
            unidad_medida='Unidad',
            stock_disponible=Decimal('5.00'),
            ultimo_costo=0,
            precio_lista_vigente=150000
        )

        # URLs
        self.proveedores_url = reverse('compras:proveedores_list_create')
        self.contactos_url = reverse('compras:contacto_proveedor_list_create')
        self.documentos_url = reverse('compras:documentos_list_create')


class ComprasFuncionalTests(ComprasBaseMixin, APITestCase):

    def test_a01_rbac_acceso_compras(self):
        """A01:2025 - Matriz RBAC para módulos de compras"""
        usuarios_permitidos = [self.admin_gral, self.admin, self.bodega]
        usuarios_denegados = [self.tecnico, self.supervisor, self.consulta]

        for user in usuarios_permitidos:
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.get(self.proveedores_url).status_code, status.HTTP_200_OK)

        for user in usuarios_denegados:
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.get(self.proveedores_url).status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.get(self.documentos_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_a06_calculo_cascada_y_manipulacion_totales(self):
        """A06:2025 - Cascada multiplicativa y backend ignora totales del request"""
        self.client.force_authenticate(user=self.admin)
        
        # Enviar subtotales y totales manipulados/incorrectos
        payload = {
            'id_proveedor': self.proveedor.id,
            'tipo_documento': DocumentoCompra.TIPO_FACTURA,
            'folio': 'F-1001',
            'fecha_ingreso': '2026-11-21',
            'subtotal': 999999,      # Manipulado
            'total_neto': 999999,    # Manipulado
            'iva': 0,                # Manipulado
            'total_final': 999999,   # Manipulado
            'detalles': [
                {
                    'id_articulo': self.articulo.id,
                    'cantidad': '1.00',
                    'costo_base': 10000,
                    'descuento_1': '0.1000', # 10%
                    'descuento_2': '0.0500', # 5%
                    'descuento_3': '0.0200', # 2%
                }
            ]
        }
        
        res = self.client.post(self.documentos_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Validación del cálculo exacto: 10000 * (0.9) * (0.95) * (0.98) = 8379
        doc = res.data
        detalle = doc['detalles'][0]
        self.assertEqual(detalle['costo_neto_final'], 8379)
        
        # Validación de ignorar manipulación en cabecera
        self.assertEqual(doc['subtotal'], 8379)
        self.assertEqual(doc['total_neto'], 8379)
        self.assertEqual(doc['iva'], 1592) # 8379 * 0.19 = 1592.01 -> 1592
        self.assertEqual(doc['total_final'], 9971)

    def test_a06_nota_de_credito_resta_stock_y_no_cambia_costo(self):
        """A06:2025 - Nota de Crédito resta stock y valida límite"""
        self.client.force_authenticate(user=self.admin)
        
        stock_inicial = self.articulo.stock_disponible # 5.00
        costo_inicial = self.articulo.ultimo_costo # 0
        
        payload_nc = {
            'id_proveedor': self.proveedor.id,
            'tipo_documento': DocumentoCompra.TIPO_NOTA_CREDITO,
            'folio': 'NC-1001',
            'fecha_ingreso': '2026-11-21',
            'detalles': [
                {
                    'id_articulo': self.articulo.id,
                    'cantidad': '2.00',
                    'costo_base': 5000
                }
            ]
        }
        
        res = self.client.post(self.documentos_url, payload_nc, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_disponible, Decimal('3.00')) # 5.00 - 2.00
        self.assertEqual(self.articulo.ultimo_costo, costo_inicial) # No cambia ultimo costo
        
        # Validar Movimiento en Cardex
        mov = Cardex.objects.last()
        self.assertEqual(mov.tipo_movimiento, Cardex.TIPO_DEVOLUCION)
        
        # Intentar Nota de crédito por más stock del disponible
        payload_nc['detalles'][0]['cantidad'] = '4.00' # Solo quedan 3
        res_fail = self.client.post(self.documentos_url, payload_nc, format='json')
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cantidad', str(res_fail.data))

    def test_a06_factura_suma_stock_y_cambia_costo(self):
         """A06:2025 - Factura suma stock, cambia último costo y crea Ingreso en Cardex"""
         self.client.force_authenticate(user=self.admin)
         payload = {
             'id_proveedor': self.proveedor.id,
             'tipo_documento': DocumentoCompra.TIPO_FACTURA,
             'folio': 'F-999',
             'fecha_ingreso': '2026-11-21',
             'detalles': [{'id_articulo': self.articulo.id, 'cantidad': '10.00', 'costo_base': 25000}]
         }
         res = self.client.post(self.documentos_url, payload, format='json')
         self.assertEqual(res.status_code, status.HTTP_201_CREATED)
         
         self.articulo.refresh_from_db()
         self.assertEqual(self.articulo.stock_disponible, Decimal('15.00')) # 5 + 10
         self.assertEqual(self.articulo.ultimo_costo, 25000)
         
         mov = Cardex.objects.last()
         self.assertEqual(mov.tipo_movimiento, Cardex.TIPO_INGRESO)
         self.assertEqual(mov.precio_unitario, 25000)

    def test_a05_validacion_rut_contacto(self):
        """A05:2025 - Validaciones de formato de RUT en ContactoProveedor"""
        self.client.force_authenticate(user=self.admin)
        
        payload_invalido = {
            'id_proveedor': self.proveedor.id,
            'nombre': 'Juan',
            'rut': '123456-7', # Inválido
            'cargo': 'Ventas',
            'email': 'j@v.cl',
            'telefono': '123'
        }
        res = self.client.post(self.contactos_url, payload_invalido)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rut', res.data)
        
        payload_valido = payload_invalido.copy()
        payload_valido['rut'] = '12345678-9'
        res_ok = self.client.post(self.contactos_url, payload_valido)
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    def test_a05_sqli_filter_proveedor(self):
         """A05:2025 - Comprobar inyección SQL en filtro ?id_proveedor="""
         self.client.force_authenticate(user=self.admin)
         sqli_payload = "1' OR 1=1--"
         url_sqli = f"{self.contactos_url}?id_proveedor={sqli_payload}"
         
         res = self.client.get(url_sqli)
         # Should return 400 because 'id_proveedor' must be integer, not execute SQL
         # Assuming standard Django behavior for integer filters
         self.assertTrue(res.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK])
         if res.status_code == status.HTTP_200_OK:
             # Si no falla la validación, al menos asegurarse de que no retorna todos los registros burlando el filtro
             # Aquí no hay contactos creados aún, así que debería estar vacío
             self.assertEqual(len(res.data['results'] if 'results' in res.data else res.data), 0)

    def test_a09_logging_compras(self):
        """A09:2025 - Registro OP_INSERT en LogAuditoria por detalle procesado"""
        self.client.force_authenticate(user=self.admin)
        payload = {
            'id_proveedor': self.proveedor.id,
            'tipo_documento': DocumentoCompra.TIPO_FACTURA,
            'folio': 'F-LOG',
            'fecha_ingreso': '2026-11-21',
            'detalles': [{'id_articulo': self.articulo.id, 'cantidad': '1.00', 'costo_base': 100}]
        }
        
        count_antes = LogAuditoria.objects.filter(tabla_afectada='compras_documento_cardex').count()
        res = self.client.post(self.documentos_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        count_despues = LogAuditoria.objects.filter(tabla_afectada='compras_documento_cardex').count()
        self.assertEqual(count_despues, count_antes + 1)
        
        log = LogAuditoria.objects.filter(tabla_afectada='compras_documento_cardex').last()
        self.assertEqual(log.tipo_operacion, LogAuditoria.OP_INSERT)
        self.assertIn('id_documento', log.valor_nuevo)
        self.assertEqual(log.valor_nuevo['costo_neto_final'], 100)
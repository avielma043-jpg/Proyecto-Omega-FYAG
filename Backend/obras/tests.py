import uuid
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import LogAuditoria, Rol, Usuario
from logistica.models import Articulo, Cardex
from obras.models import (
    ClienteMandante,
    ContactoCliente,
    HojaServicio,
    HorasTrabajadas,
    Obra,
    Presupuesto,
)


class ObrasBaseTestCase(APITestCase):
    def setUp(self):
        super().setUp()

        # Roles
        self.rol_admin_gral = Rol.objects.create(nombre_rol=Rol.ADMIN_GENERAL)
        self.rol_admin = Rol.objects.create(nombre_rol=Rol.ADMINISTRACION)
        self.rol_tecnico = Rol.objects.create(nombre_rol=Rol.TECNICO)
        self.rol_supervisor = Rol.objects.create(nombre_rol=Rol.SUPERVISOR)
        self.rol_consulta = Rol.objects.create(nombre_rol=Rol.CONSULTA)

        # Usuarios
        self.admin = Usuario.objects.create_user(
            username='admin', rut='111-1', password='pass', rol=self.rol_admin
        )
        self.tecnico1 = Usuario.objects.create_user(
            username='tecnico1', rut='222-2', password='pass', rol=self.rol_tecnico
        )
        self.tecnico2 = Usuario.objects.create_user(
            username='tecnico2', rut='333-3', password='pass', rol=self.rol_tecnico
        )

        # Entidades Base
        self.cliente = ClienteMandante.objects.create(rut='777-7', razon_social='Cliente Test', giro='Giro Test')
        self.presupuesto = Presupuesto.objects.create(id_cliente=self.cliente, estado=Presupuesto.ESTADO_PENDIENTE, monto_total=100000)
        
        # Obras
        self.obra_tec1 = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            id_tecnico=self.tecnico1,
            tipo_servicio='Mantenimiento',
            estado=Obra.ESTADO_PROCESO
        )
        self.obra_tec2 = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            id_tecnico=self.tecnico2,
            tipo_servicio='Instalación',
            estado=Obra.ESTADO_PROCESO
        )
        self.obra_sin_tecnico = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            tipo_servicio='Reparación',
            estado=Obra.ESTADO_PROCESO
        )

        # URLs
        self.clientes_url = reverse('obras:clientes_list_create')
        self.contactos_url = reverse('obras:contacto_cliente_list_create')
        self.presupuestos_url = reverse('obras:presupuestos_list_create')
        self.obras_url = reverse('obras:obras_list_create')
        self.hojas_servicio_url = reverse('obras:hojas_servicio_list_create')


class ObrasFuncionalTests(ObrasBaseTestCase):

    def test_a01_rbac_clientes_presupuestos_denegados_tecnico(self):
        """A01:2025 - Técnico no puede acceder a clientes, contactos ni presupuestos"""
        self.client.force_authenticate(user=self.tecnico1)
        self.assertEqual(self.client.get(self.clientes_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.contactos_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.presupuestos_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_a01_rbac_obras_filtro_por_tecnico(self):
        """A01:2025 - Técnico solo ve sus propias obras y no puede editarlas/crearlas"""
        self.client.force_authenticate(user=self.tecnico1)
        
        # Listado: Solo ve la obra de tecnico1
        res = self.client.get(self.obras_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Check based on pagination or direct list
        data = res.data['results'] if 'results' in res.data else res.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id_tecnico'], self.tecnico1.id_usuario)

        # Intento de GET a obra ajena (tec2) -> 404 Not Found (porque el queryset lo filtra)
        url_obra_ajena = reverse('obras:obras_detail', kwargs={'pk': self.obra_tec2.id})
        self.assertEqual(self.client.get(url_obra_ajena).status_code, status.HTTP_404_NOT_FOUND)

        # Intento de crear obra -> 403 Forbidden
        payload = {'id_cliente': self.cliente.id, 'tipo_servicio': 'Test'}
        self.assertEqual(self.client.post(self.obras_url, payload).status_code, status.HTTP_403_FORBIDDEN)

        # Intento de editar su propia obra -> 403 Forbidden
        url_obra_propia = reverse('obras:obras_detail', kwargs={'pk': self.obra_tec1.id})
        self.assertEqual(self.client.patch(url_obra_propia, {'estado': Obra.ESTADO_FINALIZADA}).status_code, status.HTTP_403_FORBIDDEN)

    def test_a06_maquina_estados_cierre_obra_fallos(self):
        """A06:2025 - Reglas de negocio para pasar a 'Finalizada' (422 Unprocessable Entity)"""
        self.client.force_authenticate(user=self.admin)
        
        # 1. Fallo: Sin técnico
        url_sin_tec = reverse('obras:obras_detail', kwargs={'pk': self.obra_sin_tecnico.id})
        res1 = self.client.patch(url_sin_tec, {'estado': Obra.ESTADO_FINALIZADA})
        self.assertEqual(res1.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("La obra no tiene un técnico asignado.", res1.data['errores'])

        # Usamos obra_tec1 para el resto
        url_obra = reverse('obras:obras_detail', kwargs={'pk': self.obra_tec1.id})

        # 2. Fallo: Sin Hoja de Servicio firmada
        res2 = self.client.patch(url_obra, {'estado': Obra.ESTADO_FINALIZADA})
        self.assertEqual(res2.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(any("hoja de servicio" in e for e in res2.data['errores']))

        # Creamos Hoja (estado_firma=False no sirve, debe ser True)
        HojaServicio.objects.create(id_obra=self.obra_tec1, estado_firma=True)

        # 3. Fallo: Sin Horas Trabajadas
        res3 = self.client.patch(url_obra, {'estado': Obra.ESTADO_FINALIZADA})
        self.assertEqual(res3.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(any("horas trabajadas" in e for e in res3.data['errores']))

        # Agregamos Horas
        HorasTrabajadas.objects.create(id_obra=self.obra_tec1, id_tecnico=self.tecnico1, cantidad_horas=Decimal('2.5'), costo_hora=10000)

        # 4. Fallo: Sin Egresos en Cardex
        res4 = self.client.patch(url_obra, {'estado': Obra.ESTADO_FINALIZADA})
        self.assertEqual(res4.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(any("Cardex" in e for e in res4.data['errores']))

    def test_a06_maquina_estados_cierre_obra_exito(self):
         """A06:2025 - Cierre de obra exitoso tras cumplir 4 requisitos"""
         self.client.force_authenticate(user=self.admin)
         url_obra = reverse('obras:obras_detail', kwargs={'pk': self.obra_tec1.id})
         
         # Cumplir todos los requisitos
         HojaServicio.objects.create(id_obra=self.obra_tec1, estado_firma=True)
         HorasTrabajadas.objects.create(id_obra=self.obra_tec1, id_tecnico=self.tecnico1, cantidad_horas=Decimal('2.5'), costo_hora=10000)
         
         articulo = Articulo.objects.create(codigo_interno='TEST', nombre='Test', categoria='Test', unidad_medida='U')
         Cardex.objects.create(id_articulo=articulo, id_usuario=self.tecnico1, id_obra=self.obra_tec1, tipo_movimiento=Cardex.TIPO_EGRESO, cantidad=1, precio_unitario=100)

         res = self.client.patch(url_obra, {'estado': Obra.ESTADO_FINALIZADA})
         self.assertEqual(res.status_code, status.HTTP_200_OK)
         self.assertEqual(res.data['estado'], Obra.ESTADO_FINALIZADA)

    def test_a06_presupuesto_no_puede_retroceder(self):
        """A06:2025 - Presupuesto Aprobado no puede volver a Pendiente"""
        self.client.force_authenticate(user=self.admin)
        url_presupuesto = reverse('obras:presupuesto_detail', kwargs={'pk': self.presupuesto.id})
        
        # Pasar a Aprobado (200)
        res_aprob = self.client.patch(url_presupuesto, {'estado': Presupuesto.ESTADO_APROBADO})
        self.assertEqual(res_aprob.status_code, status.HTTP_200_OK)
        
        # Intentar retroceder a Pendiente (400)
        res_fallo = self.client.patch(url_presupuesto, {'estado': Presupuesto.ESTADO_PENDIENTE})
        self.assertEqual(res_fallo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no puede retroceder", str(res_fallo.data))

    def test_a08_idempotencia_hoja_servicio(self):
        """A08:2025 - Idempotencia en HojaServicio con client_uuid (201 -> 200)"""
        self.client.force_authenticate(user=self.tecnico1)
        uid = str(uuid.uuid4())
        
        payload = {
            'client_uuid': uid,
            'id_obra': self.obra_tec1.id,
            'estado_firma': True
        }
        
        # Primera petición: 201 Created
        res1 = self.client.post(self.hojas_servicio_url, payload)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        # Segunda petición (reintento por fallo de red): 200 OK, sin duplicar
        res2 = self.client.post(self.hojas_servicio_url, payload)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        
        self.assertEqual(HojaServicio.objects.filter(client_uuid=uid).count(), 1)

    def test_a10_firma_canvas_base64_extensa(self):
        """A10:2025 - Almacenamiento de string Base64 >10.000 chars en TextField"""
        self.client.force_authenticate(user=self.tecnico1)
        firma_gigante = "data:image/png;base64," + ("A" * 15000)
        
        payload = {
            'id_obra': self.obra_tec1.id,
            'firma_canvas_base64': firma_gigante,
            'estado_firma': True
        }
        
        res = self.client.post(self.hojas_servicio_url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        hoja = HojaServicio.objects.get(id=res.data['id'])
        self.assertEqual(len(hoja.firma_canvas_base64), len(firma_gigante))
        self.assertEqual(hoja.firma_canvas_base64, firma_gigante)

    def test_a05_validacion_rut_y_sqli_cliente(self):
        """A05:2025 - Validación RUT y SQLi en filtro ?id_cliente="""
        self.client.force_authenticate(user=self.admin)
        
        # RUT inválido en creación (400)
        payload = {'id_cliente': self.cliente.id, 'nombre': 'N', 'rut': 'INVAL1D', 'cargo': 'C', 'email': 'a@a.cl', 'telefono': '1'}
        res = self.client.post(self.contactos_url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
        # SQLi en ?id_cliente= (400 Bad Request o vacío si sanitizado)
        # Note: views.py needs to handle non-integer gracefully or throw ValidationError.
        # Assuming we apply similar sanitization as done in compras:
        sqli_payload = "1; DROP TABLE obras_cliente_mandante--"
        url = f"{self.contactos_url}?id_cliente={sqli_payload}"
        try:
            res_sqli = self.client.get(url)
            self.assertTrue(res_sqli.status_code in [400, 200])
        except ValueError:
            self.fail("SQLi provocó un ValueError no controlado. Requiere sanitización (ValidationError).")

    def test_a09_logging_auditoria_presupuestos(self):
        """A09:2025 - Registro OP_UPDATE en LogAuditoria al cambiar estado de Presupuesto"""
        self.client.force_authenticate(user=self.admin)
        url_presupuesto = reverse('obras:presupuesto_detail', kwargs={'pk': self.presupuesto.id})
        
        count_antes = LogAuditoria.objects.filter(tabla_afectada='obras_presupuesto').count()
        
        # Cambiar de Pendiente a Rechazado
        res = self.client.patch(url_presupuesto, {'estado': Presupuesto.ESTADO_RECHAZADO})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        count_despues = LogAuditoria.objects.filter(tabla_afectada='obras_presupuesto').count()
        self.assertEqual(count_despues, count_antes + 1)
        
        log = LogAuditoria.objects.filter(tabla_afectada='obras_presupuesto').last()
        self.assertEqual(log.tipo_operacion, LogAuditoria.OP_UPDATE)
        self.assertEqual(log.valor_anterior['estado'], Presupuesto.ESTADO_PENDIENTE)
        self.assertEqual(log.valor_nuevo['estado'], Presupuesto.ESTADO_RECHAZADO)
import base64
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.test import TransactionTestCase
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APIClient

from compras.models import DetalleCompra, DocumentoCompra, Proveedor
from core.models import LogAuditoria, Rol, Usuario
from logistica.models import Articulo, Cardex
from obras.models import ClienteMandante, HojaServicio, HorasTrabajadas, Obra, Presupuesto


def _generar_png_base64_valido() -> str:
    """Genera un PNG válido en memoria codificado en Base64 para probar ReportLab."""
    buffer = BytesIO()
    img = PILImage.new('RGB', (40, 20), color=(0, 51, 102))
    img.save(buffer, format='PNG')
    b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f"data:image/png;base64,{b64}"


class ReportesTransactionTests(TransactionTestCase):

    def setUp(self):
        self.client = APIClient()

        # Roles y Usuarios
        self.rol_admin = Rol.objects.create(nombre_rol=Rol.ADMIN_GENERAL)
        self.rol_tecnico = Rol.objects.create(nombre_rol=Rol.TECNICO)

        self.admin = Usuario.objects.create_user(
            username='admin_reportes', rut='1-1', password='pass', rol=self.rol_admin
        )
        self.tecnico1 = Usuario.objects.create_user(
            username='tec1_reportes', rut='2-2', password='pass', rol=self.rol_tecnico
        )
        self.tecnico2 = Usuario.objects.create_user(
            username='tec2_reportes', rut='3-3', password='pass', rol=self.rol_tecnico
        )

        # Entidades Base
        self.cliente = ClienteMandante.objects.create(
            rut='4-4', razon_social='Cliente R', giro='Agroindustria'
        )
        self.presupuesto = Presupuesto.objects.create(
            id_cliente=self.cliente,
            estado=Presupuesto.ESTADO_APROBADO,
            monto_total=500000,
        )

        self.obra_tec1 = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            id_tecnico=self.tecnico1,
            tipo_servicio='Instalación Frigorífica',
            estado=Obra.ESTADO_FINALIZADA,
        )
        self.obra_tec2 = Obra.objects.create(
            id_presupuesto=self.presupuesto,
            id_cliente=self.cliente,
            id_tecnico=self.tecnico2,
            tipo_servicio='Mantención',
            estado=Obra.ESTADO_PROCESO,
        )

        # Artículos (uno normal y dos críticos para probar ordenamiento por déficit)
        self.articulo = Articulo.objects.create(
            codigo_interno='ART-R1',
            nombre='Tubo Cobre',
            categoria='C',
            unidad_medida='U',
            stock_disponible=Decimal('10.00'),
            stock_minimo=Decimal('5.00'),
            precio_lista_vigente=5000,
        )
        self.articulo_critico_bajo = Articulo.objects.create(
            codigo_interno='ART-CRIT-2',
            nombre='Válvula Solenoide',
            categoria='C',
            unidad_medida='U',
            stock_disponible=Decimal('3.00'),
            stock_minimo=Decimal('5.00'),  # déficit = 2
            precio_lista_vigente=12000,
        )
        self.articulo_critico_alto = Articulo.objects.create(
            codigo_interno='ART-CRIT-8',
            nombre='Gas Refrigerante R404A',
            categoria='C',
            unidad_medida='Kg',
            stock_disponible=Decimal('2.00'),
            stock_minimo=Decimal('10.00'),  # déficit = 8
            precio_lista_vigente=25000,
        )

        # Movimientos Cardex y Horas (para rentabilidad: 500.000 - (15.000 - 5.000) - 30.000 = 460.000)
        self.mov_egreso = Cardex.objects.create(
            id_articulo=self.articulo,
            id_usuario=self.tecnico1,
            id_obra=self.obra_tec1,
            tipo_movimiento=Cardex.TIPO_EGRESO,
            cantidad=Decimal('3.00'),
            precio_unitario=5000,
        )
        self.mov_reversa = Cardex.objects.create(
            id_articulo=self.articulo,
            id_usuario=self.admin,
            tipo_movimiento=Cardex.TIPO_REVERSA,
            cantidad=Decimal('1.00'),
            precio_unitario=5000,
            id_movimiento_original=self.mov_egreso,
            motivo_reversa='Devolución sobrante de obra',
        )
        HorasTrabajadas.objects.create(
            id_obra=self.obra_tec1,
            id_tecnico=self.tecnico1,
            cantidad_horas=Decimal('3.00'),
            costo_hora=10000,
        )

        self.hoja_tec1 = HojaServicio.objects.create(
            id_obra=self.obra_tec1,
            estado_firma=True,
            firma_canvas_base64=_generar_png_base64_valido(),
        )
        self.hoja_tec2 = HojaServicio.objects.create(
            id_obra=self.obra_tec2,
            estado_firma=True,
        )

        # Compras del mes (Factura 119.000 - Nota de Crédito 19.000 = 100.000 neto compras mes)
        hoy_str = date.today().isoformat()
        self.proveedor = Proveedor.objects.create(rut='5-5', razon_social='Prov R', direccion='D')
        doc_factura = DocumentoCompra.objects.create(
            id_proveedor=self.proveedor,
            tipo_documento=DocumentoCompra.TIPO_FACTURA,
            folio='F-001',
            fecha_ingreso=hoy_str,
            subtotal=100000,
            total_neto=100000,
            iva=19000,
            total_final=119000,
        )
        DetalleCompra.objects.create(
            id_documento=doc_factura,
            id_articulo=self.articulo,
            cantidad=Decimal('1.00'),
            costo_base=100000,
            costo_neto_final=100000,
        )
        DocumentoCompra.objects.create(
            id_proveedor=self.proveedor,
            tipo_documento=DocumentoCompra.TIPO_NOTA_CREDITO,
            folio='NC-001',
            fecha_ingreso=hoy_str,
            subtotal=15966,
            total_neto=15966,
            iva=3034,
            total_final=19000,
        )

        # URLs resueltas dinámicamente desde reportes.urls
        self.url_kpis = reverse('reportes:dashboard_kpis')
        self.url_rentabilidad = reverse('reportes:rentabilidad_obras')
        self.url_alertas = reverse('reportes:alertas_stock')
        self.url_excel = reverse('reportes:exportar_cardex_excel')
        self.url_pdf_tec1 = reverse('reportes:exportar_hoja_pdf', kwargs={'id_hoja': self.hoja_tec1.id})
        self.url_pdf_tec2 = reverse('reportes:exportar_hoja_pdf', kwargs={'id_hoja': self.hoja_tec2.id})

    def test_a01_rbac_e_idor_reportes(self):
        """A01:2025 - Bloqueo 403 a técnicos en reportes globales e IDOR en PDF"""
        self.client.force_authenticate(user=self.tecnico1)

        self.assertEqual(self.client.get(self.url_kpis).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.url_rentabilidad).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.url_alertas).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.url_excel).status_code, status.HTTP_403_FORBIDDEN)

        # Técnico asignado puede descargar su propia hoja de servicio (200 OK)
        res_pdf_propio = self.client.get(self.url_pdf_tec1)
        self.assertEqual(res_pdf_propio.status_code, status.HTTP_200_OK)
        self.assertTrue(res_pdf_propio.content.startswith(b'%PDF'))

        # Técnico bloqueado al intentar descargar hoja de otro técnico (403 Forbidden)
        res_pdf_ajeno = self.client.get(self.url_pdf_tec2)
        self.assertEqual(res_pdf_ajeno.status_code, status.HTTP_403_FORBIDDEN)

    def test_math_rentabilidad_kpis_y_alertas(self):
        """Exactitud Matemática SQL en KPIs, Rentabilidad (sin duplicación) y Alertas ordenadas por déficit"""
        self.client.force_authenticate(user=self.admin)

        # 1. Dashboard KPIs
        res_kpis = self.client.get(self.url_kpis)
        self.assertEqual(res_kpis.status_code, status.HTTP_200_OK)
        self.assertEqual(res_kpis.data['obras_por_estado'].get(Obra.ESTADO_FINALIZADA), 1)
        self.assertEqual(res_kpis.data['obras_por_estado'].get(Obra.ESTADO_PROCESO), 1)
        self.assertEqual(res_kpis.data['alertas_stock_critico'], 2)
        self.assertEqual(res_kpis.data['compras_del_mes'], 100000)
        self.assertEqual(res_kpis.data['presupuestos_aprobados_mes'], 1000000)

        # 2. Rentabilidad de Obras
        res_rentabilidad = self.client.get(self.url_rentabilidad)
        self.assertEqual(res_rentabilidad.status_code, status.HTTP_200_OK)
        obras_data = (
            res_rentabilidad.data.get('results', res_rentabilidad.data)
            if isinstance(res_rentabilidad.data, dict)
            else res_rentabilidad.data
        )
        obra_rent = next((o for o in obras_data if o['id'] == self.obra_tec1.id), None)
        self.assertIsNotNone(obra_rent)
        self.assertEqual(obra_rent['monto_presupuesto'], 500000)
        self.assertEqual(obra_rent['costo_materiales'], 10000)  # (3*5000) - (1*5000)
        self.assertEqual(obra_rent['costo_horas'], 30000)       # 3 * 10000
        self.assertEqual(obra_rent['margen_neto'], 460000)      # 500000 - 10000 - 30000

        # 3. Alertas de Stock ordenadas por déficit descendente
        res_alertas = self.client.get(self.url_alertas)
        self.assertEqual(res_alertas.status_code, status.HTTP_200_OK)
        alertas_data = (
            res_alertas.data.get('results', res_alertas.data)
            if isinstance(res_alertas.data, dict)
            else res_alertas.data
        )
        self.assertEqual(len(alertas_data), 2)
        self.assertEqual(alertas_data[0]['codigo_interno'], 'ART-CRIT-8')
        self.assertEqual(alertas_data[1]['codigo_interno'], 'ART-CRIT-2')

    def test_exportacion_binaria_y_excepciones_base64(self):
        """A10:2025 & Exportación Binaria - Verifica firmas binarias, filtros y tolerancia a Base64 corrupto"""
        self.client.force_authenticate(user=self.admin)

        # Verificar cabecera XLSX (PK) y filtros
        hoy_str = date.today().isoformat()
        res_excel = self.client.get(
            f"{self.url_excel}?fecha_inicio={hoy_str}&fecha_fin={hoy_str}&id_articulo={self.articulo.id}"
        )
        self.assertEqual(res_excel.status_code, status.HTTP_200_OK)
        self.assertTrue(res_excel.content.startswith(b'PK'))
        self.assertEqual(
            res_excel['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        # Verificar PDF con Base64 válido (%PDF)
        res_pdf = self.client.get(self.url_pdf_tec1)
        self.assertEqual(res_pdf.status_code, status.HTTP_200_OK)
        self.assertTrue(res_pdf.content.startswith(b'%PDF'))

        # A10: Manejo excepcional de Base64 corrupto sin HTTP 500
        hoja_corrupta = HojaServicio.objects.create(
            id_obra=self.obra_tec1,
            estado_firma=True,
            firma_canvas_base64='ESTO_NO_ES_BASE_64_*&@^',
        )
        url_corrupta = reverse('reportes:exportar_hoja_pdf', kwargs={'id_hoja': hoja_corrupta.id})
        res_pdf_corrupto = self.client.get(url_corrupta)
        self.assertEqual(res_pdf_corrupto.status_code, status.HTTP_200_OK)
        self.assertTrue(res_pdf_corrupto.content.startswith(b'%PDF'))

    def test_a09_logging_exportaciones(self):
        """A09:2025 - LogAuditoria registra cada exportación de Excel y PDF"""
        self.client.force_authenticate(user=self.admin)

        logs_excel_antes = LogAuditoria.objects.filter(
            tabla_afectada='logistica_cardex',
            valor_nuevo__accion='Exportación Excel Cardex',
        ).count()
        logs_pdf_antes = LogAuditoria.objects.filter(
            tabla_afectada='obras_hoja_servicio',
            valor_nuevo__accion='Generación PDF',
        ).count()

        res_excel = self.client.get(self.url_excel)
        self.assertEqual(res_excel.status_code, status.HTTP_200_OK)

        res_pdf = self.client.get(self.url_pdf_tec1)
        self.assertEqual(res_pdf.status_code, status.HTTP_200_OK)

        logs_excel_despues = LogAuditoria.objects.filter(
            tabla_afectada='logistica_cardex',
            valor_nuevo__accion='Exportación Excel Cardex',
        ).count()
        logs_pdf_despues = LogAuditoria.objects.filter(
            tabla_afectada='obras_hoja_servicio',
            valor_nuevo__accion='Generación PDF',
        ).count()

        self.assertEqual(logs_excel_despues, logs_excel_antes + 1)
        self.assertEqual(logs_pdf_despues, logs_pdf_antes + 1)
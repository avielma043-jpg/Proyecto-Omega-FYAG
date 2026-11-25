"""
Vistas analíticas del Dashboard Gerencial y Reportes Operativos.
Optimizadas mediante Aggregates, Annotates y Subqueries nativas.
"""

import base64
from io import BytesIO
from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

import openpyxl
from openpyxl.styles import Font, PatternFill
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader


from datetime import datetime
from django.utils import timezone
from django.db.models import (
    Count, Sum, F, Q, ExpressionWrapper, IntegerField, OuterRef, Subquery
)
from django.db.models.functions import Coalesce

from rest_framework import generics
from rest_framework.response import Response

from .permissions import CanViewDashboard
from .serializers import RentabilidadObraSerializer, AlertaStockSerializer

from obras.models import Obra, HorasTrabajadas, Presupuesto, HojaServicio
from logistica.models import Articulo, Cardex
from compras.models import DocumentoCompra
from core.models import LogAuditoria, Rol

class ExportarCardexExcelAPIView(APIView):
    """Genera Excel en memoria del historial Cardex."""
    permission_classes = [CanViewDashboard]

    def get(self, request, *args, **kwargs):
        # Filtros opcionales
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        id_articulo = request.query_params.get('id_articulo')

        queryset = Cardex.objects.select_related('id_articulo', 'id_usuario').all().order_by('-fecha_movimiento')
        if fecha_inicio:
            queryset = queryset.filter(fecha_movimiento__date__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_movimiento__date__lte=fecha_fin)
        if id_articulo:
            queryset = queryset.filter(id_articulo_id=id_articulo)

        # Creación del Workbook en memoria
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Historial Cardex FYAG"

        # Estilos corporativos FYAG
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
        
        headers = [
            "ID", "Fecha", "Código", "Artículo", 
            "Tipo Movimiento", "Cantidad", "Precio Unitario (CLP)", 
            "Usuario", "ID Obra Asociada"
        ]
        ws.append(headers)
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        # Poblar datos respetando tipos (Cantidades en Decimal, Precios en Int)
        for mov in queryset:
            ws.append([
                mov.id,
                mov.fecha_movimiento.strftime('%Y-%m-%d %H:%M'),
                mov.id_articulo.codigo_interno,
                mov.id_articulo.nombre,
                mov.tipo_movimiento,
                float(mov.cantidad),
                mov.precio_unitario,
                mov.id_usuario.username,
                mov.id_obra_id or "N/A"
            ])

        # Auditoría de exportación financiera
        LogAuditoria.objects.create(
            usuario=request.user,
            tabla_afectada='logistica_cardex',
            tipo_operacion=LogAuditoria.OP_INSERT,
            valor_anterior=None,
            valor_nuevo={
                'accion': 'Exportación Excel Cardex', 
                'filtros': request.query_params.dict(),
                'registros_exportados': queryset.count()
            }
        )

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(), 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="Reporte_Cardex_FYAG.xlsx"'
        return response


class ExportarHojaServicioPDFAPIView(APIView):
    """Genera PDF en memoria con decodificación de firma Base64."""
    permission_classes = [IsAuthenticated] 

    def get(self, request, id_hoja, *args, **kwargs):
        try:
            hoja = HojaServicio.objects.select_related(
                'id_obra', 'id_obra__id_cliente', 'id_obra__id_tecnico'
            ).get(id=id_hoja)
        except HojaServicio.DoesNotExist:
            raise Http404

        usuario = request.user
        rol_nombre = usuario.rol.nombre_rol if usuario.rol else None

        # RBAC dinámico: Técnico solo puede exportar SI la obra es suya
        if not usuario.is_superuser:
            if rol_nombre == Rol.TECNICO:
                if hoja.id_obra.id_tecnico_id != usuario.id_usuario:
                    raise PermissionDenied("No puede exportar una Hoja de Servicio que no le pertenece.")
            elif rol_nombre not in [Rol.ADMIN_GENERAL, Rol.ADMINISTRACION, Rol.SUPERVISOR]:
                 raise PermissionDenied("Su perfil no tiene permisos para generar este comprobante.")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
        styles = getSampleStyleSheet()
        elements = []

        # Encabezado Institucional
        elements.append(Paragraph("Frío y Agroindustria SpA (FYAG)", styles['Title']))
        elements.append(Paragraph(f"Comprobante Oficial - Hoja de Servicio #{hoja.id}", styles['Heading2']))
        elements.append(Spacer(1, 15))

        # Información General
        obra = hoja.id_obra
        cliente = obra.id_cliente
        tecnico = obra.id_tecnico

        datos_info = [
            ["Fecha del Servicio:", hoja.fecha_servicio.strftime('%Y-%m-%d %H:%M')],
            ["Cliente Mandante:", cliente.razon_social],
            ["RUT Cliente:", cliente.rut],
            ["Obra ID / Estado:", f"#{obra.id} - {obra.estado}"],
            ["Técnico Ejecutor:", f"{tecnico.get_full_name()} ({tecnico.rut})" if tecnico else "No asignado"],
        ]
        
        t_info = Table(datos_info, colWidths=[150, 350])
        t_info.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 20))

        # Cuadro de Materiales Egresados en la Obra
        egresos = Cardex.objects.filter(id_obra=obra.id, tipo_movimiento=Cardex.TIPO_EGRESO).select_related('id_articulo')
        if egresos.exists():
            elements.append(Paragraph("Materiales Insumidos en Terreno:", styles['Heading3']))
            mat_data = [["Código", "Artículo", "Cantidad"]]
            for egreso in egresos:
                mat_data.append([
                    egreso.id_articulo.codigo_interno,
                    egreso.id_articulo.nombre,
                    f"{float(egreso.cantidad)} {egreso.id_articulo.unidad_medida}"
                ])
            t_mat = Table(mat_data, colWidths=[100, 300, 100])
            t_mat.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
            ]))
            elements.append(t_mat)
        else:
            elements.append(Paragraph("No se registraron egresos de materiales de bodega para esta obra.", styles['Normal']))

        elements.append(Spacer(1, 40))

        # Decodificación segura e incrustación de la Firma Canvas Base64
        if hoja.estado_firma and hoja.firma_canvas_base64:
            try:
                # Separar cabecera MIME si existe (ej. data:image/png;base64,iVBORw0...)
                base64_str = hoja.firma_canvas_base64.split('base64,')[-1]
                image_data = base64.b64decode(base64_str)
                img_buffer = BytesIO(image_data)
                img_reader = ImageReader(img_buffer)
                
                elements.append(Image(img_reader, width=200, height=100))
                elements.append(Paragraph("Firma Electrónica de Conformidad del Cliente", styles['Normal']))
            except Exception as e:
                elements.append(Paragraph("[Error de formato al procesar la firma táctil]", styles['Normal']))
        else:
            elements.append(Paragraph("Hoja de servicio sin firma del cliente.", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)

        # Auditoría de descarga
        LogAuditoria.objects.create(
            usuario=request.user,
            tabla_afectada='obras_hoja_servicio',
            tipo_operacion=LogAuditoria.OP_INSERT,
            valor_anterior=None,
            valor_nuevo={'accion': 'Generación PDF', 'id_hoja': id_hoja}
        )

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Comprobante_Servicio_{id_hoja}.pdf"'
        return response


class DashboardKPIsAPIView(APIView):
    """
    Retorna los KPIs principales del mes en una sola respuesta JSON.
    """
    permission_classes = [CanViewDashboard]

    def get(self, request, *args, **kwargs):
        hoy = timezone.now()
        inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 1. Conteo de obras por estado
        obras_agrupadas = Obra.objects.values('estado').annotate(total=Count('id'))
        estado_obras = {item['estado']: item['total'] for item in obras_agrupadas}

        # 2. Conteo de artículos en stock crítico
        alertas_count = Articulo.objects.filter(stock_disponible__lte=F('stock_minimo')).count()

        # 3. Total de compras del mes (Facturas/Boletas - Notas de Crédito)
        compras_positivas = DocumentoCompra.objects.filter(
            fecha_ingreso__gte=inicio_mes.date(),
            tipo_documento__in=[DocumentoCompra.TIPO_FACTURA, DocumentoCompra.TIPO_BOLETA, DocumentoCompra.TIPO_GUIA]
        ).aggregate(total=Coalesce(Sum('total_final'), 0))['total']

        compras_negativas = DocumentoCompra.objects.filter(
            fecha_ingreso__gte=inicio_mes.date(),
            tipo_documento=DocumentoCompra.TIPO_NOTA_CREDITO
        ).aggregate(total=Coalesce(Sum('total_final'), 0))['total']
        
        total_compras_mes = int(compras_positivas - compras_negativas)

        # 4. Total de presupuestos aprobados asociados a obras de este mes
        presupuestos_aprobados = Obra.objects.filter(
            fecha_creacion__gte=inicio_mes.date(),
            id_presupuesto__estado=Presupuesto.ESTADO_APROBADO
        ).aggregate(total=Coalesce(Sum('id_presupuesto__monto_total'), 0))['total']

        return Response({
            "obras_por_estado": estado_obras,
            "alertas_stock_critico": alertas_count,
            "compras_del_mes": total_compras_mes,
            "presupuestos_aprobados_mes": int(presupuestos_aprobados)
        })


class RentabilidadObrasListAPIView(generics.ListAPIView):
    """
    Calcula la rentabilidad real de cada obra mediante Subqueries
    para evitar productos cartesianos (explosión de joins) en PostgreSQL.
    """
    serializer_class = RentabilidadObraSerializer
    permission_classes = [CanViewDashboard]

    def get_queryset(self):
        # Subquery: Costo de Mano de Obra
        horas_sq = HorasTrabajadas.objects.filter(
            id_obra=OuterRef('pk')
        ).values('id_obra').annotate(
            total=Sum(
                ExpressionWrapper(F('cantidad_horas') * F('costo_hora'), output_field=IntegerField())
            )
        ).values('total')

        # Subquery: Costo Materiales Egresados
        egresos_sq = Cardex.objects.filter(
            id_obra=OuterRef('pk'),
            tipo_movimiento=Cardex.TIPO_EGRESO
        ).values('id_obra').annotate(
            total=Sum(
                ExpressionWrapper(F('cantidad') * F('precio_unitario'), output_field=IntegerField())
            )
        ).values('total')

        # Subquery: Materiales Devueltos (Reversas apuntando al egreso original de la obra)
        reversas_sq = Cardex.objects.filter(
            id_movimiento_original__id_obra=OuterRef('pk'),
            tipo_movimiento=Cardex.TIPO_REVERSA
        ).values('id_movimiento_original__id_obra').annotate(
            total=Sum(
                ExpressionWrapper(F('cantidad') * F('precio_unitario'), output_field=IntegerField())
            )
        ).values('total')

        # Inyectar subqueries y calcular margen en tiempo real
        queryset = Obra.objects.annotate(
            monto_presupuesto=Coalesce(F('id_presupuesto__monto_total'), 0),
            costo_horas=Coalesce(Subquery(horas_sq, output_field=IntegerField()), 0),
            costo_egresos=Coalesce(Subquery(egresos_sq, output_field=IntegerField()), 0),
            costo_reversas=Coalesce(Subquery(reversas_sq, output_field=IntegerField()), 0),
        ).annotate(
            costo_materiales=ExpressionWrapper(F('costo_egresos') - F('costo_reversas'), output_field=IntegerField())
        ).annotate(
            margen_neto=ExpressionWrapper(
                F('monto_presupuesto') - F('costo_materiales') - F('costo_horas'),
                output_field=IntegerField()
            )
        ).order_by('-fecha_creacion')

        return queryset


class AlertasStockListAPIView(generics.ListAPIView):
    """
    Lista los artículos donde el stock disponible ha caído igual o debajo del mínimo.
    Ordena los resultados mostrando primero los de mayor déficit.
    """
    serializer_class = AlertaStockSerializer
    permission_classes = [CanViewDashboard]

    def get_queryset(self):
        return Articulo.objects.filter(
            stock_disponible__lte=F('stock_minimo')
        ).annotate(
            deficit=ExpressionWrapper(
                F('stock_minimo') - F('stock_disponible'), 
                output_field=IntegerField() # Definido como Integer para el ordenamiento
            )
        ).order_by('-deficit')
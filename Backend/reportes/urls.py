"""
Rutas del módulo analítico (Dashboard y Reportes).
"""
from django.urls import path
from .views import DashboardKPIsAPIView, RentabilidadObrasListAPIView, AlertasStockListAPIView, ExportarCardexExcelAPIView, ExportarHojaServicioPDFAPIView

app_name = 'reportes'

urlpatterns = [
    path('dashboard-kpis/', DashboardKPIsAPIView.as_view(), name='dashboard_kpis'),
    path('rentabilidad-obras/', RentabilidadObrasListAPIView.as_view(), name='rentabilidad_obras'),
    path('alertas-stock/', AlertasStockListAPIView.as_view(), name='alertas_stock'),
    path('exportar/cardex-excel/', ExportarCardexExcelAPIView.as_view(), name='exportar_cardex_excel'),
    path('exportar/hoja-servicio-pdf/<int:id_hoja>/', ExportarHojaServicioPDFAPIView.as_view(), name='exportar_hoja_pdf'),
]
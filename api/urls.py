from django.urls import path
from .views import (
    sancionados_list,
    buscar_expediente,
    buscar_nombre,
    crear_estatal,
    crear_federal,
    detalle_federal,
    editar_federal,
    eliminar_federal,
    detalle_estatal,
    editar_estatal,
    eliminar_estatal,
    cargar_excel_federal,
    catalogos_estatal,
)

urlpatterns = [
    path("sancionados", sancionados_list),
    path("buscar-expediente", buscar_expediente),
    path("buscar-nombre", buscar_nombre),

    path("estatal/crear", crear_estatal),
    path("estatal/detalle", detalle_estatal),
    path("estatal/editar", editar_estatal),
    path("estatal/eliminar", eliminar_estatal),

    path("federal/crear", crear_federal),
    path("federal/detalle", detalle_federal),
    path("federal/editar", editar_federal),
    path("federal/eliminar", eliminar_federal),
    path("federal/cargar-excel", cargar_excel_federal),

    path("catalogos/estatal", catalogos_estatal),
]
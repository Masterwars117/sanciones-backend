from datetime import datetime
import json
import re

import pandas as pd
from django.db.models import Q, Value, CharField
from django.db.models.functions import Coalesce, Concat
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import (
    Inhabilitado,
    InhabilitadoFederal,
    CatalogoGenero,
    CatalogoTipoSancion,
    CatalogoMoneda,
    CatalogoTipoFalta,
    CatalogoTipoDocto,
    Dependencia,
)


ESTADOS_CURP = (
    "AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|"
    "NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE"
)

# CAT_NGRAVEDAD no existe en el esquema INHABIL (Oracle 10g).
NIVELES_GRAVEDAD_ESTATAL = [
    {"clave": "L", "descripcion": "Leve"},
    {"clave": "M", "descripcion": "Media"},
    {"clave": "G", "descripcion": "Grave"},
    {"clave": "N", "descripcion": "No aplica"},
]


def parse_date(value):
    if not value:
        return None

    value = str(value).strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def parse_number(value):
    if value is None:
        return None

    value = str(value).strip()
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def normalize_rfc(value):
    if not value:
        return ""
    return re.sub(r"[\s-]", "", str(value).strip().upper())


def normalize_curp(value):
    if not value:
        return ""
    return re.sub(r"[\s-]", "", str(value).strip().upper())


def normalize_homoclave(value):
    if not value:
        return ""
    return re.sub(r"[\s-]", "", str(value).strip().upper())


def validar_rfc_estatal(rfc):
    # Persona moral: 3 letras + 6 dígitos + 3 homoclave = 12
    # Persona física: 4 letras + 6 dígitos + 3 homoclave = 13
    return bool(re.fullmatch(r"[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}", rfc))


def validar_curp(curp):
    patron = (
        rf"^[A-Z][AEIOUX][A-Z]{{2}}[0-9]{{6}}[HM]"
        rf"({ESTADOS_CURP})"
        rf"[B-DF-HJ-NP-TV-Z]{{3}}[A-Z0-9][0-9]$"
    )
    return bool(re.fullmatch(patron, curp))


def validar_rfc_federal_base(rfc):
    # 3 o 4 letras + 6 dígitos = 9 o 10 caracteres
    return bool(re.fullmatch(r"[A-ZÑ&]{3,4}[0-9]{6}", rfc))


def validar_homoclave(homoclave):
    if homoclave == "":
        return True
    return bool(re.fullmatch(r"[A-Z0-9]{3}", homoclave))


DEFAULT_PAGE_SIZE = 200
MAX_PAGE_SIZE = 200

FEDERAL_SEARCH_FIELDS = (
    "rfc__icontains",
    "homoclave__icontains",
    "apaterno__icontains",
    "amaterno__icontains",
    "nombres__icontains",
    "dependencia__icontains",
    "cargo__icontains",
    "periodo__icontains",
)

ESTATAL_SEARCH_FIELDS = (
    "anio__icontains",
    "sancionid__icontains",
    "expediente__icontains",
    "apaterno__icontains",
    "amaterno__icontains",
    "nombres__icontains",
    "rfc__icontains",
    "curp__icontains",
    "dependencia__icontains",
    "cargo__icontains",
)

NAME_SEARCH_FIELDS = (
    "apaterno__icontains",
    "amaterno__icontains",
    "nombres__icontains",
)


def _or_filter(value, field_lookups):
    filtro = Q()
    for lookup in field_lookups:
        filtro |= Q(**{lookup: value})
    return filtro


def _token_name_filter(tokens):
    filtro = Q()
    for token in tokens:
        filtro &= _or_filter(token, NAME_SEARCH_FIELDS)
    return filtro


def _annotate_nombre_completo(qs):
    return qs.annotate(
        _nombre_completo=Concat(
            Coalesce("nombres", Value("")),
            Value(" "),
            Coalesce("apaterno", Value("")),
            Value(" "),
            Coalesce("amaterno", Value("")),
            output_field=CharField(),
        ),
        _apellidos=Concat(
            Coalesce("apaterno", Value("")),
            Value(" "),
            Coalesce("amaterno", Value("")),
            output_field=CharField(),
        ),
    )


def apply_search_filter(qs, q, field_lookups):
    tokens = [t for t in re.split(r"\s+", q.strip()) if t]
    if not tokens:
        return qs

    if len(tokens) == 1:
        return qs.filter(_or_filter(tokens[0], field_lookups))

    non_name_fields = tuple(
        lookup for lookup in field_lookups if lookup not in NAME_SEARCH_FIELDS
    )

    filtro = _token_name_filter(tokens)
    if non_name_fields:
        filtro |= _or_filter(q, non_name_fields)

    return _annotate_nombre_completo(qs).filter(
        filtro | Q(_nombre_completo__icontains=q) | Q(_apellidos__icontains=q)
    )


def paginate_queryset(qs, request):
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1

    try:
        page_size = int(request.GET.get("page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        page_size = DEFAULT_PAGE_SIZE
    if page_size < 1:
        page_size = DEFAULT_PAGE_SIZE
    page_size = min(page_size, MAX_PAGE_SIZE)

    total = qs.count()
    total_pages = (total + page_size - 1) // page_size if total else 0

    if total_pages == 0:
        return {
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "next": False,
            "previous": False,
            "results": [],
        }

    if page > total_pages:
        return {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next": False,
            "previous": True,
            "message": "no hay mas datos",
        }

    offset = (page - 1) * page_size
    results = list(qs.values()[offset:offset + page_size])

    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next": page < total_pages,
        "previous": page > 1,
        "results": results,
    }


@require_GET
def sancionados_list(request):
    tipo = (request.GET.get("tipo") or "").lower().strip()
    q = (request.GET.get("q") or "").strip()

    if tipo == "federal":
        qs = InhabilitadoFederal.objects.all()
        sort = (request.GET.get("sort") or "reciente").strip()

        if q:
            qs = apply_search_filter(qs, q, FEDERAL_SEARCH_FIELDS)

        if sort == "antiguo":
            qs = qs.order_by("fechares", "rfc")
        elif sort == "nombre_asc":
            qs = _annotate_nombre_completo(qs).order_by("_nombre_completo", "rfc")
        elif sort == "nombre_desc":
            qs = _annotate_nombre_completo(qs).order_by("-_nombre_completo", "-rfc")
        else:
            qs = qs.order_by("-fechares", "-rfc")

        payload = paginate_queryset(qs, request)
        payload["tipo"] = "federal"
        return JsonResponse(payload)

    if tipo == "estatal":
        qs = Inhabilitado.objects.all()
        sort = (request.GET.get("sort") or "reciente").strip()

        if q:
            qs = apply_search_filter(qs, q, ESTATAL_SEARCH_FIELDS)

        if sort == "antiguo":
            qs = qs.order_by("fechareg", "anio", "sancionid")
        elif sort == "nombre_asc":
            qs = _annotate_nombre_completo(qs).order_by("_nombre_completo", "anio", "sancionid")
        elif sort == "nombre_desc":
            qs = _annotate_nombre_completo(qs).order_by("-_nombre_completo", "-anio", "-sancionid")
        else:
            qs = qs.order_by("-fechareg", "-anio", "-sancionid")

        payload = paginate_queryset(qs, request)
        payload["tipo"] = "estatal"
        return JsonResponse(payload)

    return JsonResponse(
        {"error": "Parámetro 'tipo' requerido: federal | estatal"},
        status=400
    )


@require_GET
def buscar_expediente(request):
    q = (request.GET.get("q") or "").strip()

    if not q:
        return JsonResponse({"error": "Debe enviar el parámetro q"}, status=400)

    resultados = list(
        Inhabilitado.objects.filter(expediente__iexact=q).values()[:200]
    )

    return JsonResponse({
        "tipo": "expediente",
        "q": q,
        "count": len(resultados),
        "resultados": resultados
    })


@require_GET
def buscar_nombre(request):
    paterno = (request.GET.get("paterno") or "").strip()
    materno = (request.GET.get("materno") or "").strip()
    nombre = (request.GET.get("nombre") or "").strip()

    if not paterno and not materno and not nombre:
        return JsonResponse(
            {"error": "Debe enviar al menos uno de estos parámetros: paterno, materno, nombre"},
            status=400
        )

    filtro_estatal = Q()
    filtro_federal = Q()

    if paterno:
        filtro_estatal &= Q(apaterno__icontains=paterno)
        filtro_federal &= Q(apaterno__icontains=paterno)

    if materno:
        filtro_estatal &= Q(amaterno__icontains=materno)
        filtro_federal &= Q(amaterno__icontains=materno)

    if nombre:
        filtro_estatal &= Q(nombres__icontains=nombre)
        filtro_federal &= Q(nombres__icontains=nombre)

    resultados_estatal = list(
        Inhabilitado.objects.filter(filtro_estatal).values()[:200]
    )

    resultados_federal = list(
        InhabilitadoFederal.objects.filter(filtro_federal).values()[:200]
    )

    return JsonResponse({
        "tipo": "nombre",
        "busqueda": {
            "paterno": paterno,
            "materno": materno,
            "nombre": nombre
        },
        "estatal_count": len(resultados_estatal),
        "federal_count": len(resultados_federal),
        "estatal": resultados_estatal,
        "federal": resultados_federal
    })


@csrf_exempt
@require_POST
def crear_estatal(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

        anio = (data.get("anio") or "").strip()
        sancionid = (data.get("sancionid") or "").strip()
        rfc = normalize_rfc(data.get("rfc"))
        curp = normalize_curp(data.get("curp"))

        if not anio or not sancionid:
            return JsonResponse(
                {"error": "AÑO y SANCIONID son obligatorios."},
                status=400
            )

        if rfc and not validar_rfc_estatal(rfc):
            return JsonResponse(
                {"error": "RFC inválido. En la estructura actual solo se admiten RFC de 12 o 13 caracteres."},
                status=400
            )

        if curp and not validar_curp(curp):
            return JsonResponse(
                {"error": "CURP inválida. Debe tener 18 caracteres y estructura válida."},
                status=400
            )

        existe = Inhabilitado.objects.filter(anio=anio, sancionid=sancionid).exists()
        if existe:
            return JsonResponse(
                {"error": "Ya existe un registro con ese AÑO y SANCIONID."},
                status=400
            )

        obj = Inhabilitado(
            anio=anio,
            sancionid=sancionid,
            oficio=(data.get("oficio") or "").strip() or None,
            f_oficio=parse_date(data.get("f_oficio")),
            expediente=(data.get("expediente") or "").strip() or None,
            f_resolucion=parse_date(data.get("f_resolucion")),
            apaterno=(data.get("apaterno") or "").strip() or None,
            amaterno=(data.get("amaterno") or "").strip() or None,
            nombres=(data.get("nombres") or "").strip() or None,
            dependencia=(data.get("dependencia") or "").strip() or None,
            cargo=(data.get("cargo") or "").strip() or None,
            entidad_labora=(data.get("entidad_labora") or "").strip() or None,
            tiposancion=(data.get("tiposancion") or "").strip() or None,
            tiposancion2=(data.get("tiposancion2") or "").strip() or None,
            periodo=(data.get("periodo") or "").strip() or None,
            deinhabil=parse_date(data.get("deinhabil")),
            ainhabil=parse_date(data.get("ainhabil")),
            motivo=(data.get("motivo") or "").strip() or None,
            statussanc1=(data.get("statussanc1") or "").strip() or None,
            statussanc2=(data.get("statussanc2") or "").strip() or None,
            rfc=rfc or None,
            fejec1=parse_date(data.get("fejec1")),
            fejec2=parse_date(data.get("fejec2")),
            monto1=(data.get("monto1") or "").strip() or None,
            monto2=(data.get("monto2") or "").strip() or None,
            curp=curp or None,
            fechareg=timezone.now(),
            genero=(data.get("genero") or "").strip() or None,
            idsesea=parse_number(data.get("idsesea")),
            cve_entidad_labora=(data.get("cve_entidad_labora") or "").strip() or None,
            tipofalta=(data.get("tipofalta") or "").strip() or None,
            nivelcateg=(data.get("nivelcateg") or "").strip() or None,
            resolucionurl=(data.get("resolucionurl") or "").strip() or None,
            observaciones=(data.get("observaciones") or "").strip() or None,
            cve_moneda1=(data.get("cve_moneda1") or "").strip() or None,
            cve_moneda2=(data.get("cve_moneda2") or "").strip() or None,
            tipo_docto=(data.get("tipo_docto") or "").strip() or None,
            titulo_docto=(data.get("titulo_docto") or "").strip() or None,
            descripcion_docto=(data.get("descripcion_docto") or "").strip() or None,
            fecha_docto=parse_date(data.get("fecha_docto")),
            particular=(data.get("particular") or "").strip() or None,
            montoapi1=parse_number(data.get("montoapi1")),
            montoapi2=parse_number(data.get("montoapi2")),
            gravedad=(data.get("gravedad") or "").strip() or None,
        )
        obj.save()

        return JsonResponse({
            "ok": True,
            "message": "Registro estatal creado correctamente."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def crear_federal(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

        rfc = normalize_rfc(data.get("rfc"))
        homoclave = normalize_homoclave(data.get("homoclave"))

        if not rfc:
            return JsonResponse(
                {"error": "RFC es obligatorio."},
                status=400
            )

        if not validar_rfc_federal_base(rfc):
            return JsonResponse(
                {"error": "RFC federal inválido. Debe capturarse sin homoclave y con base de 9 o 10 caracteres."},
                status=400
            )

        if not validar_homoclave(homoclave):
            return JsonResponse(
                {"error": "Homoclave inválida. Debe tener 3 caracteres alfanuméricos."},
                status=400
            )

        existe = InhabilitadoFederal.objects.filter(rfc=rfc).exists()
        if existe:
            return JsonResponse(
                {"error": "Ya existe un registro con ese RFC."},
                status=400
            )

        obj = InhabilitadoFederal(
            dependencia=(data.get("dependencia") or "").strip() or None,
            rfc=rfc,
            homoclave=homoclave or None,
            apaterno=(data.get("apaterno") or "").strip() or None,
            amaterno=(data.get("amaterno") or "").strip() or None,
            nombres=(data.get("nombres") or "").strip() or None,
            autsanc=(data.get("autsanc") or "").strip() or None,
            cargo=(data.get("cargo") or "").strip() or None,
            periodo=(data.get("periodo") or "").strip() or None,
            fechares=parse_date(data.get("fechares")),
            fechanot=parse_date(data.get("fechanot")),
            deinhabil=parse_date(data.get("deinhabil")),
            ainhabil=parse_date(data.get("ainhabil")),
            fechainf=parse_date(data.get("fechainf")),
        )
        obj.save()

        return JsonResponse({
            "ok": True,
            "message": "Registro federal creado correctamente."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def detalle_federal(request):
    rfc = normalize_rfc(request.GET.get("rfc"))

    if not rfc:
        return JsonResponse({"error": "RFC es obligatorio."}, status=400)

    try:
        obj = InhabilitadoFederal.objects.get(rfc=rfc)
        return JsonResponse({
            "ok": True,
            "registro": {
                "dependencia": obj.dependencia,
                "rfc": obj.rfc,
                "homoclave": obj.homoclave,
                "apaterno": obj.apaterno,
                "amaterno": obj.amaterno,
                "nombres": obj.nombres,
                "autsanc": obj.autsanc,
                "cargo": obj.cargo,
                "periodo": obj.periodo,
                "fechares": obj.fechares.isoformat() if obj.fechares else "",
                "fechanot": obj.fechanot.isoformat() if obj.fechanot else "",
                "deinhabil": obj.deinhabil.isoformat() if obj.deinhabil else "",
                "ainhabil": obj.ainhabil.isoformat() if obj.ainhabil else "",
                "fechainf": obj.fechainf.isoformat() if obj.fechainf else "",
            }
        })
    except InhabilitadoFederal.DoesNotExist:
        return JsonResponse({"error": "Registro federal no encontrado."}, status=404)


@csrf_exempt
@require_POST
def editar_federal(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

        rfc_original = normalize_rfc(data.get("rfc_original"))
        homoclave = normalize_homoclave(data.get("homoclave"))

        if not rfc_original:
            return JsonResponse({"error": "RFC original es obligatorio."}, status=400)

        if not validar_rfc_federal_base(rfc_original):
            return JsonResponse(
                {"error": "RFC federal inválido. Debe capturarse sin homoclave y con base de 9 o 10 caracteres."},
                status=400
            )

        if not validar_homoclave(homoclave):
            return JsonResponse(
                {"error": "Homoclave inválida. Debe tener 3 caracteres alfanuméricos."},
                status=400
            )

        try:
            obj = InhabilitadoFederal.objects.get(rfc=rfc_original)
        except InhabilitadoFederal.DoesNotExist:
            return JsonResponse({"error": "Registro federal no encontrado."}, status=404)

        obj.dependencia = (data.get("dependencia") or "").strip() or None
        obj.homoclave = homoclave or None
        obj.apaterno = (data.get("apaterno") or "").strip() or None
        obj.amaterno = (data.get("amaterno") or "").strip() or None
        obj.nombres = (data.get("nombres") or "").strip() or None
        obj.autsanc = (data.get("autsanc") or "").strip() or None
        obj.cargo = (data.get("cargo") or "").strip() or None
        obj.periodo = (data.get("periodo") or "").strip() or None
        obj.fechares = parse_date(data.get("fechares"))
        obj.fechanot = parse_date(data.get("fechanot"))
        obj.deinhabil = parse_date(data.get("deinhabil"))
        obj.ainhabil = parse_date(data.get("ainhabil"))
        obj.fechainf = parse_date(data.get("fechainf"))
        obj.save()

        return JsonResponse({
            "ok": True,
            "message": "Registro federal actualizado correctamente."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def eliminar_federal(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        rfc = normalize_rfc(data.get("rfc"))

        if not rfc:
            return JsonResponse({"error": "RFC es obligatorio."}, status=400)

        try:
            obj = InhabilitadoFederal.objects.get(rfc=rfc)
        except InhabilitadoFederal.DoesNotExist:
            return JsonResponse({"error": "Registro federal no encontrado."}, status=404)

        obj.delete()

        return JsonResponse({
            "ok": True,
            "message": "Registro federal eliminado correctamente."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def detalle_estatal(request):
    anio = (request.GET.get("anio") or "").strip()
    sancionid = (request.GET.get("sancionid") or "").strip()

    if not anio or not sancionid:
        return JsonResponse({"error": "AÑO y SANCIONID son obligatorios."}, status=400)

    try:
        obj = Inhabilitado.objects.get(anio=anio, sancionid=sancionid)
        return JsonResponse({
            "ok": True,
            "registro": {
                "anio": obj.anio,
                "sancionid": obj.sancionid,
                "oficio": obj.oficio or "",
                "f_oficio": obj.f_oficio.isoformat() if obj.f_oficio else "",
                "expediente": obj.expediente or "",
                "f_resolucion": obj.f_resolucion.isoformat() if obj.f_resolucion else "",
                "apaterno": obj.apaterno or "",
                "amaterno": obj.amaterno or "",
                "nombres": obj.nombres or "",
                "dependencia": obj.dependencia or "",
                "cargo": obj.cargo or "",
                "entidad_labora": obj.entidad_labora or "",
                "tiposancion": obj.tiposancion or "",
                "tiposancion2": obj.tiposancion2 or "",
                "periodo": obj.periodo or "",
                "deinhabil": obj.deinhabil.isoformat() if obj.deinhabil else "",
                "ainhabil": obj.ainhabil.isoformat() if obj.ainhabil else "",
                "motivo": obj.motivo or "",
                "statussanc1": obj.statussanc1 or "",
                "statussanc2": obj.statussanc2 or "",
                "rfc": obj.rfc or "",
                "fejec1": obj.fejec1.isoformat() if obj.fejec1 else "",
                "fejec2": obj.fejec2.isoformat() if obj.fejec2 else "",
                "monto1": obj.monto1 or "",
                "monto2": obj.monto2 or "",
                "curp": obj.curp or "",
                "fechareg": obj.fechareg.isoformat() if obj.fechareg else "",
                "genero": obj.genero or "",
                "idsesea": str(obj.idsesea) if obj.idsesea is not None else "",
                "cve_entidad_labora": obj.cve_entidad_labora or "",
                "tipofalta": obj.tipofalta or "",
                "nivelcateg": obj.nivelcateg or "",
                "resolucionurl": obj.resolucionurl or "",
                "observaciones": obj.observaciones or "",
                "cve_moneda1": obj.cve_moneda1 or "",
                "cve_moneda2": obj.cve_moneda2 or "",
                "tipo_docto": obj.tipo_docto or "",
                "titulo_docto": obj.titulo_docto or "",
                "descripcion_docto": obj.descripcion_docto or "",
                "fecha_docto": obj.fecha_docto.isoformat() if obj.fecha_docto else "",
                "particular": obj.particular or "",
                "montoapi1": str(obj.montoapi1) if obj.montoapi1 is not None else "",
                "montoapi2": str(obj.montoapi2) if obj.montoapi2 is not None else "",
                "gravedad": obj.gravedad or "",
            }
        })
    except Inhabilitado.DoesNotExist:
        return JsonResponse({"error": "Registro estatal no encontrado."}, status=404)


@csrf_exempt
@require_POST
def editar_estatal(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

        anio_original = (data.get("anio_original") or "").strip()
        sancionid_original = (data.get("sancionid_original") or "").strip()
        rfc = normalize_rfc(data.get("rfc"))
        curp = normalize_curp(data.get("curp"))

        if not anio_original or not sancionid_original:
            return JsonResponse({"error": "AÑO original y SANCIONID original son obligatorios."}, status=400)

        if rfc and not validar_rfc_estatal(rfc):
            return JsonResponse(
                {"error": "RFC inválido. En la estructura actual solo se admiten RFC de 12 o 13 caracteres."},
                status=400
            )

        if curp and not validar_curp(curp):
            return JsonResponse(
                {"error": "CURP inválida. Debe tener 18 caracteres y estructura válida."},
                status=400
            )

        try:
            obj = Inhabilitado.objects.get(anio=anio_original, sancionid=sancionid_original)
        except Inhabilitado.DoesNotExist:
            return JsonResponse({"error": "Registro estatal no encontrado."}, status=404)

        obj.oficio = (data.get("oficio") or "").strip() or None
        obj.f_oficio = parse_date(data.get("f_oficio"))
        obj.expediente = (data.get("expediente") or "").strip() or None
        obj.f_resolucion = parse_date(data.get("f_resolucion"))
        obj.apaterno = (data.get("apaterno") or "").strip() or None
        obj.amaterno = (data.get("amaterno") or "").strip() or None
        obj.nombres = (data.get("nombres") or "").strip() or None
        obj.dependencia = (data.get("dependencia") or "").strip() or None
        obj.cargo = (data.get("cargo") or "").strip() or None
        obj.entidad_labora = (data.get("entidad_labora") or "").strip() or None
        obj.tiposancion = (data.get("tiposancion") or "").strip() or None
        obj.tiposancion2 = (data.get("tiposancion2") or "").strip() or None
        obj.periodo = (data.get("periodo") or "").strip() or None
        obj.deinhabil = parse_date(data.get("deinhabil"))
        obj.ainhabil = parse_date(data.get("ainhabil"))
        obj.motivo = (data.get("motivo") or "").strip() or None
        obj.statussanc1 = (data.get("statussanc1") or "").strip() or None
        obj.statussanc2 = (data.get("statussanc2") or "").strip() or None
        obj.rfc = rfc or None
        obj.fejec1 = parse_date(data.get("fejec1"))
        obj.fejec2 = parse_date(data.get("fejec2"))
        obj.monto1 = (data.get("monto1") or "").strip() or None
        obj.monto2 = (data.get("monto2") or "").strip() or None
        obj.curp = curp or None
        obj.genero = (data.get("genero") or "").strip() or None
        obj.idsesea = parse_number(data.get("idsesea"))
        obj.cve_entidad_labora = (data.get("cve_entidad_labora") or "").strip() or None
        obj.tipofalta = (data.get("tipofalta") or "").strip() or None
        obj.nivelcateg = (data.get("nivelcateg") or "").strip() or None
        obj.resolucionurl = (data.get("resolucionurl") or "").strip() or None
        obj.observaciones = (data.get("observaciones") or "").strip() or None
        obj.cve_moneda1 = (data.get("cve_moneda1") or "").strip() or None
        obj.cve_moneda2 = (data.get("cve_moneda2") or "").strip() or None
        obj.tipo_docto = (data.get("tipo_docto") or "").strip() or None
        obj.titulo_docto = (data.get("titulo_docto") or "").strip() or None
        obj.descripcion_docto = (data.get("descripcion_docto") or "").strip() or None
        obj.fecha_docto = parse_date(data.get("fecha_docto"))
        obj.particular = (data.get("particular") or "").strip() or None
        obj.montoapi1 = parse_number(data.get("montoapi1"))
        obj.montoapi2 = parse_number(data.get("montoapi2"))
        obj.gravedad = (data.get("gravedad") or "").strip() or None
        obj.save()

        return JsonResponse({
            "ok": True,
            "message": "Registro estatal actualizado correctamente."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def eliminar_estatal(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        anio = (data.get("anio") or "").strip()
        sancionid = (data.get("sancionid") or "").strip()

        if not anio or not sancionid:
            return JsonResponse({"error": "AÑO y SANCIONID son obligatorios."}, status=400)

        try:
            obj = Inhabilitado.objects.get(anio=anio, sancionid=sancionid)
        except Inhabilitado.DoesNotExist:
            return JsonResponse({"error": "Registro estatal no encontrado."}, status=404)

        obj.delete()

        return JsonResponse({
            "ok": True,
            "message": "Registro estatal eliminado correctamente."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def cargar_excel_federal(request):
    if "file" not in request.FILES:
        return JsonResponse({"error": "No se envió archivo."}, status=400)

    file = request.FILES["file"]

    try:
        df = pd.read_excel(file, header=1)
        df.columns = [str(c).strip() for c in df.columns]

        insertados = 0
        duplicados = 0
        omitidos = 0

        for _, row in df.iterrows():
            def txt(col):
                val = row.get(col, None)
                if pd.isna(val):
                    return None
                return str(val).strip()

            def fecha(col):
                val = row.get(col, None)
                if pd.isna(val) or val in ("", None):
                    return None
                try:
                    return pd.to_datetime(val).date()
                except Exception:
                    return None

            rfc = normalize_rfc(txt("RFC"))
            homoclave = normalize_homoclave(txt("HOMO"))

            if not rfc:
                omitidos += 1
                continue

            if not validar_rfc_federal_base(rfc):
                omitidos += 1
                continue

            if not validar_homoclave(homoclave):
                omitidos += 1
                continue

            existe = InhabilitadoFederal.objects.filter(rfc=rfc).exists()
            if existe:
                duplicados += 1
                continue

            InhabilitadoFederal.objects.create(
                dependencia=txt("DEPENDENCIA"),
                rfc=rfc,
                homoclave=homoclave or None,
                apaterno=txt("APELLIDO PATERNO"),
                amaterno=txt("APELLIDO MATERNO"),
                nombres=txt("NOMBRE"),
                autsanc=txt("AUTORIDAD SANCIONADORA"),
                cargo=txt("PUESTO"),
                periodo=txt("PERIODO"),
                fechares=fecha("FECHA RESOLUCION"),
                fechanot=fecha("FECHA NOTIFICACION"),
                deinhabil=fecha("FECHA INICIO"),
                ainhabil=fecha("FECHA FIN"),
                fechainf=None,
            )

            insertados += 1

        return JsonResponse({
            "ok": True,
            "insertados": insertados,
            "duplicados": duplicados,
            "omitidos": omitidos
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def catalogos_estatal(request):
    try:
        tipos_entidad_sancionadora = [
            {"clave": 1, "descripcion": "Dependencia"},
            {"clave": 2, "descripcion": "Órgano Desconcentrado"},
            {"clave": 3, "descripcion": "Autónomos"},
            {"clave": 4, "descripcion": "Entes"},
            {"clave": 5, "descripcion": "Municipio"},
            {"clave": 6, "descripcion": "Descentralizado"},
            {"clave": 7, "descripcion": "Otros"},
        ]

        estatus_sancion = [
            {"clave": "P", "descripcion": "Preventiva"},
            {"clave": "E", "descripcion": "Ejecutoria"},
        ]

        opciones_particular = [
            {"clave": "S", "descripcion": "Sí"},
            {"clave": "N", "descripcion": "No"},
        ]

        generos = [
            {
                "clave": item["gen_cve"],
                "descripcion": item["gen_descripcion"],
            }
            for item in CatalogoGenero.objects.values("gen_cve", "gen_descripcion")
        ]

        tipos_sancion = [
            {
                "clave": item["clave"],
                "descripcion": item["descripcion"],
            }
            for item in CatalogoTipoSancion.objects.values("clave", "descripcion")
        ]

        monedas = [
            {
                "clave": item["mon_cve"],
                "descripcion": item["mon_descripcion"],
            }
            for item in CatalogoMoneda.objects.values("mon_cve", "mon_descripcion")
        ]

        niveles_gravedad = list(NIVELES_GRAVEDAD_ESTATAL)

        tipos_falta = [
            {
                "clave": item["fal_clave"],
                "descripcion": item["fal_descripcion"],
            }
            for item in CatalogoTipoFalta.objects.values("fal_clave", "fal_descripcion")
        ]

        tipos_docto = [
            {
                "clave": item["descripdocto"],
                "descripcion": item["descripdocto"],
            }
            for item in CatalogoTipoDocto.objects.values("descripdocto")
        ]

        dependencias_qs = Dependencia.objects.filter(
            Q(dep_habilitado="S") | Q(dep_habilitado__isnull=True)
        ).values(
            "clave",
            "descripcion",
            "tipo",
            "dep_siglas",
            "dep_habilitado",
        )

        dependencias = []
        for item in dependencias_qs:
            dependencias.append({
                "clave": item["clave"],
                "descripcion": item["descripcion"],
                "tipo": item["tipo"],
                "siglas": item["dep_siglas"],
                "habilitado": item["dep_habilitado"],
            })

        dependencias_por_tipo = {str(i): [] for i in range(1, 8)}
        for dep in dependencias:
            tipo = str(dep["tipo"])
            if tipo not in dependencias_por_tipo:
                dependencias_por_tipo[tipo] = []
            dependencias_por_tipo[tipo].append(dep)

        return JsonResponse({
            "ok": True,
            "catalogos": {
                "generos": generos,
                "tipos_sancion": tipos_sancion,
                "monedas": monedas,
                "niveles_gravedad": niveles_gravedad,
                "tipos_falta": tipos_falta,
                "tipos_docto": tipos_docto,
                "estatus_sancion": estatus_sancion,
                "opciones_particular": opciones_particular,
                "tipos_entidad_sancionadora": tipos_entidad_sancionadora,
                "dependencias": dependencias,
                "dependencias_por_tipo": dependencias_por_tipo,
            }
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
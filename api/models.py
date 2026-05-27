from django.db import models


class InhabilitadoFederal(models.Model):
    dependencia = models.CharField(db_column="DEPENDENCIA", max_length=500, null=True, blank=True)
    rfc = models.CharField(db_column="RFC", max_length=10, primary_key=True)
    homoclave = models.CharField(db_column="HOMOCLAVE", max_length=3, null=True, blank=True)
    apaterno = models.CharField(db_column="APATERNO", max_length=300, null=True, blank=True)
    amaterno = models.CharField(db_column="AMATERNO", max_length=300, null=True, blank=True)
    nombres = models.CharField(db_column="NOMBRES", max_length=300, null=True, blank=True)
    autsanc = models.CharField(db_column="AUTSANC", max_length=500, null=True, blank=True)
    cargo = models.CharField(db_column="CARGO", max_length=500, null=True, blank=True)
    periodo = models.CharField(db_column="PERIODO", max_length=300, null=True, blank=True)
    fechares = models.DateField(db_column="FECHARES", null=True, blank=True)
    fechanot = models.DateField(db_column="FECHANOT", null=True, blank=True)
    deinhabil = models.DateField(db_column="DEINHABIL", null=True, blank=True)
    ainhabil = models.DateField(db_column="AINHABIL", null=True, blank=True)
    fechainf = models.DateField(db_column="FECHAINF", null=True, blank=True)

    class Meta:
        db_table = "INHABILIFEDERAL"
        managed = False


class Inhabilitado(models.Model):
    anio = models.CharField(db_column="AÑO", max_length=4, primary_key=True)
    sancionid = models.CharField(db_column="SANCIONID", max_length=6)

    oficio = models.CharField(db_column="OFICIO", max_length=40, null=True, blank=True)
    f_oficio = models.DateField(db_column="F_OFICIO", null=True, blank=True)
    expediente = models.CharField(db_column="EXPEDIENTE", max_length=30, null=True, blank=True)
    f_resolucion = models.DateField(db_column="F_RESOLUCION", null=True, blank=True)

    apaterno = models.CharField(db_column="APATERNO", max_length=20, null=True, blank=True)
    amaterno = models.CharField(db_column="AMATERNO", max_length=20, null=True, blank=True)
    nombres = models.CharField(db_column="NOMBRES", max_length=50, null=True, blank=True)

    dependencia = models.CharField(db_column="DEPENDENCIA", max_length=3, null=True, blank=True)
    cargo = models.CharField(db_column="CARGO", max_length=100, null=True, blank=True)
    entidad_labora = models.CharField(db_column="ENTIDAD_LABORA", max_length=80, null=True, blank=True)

    tiposancion = models.CharField(db_column="TIPOSANCION", max_length=2, null=True, blank=True)
    tiposancion2 = models.CharField(db_column="TIPOSANCION2", max_length=2, null=True, blank=True)

    periodo = models.CharField(db_column="PERIODO", max_length=20, null=True, blank=True)
    deinhabil = models.DateField(db_column="DEINHABIL", null=True, blank=True)
    ainhabil = models.DateField(db_column="AINHABIL", null=True, blank=True)

    motivo = models.CharField(db_column="MOTIVO", max_length=300, null=True, blank=True)
    statussanc1 = models.CharField(db_column="STATUSSANC1", max_length=1, null=True, blank=True)
    statussanc2 = models.CharField(db_column="STATUSSANC2", max_length=1, null=True, blank=True)

    rfc = models.CharField(db_column="RFC", max_length=13, null=True, blank=True)
    fejec1 = models.DateField(db_column="FEJEC1", null=True, blank=True)
    fejec2 = models.DateField(db_column="FEJEC2", null=True, blank=True)

    monto1 = models.CharField(db_column="MONTO1", max_length=30, null=True, blank=True)
    monto2 = models.CharField(db_column="MONTO2", max_length=30, null=True, blank=True)

    curp = models.CharField(db_column="CURP", max_length=18, null=True, blank=True)
    fechareg = models.DateTimeField(db_column="FECHAREG", null=True, blank=True)
    genero = models.CharField(db_column="GENERO", max_length=1, null=True, blank=True)

    idsesea = models.DecimalField(db_column="IDSESEA", max_digits=38, decimal_places=0, null=True, blank=True)
    cve_entidad_labora = models.CharField(db_column="CVE_ENTIDAD_LABORA", max_length=6, null=True, blank=True)
    tipofalta = models.CharField(db_column="TIPOFALTA", max_length=4, null=True, blank=True)
    nivelcateg = models.CharField(db_column="NIVELCATEG", max_length=10, null=True, blank=True)

    resolucionurl = models.CharField(db_column="RESOLUCIONURL", max_length=300, null=True, blank=True)
    observaciones = models.CharField(db_column="OBSERVACIONES", max_length=500, null=True, blank=True)

    cve_moneda1 = models.CharField(db_column="CVE_MONEDA1", max_length=6, null=True, blank=True)
    cve_moneda2 = models.CharField(db_column="CVE_MONEDA2", max_length=6, null=True, blank=True)

    tipo_docto = models.CharField(db_column="TIPO_DOCTO", max_length=25, null=True, blank=True)
    titulo_docto = models.CharField(db_column="TITULO_DOCTO", max_length=50, null=True, blank=True)
    descripcion_docto = models.CharField(db_column="DESCRIPCION_DOCTO", max_length=50, null=True, blank=True)
    fecha_docto = models.DateField(db_column="FECHA_DOCTO", null=True, blank=True)

    particular = models.CharField(db_column="PARTICULAR", max_length=1, null=True, blank=True)

    montoapi1 = models.DecimalField(db_column="MONTOAPI1", max_digits=38, decimal_places=0, null=True, blank=True)
    montoapi2 = models.DecimalField(db_column="MONTOAPI2", max_digits=38, decimal_places=0, null=True, blank=True)

    gravedad = models.CharField(db_column="GRAVEDAD", max_length=1, null=True, blank=True)

    class Meta:
        db_table = "INHABILITADOS"
        managed = False
        unique_together = (("anio", "sancionid"),)


class CatalogoGenero(models.Model):
    gen_cve = models.CharField(db_column="GEN_CVE", max_length=1, primary_key=True)
    gen_descripcion = models.CharField(db_column="GEN_DESCRIPCION", max_length=20)

    class Meta:
        db_table = "CAT_GENERO"
        managed = False
        ordering = ["gen_cve"]


class CatalogoTipoSancion(models.Model):
    clave = models.CharField(db_column="CLAVE", max_length=2, primary_key=True)
    descripcion = models.CharField(db_column="DESCRIPCION", max_length=100)

    class Meta:
        db_table = "TIPOSANCION"
        managed = False
        ordering = ["clave"]


class CatalogoMoneda(models.Model):
    mon_cve = models.CharField(db_column="MON_CVE", max_length=6, primary_key=True)
    mon_descripcion = models.CharField(db_column="MON_DESCRIPCION", max_length=150)

    class Meta:
        db_table = "CAT_MONEDAS"
        managed = False
        ordering = ["mon_cve"]


class CatalogoTipoFalta(models.Model):
    fal_clave = models.CharField(db_column="FAL_CLAVE", max_length=4, primary_key=True)
    fal_descripcion = models.CharField(db_column="FAL_DESCRIPCION", max_length=150)

    class Meta:
        db_table = "CAT_TFALTA"
        managed = False
        ordering = ["fal_clave"]


class CatalogoTipoDocto(models.Model):
    # Esta tabla no trae PK en Oracle.
    # Para que Django pueda leerla sin inventar un campo "id",
    # usamos DESCRIPDOCTO como primary_key lógico.
    descripdocto = models.CharField(db_column="DESCRIPDOCTO", max_length=50, primary_key=True)

    class Meta:
        db_table = "CAT_TIPODOCTO"
        managed = False
        ordering = ["descripdocto"]


class Dependencia(models.Model):
    clave = models.CharField(db_column="CLAVE", max_length=3, primary_key=True)
    descripcion = models.CharField(db_column="DESCRIPCION", max_length=110)
    tipo = models.IntegerField(db_column="TIPO")
    dep_siglas = models.CharField(db_column="DEP_SIGLAS", max_length=50, null=True, blank=True)
    dep_habilitado = models.CharField(db_column="DEP_HABILITADO", max_length=1, null=True, blank=True)
    dep_idanterior = models.CharField(db_column="DEP_IDANTERIOR", max_length=6, null=True, blank=True)
    dep_cvefinanzas = models.CharField(db_column="DEP_CVEFINANZAS", max_length=6, null=True, blank=True)
    mostrarseesa = models.CharField(db_column="MOSTRARSESEA", max_length=2, null=True, blank=True)

    class Meta:
        db_table = "DEPENDENCIAS"
        managed = False
        ordering = ["tipo", "descripcion"]
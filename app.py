from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import os

app = Flask(__name__)

# Ruta del conjunto de datos
DATA_PATH = os.path.join("data", "Histórico_de_participaciones.csv")


def cargar_datos():
    """Carga el conjunto de datos."""
    df = pd.read_csv(DATA_PATH)

    # Convertir año a entero
    df["año"] = pd.to_numeric(df["año"], errors="coerce")
    df = df.dropna(subset=["año"])
    df["año"] = df["año"].astype(int)

    return df


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/poblacional")
def poblacional():
    df_total = cargar_datos()

    # -----------------------------
    # FILTROS (año y etapa)
    # -----------------------------
    año = request.args.get("año", "Todos")
    etapa = request.args.get("etapa", "Todas")

    df = df_total.copy()

    if año.isdigit():
        df = df[df["año"] == int(año)]
    else:
        año = "Todos"

    if etapa in df_total["etapa"].unique():
        df = df[df["etapa"] == etapa]
    else:
        etapa = "Todas"

    total_registros = len(df)
    hay_datos = total_registros > 0
    base = total_registros if hay_datos else 1  # evita división por cero

    def a_html(fig):
        # Plotly ya se carga en base.html
        fig.update_layout(margin=dict(t=50, b=40))
        return pio.to_html(fig, full_html=False, include_plotlyjs=False)

    # -----------------------------
    # INDICADORES
    # -----------------------------
    deportistas_unicos = df["id_deportista"].nunique()
    deportes = df["deporte"].nunique()
    pct_mujeres = (df["genero"] == "Mujer").sum() / base * 100

    # -----------------------------
    # TABLA: participación por categoría
    # -----------------------------
    tabla_categorias = []
    for columna, nombre in [
        ("genero", "Género"),
        ("tipo_deporte", "Tipo de deporte"),
        ("etapa", "Etapa"),
    ]:
        conteo = df[columna].value_counts()
        for categoria, cantidad in conteo.items():
            tabla_categorias.append({
                "variable": nombre,
                "categoria": categoria,
                "registros": int(cantidad),
                "porcentaje": cantidad / base * 100,
            })

    # -----------------------------
    # GRÁFICA 1: composición por género
    # -----------------------------
    datos_genero = df.groupby("genero").size().reset_index(name="registros")
    fig_genero = px.pie(
        datos_genero, names="genero", values="registros", hole=0.45,
        title="Distribución de registros por género"
    )
    fig_genero.update_traces(textinfo="percent+label")

    # -----------------------------
    # GRÁFICA 2: rango de edad
    # -----------------------------
    orden_edad = ["8 a 11", "12 a 15", "16 a 19", "20 a 23", "No registra"]
    datos_edad = (
        df.groupby("rango_edad").size().reindex(orden_edad, fill_value=0)
        .reset_index(name="registros")
    )
    datos_edad["porcentaje"] = datos_edad["registros"] / base * 100
    fig_edad = px.bar(
        datos_edad, x="rango_edad", y="registros",
        text=datos_edad["porcentaje"].map(lambda v: f"{v:.1f}%"),
        title="Registros por rango de edad",
        labels={"rango_edad": "Rango de edad", "registros": "Cantidad de registros"}
    )

    # -----------------------------
    # GRÁFICA 3: top 10 deportes
    # -----------------------------
    datos_deporte = (
        df.groupby("deporte").size().reset_index(name="registros")
        .sort_values("registros", ascending=False).head(10)
        .sort_values("registros")
    )
    datos_deporte["porcentaje"] = datos_deporte["registros"] / base * 100
    fig_deporte = px.bar(
        datos_deporte, x="registros", y="deporte", orientation="h",
        text=datos_deporte["porcentaje"].map(lambda v: f"{v:.1f}%"),
        title="10 deportes con más registros",
        labels={"deporte": "Deporte", "registros": "Cantidad de registros"}
    )

    # -----------------------------
    # GRÁFICA 4: poblaciones diferenciales (registros marcados con «Sí»)
    # -----------------------------
    columnas_poblacion = [c for c in df.columns if c.startswith("Población")]

    def nombre_grupo(columna):
        texto = columna.replace("Población ", "", 1)
        if texto.startswith("en "):
            texto = texto[3:]
        return texto[0].upper() + texto[1:]

    filas = []
    for c in columnas_poblacion:
        si = int((df[c] == "Sí").sum())
        filas.append({
            "grupo": nombre_grupo(c),
            "registros": si,
            "porcentaje": si / base * 100,
        })
    datos_poblacion = pd.DataFrame(filas).sort_values("porcentaje")
    fig_poblacion = px.bar(
        datos_poblacion, x="porcentaje", y="grupo", orientation="h",
        text=datos_poblacion["porcentaje"].map(lambda v: f"{v:.1f}%"),
        title="Registros que pertenecen a poblaciones diferenciales (%)",
        labels={"grupo": "Población", "porcentaje": "% de los registros"}
    )

    # -----------------------------
    # INTERPRETACIONES (calculadas sobre los datos filtrados)
    # -----------------------------
    interpretaciones = {}
    if hay_datos:
        g = df["genero"].value_counts(normalize=True) * 100
        interpretaciones["genero"] = (
            f"La categoría predominante es «{g.index[0]}» con {g.iloc[0]:.1f}% de los "
            f"registros, frente a {g.iloc[1]:.1f}% de «{g.index[1]}»."
            if len(g) > 1 else f"Solo aparece la categoría «{g.index[0]}»."
        )
        e = datos_edad.sort_values("porcentaje", ascending=False)
        interpretaciones["edad"] = (
            f"El rango «{e.iloc[0]['rango_edad']}» concentra {e.iloc[0]['porcentaje']:.1f}% "
            f"de los registros y «{e.iloc[1]['rango_edad']}» aporta {e.iloc[1]['porcentaje']:.1f}%. "
            f"Los rangos restantes tienen una participación muy baja."
        )
        d = datos_deporte.sort_values("registros", ascending=False)
        top3 = d.head(3)["porcentaje"].sum()
        interpretaciones["deporte"] = (
            f"«{d.iloc[0]['deporte']}» es el deporte con más registros "
            f"({d.iloc[0]['porcentaje']:.1f}%). Los tres primeros suman {top3:.1f}% del total."
        )
        p = datos_poblacion.sort_values("porcentaje", ascending=False)
        interpretaciones["poblacion"] = (
            f"El grupo con mayor presencia es «{p.iloc[0]['grupo']}» "
            f"({p.iloc[0]['porcentaje']:.1f}% de los registros); el de menor presencia es "
            f"«{p.iloc[-1]['grupo']}» ({p.iloc[-1]['porcentaje']:.1f}%). Un mismo registro puede "
            f"pertenecer a más de un grupo."
        )

    # -----------------------------
    # CONOCIMIENTOS EVIDENTES (siempre sobre el total de los datos)
    # -----------------------------
    T = len(df_total)
    gt = df_total["genero"].value_counts(normalize=True) * 100
    et = df_total["rango_edad"].value_counts(normalize=True) * 100
    edad_escolar = et.get("8 a 11", 0) + et.get("12 a 15", 0)
    dt = df_total["deporte"].value_counts()
    top5 = dt.head(5)
    top5_pct = top5.sum() / T * 100

    conocimientos = [
        {
            "titulo": "Participación según género",
            "pregunta": "¿Cómo se reparte la participación entre hombres y mujeres?",
            "variables": "genero",
            "procedimiento": "Se contaron los registros por categoría de género y se calculó el porcentaje sobre el total.",
            "evidencia": "Gráfica 1 y tabla de participación por categoría.",
            "hallazgo": (
                f"«{gt.index[0]}» representa {gt.iloc[0]:.1f}% de los registros y "
                f"«{gt.index[1]}» {gt.iloc[1]:.1f}%, una diferencia de "
                f"{round(gt.iloc[0], 1) - round(gt.iloc[1], 1):.1f} puntos porcentuales."
            ),
            "interpretacion": "La participación no es paritaria: hay una categoría con mayor presencia en los Juegos.",
            "utilidad": "Permite plantear estrategias para equilibrar la participación entre géneros.",
            "limitacion": "No explica por qué existe la diferencia ni si se repite en todos los deportes o territorios.",
        },
        {
            "titulo": "Concentración en edades escolares tempranas",
            "pregunta": "¿En qué rangos de edad se concentra la población participante?",
            "variables": "rango_edad",
            "procedimiento": "Se contaron los registros por rango de edad y se sumaron los porcentajes de los dos primeros rangos.",
            "evidencia": "Gráfica 2.",
            "hallazgo": (
                f"Los rangos «8 a 11» y «12 a 15» suman {edad_escolar:.1f}% de los registros; "
                f"«No registra» corresponde a {et.get('No registra', 0):.1f}%."
            ),
            "interpretacion": "La población está formada casi en su totalidad por niños y adolescentes, coherente con un evento escolar.",
            "utilidad": "Ayuda a diseñar la oferta deportiva y los recursos para esas edades.",
            "limitacion": "El rango «No registra» impide clasificar a una parte de los registros.",
        },
        {
            "titulo": "Pocos deportes concentran la participación",
            "pregunta": "¿Qué deportes tienen mayor y menor participación?",
            "variables": "deporte",
            "procedimiento": "Se contaron los registros por deporte, se ordenaron de mayor a menor y se sumó el porcentaje de los cinco primeros.",
            "evidencia": "Gráfica 3.",
            "hallazgo": (
                f"Los 5 deportes principales ({', '.join(top5.index)}) reúnen {top5_pct:.1f}% de los registros, "
                f"de un total de {dt.size} deportes. El de menor participación es «{dt.index[-1]}» "
                f"({dt.iloc[-1]:,} registros)."
            ),
            "interpretacion": "La participación está muy concentrada en pocas disciplinas, y varias tienen presencia mínima.",
            "utilidad": "Orienta la asignación de escenarios y apoyo, y la promoción de los deportes menos practicados.",
            "limitacion": "Un mayor número de registros no equivale a mayor calidad ni a más personas, porque un deportista puede tener varios registros.",
        },
    ]

    return render_template(
        "poblacional.html",
        hay_datos=hay_datos,
        total_registros=total_registros,
        deportistas_unicos=deportistas_unicos,
        deportes=deportes,
        pct_mujeres=pct_mujeres,
        tabla_categorias=tabla_categorias,
        grafica_genero=a_html(fig_genero) if hay_datos else "",
        grafica_edad=a_html(fig_edad) if hay_datos else "",
        grafica_deporte=a_html(fig_deporte) if hay_datos else "",
        grafica_poblacion=a_html(fig_poblacion) if hay_datos else "",
        interpretaciones=interpretaciones,
        conocimientos=conocimientos,
        años=sorted(df_total["año"].unique()),
        etapas=sorted(df_total["etapa"].unique()),
        año_seleccionado=año,
        etapa_seleccionada=etapa,
    )


@app.route("/territorial")
def territorial():
    df = cargar_datos()

    # Filtros recibidos desde la página
    año = request.args.get("año", "Todos")
    subregion_filtro = request.args.get("subregion", "Todas")

    # Aplicar filtro de año
    if año != "Todos":
        df = df[df["año"] == int(año)]

    # Aplicar filtro de subregión
    if subregion_filtro != "Todas":
        df = df[df["subregion"] == subregion_filtro]

    # -----------------------------
    # INDICADORES
    # -----------------------------

    total_registros = len(df)
    municipios = df["municipio"].nunique()
    subregiones = df["subregion"].nunique()

    # -----------------------------
    # GRÁFICA 1
    # Registros por subregión
    # -----------------------------

    datos_subregion = (
        df.groupby("subregion")
        .size()
        .reset_index(name="registros")
        .sort_values("registros", ascending=False)
    )

    fig_subregion = px.bar(
        datos_subregion,
        x="subregion",
        y="registros",
        title="Registros de participación por subregión",
        labels={
            "subregion": "Subregión",
            "registros": "Cantidad de registros"
        }
    )

    fig_subregion.update_layout(
        xaxis_tickangle=-45
    )

    grafica_subregion = pio.to_html(
        fig_subregion,
        full_html=False,
        include_plotlyjs="cdn"
    )

    # -----------------------------
    # GRÁFICA 2
    # Top 10 municipios
    # -----------------------------

    datos_municipios = (
        df.groupby("municipio")
        .size()
        .reset_index(name="registros")
        .sort_values("registros", ascending=False)
        .head(10)
        .sort_values("registros")
    )

    fig_municipios = px.bar(
        datos_municipios,
        x="registros",
        y="municipio",
        orientation="h",
        title="Top 10 municipios por cantidad de registros",
        labels={
            "municipio": "Municipio",
            "registros": "Cantidad de registros"
        }
    )

    grafica_municipios = pio.to_html(
        fig_municipios,
        full_html=False,
        include_plotlyjs=False
    )

    # -----------------------------
    # GRÁFICA 3
    # Subregión × género
    # -----------------------------

    datos_genero = (
        df.groupby(["subregion", "genero"])
        .size()
        .reset_index(name="registros")
    )

    fig_genero = px.bar(
        datos_genero,
        x="subregion",
        y="registros",
        color="genero",
        barmode="stack",
        title="Distribución de registros por subregión y género",
        labels={
            "subregion": "Subregión",
            "registros": "Cantidad de registros",
            "genero": "Género"
        }
    )

    fig_genero.update_layout(
        xaxis_tickangle=-45
    )

    grafica_genero = pio.to_html(
        fig_genero,
        full_html=False,
        include_plotlyjs=False
    )

    # -----------------------------
    # OPCIONES DE FILTROS
    # -----------------------------

    df_completo = cargar_datos()

    años = sorted(df_completo["año"].unique())
    subregiones_lista = sorted(df_completo["subregion"].dropna().unique())

    return render_template(
        "territorial.html",
        total_registros=total_registros,
        municipios=municipios,
        subregiones=subregiones,
        grafica_subregion=grafica_subregion,
        grafica_municipios=grafica_municipios,
        grafica_genero=grafica_genero,
        años=años,
        subregiones_lista=subregiones_lista,
        año_seleccionado=año,
        subregion_seleccionada=subregion_filtro
    )

@app.route("/temporal")
def temporal():
    df = cargar_datos()

    def a_html(fig):
        # Plotly ya se carga en base.html, por eso include_plotlyjs=False
        return pio.to_html(fig, full_html=False, include_plotlyjs=False)

    # -----------------------------
    # DATOS BASE
    # -----------------------------
    por_anio = (
        df.groupby("año")
        .size()
        .reset_index(name="registros")
        .sort_values("año")
    )
    por_anio["variacion"] = por_anio["registros"].pct_change() * 100

    anio_min = int(por_anio["año"].min())
    anio_max = int(por_anio["año"].max())

    fila_pico = por_anio.loc[por_anio["registros"].idxmax()]
    fila_valle = por_anio.loc[por_anio["registros"].idxmin()]

    primero = por_anio["registros"].iloc[0]
    ultimo = por_anio["registros"].iloc[-1]
    cambio_total = ((ultimo - primero) / primero * 100) if primero else 0

    # -----------------------------
    # GRÁFICA 1: evolución total
    # -----------------------------
    fig_total = px.line(
        por_anio, x="año", y="registros", markers=True,
        title="Registros de participación por año",
        labels={"año": "Año", "registros": "Cantidad de registros"}
    )
    fig_total.update_xaxes(dtick=1)

    # -----------------------------
    # GRÁFICA 2: variación interanual
    # -----------------------------
    var = por_anio.dropna(subset=["variacion"]).copy()
    var["color"] = var["variacion"].apply(lambda v: "Aumento" if v >= 0 else "Disminución")
    fig_var = px.bar(
        var, x="año", y="variacion", color="color",
        color_discrete_map={"Aumento": "#2e7d32", "Disminución": "#c62828"},
        title="Variación porcentual anual (%)",
        labels={"año": "Año", "variacion": "Variación (%)", "color": ""}
    )
    fig_var.update_xaxes(dtick=1)

    # -----------------------------
    # GRÁFICA 3: por género
    # -----------------------------
    datos_genero = df.groupby(["año", "genero"]).size().reset_index(name="registros")
    fig_genero = px.line(
        datos_genero, x="año", y="registros", color="genero", markers=True,
        title="Evolución de registros por género",
        labels={"año": "Año", "registros": "Cantidad de registros", "genero": "Género"}
    )
    fig_genero.update_xaxes(dtick=1)

    # -----------------------------
    # GRÁFICA 4: por subregión
    # -----------------------------
    datos_sub = df.groupby(["año", "subregion"]).size().reset_index(name="registros")
    fig_sub = px.line(
        datos_sub, x="año", y="registros", color="subregion", markers=True,
        title="Evolución de registros por subregión",
        labels={"año": "Año", "registros": "Cantidad de registros", "subregion": "Subregión"}
    )
    fig_sub.update_xaxes(dtick=1)

    # -----------------------------
    # GRÁFICA 5: municipios activos por año
    # -----------------------------
    muni_anio = df.groupby("año")["municipio"].nunique().reset_index(name="municipios")
    fig_muni = px.bar(
        muni_anio, x="año", y="municipios",
        title="Municipios con al menos un registro, por año",
        labels={"año": "Año", "municipios": "Municipios"}
    )
    fig_muni.update_xaxes(dtick=1)

    # -----------------------------
    # CONCLUSIONES 
    # -----------------------------
    conclusiones = []

    tendencia = "aumentó" if cambio_total > 0 else "disminuyó"
    conclusiones.append(
        f"Entre {anio_min} y {anio_max} la participación {tendencia} un "
        f"{abs(cambio_total):.1f}% (de {primero:,} a {ultimo:,} registros)."
    )
    conclusiones.append(
        f"El año de mayor participación fue {int(fila_pico['año'])} "
        f"({int(fila_pico['registros']):,} registros) y el de menor fue "
        f"{int(fila_valle['año'])} ({int(fila_valle['registros']):,} registros)."
    )

    if not var.empty:
        mayor_alza = var.loc[var["variacion"].idxmax()]
        mayor_caida = var.loc[var["variacion"].idxmin()]
        conclusiones.append(
            f"El mayor crecimiento interanual ocurrió en {int(mayor_alza['año'])} "
            f"({mayor_alza['variacion']:+.1f}%) y la mayor caída en "
            f"{int(mayor_caida['año'])} ({mayor_caida['variacion']:+.1f}%)."
        )

    # Género: proporción en el primer y último año
    gen = df.groupby(["año", "genero"]).size().unstack(fill_value=0)
    if not gen.empty:
        prop = gen.div(gen.sum(axis=1), axis=0) * 100
        dominante = prop.iloc[-1].idxmax()
        conclusiones.append(
            f"En {anio_max}, la categoría de género con mayor peso fue «{dominante}» "
            f"({prop.iloc[-1][dominante]:.1f}%), frente a {prop.iloc[0][dominante]:.1f}% en {anio_min}."
        )

    conclusiones.append(
        f"La cobertura territorial pasó de {int(muni_anio['municipios'].iloc[0])} municipios en "
        f"{anio_min} a {int(muni_anio['municipios'].iloc[-1])} en {anio_max}."
    )

    return render_template(
        "temporal.html",
        anio_min=anio_min,
        anio_max=anio_max,
        anio_pico=int(fila_pico["año"]),
        registros_pico=int(fila_pico["registros"]),
        anio_valle=int(fila_valle["año"]),
        registros_valle=int(fila_valle["registros"]),
        cambio_total=float(cambio_total),
        grafica_total=a_html(fig_total),
        grafica_variacion=a_html(fig_var),
        grafica_genero=a_html(fig_genero),
        grafica_subregion=a_html(fig_sub),
        grafica_municipios=a_html(fig_muni),
        conclusiones=conclusiones,
    )


# =====================================================================
# DIMENSIÓN RELACIONAL Y MULTIVARIADA (Integrante 4)
# Cada gráfica cruza: 2 variables de población + territorio + año
# =====================================================================

# Las subregiones cambiaron en 2024: se agrupan los años 2021-2023
# con los mismos nombres de 2024-2025 para poder compararlos.
HOMOLOGACION_SUBREGION = {
    "Norte": "Norte y Bajo Cauca",
    "Bajo Cauca": "Norte y Bajo Cauca",
    "Nordeste": "Nordeste y Magdalena Medio",
    "Magdalena Medio": "Nordeste y Magdalena Medio",
}

# Columnas de población vulnerable disponibles en el dataset
GRUPOS_VULNERABLES = [
    "Población víctima",
    "Población en Situación de desplazamiento",
    "Población campesina",
    "Población con discapacidad",
    "Población migrante",
    "Población en proceso de reincorporación",
    "Población LGTBI",
]

# Rangos de edad con datos suficientes (los demás tienen 4 registros en total)
RANGOS_EDAD = ["8 a 11", "12 a 15"]

# Cantidad máxima de municipios a mostrar cuando se elige una subregión
MAX_MUNICIPIOS = 8

# Mínimo de registros para que un porcentaje se tenga en cuenta en los indicadores
MIN_REGISTROS = 30


# ---------------------------------------------------------------------
# PREGUNTA 1: brecha de género por deporte y rango de edad
# ---------------------------------------------------------------------
COLOR_GENERO = {"Hombre": "#1f77b4", "Mujer": "#e377c2"}
AÑOS_COMPARABLES = [2021, 2022, 2023]  # desde 2024 casi no hay registros de 12 a 15 años
MIN_REGISTROS_DEPORTE = 20  # mínimo por rango de edad para mostrar un deporte


def pregunta_genero_edad(df, subregion_sel, deporte_sel):
    """Calcula indicadores y gráficas de la pregunta 1."""
    df = df[df["rango_edad"].isin(RANGOS_EDAD)].copy()
    df["es_mujer"] = (df["genero"] == "Mujer") * 100

    # Cada gráfica usa un filtro distinto (se explica en la página)
    df_sub = df if subregion_sel == "Todas" else df[df["subregion_h"] == subregion_sel]
    df_dep = df if deporte_sel == "Todos" else df[df["deporte"] == deporte_sel]
    df_ambos = df_sub if deporte_sel == "Todos" else df_sub[df_sub["deporte"] == deporte_sel]

    def a_html(fig, alto=500):
        fig.update_layout(margin=dict(t=40, b=40), height=alto)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        return pio.to_html(fig, full_html=False, include_plotlyjs=False)

    # --- Indicadores (años comparables, con ambos filtros) ---
    # Brecha = % de hombres - % de mujeres (en puntos porcentuales)
    comparable = df_ambos[df_ambos["año"].isin(AÑOS_COMPARABLES)]
    pct = comparable.groupby("rango_edad")["es_mujer"].mean()
    mujeres_8 = round(float(pct.get("8 a 11", 0)), 1)
    mujeres_12 = round(float(pct.get("12 a 15", 0)), 1)
    brecha_8 = round(100 - 2 * mujeres_8, 1)    # (100 - M) - M
    brecha_12 = round(100 - 2 * mujeres_12, 1)
    aumento_brecha = round(brecha_12 - brecha_8, 1)

    # --- Gráfica 1.1: % de hombres y mujeres por deporte en cada rango de edad ---
    base_a = df_sub[df_sub["año"].isin(AÑOS_COMPARABLES)]
    conteo = base_a.groupby(["deporte", "rango_edad"])["es_mujer"].agg(["mean", "size"]).unstack()
    conteo = conteo[(conteo["size"] >= MIN_REGISTROS_DEPORTE).all(axis=1)]  # datos en ambos rangos
    orden_deportes = conteo["mean"]["8 a 11"].sort_values().index.tolist()

    ga = (base_a[base_a["deporte"].isin(orden_deportes)]
          .groupby(["deporte", "rango_edad"])["genero"]
          .value_counts(normalize=True).mul(100).round(1)
          .reset_index(name="porcentaje"))

    fig_a = px.bar(
        ga, x="porcentaje", y="deporte", color="genero", facet_col="rango_edad",
        orientation="h", barmode="stack", text_auto=".0f",
        category_orders={"deporte": orden_deportes, "rango_edad": RANGOS_EDAD,
                         "genero": ["Hombre", "Mujer"]},
        color_discrete_map=COLOR_GENERO,
        labels={"porcentaje": "% de registros", "deporte": "Deporte",
                "genero": "Género", "rango_edad": "Rango de edad"},
    )
    fig_a.add_vline(x=50, line_dash="dot", line_color="white")
    fig_a.update_layout(legend=dict(orientation="h", y=1.08))
    grafica_a = a_html(fig_a, alto=max(450, 30 * len(orden_deportes)))

    # Deporte donde más cae la participación femenina al pasar a 12 a 15
    cambio = (conteo["mean"]["8 a 11"] - conteo["mean"]["12 a 15"]).sort_values()
    deporte_mayor_caida = cambio.index[-1] if len(cambio) else "Sin datos"
    caida_max = round(float(cambio.iloc[-1]), 1) if len(cambio) else 0

    # --- Gráfica 1B: cantidad de hombres y mujeres por año y rango de edad ---
    gb = df_ambos.groupby(["año", "rango_edad", "genero"]).size().reset_index(name="registros")
    fig_b = px.bar(
        gb, x="año", y="registros", color="genero", barmode="group",
        facet_col="rango_edad", text_auto=True,
        category_orders={"rango_edad": RANGOS_EDAD},
        color_discrete_map=COLOR_GENERO,
        labels={"año": "Año", "registros": "Registros", "genero": "Género", "rango_edad": "Rango de edad"},
    )
    fig_b.update_xaxes(dtick=1)
    grafica_b = a_html(fig_b, alto=450)

    # --- Gráfica 1.3: % de hombres y mujeres por subregión en cada rango de edad ---
    base_c = df_dep[df_dep["año"].isin(AÑOS_COMPARABLES)]
    gc = (base_c.groupby(["subregion_h", "rango_edad"])["genero"]
          .value_counts(normalize=True).mul(100).round(1)
          .reset_index(name="porcentaje"))
    fig_c = px.bar(
        gc, x="porcentaje", y="subregion_h", color="genero", facet_col="rango_edad",
        orientation="h", barmode="stack", text_auto=".0f",
        category_orders={"rango_edad": RANGOS_EDAD, "genero": ["Hombre", "Mujer"]},
        color_discrete_map=COLOR_GENERO,
        labels={"porcentaje": "% de registros", "subregion_h": "Subregión",
                "genero": "Género", "rango_edad": "Rango de edad"},
    )
    fig_c.add_vline(x=50, line_dash="dot", line_color="white")
    fig_c.update_layout(legend=dict(orientation="h", y=1.1))
    grafica_c = a_html(fig_c, alto=420)

    return dict(
        p1_mujeres_8=mujeres_8, p1_mujeres_12=mujeres_12,
        p1_brecha_8=brecha_8, p1_brecha_12=brecha_12, p1_aumento_brecha=aumento_brecha,
        p1_deporte_caida=deporte_mayor_caida, p1_caida=caida_max,
        p1_grafica_a=grafica_a, p1_grafica_b=grafica_b, p1_grafica_c=grafica_c,
    )


@app.route("/multivariada")
def multivariada():
    df = cargar_datos()
    df["subregion_h"] = df["subregion"].replace(HOMOLOGACION_SUBREGION)
    subregiones = sorted(df["subregion_h"].unique())

    # -----------------------------
    # FILTROS
    # -----------------------------
    subregion_sel = request.args.get("subregion", "Todas")
    grupo_sel = request.args.get("grupo", GRUPOS_VULNERABLES[0])

    if grupo_sel not in GRUPOS_VULNERABLES:
        grupo_sel = GRUPOS_VULNERABLES[0]

    # Filtros de la pregunta 1
    deportes = sorted(df["deporte"].unique())
    p1_subregion = request.args.get("p1_subregion", "Todas")
    p1_deporte = request.args.get("p1_deporte", "Todos")
    if p1_subregion not in subregiones:
        p1_subregion = "Todas"
    if p1_deporte not in deportes:
        p1_deporte = "Todos"
    pregunta1 = pregunta_genero_edad(df, p1_subregion, p1_deporte)

    # Filtro 1: con "Todas" se comparan subregiones;
    # con una subregión elegida se comparan sus municipios principales.
    if subregion_sel in subregiones:
        df = df[df["subregion_h"] == subregion_sel]
        principales = df["municipio"].value_counts().head(MAX_MUNICIPIOS).index
        df = df[df["municipio"].isin(principales)].copy()
        territorio = "municipio"
        nombre_territorio = "Municipio"
    else:
        subregion_sel = "Todas"
        territorio = "subregion_h"
        nombre_territorio = "Subregión"

    # Columnas auxiliares: valen 100 si se cumple la condición y 0 si no.
    # Así, el promedio de la columna en cada grupo es directamente un porcentaje.
    df["es_mujer"] = (df["genero"] == "Mujer") * 100
    df["es_final"] = (df["etapa"] == "Final") * 100
    df["es_12_15"] = (df["rango_edad"] == "12 a 15") * 100
    df["es_vulnerable"] = (df[grupo_sel] == "Sí") * 100

    grupo_txt = grupo_sel.lower()
    etiquetas = {
        "año": "Año",
        territorio: nombre_territorio,
        "etapa": "Etapa", "rango_edad": "Rango de edad",
        "deporte": "Deporte", "genero": "Género",
        "es_mujer": "% de mujeres",
        "es_final": "% en etapa Final",
        "es_12_15": "% de 12 a 15 años",
        "es_vulnerable": f"% {grupo_txt}",
        "registros": "Registros",
    }

    def a_html(fig, alto=550):
        fig.update_layout(margin=dict(t=40, b=40), height=alto)
        return pio.to_html(fig, full_html=False, include_plotlyjs=False)

    años = sorted(df["año"].unique())

    # -----------------------------
    # GRÁFICA 1: Género + Etapa + Territorio + Año  →  burbujas animadas
    # Cada burbuja es un territorio en un año:
    #   eje X = % de mujeres, eje Y = % en etapa Final, tamaño = registros
    # -----------------------------
    g1 = df.groupby(["año", territorio]).agg(
        es_mujer=("es_mujer", "mean"),
        es_final=("es_final", "mean"),
        registros=("es_mujer", "size"),
    ).round(1)

    # Completa las combinaciones año-territorio que no existan, para que
    # todos los territorios aparezcan en la animación desde el primer año.
    todas = pd.MultiIndex.from_product([años, sorted(df[territorio].unique())],
                                       names=["año", territorio])
    g1 = g1.reindex(todas).reset_index()
    g1["registros"] = g1["registros"].fillna(0)

    fig1 = px.scatter(
        g1, x="es_mujer", y="es_final", size="registros", color=territorio,
        animation_frame="año", animation_group=territorio,
        size_max=55, range_x=[20, 80], range_y=[-5, 60],
        hover_name=territorio, labels=etiquetas,
    )
    fig1.add_vline(x=50, line_dash="dot", line_color="gray")  # línea de paridad de género
    grafica1 = a_html(fig1)

    # -----------------------------
    # GRÁFICA 2: Rango de edad + Deporte + Territorio + Año  →  categorías paralelas
    # Cada columna es una variable; el grosor de cada cinta es la cantidad de registros
    # y su color indica el año.
    # -----------------------------
    top_deportes = df["deporte"].value_counts().head(5).index
    g2 = (
        df[df["rango_edad"].isin(RANGOS_EDAD) & df["deporte"].isin(top_deportes)]
        .groupby(["año", territorio, "rango_edad", "deporte"]).size()
        .reset_index(name="registros")
    )

    fig2 = go.Figure(go.Parcats(
        dimensions=[
            dict(label="Año", values=g2["año"], categoryorder="category ascending"),
            dict(label=nombre_territorio, values=g2[territorio]),
            dict(label="Rango de edad", values=g2["rango_edad"],
                 categoryorder="array", categoryarray=RANGOS_EDAD),
            dict(label="Deporte", values=g2["deporte"]),
        ],
        counts=g2["registros"],
        line=dict(color=g2["año"], colorscale="Viridis", shape="hspline",
                  showscale=True, colorbar=dict(title="Año", dtick=1)),
        hoveron="color",
        hoverinfo="count+probability",
        arrangement="freeform",
    ))
    grafica2 = a_html(fig2, alto=650)

    # -----------------------------
    # GRÁFICA 3: Deporte + Población vulnerable + Territorio + Año  →  sunburst
    # Centro = año, anillo medio = territorio, anillo exterior = deporte.
    # Tamaño = registros; color = % del grupo vulnerable seleccionado.
    # -----------------------------
    g3 = (
        df[df["deporte"].isin(top_deportes)]
        .groupby(["año", territorio, "deporte"])
        .agg(registros=("es_vulnerable", "size"), es_vulnerable=("es_vulnerable", "mean"))
        .round(1).reset_index()
    )
    g3["año"] = g3["año"].astype(str)  # el año como texto para que funcione como categoría

    fig3 = px.sunburst(
        g3, path=["año", territorio, "deporte"], values="registros",
        color="es_vulnerable", color_continuous_scale="Reds",
        labels=etiquetas,
    )
    fig3.update_traces(
        hovertemplate="<b>%{label}</b><br>Registros: %{value}<br>"
                      f"% {grupo_txt}: " + "%{color:.1f}%<extra></extra>"
    )
    grafica3 = a_html(fig3, alto=650)

    # -----------------------------
    # INDICADORES
    # -----------------------------
    total_registros = len(df)
    num_territorios = df[territorio].nunique()

    # 1. Combinación más frecuente (territorio + deporte + género + año)
    combo = df.groupby([territorio, "deporte", "genero", "año"]).size().sort_values(ascending=False)
    combo_nombre = " · ".join(str(v) for v in combo.index[0])
    combo_registros = int(combo.iloc[0])

    # 2. Mayor % de mujeres en la etapa Final (solo grupos con suficientes registros)
    finales = df[df["etapa"] == "Final"].groupby([territorio, "año"])["es_mujer"].agg(["mean", "size"])
    finales = finales[finales["size"] >= MIN_REGISTROS]
    if finales.empty:
        mujeres_final_nombre, mujeres_final_pct = "Sin datos", 0
    else:
        top = finales["mean"].idxmax()
        mujeres_final_nombre = f"{top[0]} · {top[1]}"
        mujeres_final_pct = round(finales["mean"].max(), 1)

    # 3. Año con mayor % del grupo vulnerable seleccionado
    vulnerable_por_año = df.groupby("año")["es_vulnerable"].mean()
    vulnerable_año = int(vulnerable_por_año.idxmax())
    vulnerable_pct = round(vulnerable_por_año.max(), 1)

    return render_template(
        "multivariada.html",
        subregiones=subregiones, subregion_sel=subregion_sel,
        deportes=deportes, p1_subregion=p1_subregion, p1_deporte=p1_deporte,
        **pregunta1,
        grupos=GRUPOS_VULNERABLES, grupo_sel=grupo_sel,
        nombre_territorio=nombre_territorio,
        total_registros=total_registros, num_territorios=num_territorios,
        combo_nombre=combo_nombre, combo_registros=combo_registros,
        mujeres_final_nombre=mujeres_final_nombre, mujeres_final_pct=mujeres_final_pct,
        vulnerable_año=vulnerable_año, vulnerable_pct=vulnerable_pct,
        grafica1=grafica1,
        grafica2=grafica2,
        grafica3=grafica3,
    )


if __name__ == "__main__":
    app.run(debug=True)
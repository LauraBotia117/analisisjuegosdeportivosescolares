from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.io as pio
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

    # =====================================================
# INTEGRANTE 4: DIMENSIÓN RELACIONAL Y MULTIVARIADA
# =====================================================
COLUMNAS_DIFERENCIALES = [
    'Población en Situación de desplazamiento', 'Población campesina',
    'Población con discapacidad', 'Población en proceso de reincorporación',
    'Población migrante', 'Población víctima', 'Población LGTBI'
]

def calcular_indicadores_multivariada(df_filtrado, total_general):
    """Calcula los 3 indicadores principales para el tablero multivariado."""
    total_filtrado = len(df_filtrado)
    if total_filtrado == 0:
        return {
            'total_participantes': 0,
            'porcentaje_general': 0.0,
            'total_inclusion': 0,
            'porcentaje_inclusion': 0.0,
            'porcentaje_mujeres': 0.0,
            'porcentaje_finalistas': 0.0
        }

    pct_general = round((total_filtrado / total_general) * 100, 1)

    # Inclusión diferencial (al menos un 'Sí')
    cols_existentes = [c for c in COLUMNAS_DIFERENCIALES if c in df_filtrado.columns]
    es_vulnerable = (df_filtrado[cols_existentes] == 'Sí').any(axis=1) if cols_existentes else pd.Series(False, index=df_filtrado.index)
    total_inclusion = int(es_vulnerable.sum())
    pct_inclusion = round((total_inclusion / total_filtrado) * 100, 1)

    # Género y acceso a finales
    mujeres = (df_filtrado['genero'] == 'Mujer').sum()
    pct_mujeres = round((mujeres / total_filtrado) * 100, 1)

    finalistas = (df_filtrado['etapa'] == 'Final').sum()
    pct_finalistas = round((finalistas / total_filtrado) * 100, 1)

    return {
        'total_participantes': total_filtrado,
        'porcentaje_general': pct_general,
        'total_inclusion': total_inclusion,
        'porcentaje_inclusion': pct_inclusion,
        'porcentaje_mujeres': pct_mujeres,
        'porcentaje_finalistas': pct_finalistas
    }
@app.route("/multivariada")
def multivariada():
    df_completo = cargar_datos()
 
    # 1. Leer filtros de la URL
    subregion_sel = request.args.get("subregion", "Todas")
    año_sel = request.args.get("año", "Todos")
    etapa_sel = request.args.get("etapa", "Todas")
    genero_sel = request.args.get("genero", "Todos")
 
    # 2. Filtrar datos
    df = aplicar_filtros(df_completo, subregion_sel, año_sel, etapa_sel, genero_sel)
 
    # 3. Calcular indicadores
    indicadores = calcular_indicadores_multivariada(df, len(df_completo))
 
    # 4. Enviar todo a la plantilla
    return render_template(
        "multivariada.html",
        hay_datos=len(df) > 0,
        indicadores=indicadores,
        subregiones_lista=opciones_unicas(df_completo, "subregion"),
        años_lista=opciones_unicas(df_completo, "año", como_entero=True),
        etapas_lista=opciones_unicas(df_completo, "etapa"),
        generos_lista=opciones_unicas(df_completo, "genero"),
        subregion_seleccionada=subregion_sel,
        año_seleccionado=año_sel,
        etapa_seleccionada=etapa_sel,
        genero_seleccionado=genero_sel,
    )
if __name__ == "__main__":
    app.run(debug=True)
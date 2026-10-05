from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = Flask(__name__)

# Ruta del conjunto de datos
DATA_PATH = os.path.join("data", "Histórico_de_participaciones.csv")


def cargar_datos(solo_con_año=True):
    """Carga el conjunto de datos.

    solo_con_año=True  -> elimina las filas sin año (comportamiento original,
                          lo usan poblacional, temporal y multivariada).
    solo_con_año=False -> conserva todas las filas; la dimensión territorial
                          no depende del año, así que usa el total completo.
    """
    df = pd.read_csv(DATA_PATH)

    # Convertir año a entero
    df["año"] = pd.to_numeric(df["año"], errors="coerce")
    if solo_con_año:
        df = df.dropna(subset=["año"])
        df["año"] = df["año"].astype(int)

    return df


@app.route("/")
def inicio():
    return render_template("index.html")


def coma_txt(valor, decimales=2):
    """11.886 -> '11,89'"""
    return f"{valor:.{decimales}f}".replace(".", ",")


def pct_txt(valor, decimales=2):
    """55.94 -> '55,94 %'"""
    return coma_txt(valor, decimales) + " %"


def calcular_hallazgos(df):
    """Convierte los datos (ya filtrados) en hallazgos con una decisión asociada.

    Cada hallazgo es un diccionario con:
      titulo     tema del hallazgo
      cifra      dato clave que se muestra en grande
      etiqueta   qué significa la cifra
      hallazgo   comportamiento identificado en los datos
      decision   decisión que ese hallazgo permite sustentar
      evidencia  dónde se ve en el tablero
    """
    hallazgos = []
    if len(df) == 0:
        return hallazgos

    # ---------- Hallazgo 1: género ----------
    art = {"Hombre": "los hombres", "Mujer": "las mujeres"}
    g = df["genero"].value_counts(normalize=True) * 100
    if len(g) > 1:
        mayor, menor = g.index[0], g.index[1]
        diferencia = g.iloc[0] - g.iloc[1]
        if diferencia >= 5:
            decision = (
                "Diseñar estrategias de convocatoria y permanencia dirigidas a "
                f"{art.get(menor, menor)}, que son el grupo con menor presencia."
            )
        else:
            decision = (
                "La participación por género es casi paritaria: mantener el "
                "seguimiento anual sin priorizar un grupo."
            )
        hallazgos.append({
            "titulo": "Participación por género",
            "cifra": coma_txt(diferencia) + " pp",
            "etiqueta": (
                "puntos porcentuales de diferencia entre "
                f"{art.get(mayor, mayor)} y {art.get(menor, menor)}"
            ),
            "hallazgo": (
                f"{art.get(mayor, mayor).capitalize()} representan {pct_txt(g.iloc[0])} "
                f"de los registros y {art.get(menor, menor)} {pct_txt(g.iloc[1])}."
            ),
            "decision": decision,
            "evidencia": "Gráfica 1 y tabla «Participación por categoría».",
        })

    # ---------- Hallazgo 2: edad ----------
    escolar = df["rango_edad"].isin(["8 a 11", "12 a 15"]).mean() * 100
    mayores = df["rango_edad"].isin(["16 a 19", "20 a 23"]).mean() * 100
    sin_edad = (df["rango_edad"] == "No registra").mean() * 100
    hallazgos.append({
        "titulo": "Edad de los participantes",
        "cifra": pct_txt(escolar),
        "etiqueta": "de los registros corresponde a niños y adolescentes de 8 a 15 años",
        "hallazgo": (
            f"Los rangos de 8 a 11 y de 12 a 15 años reúnen {pct_txt(escolar)} de los "
            f"registros. Los de 16 a 23 años suman {pct_txt(mayores)} y el "
            f"{pct_txt(sin_edad)} no informa la edad."
        ),
        "decision": (
            "Dimensionar escenarios, entrenadores y calendario de competencias para "
            "las edades de 8 a 15 años; si se desea ampliar la cobertura, revisar por "
            "qué casi no hay participantes de 16 años en adelante."
        ),
        "evidencia": "Gráfica 2 (registros por rango de edad).",
    })

    # ---------- Hallazgo 3: concentración por deporte ----------
    conteo = df["deporte"].value_counts()
    top5 = conteo.head(5)
    top5_pct = top5.sum() / len(df) * 100
    pocos = int((conteo / len(df) * 100 < 1).sum())
    if pocos == 0:
        extra = ""
    elif pocos == 1:
        extra = ", y 1 deporte tiene menos de 1 % de los registros"
    else:
        extra = f", y {pocos} deportes tienen cada uno menos de 1 % de los registros"
    hallazgos.append({
        "titulo": "Concentración por deporte",
        "cifra": pct_txt(top5_pct),
        "etiqueta": f"de los registros está en solo {len(top5)} de los {len(conteo)} deportes",
        "hallazgo": (
            f"{', '.join(top5.index)} reúnen {pct_txt(top5_pct)} de los registros{extra}."
        ),
        "decision": (
            "Priorizar escenarios, jueces y apoyo logístico para los deportes de mayor "
            "demanda y diseñar un plan de promoción para los de menor participación."
        ),
        "evidencia": "Gráfica 3 (10 deportes con más registros).",
    })

    # ---------- Hallazgo 4: modalidad y etapa ----------
    conjunto = (df["tipo_deporte"] == "Conjunto").mean() * 100
    if df["etapa"].nunique() > 1:
        final = (df["etapa"] == "Final").mean() * 100
        hallazgos.append({
            "titulo": "Modalidad y etapa",
            "cifra": pct_txt(final),
            "etiqueta": "de los registros corresponde a la etapa Final",
            "hallazgo": (
                f"Los deportes de conjunto reúnen {pct_txt(conjunto)} de los registros y "
                f"la etapa Final {pct_txt(final)}, cerca de 1 de cada {round(100 / final)} "
                "registros. No es una tasa de clasificación, porque un mismo deportista "
                "puede tener varios registros."
            ),
            "decision": (
                "Usar esta proporción como referencia para planear los escenarios y el "
                "alojamiento de la etapa Final, teniendo en cuenta que en los deportes "
                "de conjunto viajan equipos completos."
            ),
            "evidencia": "Tabla «Participación por categoría» (tipo de deporte y etapa).",
        })
    else:
        hallazgos.append({
            "titulo": "Modalidad del deporte",
            "cifra": pct_txt(conjunto),
            "etiqueta": "de los registros corresponde a deportes de conjunto",
            "hallazgo": (
                f"Los deportes de conjunto reúnen {pct_txt(conjunto)} de los registros "
                "analizados."
            ),
            "decision": (
                "Prever transporte y alojamiento para equipos completos en los deportes "
                "de conjunto."
            ),
            "evidencia": "Tabla «Participación por categoría» (tipo de deporte).",
        })
    
    return hallazgos

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

     hallazgos = calcular_hallazgos(df)
   # -----------------------------
    # CONOCIMIENTOS EVIDENTES 
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
         hallazgos=hallazgos,
        años=sorted(df_total["año"].unique()),
        etapas=sorted(df_total["etapa"].unique()),
        año_seleccionado=año,
        etapa_seleccionada=etapa,
    )


# =====================================================================
# DIMENSIÓN TERRITORIAL (Integrante 2)
# =====================================================================

def miles(n):
    """10214 -> '10.214'"""
    return f"{int(n):,}".replace(",", ".")


def coma(x, decimales=1):
    """9.69 -> '9,7'"""
    return f"{x:.{decimales}f}".replace(".", ",")


def porcentaje(parte, total):
    """10214, 53579 -> '19,06 %'"""
    if total == 0:
        return "0 %"
    return coma(parte / total * 100, 2) + " %"


def html_plotly(fig):
    # Plotly ya se carga en base.html, por eso include_plotlyjs=False
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def texto_composicion(df, top_municipios):
    """Subregión de los municipios del top. Ej.: '5 de X, 4 de Y y 1 de Z'."""
    mapa = df.groupby("municipio")["subregion"].agg(
        lambda s: s.mode().iat[0] if not s.mode().empty else "Sin dato"
    )
    conteo = top_municipios["municipio"].map(mapa).value_counts()
    partes = [f"{n} de {sub}" for sub, n in conteo.items()]
    if len(partes) > 1:
        return ", ".join(partes[:-1]) + " y " + partes[-1]
    return partes[0] if partes else ""


def conocimientos_territorial(df):
    """Los 3 conocimientos evidentes, calculados con TODOS los registros."""
    total = len(df)
    subs = df.groupby("subregion").size().sort_values(ascending=False)
    muns = (
        df.groupby("municipio").size().reset_index(name="registros")
        .sort_values("registros", ascending=False)
    )
    top10 = muns.head(10)

    # --- Conocimiento 1: concentración por subregión
    top3 = subs.head(3)
    suma3 = top3.sum()
    lista_top3 = ", ".join(
        f"{s} ({miles(v)} registros, {porcentaje(v, total)})" for s, v in top3.items()
    )
    cuanto = "más de la mitad" if suma3 / total > 0.5 else "una parte importante"

    k1 = {
        "titulo": "Los registros se concentran en pocas subregiones",
        "partes": [
            ("Pregunta", "¿Los registros de participación se reparten de forma uniforme entre las subregiones?"),
            ("Variables", "subregion (territorio) y la cantidad de registros."),
            ("Procedimiento", f"Se contaron los registros de cada subregión y se dividió cada cantidad entre el total del conjunto de datos ({miles(total)} registros)."),
            ("Evidencia", "Gráfica 1: registros por subregión, con el porcentaje de cada una sobre las barras."),
            ("Hallazgo", f"{lista_top3}. Entre las tres reúnen el {porcentaje(suma3, total)} de los registros."),
            ("Interpretación", f"Tres de las {len(subs)} subregiones concentran {cuanto} de los registros; la distribución territorial no es uniforme."),
            ("Utilidad", "Permite saber en qué territorios se concentra la participación y dónde es menor, para orientar la planeación de los juegos."),
            ("Limitación", "Un registro no equivale a una persona (un deportista puede aparecer en varios registros) y no se conoce la población escolar de cada subregión, por lo que no puede medirse qué proporción de estudiantes participa."),
        ],
    }

    # --- Conocimiento 2: brecha entre extremos
    mayor, menor = subs.index[0], subs.index[-1]
    vmayor, vmenor = subs.iloc[0], subs.iloc[-1]
    ultimas = ", ".join(subs.sort_values().head(3).index)

    k2 = {
        "titulo": "Gran diferencia entre la subregión con más y con menos registros",
        "partes": [
            ("Pregunta", "¿Qué tan grande es la diferencia entre los territorios extremos?"),
            ("Variables", "subregion (territorio) y la cantidad de registros."),
            ("Procedimiento", "Se comparó la subregión con más registros con la que tiene menos, en cantidad absoluta (resta) y como razón (división)."),
            ("Evidencia", "Gráfica 1: barras ordenadas de mayor a menor."),
            ("Hallazgo", f"{mayor} tiene {miles(vmayor)} registros y {menor} {miles(vmenor)}: una diferencia de {miles(vmayor - vmenor)}. {mayor} tiene unas {coma(vmayor / vmenor)} veces los registros de {menor}, que aporta solo el {porcentaje(vmenor, total)}."),
            ("Interpretación", "Hay territorios con una representación muy baja frente al resto del conjunto de datos."),
            ("Utilidad", f"Permite identificar las subregiones menos representadas ({ultimas}) para revisar si el vacío se debe a menor participación o a menor registro de los datos."),
            ("Limitación", "Los datos no explican la causa de la diferencia. Además, las subregiones cambiaron en 2024: desde ese año Norte se agrupa con Bajo Cauca y Nordeste con Magdalena Medio, por lo que los registros de una misma zona están repartidos entre varias categorías según el año."),
        ],
    }

    # --- Conocimiento 3: concentración municipal
    m1, m2 = muns.iloc[0], muns.iloc[1]
    k3 = {
        "titulo": "La concentración también se observa en los municipios",
        "partes": [
            ("Pregunta", "¿La concentración territorial también se observa a nivel de municipio?"),
            ("Variables", "municipio y subregion (territorio)."),
            ("Procedimiento", "Se contaron los registros por municipio, se tomaron los 10 con más registros y se identificó la subregión de cada uno."),
            ("Evidencia", "Gráfica 2: top 10 de municipios por cantidad de registros."),
            ("Hallazgo", f"{m1['municipio']} ({miles(m1['registros'])}) y {m2['municipio']} ({miles(m2['registros'])}) son los municipios con más registros. Entre los 10 primeros hay {texto_composicion(df, top10)}, y juntos reúnen el {porcentaje(top10['registros'].sum(), total)} de los registros."),
            ("Interpretación", "Pocos municipios, ubicados en pocas subregiones, aportan una parte importante de los registros. Urabá no depende de un solo municipio: varios aparecen entre los primeros."),
            ("Utilidad", "Indica en qué municipios se concentra la actividad y dónde conviene mirar con más detalle."),
            ("Limitación", f"Se comparan {df['municipio'].nunique()} municipios de tamaños muy distintos y no se dispone de su población escolar, por lo que no puede decirse en cuáles participan proporcionalmente más estudiantes."),
        ],
    }

    return [k1, k2, k3]


@app.route("/territorial")
def territorial():
    df_completo = cargar_datos(solo_con_año=False)
    df = df_completo

    # Filtros recibidos desde la página
    año = request.args.get("año", "Todos")
    subregion_filtro = request.args.get("subregion", "Todas")

    if año.isdigit():
        df = df[df["año"] == int(año)]
    else:
        año = "Todos"

    if subregion_filtro != "Todas":
        df = df[df["subregion"] == subregion_filtro]

    # -----------------------------
    # INDICADORES
    # -----------------------------
    total_registros = len(df)
    municipios = df["municipio"].nunique()
    subregiones = df["subregion"].nunique()

    # -----------------------------
    # GRÁFICA 1: registros por subregión
    # -----------------------------
    datos_subregion = (
        df.groupby("subregion")
        .size()
        .reset_index(name="registros")
        .sort_values("registros", ascending=False)
    )
    datos_subregion["porcentaje"] = (
        datos_subregion["registros"] / max(total_registros, 1) * 100
    ).round(2)

    fig_subregion = px.bar(
        datos_subregion,
        x="subregion",
        y="registros",
        text="porcentaje",
        title="Registros de participación por subregión",
        labels={"subregion": "Subregión", "registros": "Cantidad de registros"},
    )
    fig_subregion.update_traces(
        texttemplate="%{text} %", textposition="outside", cliponaxis=False
    )
    fig_subregion.update_layout(xaxis_tickangle=-45)

    if total_registros == 0:
        subregion_lider = "Sin datos"
        interp_subregion = "No hay registros con los filtros seleccionados."
    else:
        lider = datos_subregion.iloc[0]
        subregion_lider = f"{lider['subregion']} ({porcentaje(lider['registros'], total_registros)})"
        if len(datos_subregion) == 1:
            interp_subregion = (
                f"Con los filtros aplicados solo aparece {lider['subregion']}, "
                f"con {miles(lider['registros'])} registros."
            )
        else:
            menor = datos_subregion.iloc[-1]
            top3 = datos_subregion.head(3)
            interp_subregion = (
                f"{lider['subregion']} tiene la mayor cantidad de registros "
                f"({miles(lider['registros'])}; {porcentaje(lider['registros'], total_registros)}) y "
                f"{menor['subregion']} la menor ({miles(menor['registros'])}; "
                f"{porcentaje(menor['registros'], total_registros)}). Las tres primeras subregiones "
                f"reúnen el {porcentaje(top3['registros'].sum(), total_registros)} de los registros, "
                "por lo que la distribución no es uniforme."
            )

    # -----------------------------
    # GRÁFICA 2: top 10 municipios
    # -----------------------------
    top_municipios = (
        df.groupby("municipio")
        .size()
        .reset_index(name="registros")
        .sort_values("registros", ascending=False)
        .head(10)
    )

    fig_municipios = px.bar(
        top_municipios.sort_values("registros"),
        x="registros",
        y="municipio",
        orientation="h",
        title="Top 10 municipios por cantidad de registros",
        labels={"municipio": "Municipio", "registros": "Cantidad de registros"},
    )

    if total_registros == 0:
        interp_municipios = "No hay registros con los filtros seleccionados."
    else:
        primero = top_municipios.iloc[0]
        interp_municipios = (
            f"{primero['municipio']} es el municipio con más registros "
            f"({miles(primero['registros'])}; {porcentaje(primero['registros'], total_registros)}). "
            f"Los {len(top_municipios)} primeros reúnen el "
            f"{porcentaje(top_municipios['registros'].sum(), total_registros)} de los registros: "
            f"{texto_composicion(df, top_municipios)}."
        )

    # -----------------------------
    # GRÁFICA 3: subregión x género
    # -----------------------------
    datos_genero = (
        df.groupby(["subregion", "genero"]).size().reset_index(name="registros")
    )

    fig_genero = px.bar(
        datos_genero,
        x="subregion",
        y="registros",
        color="genero",
        barmode="stack",
        title="Distribución de registros por subregión y género",
        labels={"subregion": "Subregión", "registros": "Cantidad de registros", "genero": "Género"},
    )
    fig_genero.update_layout(xaxis_tickangle=-45)

    interp_genero = "No hay registros con los filtros seleccionados."
    if total_registros:
        tabla = datos_genero.pivot(
            index="subregion", columns="genero", values="registros"
        ).fillna(0)
        if {"Hombre", "Mujer"} <= set(tabla.columns):
            hm = tabla["Hombre"] + tabla["Mujer"]
            pct_mujer = (tabla["Mujer"] / hm.where(hm > 0) * 100).dropna()
            total_hm = tabla["Hombre"].sum() + tabla["Mujer"].sum()
            interp_genero = (
                f"Las mujeres representan el {porcentaje(tabla['Mujer'].sum(), total_hm)} "
                "de los registros con género informado."
            )
            if len(pct_mujer) > 1:
                interp_genero += (
                    f" La participación femenina va de {coma(pct_mujer.min())} % en "
                    f"{pct_mujer.idxmin()} a {coma(pct_mujer.max())} % en {pct_mujer.idxmax()}."
                )
            if (tabla["Hombre"] > tabla["Mujer"]).all():
                interp_genero += " En todas las subregiones hay más registros de hombres que de mujeres."
        else:
            interp_genero = "La distribución de los registros varía según el género y la subregión."

    # -----------------------------
    # OPCIONES DE FILTROS Y DATOS GENERALES
    # -----------------------------
    años = sorted(df_completo["año"].dropna().astype(int).unique())
    subregiones_lista = sorted(df_completo["subregion"].dropna().unique())

    total_dataset = len(df_completo)
    menores = ", ".join(
        f"{s} ({porcentaje(v, total_dataset)})"
        for s, v in df_completo.groupby("subregion").size().sort_values().head(3).items()
    )

    return render_template(
        "territorial.html",
        total_registros=total_registros,
        municipios=municipios,
        subregiones=subregiones,
        subregion_lider=subregion_lider,
        grafica_subregion=html_plotly(fig_subregion),
        grafica_municipios=html_plotly(fig_municipios),
        grafica_genero=html_plotly(fig_genero),
        interp_subregion=interp_subregion,
        interp_municipios=interp_municipios,
        interp_genero=interp_genero,
        conocimientos=conocimientos_territorial(df_completo),
        total_dataset=total_dataset,
        n_municipios_total=df_completo["municipio"].nunique(),
        n_subregiones_total=df_completo["subregion"].nunique(),
        menores=menores,
        años=años,
        subregiones_lista=subregiones_lista,
        año_seleccionado=año,
        subregion_seleccionada=subregion_filtro,
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
# Organizada en tres preguntas que cruzan población, territorio y año
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


# ---------------------------------------------------------------------
# PREGUNTA 2: población vulnerable y no vulnerable por etapa, territorio y año
# ---------------------------------------------------------------------
COLOR_VULNERABLE = {"Vulnerable": "#e76f51", "No vulnerable": "#8ecae6"}
ORDEN_VULNERABLE = ["Vulnerable", "No vulnerable"]
ORDEN_ETAPAS = ["Subregional", "Final"]
MIN_REGISTROS_MUNICIPIO = 100  # mínimo para mostrar el porcentaje de un municipio
MAX_MUNICIPIOS_P2 = 15


def pregunta_vulnerable(df, subregion_sel, grupo_sel):
    """Calcula indicadores y gráficas de la pregunta 2."""
    df = df.copy()

    # Un registro es "Vulnerable" si tiene "Sí" en el grupo elegido
    # (o en al menos uno de los grupos, si se elige "Cualquier grupo").
    # "No" y "No registra" se cuentan como "No vulnerable".
    columnas = GRUPOS_VULNERABLES if grupo_sel == "Cualquier grupo" else [grupo_sel]
    es_vulnerable = (df[columnas] == "Sí").any(axis=1)
    df["condicion"] = es_vulnerable.map({True: "Vulnerable", False: "No vulnerable"})
    df["es_vulnerable"] = es_vulnerable * 100

    df_sub = df if subregion_sel == "Todas" else df[df["subregion_h"] == subregion_sel]

    def a_html(fig, alto=450):
        fig.update_layout(margin=dict(t=40, b=40), height=alto,
                          legend=dict(orientation="h", y=1.1))
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        return pio.to_html(fig, full_html=False, include_plotlyjs=False)

    def porcentajes(datos, grupos):
        """% de vulnerables y no vulnerables dentro de cada grupo."""
        return (datos.groupby(grupos)["condicion"]
                .value_counts(normalize=True).mul(100).round(1)
                .reset_index(name="porcentaje"))

    etiquetas = {"porcentaje": "% de registros", "condicion": "Condición",
                 "subregion_h": "Subregión", "municipio": "Municipio",
                 "etapa": "Etapa", "año": "Año", "registros": "Registros"}
    orden = {"condicion": ORDEN_VULNERABLE, "etapa": ORDEN_ETAPAS}

    # --- Indicadores (con el filtro de subregión) ---
    total_vulnerables = int(es_vulnerable[df_sub.index].sum())
    pct_vulnerable = round(float(df_sub["es_vulnerable"].mean()), 1)
    por_etapa = df_sub.groupby("etapa")["es_vulnerable"].mean()
    pct_subregional = round(float(por_etapa.get("Subregional", 0)), 1)
    pct_final = round(float(por_etapa.get("Final", 0)), 1)

    por_municipio = df_sub.groupby("municipio")["es_vulnerable"].agg(["mean", "size"])
    por_municipio = por_municipio[por_municipio["size"] >= MIN_REGISTROS_MUNICIPIO]
    if por_municipio.empty:
        municipio_max, pct_municipio_max = "Sin datos", 0
    else:
        municipio_max = por_municipio["mean"].idxmax()
        pct_municipio_max = round(float(por_municipio["mean"].max()), 1)

    # --- Gráfica 2.1: vulnerables y no vulnerables por subregión y etapa ---
    g1 = porcentajes(df, ["subregion_h", "etapa"])
    fig1 = px.bar(
        g1, x="porcentaje", y="subregion_h", color="condicion", facet_col="etapa",
        orientation="h", barmode="stack", text_auto=".0f",
        category_orders=orden, color_discrete_map=COLOR_VULNERABLE, labels=etiquetas,
    )
    grafica1 = a_html(fig1, alto=420)

    # --- Gráfica 2.2: municipios con mayor porcentaje de población vulnerable ---
    orden_mun = por_municipio["mean"].sort_values(ascending=False).head(MAX_MUNICIPIOS_P2).index
    g2 = porcentajes(df_sub[df_sub["municipio"].isin(orden_mun)], ["municipio"])
    fig2 = px.bar(
        g2, x="porcentaje", y="municipio", color="condicion",
        orientation="h", barmode="stack", text_auto=".0f",
        category_orders={**orden, "municipio": list(orden_mun)},
        color_discrete_map=COLOR_VULNERABLE, labels=etiquetas,
    )
    grafica2 = a_html(fig2, alto=max(350, 32 * len(orden_mun)))

    # --- Gráfica 2.3: evolución anual por etapa (cantidad de registros) ---
    g3 = df_sub.groupby(["año", "etapa", "condicion"]).size().reset_index(name="registros")
    fig3 = px.bar(
        g3, x="año", y="registros", color="condicion", facet_col="etapa",
        barmode="stack", text_auto=True,
        category_orders=orden, color_discrete_map=COLOR_VULNERABLE, labels=etiquetas,
    )
    fig3.update_xaxes(dtick=1)
    fig3.update_yaxes(matches=None, showticklabels=True)  # cada etapa con su propia escala
    grafica3 = a_html(fig3, alto=450)

    # % de vulnerables por año y etapa (tabla debajo de la gráfica 2.3)
    tabla = (df_sub.groupby(["año", "etapa"])["es_vulnerable"].mean().round(1)
             .unstack().reindex(columns=ORDEN_ETAPAS))
    tabla_anual = [
        dict(año=int(año),
             subregional=fila["Subregional"] if pd.notna(fila["Subregional"]) else None,
             final=fila["Final"] if pd.notna(fila["Final"]) else None)
        for año, fila in tabla.iterrows()
    ]

    return dict(
        p2_total_vulnerables=total_vulnerables, p2_pct_vulnerable=pct_vulnerable,
        p2_pct_subregional=pct_subregional, p2_pct_final=pct_final,
        p2_municipio_max=municipio_max, p2_pct_municipio_max=pct_municipio_max,
        p2_tabla_anual=tabla_anual,
        p2_grafica1=grafica1, p2_grafica2=grafica2, p2_grafica3=grafica3,
    )


# ---------------------------------------------------------------------
# PREGUNTA 3: perfil de quienes llegan a la etapa Final
# ---------------------------------------------------------------------
AÑOS_CON_FINAL = [2021, 2022, 2023, 2025]  # en 2024 no hubo etapa Final
UMBRAL_SIN_SUBREGIONAL = 90  # deportes con 90% o más de registros en la Final no tienen fase subregional real
MIN_REGISTROS_DEPORTE_P3 = 100  # mínimo por género para mostrar un deporte


def pregunta_final(df, subregion_sel, edad_sel):
    """Calcula indicadores y gráficas de la pregunta 3."""
    df = df[df["año"].isin(AÑOS_CON_FINAL) & df["rango_edad"].isin(RANGOS_EDAD)].copy()

    # Se excluyen los deportes que casi solo tienen registros en la Final
    pct_final_deporte = df.groupby("deporte")["etapa"].apply(lambda s: (s == "Final").mean() * 100)
    excluidos = sorted(pct_final_deporte[pct_final_deporte >= UMBRAL_SIN_SUBREGIONAL].index)
    df = df[~df["deporte"].isin(excluidos)]

    es_vulnerable = (df[GRUPOS_VULNERABLES] == "Sí").any(axis=1)
    df["condicion"] = es_vulnerable.map({True: "Vulnerable", False: "No vulnerable"})
    df["es_final"] = (df["etapa"] == "Final") * 100
    df["perfil"] = df["genero"] + " · " + df["rango_edad"] + " · " + df["condicion"]

    df_sub = df if subregion_sel == "Todas" else df[df["subregion_h"] == subregion_sel]
    df_edad = df if edad_sel == "Todos" else df[df["rango_edad"] == edad_sel]
    df_ambos = df_sub if edad_sel == "Todos" else df_sub[df_sub["rango_edad"] == edad_sel]

    def a_html(fig, alto=450):
        fig.update_layout(margin=dict(t=40, b=40), height=alto,
                          legend=dict(orientation="h", y=1.1))
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        return pio.to_html(fig, full_html=False, include_plotlyjs=False)

    etiquetas = {"es_final": "% de registros en la Final", "perfil": "Perfil",
                 "condicion": "Condición", "genero": "Género", "deporte": "Deporte",
                 "subregion_h": "Subregión", "año": "Año"}

    # --- Indicadores (con ambos filtros) ---
    pct_final = round(float(df_ambos["es_final"].mean()), 1)
    por_condicion = df_ambos.groupby("condicion")["es_final"].mean()
    brecha_vulnerable = round(float(por_condicion.get("No vulnerable", 0) - por_condicion.get("Vulnerable", 0)), 1)

    # --- Gráfica 3.1: % que llega a la Final por perfil (género + edad + condición) ---
    g1 = df_sub.groupby(["perfil", "condicion"])["es_final"].mean().round(1).reset_index()
    g1 = g1.sort_values("es_final")
    fig1 = px.bar(
        g1, x="es_final", y="perfil", color="condicion", orientation="h", text_auto=".1f",
        color_discrete_map=COLOR_VULNERABLE, labels=etiquetas,
        category_orders={"perfil": g1["perfil"].tolist(), "condicion": ORDEN_VULNERABLE},
    )
    grafica1 = a_html(fig1, alto=420)

    perfil_max = g1.iloc[-1]["perfil"] if len(g1) else "Sin datos"
    pct_perfil_max = round(float(g1.iloc[-1]["es_final"]), 1) if len(g1) else 0
    perfil_min = g1.iloc[0]["perfil"] if len(g1) else "Sin datos"
    pct_perfil_min = round(float(g1.iloc[0]["es_final"]), 1) if len(g1) else 0

    # --- Gráfica 3.2: % que llega a la Final por deporte, hombres y mujeres ---
    conteo = df_ambos.groupby(["deporte", "genero"])["es_final"].agg(["mean", "size"]).unstack()
    conteo = conteo[(conteo["size"] >= MIN_REGISTROS_DEPORTE_P3).all(axis=1)]
    orden_deportes = conteo["mean"].mean(axis=1).sort_values().index.tolist()
    g2 = (df_ambos[df_ambos["deporte"].isin(orden_deportes)]
          .groupby(["deporte", "genero"])["es_final"].mean().round(1).reset_index())
    fig2 = px.bar(
        g2, x="es_final", y="deporte", color="genero", barmode="group",
        orientation="h", text_auto=".0f",
        category_orders={"deporte": orden_deportes, "genero": ["Hombre", "Mujer"]},
        color_discrete_map=COLOR_GENERO, labels=etiquetas,
    )
    grafica2 = a_html(fig2, alto=max(400, 40 * len(orden_deportes)))

    # --- Gráfica 3.3: % que llega a la Final por subregión y año, según condición ---
    g3 = df_edad.groupby(["subregion_h", "año", "condicion"])["es_final"].mean().round(1).reset_index()
    g3["año"] = g3["año"].astype(str)
    fig3 = px.density_heatmap(
        g3, x="año", y="subregion_h", z="es_final", histfunc="avg",
        facet_col="condicion", text_auto=".0f", color_continuous_scale="Blues",
        category_orders={"condicion": ORDEN_VULNERABLE, "año": [str(a) for a in AÑOS_CON_FINAL]},
        labels=etiquetas,
    )
    fig3.update_layout(coloraxis_colorbar_title="% Final")
    grafica3 = a_html(fig3, alto=450)

    return dict(
        p3_pct_final=pct_final, p3_brecha_vulnerable=brecha_vulnerable,
        p3_perfil_max=perfil_max, p3_pct_perfil_max=pct_perfil_max,
        p3_perfil_min=perfil_min, p3_pct_perfil_min=pct_perfil_min,
        p3_excluidos=excluidos,
        p3_grafica1=grafica1, p3_grafica2=grafica2, p3_grafica3=grafica3,
    )


@app.route("/multivariada")
def multivariada():
    df = cargar_datos()
    df["subregion_h"] = df["subregion"].replace(HOMOLOGACION_SUBREGION)
    subregiones = sorted(df["subregion_h"].unique())
    deportes = sorted(df["deporte"].unique())

    # Lee un filtro de la URL; si el valor no es válido, usa el valor por defecto
    def leer_filtro(nombre, opciones, por_defecto):
        valor = request.args.get(nombre, por_defecto)
        return valor if valor in opciones else por_defecto

    # Pregunta 1: brecha de género por deporte y edad
    p1_subregion = leer_filtro("p1_subregion", subregiones, "Todas")
    p1_deporte = leer_filtro("p1_deporte", deportes, "Todos")
    pregunta1 = pregunta_genero_edad(df, p1_subregion, p1_deporte)

    # Pregunta 2: población vulnerable por etapa, territorio y año
    grupos_p2 = ["Cualquier grupo"] + GRUPOS_VULNERABLES
    p2_subregion = leer_filtro("p2_subregion", subregiones, "Todas")
    p2_grupo = leer_filtro("p2_grupo", grupos_p2, "Cualquier grupo")
    pregunta2 = pregunta_vulnerable(df, p2_subregion, p2_grupo)

    # Pregunta 3: perfil de quienes llegan a la Final
    edades_p3 = ["Todos"] + RANGOS_EDAD
    p3_subregion = leer_filtro("p3_subregion", subregiones, "Todas")
    p3_edad = leer_filtro("p3_edad", edades_p3, "Todos")
    pregunta3 = pregunta_final(df, p3_subregion, p3_edad)

    # Valores de todos los filtros, para que cada formulario conserve los de las demás preguntas
    filtros = {
        "p1_subregion": p1_subregion, "p1_deporte": p1_deporte,
        "p2_subregion": p2_subregion, "p2_grupo": p2_grupo,
        "p3_subregion": p3_subregion, "p3_edad": p3_edad,
    }

    return render_template(
        "multivariada.html",
        subregiones=subregiones, deportes=deportes, filtros=filtros,
        p1_subregion=p1_subregion, p1_deporte=p1_deporte, **pregunta1,
        grupos_p2=grupos_p2, p2_subregion=p2_subregion, p2_grupo=p2_grupo, **pregunta2,
        edades_p3=edades_p3, p3_subregion=p3_subregion, p3_edad=p3_edad, **pregunta3,
    )


if __name__ == "__main__":
    app.run(debug=True)
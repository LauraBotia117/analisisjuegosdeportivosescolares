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
    # CONCLUSIONES AUTOMÁTICAS
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
if __name__ == "__main__":
    app.run(debug=True)
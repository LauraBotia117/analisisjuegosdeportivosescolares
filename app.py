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


if __name__ == "__main__":
    app.run(debug=True)
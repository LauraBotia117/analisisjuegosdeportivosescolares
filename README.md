# Análisis de los Juegos Deportivos Institucionales Escolares

Aplicación web desarrollada con **Python, Flask y Bootstrap** que presenta un análisis exploratorio del histórico de participaciones en los Juegos Deportivos Institucionales Escolares (2021–2025), a partir de datos abiertos del Portal Nacional de Datos Abiertos de Colombia.

- **Aplicación publicada:** ()
- **Conjunto de datos original:** https://www.datos.gov.co/Deporte-y-Recreaci-n/Hist-rico-de-participaciones-en-Juegos-Deportivos-/bsta-rw3e/about_data


## Conjunto de datos

Consolida la información individualizada de los deportistas participantes en los Juegos Deportivos Institucionales Escolares. Cada fila es un **registro de participación**: un mismo deportista puede aparecer en varios registros (por deporte, etapa o año), por lo que la cantidad de registros no equivale a la cantidad de personas.

| Dato | Valor |
|---|---|
| Archivo | `data/Histórico_de_participaciones.csv` |
| Filas del archivo | 53.579 |
| Registros con año válido (los que usa la aplicación) | 53.510 |
| Deportistas distintos | 33.331 |
| Periodo | 2021 a 2025 |
| Municipios / Subregiones / Deportes | 127 / 11 / 24 |

### Variables

| Variable | Descripción |
|---|---|
| `id_deportista` | Código asignado a cada participante. Se usa solo para contar deportistas distintos. |
| `etapa` | Fase del evento: Subregional (clasificatoria) o Final (departamental). |
| `tipo_deporte` | Modalidad del deporte: Conjunto (equipos) o Individual. |
| `deporte` | Disciplina específica en la que participó el deportista. |
| `municipio` | Municipio por el que participa el deportista. |
| `subregion` | Subregión por la que participa el deportista. |
| `genero` | Género del participante (Hombre o Mujer). |
| `año` | Año de participación (2021 a 2025). |
| `rango_edad` | Rango de edad: 8 a 11, 12 a 15, 16 a 19, 20 a 23 o No registra. |
| `Población ...` (7 columnas) | Indican si el registro pertenece a una población diferencial: en situación de desplazamiento, campesina, con discapacidad, en proceso de reincorporación, migrante, víctima y LGTBI. Valores: Sí, No o No registra. |

Notas: 69 filas no tienen año registrado y la aplicación las excluye. En 2024 algunas subregiones se fusionaron (la dimensión multivariada lo tiene en cuenta). En 2024 no hay registros de la etapa Final.

## Dimensiones de análisis

| Página | Pregunta | Rama |
|---|---|---|
| `/poblacional` | ¿Cómo está compuesta y distribuida la población según sus principales características? | `feature/dimension-poblacional` |
| `/territorial` | ¿Cómo se distribuye la población entre los territorios disponibles? | `feature/dimension-territorial` |
| `/temporal` | ¿Cómo ha cambiado el comportamiento de la población durante el periodo disponible? | `feature/dimension-temporal` |
| `/multivariada` | ¿Qué diferencias o relaciones evidentes aparecen al analizar tres o más variables? | `feature/dimension-multivariada` |

## Integrantes

| N.° | Integrante | Usuario de GitHub | Dimensión | Responsabilidad |
|---|---|---|---|---|
| 1 | Laura Danniela Botia Ordoñez | LauraBotia117 | Poblacional | Administración del repositorio |
| 2 | Luis Felipe Murcia Rojas | LMurcia16 | Territorial | Configuración de Flask |
| 3 | Carlos Julio Pérez Rodríguez | somniumless | Temporal | Publicación de la aplicación |
| 4 | Angélica Rosa Olier Quiroga | AngelicaOlier | Relacional y multivariada | Informe técnico |

## Estructura del repositorio

```
├── app.py                 
 dimensiones
├── requirements.txt       
├── README.md
├── data/
│   └── Histórico_de_participaciones.csv
├── static/
│   └── css/style.css
└── templates/
    ├── base.html          
    ├── index.html
    ├── poblacional.html
    ├── territorial.html
    ├── temporal.html
    └── multivariada.html
```

## Cómo ejecutar el proyecto localmente

Requisitos: Python 3.10 o superior y Git.

```bash
git clone https://github.com/LauraBotia117/analisisjuegosdeportivosescolares.git
cd analisisjuegosdeportivosescolares
python -m venv venv
venv\Scripts\activate          
pip install -r requirements.txt
python app.py
```
Luego abrir `http://127.0.0.1:5000` en el navegador. 

## Flujo de trabajo en GitHub

1. Actualizar `main`: `git checkout main` y `git pull origin main`.
2. Cambiar a la rama asignada: `git checkout feature/dimension-...` y `git pull origin main`.
3. Desarrollar el tablero y hacer commits descriptivos (mínimo 3 por integrante).
4. Subir la rama: `git push -u origin feature/dimension-...`.
5. Crear un pull request hacia `main` y solicitar la revisión del integrante 1.
6. Aplicar las correcciones solicitadas.
7. Obtener la aprobación y fusionar.

### Reglas

- Nadie hace push directo a `main`.
- Cada integrante trabaja solo en su rama.
- Los mensajes de commit describen el cambio (por ejemplo: `Agrega filtros de subregión y género`).
- No se suben contraseñas, entornos virtuales (`venv/`) ni archivos temporales.

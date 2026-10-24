import requests
import pandas as pd


# Configuración compartida por las tres consultas
URL = "https://www.statshub.com/api/team/1938/performance"

TEAM_ID = 1938
TOURNAMENT_ID = 11621
SEASON = 2026

PARAMS_BASE = {
    "tournamentId": TOURNAMENT_ID,
    "limit": "season",
    "location": "all",
    "season": SEASON,
}


def obtener_datos_chivas(periodo):
    """Descargar y organizar los datos de ALL, 1ST o 2ND."""

    if periodo not in {"ALL", "1ST", "2ND"}:
        raise ValueError("El periodo debe ser ALL, 1ST o 2ND.")

    # Crear los parámetros de esta consulta sin modificar PARAMS_BASE
    params = {
        **PARAMS_BASE,
        "eventHalf": periodo,
    }

    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()

    contenido = response.json()
    df = pd.json_normalize(contenido["data"])

    if df.empty:
        raise ValueError(f"La API no devolvió partidos para {periodo}.")

    # Comprobar que todos los partidos incluyen a Chivas
    participa_chivas = (
        df["homeTeam.id"].eq(TEAM_ID)
        | df["awayTeam.id"].eq(TEAM_ID)
    )

    if not participa_chivas.all():
        raise ValueError("La respuesta incluye partidos sin Chivas.")

    # Convertir fecha a la zona horaria de CDMX
    df["fecha"] = (
        pd.to_datetime(
            pd.to_numeric(df["event.timeStartTimestamp"]),
            unit="s",
            utc=True,
        )
        .dt.tz_convert("America/Mexico_City")
    )

    # Organizar desde la perspectiva de Chivas
    es_local = df["homeTeam.id"].eq(TEAM_ID)

    df["rival_id"] = df["awayTeam.id"].where(
        es_local, df["homeTeam.id"]
    )

    df["rival"] = df["awayTeam.name"].where(
        es_local, df["homeTeam.name"]
    )

    df["localia"] = es_local.map({
        True: "Local",
        False: "Visitante",
    })

    # Estos valores proceden del marcador incluido en event.score
    df["goles_favor"] = df["event.score.home"].where(
        es_local, df["event.score.away"]
    )

    df["goles_contra"] = df["event.score.away"].where(
        es_local, df["event.score.home"]
    )

    # Identificar el periodo solicitado
    df["periodo"] = periodo

    # Detectar todas las métricas recibidas de ambos equipos
    columnas_metricas = [
        columna
        for columna in df.columns
        if columna.startswith(
            ("statistics.", "opponentStatistics.")
        )
    ]

    columnas_partido = [
        "event.id",
        "fecha",
        "league.id",
        "league.name",
        "rival_id",
        "rival",
        "localia",
        "periodo",
        "goles_favor",
        "goles_contra",
    ]

    resultado = df[
        columnas_partido + columnas_metricas
    ].copy()

    # Renombrar los datos generales
    resultado = resultado.rename(columns={
        "event.id": "partido_id",
        "league.id": "competicion_id",
        "league.name": "competicion",
    })

    # Renombrar las métricas conservando su nombre original
    nombres_metricas = {}

    for columna in columnas_metricas:
        bloque, metrica = columna.split(".", maxsplit=1)

        if bloque == "statistics":
            nombres_metricas[columna] = f"chivas_{metrica}"
        else:
            nombres_metricas[columna] = f"rival_{metrica}"

    resultado = resultado.rename(columns=nombres_metricas)

    resultado = (
        resultado
        .sort_values("fecha")
        .reset_index(drop=True)
    )

    if resultado["partido_id"].duplicated().any():
        raise ValueError(f"Hay partidos duplicados en {periodo}.")

    print(
        f"{periodo}: {resultado.shape[0]} partidos, "
        f"{resultado.shape[1]} columnas"
    )

    return resultado


# Tres consultas y tres DataFrames independientes
df_primer_tiempo = obtener_datos_chivas("1ST")
df_segundo_tiempo = obtener_datos_chivas("2ND")
df_full_time = obtener_datos_chivas("ALL")


# Comprobar que recuperamos los mismos partidos en los tres periodos
ids_1st = set(df_primer_tiempo["partido_id"])
ids_2nd = set(df_segundo_tiempo["partido_id"])
ids_all = set(df_full_time["partido_id"])

if not (ids_1st == ids_2nd == ids_all):
    raise ValueError(
        "Los periodos no contienen los mismos partidos. "
        "Revisa las respuestas antes de compararlos."
    )


# Tabla conjunta: una fila por partido y periodo
df_completo = pd.concat(
    [
        df_primer_tiempo,
        df_segundo_tiempo,
        df_full_time,
    ],
    ignore_index=True,
    sort=False,
)

# Ordenar: primer tiempo, segundo tiempo y partido completo
df_completo["periodo"] = pd.Categorical(
    df_completo["periodo"],
    categories=["1ST", "2ND", "ALL"],
    ordered=True,
)

df_completo = (
    df_completo
    .sort_values(["fecha", "partido_id", "periodo"])
    .reset_index(drop=True)
)


# Mostrar un resumen sin eliminar las demás columnas
columnas_vista = [
    "partido_id",
    "rival",
    "localia",
    "periodo",
    "goles_favor",
    "goles_contra",
    "chivas_expectedGoals",
    "rival_expectedGoals",
    "chivas_ballPossession",
]

print("\nDatos desde la perspectiva de Chivas:")
print(df_completo[columnas_vista].to_string(index=False))

columnas_dashboard = [
    # Identificación y contexto
    "partido_id",
    "fecha",
    "rival_id",
    "rival",
    "localia",
    "periodo",

    # Resultado
    "goles_favor",
    "goles_contra",

    # Peligro generado
    "chivas_expectedGoals",
    "chivas_totalShotsOnGoal",
    "chivas_shotsOnGoal",
    "chivas_bigChanceCreated",
    "chivas_totalShotsInsideBox",
    "chivas_finalThirdEntries",

    # Peligro concedido
    "rival_expectedGoals",
    "rival_totalShotsOnGoal",
    "rival_shotsOnGoal",
    "rival_bigChanceCreated",
    "rival_totalShotsInsideBox",
    "rival_finalThirdEntries",

    # Participación con balón y contexto
    "chivas_ballPossession",
    "chivas_passes",
    "chivas_pass_accuracy",
    "chivas_dispossessed",
    "chivas_ballRecovery",

    #Data asociada a errores defensivos chivas
    "chivas_errorsLeadToShot",
    "chivas_errorsLeadToGoal",
]

df_dashboard = df_completo[columnas_dashboard].copy()

df_dashboard["xg_diferencial(xG_chivas - xG_rival)"] = (
    df_dashboard["chivas_expectedGoals"]
    - df_dashboard["rival_expectedGoals"]
).round(2)

# Seleccionar exclusivamente las dos mitades
datos_mitades = df_dashboard.loc[
    df_dashboard["periodo"].isin(["1ST", "2ND"]),
    [
        "partido_id",
        "periodo",
        "xg_diferencial(xG_chivas - xG_rival)",
    ],
].copy()

# Comprobar que cada partido tenga como máximo una fila por mitad
if datos_mitades.duplicated(["partido_id", "periodo"]).any():
    raise ValueError("Hay registros duplicados por partido y mitad.")

# Convertir el balance a número; conservar los faltantes
columna_balance = "xg_diferencial(xG_chivas - xG_rival)"

datos_mitades[columna_balance] = pd.to_numeric(
    datos_mitades[columna_balance],
    errors="coerce",
)

# Pasar de una fila por partido y mitad a una fila por partido
balances = (
    datos_mitades.pivot(
        index="partido_id",
        columns="periodo",
        values=columna_balance,
    )
    .reindex(columns=["1ST", "2ND"])
    .rename(columns={
        "1ST": "balance_1t",
        "2ND": "balance_2t",
    })
)

balances.columns.name = None

# Recuperar los datos que identifican al partido
catalogo_partidos = (
    df_dashboard[
        ["partido_id", "fecha", "rival", "localia"]
    ]
    .drop_duplicates("partido_id")
)

df_comparacion = catalogo_partidos.merge(
    balances.reset_index(),
    on="partido_id",
    how="left",
    validate="one_to_one",
)

# Calcular cuánto cambió el balance entre mitades
df_comparacion["balance_cambio"] = (
    df_comparacion["balance_2t"]
    - df_comparacion["balance_1t"]
).round(2)

df_comparacion = (
    df_comparacion
    .sort_values("fecha")
    .reset_index(drop=True)
)
# Recuperar los marcadores al descanso y al final
marcadores = df_dashboard.loc[
    df_dashboard["periodo"].isin(["1ST", "ALL"]),
    ["partido_id", "periodo", "goles_favor", "goles_contra"],
].copy()

if marcadores.duplicated(["partido_id", "periodo"]).any():
    raise ValueError("Hay marcadores duplicados por partido y periodo.")

for columna in ["goles_favor", "goles_contra"]:
    marcadores[columna] = pd.to_numeric(
        marcadores[columna],
        errors="coerce",
    )


def preparar_marcador(periodo, sufijo):
    return (
        marcadores.loc[
            marcadores["periodo"].eq(periodo),
            ["partido_id", "goles_favor", "goles_contra"],
        ]
        .rename(columns={
            "goles_favor": f"goles_favor_{sufijo}",
            "goles_contra": f"goles_contra_{sufijo}",
        })
    )


# Añadir los marcadores a la tabla de comparación
df_comparacion = (
    df_comparacion
    .merge(
        preparar_marcador("1ST", "descanso"),
        on="partido_id",
        how="left",
        validate="one_to_one",
    )
    .merge(
        preparar_marcador("ALL", "final"),
        on="partido_id",
        how="left",
        validate="one_to_one",
    )
)

# Clasificar la situación al descanso
diferencia_descanso = (
    df_comparacion["goles_favor_descanso"]
    - df_comparacion["goles_contra_descanso"]
)

df_comparacion["situacion_descanso"] = "No disponible"

for condicion, etiqueta in [
    (diferencia_descanso.gt(0), "Ganando"),
    (diferencia_descanso.eq(0), "Empatando"),
    (diferencia_descanso.lt(0), "Perdiendo"),
]:
    df_comparacion.loc[condicion, "situacion_descanso"] = etiqueta

# Clasificar el resultado final
diferencia_final = (
    df_comparacion["goles_favor_final"]
    - df_comparacion["goles_contra_final"]
)

df_comparacion["resultado_final"] = "No disponible"

for condicion, etiqueta in [
    (diferencia_final.gt(0), "Victoria"),
    (diferencia_final.eq(0), "Empate"),
    (diferencia_final.lt(0), "Derrota"),
]:
    df_comparacion.loc[condicion, "resultado_final"] = etiqueta

# Evaluar la conservación de la victoria solo si iba ganando
iba_ganando = df_comparacion["situacion_descanso"].eq("Ganando")

df_comparacion["conservo_victoria"] = "No aplica"

df_comparacion.loc[
    df_comparacion["situacion_descanso"].eq("No disponible")
    | (iba_ganando & diferencia_final.isna()),
    "conservo_victoria",
] = "No disponible"

df_comparacion.loc[
    iba_ganando & diferencia_final.gt(0),
    "conservo_victoria",
] = "Sí"

df_comparacion.loc[
    iba_ganando & diferencia_final.le(0),
    "conservo_victoria",
] = "No"

# Cambios de generación y concesión entre mitades
xg_por_mitad = df_dashboard.loc[
    df_dashboard["periodo"].isin(["1ST", "2ND"]),
    [
        "partido_id",
        "periodo",
        "chivas_expectedGoals",
        "rival_expectedGoals",
    ],
].copy()

for columna in ["chivas_expectedGoals", "rival_expectedGoals"]:
    xg_por_mitad[columna] = pd.to_numeric(
        xg_por_mitad[columna],
        errors="coerce",
    )

if xg_por_mitad.duplicated(["partido_id", "periodo"]).any():
    raise ValueError("Hay registros duplicados de xG por partido y mitad.")

xg_ancho = xg_por_mitad.pivot(
    index="partido_id",
    columns="periodo",
    values=["chivas_expectedGoals", "rival_expectedGoals"],
)

# Conservar las columnas incluso si falta algún periodo
columnas_esperadas = pd.MultiIndex.from_product([
    ["chivas_expectedGoals", "rival_expectedGoals"],
    ["1ST", "2ND"],
])

xg_ancho = xg_ancho.reindex(columns=columnas_esperadas)

cambios_xg = pd.DataFrame(index=xg_ancho.index)

cambios_xg["delta_xg"] = (
    xg_ancho[("chivas_expectedGoals", "2ND")]
    - xg_ancho[("chivas_expectedGoals", "1ST")]
).round(2)

cambios_xg["delta_xga"] = (
    xg_ancho[("rival_expectedGoals", "2ND")]
    - xg_ancho[("rival_expectedGoals", "1ST")]
).round(2)

df_comparacion = df_comparacion.merge(
    cambios_xg.reset_index(),
    on="partido_id",
    how="left",
    validate="one_to_one",
)


from pathlib import Path

carpeta = Path(__file__).resolve().parent
carpeta.mkdir(parents=True, exist_ok=True)

dataframes = {
    "chivas_primer_tiempo": df_primer_tiempo,
    "chivas_segundo_tiempo": df_segundo_tiempo,
    "chivas_full_time": df_full_time,
    "chivas_completo": df_completo,
    "chivas_data_por_tiempo": df_dashboard,
    "chivas_balance_xG" : df_comparacion,
}

for nombre, tabla in dataframes.items():
    tabla.to_csv(
        carpeta / f"{nombre}.csv",
        index=False,
        float_format="%.2f",
        encoding="utf-8-sig",
    )
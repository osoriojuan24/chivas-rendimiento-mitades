from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Chivas: rendimiento entre mitades",
    page_icon="🐐",
    layout="wide",
)

# Encabezado del dashboard
st.title("Dashboard de Rendimiento por mitades de partido")
st.subheader("Club Deportivo Guadalajara, Chivas")
st.subheader("Liga MX, Apertura 2026")
st.divider()

# Leer el CSV ubicado en la misma carpeta que este script
ruta = Path(__file__).resolve().parent / "chivas_data_por_tiempo.csv"

df = pd.read_csv(ruta)

df["fecha"] = (
    pd.to_datetime(df["fecha"], utc=True)
    .dt.tz_convert("America/Mexico_City")
)

# Leer df comparación: una fila por partido
ruta_balance = Path(__file__).resolve().parent / "chivas_balance_xG.csv"

df_comparacion = pd.read_csv(ruta_balance)

df_comparacion["fecha"] = (
    pd.to_datetime(df_comparacion["fecha"], utc=True)
    .dt.tz_convert("America/Mexico_City")
)

columnas_numericas_balance = [
    "balance_1t",
    "balance_2t",
    "balance_cambio",
    "delta_xg",
    "delta_xga",
    "goles_favor_descanso",
    "goles_contra_descanso",
    "goles_favor_final",
    "goles_contra_final",
]

for columna in columnas_numericas_balance:
    df_comparacion[columna] = pd.to_numeric(
        df_comparacion[columna],
        errors="coerce",
    )

# Trabajar únicamente con las dos mitades
mitades = df.loc[
    df["periodo"].isin(["1ST", "2ND"])
].copy()

tab_resumen, tab_detalle = st.tabs([
    "Resumen del torneo",
    "Detalle del partido",
])


with tab_resumen:
    st.subheader("Filtros del resumen")
    st.caption(
        "La localía y la situación al descanso se aplican "
        "a todos los indicadores y gráficas de esta pestaña."
    )

    metricas_resumen = {
        "Goles": (
            "goles_favor",
            "goles_contra",
        ),
        "Goles esperados (xG)": (
            "chivas_expectedGoals",
            "rival_expectedGoals",
        ),
        "Tiros totales": (
            "chivas_totalShotsOnGoal",
            "rival_totalShotsOnGoal",
        ),
        "Tiros a puerta": (
            "chivas_shotsOnGoal",
            "rival_shotsOnGoal",
        ),
        "Ocasiones claras creadas": (
            "chivas_bigChanceCreated",
            "rival_bigChanceCreated",
        ),
        "Tiros dentro del área": (
            "chivas_totalShotsInsideBox",
            "rival_totalShotsInsideBox",
        ),
        "Entradas al último tercio": (
            "chivas_finalThirdEntries",
            "rival_finalThirdEntries",
        ),
    }

     # Obtener la situación al descanso a partir del primer tiempo
    descanso = mitades.loc[
        mitades["periodo"].eq("1ST"),
        ["partido_id", "goles_favor", "goles_contra"],
    ].copy()

    for columna in ["goles_favor", "goles_contra"]:
        descanso[columna] = pd.to_numeric(
            descanso[columna],
            errors="coerce",
        )

    # Si hay más de un registro de primer tiempo, no asumir un marcador
    duplicados_descanso = descanso["partido_id"].duplicated(
        keep=False
    )

    descanso = descanso.loc[~duplicados_descanso].copy()

    descanso["situacion_descanso"] = "Sin dato"

    marcador_valido = descanso[
        ["goles_favor", "goles_contra"]
    ].notna().all(axis=1)

    diferencia = descanso["goles_favor"] - descanso["goles_contra"]

    descanso.loc[
        marcador_valido & diferencia.gt(0),
        "situacion_descanso",
    ] = "Ganando"

    descanso.loc[
        marcador_valido & diferencia.eq(0),
        "situacion_descanso",
    ] = "Empatando"

    descanso.loc[
        marcador_valido & diferencia.lt(0),
        "situacion_descanso",
    ] = "Perdiendo"

    # Asignar la misma situación al descanso a las dos mitades
    situacion_por_partido = descanso.set_index(
        "partido_id"
    )["situacion_descanso"]

    historico = mitades.copy()

    historico["situacion_descanso"] = (
        historico["partido_id"]
        .map(situacion_por_partido)
        .fillna("Sin dato")
    )

    # Dos filtros colocados lado a lado
    col_localia, col_descanso = st.columns(2)

    with col_localia:
        filtro_localia = st.selectbox(
            "Localía de Chivas",
            options=["Todas", "Local", "Visitante"],
            key="filtro_localia_resumen",
        )

    opciones_descanso = [
        "Todas",
        "Ganando",
        "Empatando",
        "Perdiendo",
    ]

    if historico["situacion_descanso"].eq("Sin dato").any():
        opciones_descanso.append("Sin dato")

    with col_descanso:
        filtro_descanso = st.selectbox(
            "Situación de Chivas al descanso",
            options=opciones_descanso,
            key="filtro_descanso_resumen",
        )

    # Identificar los partidos que cumplen ambos filtros
    cumple_filtros = pd.Series(True, index=historico.index)

    if filtro_localia != "Todas":
        cumple_filtros &= historico["localia"].eq(filtro_localia)

    if filtro_descanso != "Todas":
        cumple_filtros &= historico["situacion_descanso"].eq(
            filtro_descanso
        )

    ids_filtrados = historico.loc[
        cumple_filtros, "partido_id"
    ].unique()

    # Conservar ambas mitades de los partidos seleccionados
    historico = historico.loc[
        historico["partido_id"].isin(ids_filtrados)
    ].copy()

    st.divider()
    st.subheader("¿Cómo cambia el balance de ocasiones?")

    st.caption(
        "Balance = xG de Chivas − xGA (xG del rival).  \n"
        "Cambio del Balance = Balance del segundo tiempo − Balance del primer tiempo.  \n"
    )

    # Aplicar exactamente los mismos partidos que en las otras gráficas
    comparacion_filtrada = (
        df_comparacion.loc[
            df_comparacion["partido_id"].isin(ids_filtrados)
        ]
        .copy()
        .sort_values(["fecha", "partido_id"])
    )

    ids_sin_balance = set(ids_filtrados) - set(
        comparacion_filtrada["partido_id"]
    )

    if ids_sin_balance:
        st.warning(
            f"{len(ids_sin_balance)} partido(s) seleccionado(s) "
            "no aparecen en chivas_balance_xG.csv. "
            "Vuelve a ejecutar la extracción para actualizar ambos CSV."
        )

    if comparacion_filtrada.empty:
        st.info("No hay partidos disponibles para esta comparación.")

    elif comparacion_filtrada["partido_id"].duplicated().any():
        st.error(
            "Hay partidos duplicados en chivas_balance_xG.csv. "
            "Debe existir una sola fila por partido."
        )

    else:
        # Comparar únicamente partidos con datos de ambas mitades
        comparables = comparacion_filtrada.dropna(
            subset=["balance_1t", "balance_2t", "balance_cambio"]
        ).copy()

        faltantes = len(comparacion_filtrada) - len(comparables)

        if faltantes:
            st.warning(
                f"{faltantes} partido(s) no tienen el balance completo. "
                "Se excluyen de los indicadores y de la gráfica de cambio."
            )

        if comparables.empty:
            st.info("No hay balances completos para comparar.")

        else:
            # Tolerancia para evitar clasificar pequeños residuos
            # de cálculo decimal como una mejora o un deterioro.
            tolerancia = 1e-9

            cambios = comparables["balance_cambio"]
            empeoran = cambios.lt(-tolerancia).sum()
            mejoran = cambios.gt(tolerancia).sum()
            iguales = cambios.abs().le(tolerancia).sum()
            total = len(comparables)

            col_n, col_caida, col_promedio = st.columns(3)

            with col_n:
                st.metric("Partidos comparables", total)

            with col_caida:
                st.metric(
                    "Balance empeora",
                    f"{empeoran} de {total}",
                )

            with col_promedio:
                st.metric(
                    "Cambio promedio del balance",
                    f"{cambios.mean():+.2f} xG",
                )

            st.caption(
                f"Mejora en {mejoran}, empeora en {empeoran} "
                f"y se mantiene en {iguales} partido(s). "
                #f"Cambio mediano: {cambios.median():+.2f} xG."
            )

        # Conservación de victorias:
        # no depende de que el partido tenga datos completos de xG.
        if filtro_descanso == "Ganando":
            ventajas = comparacion_filtrada.loc[
                comparacion_filtrada["situacion_descanso"].eq("Ganando")
            ]

            ventajas_evaluables = ventajas.loc[
                ventajas["conservo_victoria"].isin(["Sí", "No"])
            ]

            if ventajas_evaluables.empty:
                st.info(
                    "No hay resultados finales disponibles "
                    "para evaluar la conservación de victorias."
                )
            else:
                conservadas = (
                    ventajas_evaluables["conservo_victoria"]
                    .eq("Sí")
                    .sum()
                )

                st.metric(
                    "Victorias conservadas",
                    f"{conservadas} de {len(ventajas_evaluables)}",
                )

                st.caption(
                    "Partidos que Chivas iba ganando al descanso "
                    "y terminó ganando. No implica que mantuviera "
                    "la ventaja durante todos los minutos."
                )

            sin_resultado = len(ventajas) - len(ventajas_evaluables)

            if sin_resultado:
                st.caption(
                    f"{sin_resultado} partido(s) con ventaja al descanso "
                    "sin resultado evaluable."
                )

        # Preparar los marcadores para el hover y la tabla
        def formatear_marcador_balance(fila, sufijo):
            favor = fila[f"goles_favor_{sufijo}"]
            contra = fila[f"goles_contra_{sufijo}"]

            if pd.isna(favor) or pd.isna(contra):
                return "No disponible"

            return f"{favor:.0f} – {contra:.0f}"

        comparacion_filtrada["Al descanso"] = (
            comparacion_filtrada.apply(
                formatear_marcador_balance,
                axis=1,
                sufijo="descanso",
            )
        )

        comparacion_filtrada["Final"] = (
            comparacion_filtrada.apply(
                formatear_marcador_balance,
                axis=1,
                sufijo="final",
            )
        )

        # Mantener también el espacio de partidos sin balance
        orden_balance = (
            comparacion_filtrada["partido_id"].astype(str).tolist()
        )

        etiquetas_balance = [
            f"{fila['rival']}<br>{fila['fecha']:%d/%m/%Y}"
            for _, fila in comparacion_filtrada.iterrows()
        ]

        datos_balance = comparacion_filtrada.dropna(
            subset=["balance_1t", "balance_2t", "balance_cambio"]
        ).copy()

        if not datos_balance.empty:
            datos_balance["partido_eje"] = (
                datos_balance["partido_id"].astype(str)
            )

            datos_balance["etiqueta_cambio"] = (
            datos_balance["balance_cambio"]
            .map(lambda valor: f"{valor:+.2f}") 
            )

            fig_balance = px.bar(
                datos_balance,
                x="partido_eje",
                y="balance_cambio",
                text="etiqueta_cambio",
                custom_data=[
                    "rival",
                    "balance_1t",
                    "balance_2t",
                    "Al descanso",
                    "Final",
                ],
                category_orders={
                    "partido_eje": orden_balance,
                },
                labels={
                    "partido_eje": "",
                    "balance_cambio": "Cambio del balance de xG (2T − 1T)",
                },
                title="Cambio del balance de xG por partido",
            )

            colores_balance = [
                "#22C55E" if valor > 1e-9 else
                "#FACC15" if valor < -1e-9 else
                "#94A3B8"
                for valor in datos_balance["balance_cambio"]
            ]

            fig_balance.update_traces(
                marker_color=colores_balance,
                texttemplate="%{text}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "Rival: %{customdata[0]}<br>"
                    "Balance 1T: %{customdata[1]:+.2f}<br>"
                    "Balance 2T: %{customdata[2]:+.2f}<br>"
                    "Cambio: %{y:+.2f} xG<br>"
                    "Al descanso: %{customdata[3]}<br>"
                    "Final: %{customdata[4]}"
                    "<extra>Chivas</extra>"
                ),
            )

            # Línea que separa mejora y deterioro
            fig_balance.add_hline(
                y=0,
                line_color="#CBD5E1",
                line_width=2,
            )

            limite_balance = max(
                0.1,
                datos_balance["balance_cambio"].abs().max() * 1.3,
            )

            fig_balance.update_yaxes(
                range=[-limite_balance, limite_balance],
                tickformat=".2f",
            )

            fig_balance.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=orden_balance,
                tickmode="array",
                tickvals=orden_balance,
                ticktext=etiquetas_balance,
                range=[-0.5, len(orden_balance) - 0.5],
                tickangle=-30,
            )

            fig_balance.update_layout(
                height=460,
                showlegend=False,
                bargap=0.35,
                margin={"l": 70, "r": 30, "t": 70, "b": 110},
            )

            st.plotly_chart(
                fig_balance,
                use_container_width=True,
                key="cambio_balance_xg",
            )

            st.caption(
                "Verde: mejora el balance respecto al primer tiempo. "
                "Amarillo: empeora el balance respecto al primer tiempo. "
                "Un cambio de cero indica que el balance se mantiene entre ambos tiempos.  \n"
                "Mejorar no significa necesariamente terminar dominando ni ganar el partido."
            )

            st.subheader("¿Cómo se compone el cambio del balance?")
            st.caption(
                "Cada punto representa un partido. Se aplican los filtros de localía y situación al descanso.  \n" 
                "Sobre el eje horizontal: Valores positivos indican que Chivas generó mas xG en el segundo tiempo,"
                "valores negativos indican que Chivas generó menos xG en el segundo tiempo.  \n"
                "Sobre el eje vertical: Valores positivos indican que el rival generó mas xG en el segundo tiempo,"
                "valores negativos indican que el rival generó menos xG en el segundo tiempo"
            )

        datos_scatter = comparacion_filtrada.dropna(
            subset=["delta_xg", "delta_xga"]
        ).copy()

        faltantes_scatter = (
            len(comparacion_filtrada) - len(datos_scatter)
        )

        if faltantes_scatter:
            st.warning(
                f"{faltantes_scatter} partido(s) no tienen datos completos "
                "para descomponer el cambio del balance."
            )

        if datos_scatter.empty:
            st.info("No hay datos disponibles para esta gráfica.")

        else:
            datos_scatter["fecha_texto"] = (
                datos_scatter["fecha"].dt.strftime("%d/%m/%Y")
            )

            # Calcular el balance desde las coordenadas de esta gráfica
            datos_scatter["cambio_desde_componentes"] = (
                datos_scatter["delta_xg"]
                - datos_scatter["delta_xga"]
            ).round(2)

            fig_componentes = px.scatter(
                datos_scatter,
                x="delta_xg",
                y="delta_xga",
                color="situacion_descanso",
                text="rival",
                category_orders={
                    "situacion_descanso": [
                        "Ganando",
                        "Empatando",
                        "Perdiendo",
                        "No disponible",
                    ],
                },
                color_discrete_map={
                    "Ganando": "#60A5FA",
                    "Empatando": "#CBD5E1",
                    "Perdiendo": "#F59E0B",
                    "No disponible": "#A78BFA",
                },
                custom_data=[
                    "rival",
                    "fecha_texto",
                    "situacion_descanso",
                    "cambio_desde_componentes",
                    "Al descanso",
                    "Final",
                ],
                labels={
                    "delta_xg": "Cambio del xG de Chivas (2T − 1T)",
                    "delta_xga": "Cambio del xGA (2T − 1T)",
                    "situacion_descanso": "Al descanso",
                },
                title="Cambio de generación y concesión de ocasiones",
            )

            fig_componentes.update_traces(
                marker={
                    "size": 13,
                    "line": {
                        "width": 1,
                        "color": "#FFFFFF",
                    },
                },
                textposition="top center",
                hovertemplate=(
                    "Rival: %{customdata[0]}<br>"
                    "Fecha: %{customdata[1]}<br>"
                    "Situación al descanso: %{customdata[2]}<br>"
                    "Cambio del xG: %{x:+.2f}<br>"
                    "Cambio del xGA: %{y:+.2f}<br>"
                    "Cambio del balance: %{customdata[3]:+.2f} xG<br>"
                    "Al descanso: %{customdata[4]}<br>"
                    "Final: %{customdata[5]}"
                    "<extra></extra>"
                ),
            )

            # Mismo rango y misma escala para ambos ejes
            maximo_componentes = (
                datos_scatter[["delta_xg", "delta_xga"]]
                .abs()
                .max()
                .max()
            )

            limite_componentes = max(
                0.25,
                maximo_componentes * 1.3,
            )

            # Referencias: ningún cambio en generación o concesión
            fig_componentes.add_hline(
                y=0,
                line_color="#64748B",
                line_width=1,
            )

            fig_componentes.add_vline(
                x=0,
                line_color="#64748B",
                line_width=1,
            )

            # Sobre esta diagonal, delta_xg = delta_xga:
            # el cambio del balance es cero.
            fig_componentes.add_shape(
                type="line",
                x0=-limite_componentes,
                y0=-limite_componentes,
                x1=limite_componentes,
                y1=limite_componentes,
                line={
                    "color": "#CBD5E1",
                    "width": 2,
                    "dash": "dash",
                },
                layer="below",
            )

            fig_componentes.update_xaxes(
                range=[-limite_componentes, limite_componentes],
                tickformat="+.2f",
                zeroline=False,
                constrain="domain",
            )

            fig_componentes.update_yaxes(
                range=[-limite_componentes, limite_componentes],
                tickformat="+.2f",
                zeroline=False,
                scaleanchor="x",
                scaleratio=1,
                constrain="domain",
            )

            fig_componentes.update_layout(
                height=620,
                legend_title_text="Situación al descanso",
                margin={"l": 70, "r": 40, "t": 80, "b": 70},
            )

            st.plotly_chart(
                fig_componentes,
                use_container_width=True,
                key="componentes_cambio_balance",
            )

            st.caption(
                "Esta gráfica descompone el cambio del balance; "
                "no identifica por sí sola sus causas tácticas."
            )
            st.caption(
                "Diagonal discontinua: sin cambio del balance.  \n"
                "Puntos por encima de la diagonal: significa que el balance de Chivas empeoró (ya sea porque produjo "
                "menos, si el punto en el eje horizontal es negativo o porque su rival produjo más; si el "
                "si el punto en el eje vertidcal es positivo).  \n"
                "Puntos por debajo de la diagonal: significa que el balance de Chivas mejoró (ya sea porque produjo "
                "más; si el punto en el eje horizontal es positivo o porque su rival produjo menos; si el "
                "si el punto en el eje vertidcal es negativo). \n"
            )

            st.caption(
                "Marcadores en la siguiente tabla se muestran de la forma: Chivas – rival."
            )
        # Tabla opcional con el detalle de los partidos seleccionados
        with st.expander("Ver balances y marcadores por partido"):
            tabla_balance = comparacion_filtrada[
                [
                    "fecha",
                    "rival",
                    "localia",
                    "Al descanso",
                    "Final",
                    "balance_1t",
                    "balance_2t",
                    "balance_cambio",
                ]
            ].copy()

            tabla_balance["fecha"] = (
                tabla_balance["fecha"].dt.strftime("%d/%m/%Y")
            )

            tabla_balance = tabla_balance.rename(columns={
                "fecha": "Fecha",
                "rival": "Rival",
                "localia": "Localía",
                "balance_1t": "Balance 1T (xG Chivas - xG Rival)",
                "balance_2t": "Balance 2T (xG Chivas -xG Rival)",
                "balance_cambio": "Cambio (Balance 2T - Balance 1T)",
            })

            st.dataframe(
                tabla_balance.style.format(
                    {
                        "Balance 1T (xG Chivas - xG Rival)": "{:+.2f}",
                        "Balance 2T (xG Chivas -xG Rival)": "{:+.2f}",
                        "Cambio (Balance 2T - Balance 1T)": "{:+.2f}",
                    },
                    na_rep="No disponible",
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.caption("Fuente: StatsHub · Cálculos propios del balance de xG.")


    st.divider()
    st.subheader("Goles anotados frente al xG")
    st.caption(
        "Cada punto representa un partido.  \n"
        "Se aplican los filtros de localía y situación al descanso.  \n"
        "Ambas gráficas incluyen los mismos partidos y usan la misma escala. "
        "Los partidos con coordenadas idénticas pueden superponerse."
    )

    datos_definicion = historico[
        [
            "partido_id",
            "fecha",
            "rival",
            "localia",
            "periodo",
            "goles_favor",
            "chivas_expectedGoals",
        ]
    ].copy()

    for columna in ["goles_favor", "chivas_expectedGoals"]:
        datos_definicion[columna] = pd.to_numeric(
            datos_definicion[columna],
            errors="coerce",
        )

    duplicados_definicion = datos_definicion.duplicated(
        ["partido_id", "periodo"]
    ).any()

    if datos_definicion.empty:
        st.info("No hay partidos que cumplan los filtros seleccionados.")

    elif duplicados_definicion:
        st.error(
            "Hay registros duplicados por partido y mitad. "
            "Revisa el CSV antes de mostrar esta comparación."
        )

    else:
        # Una fila válida necesita goles y xG no negativos.
        fila_valida = (
            datos_definicion[
                ["goles_favor", "chivas_expectedGoals"]
            ].notna().all(axis=1)
            & datos_definicion["goles_favor"].ge(0)
            & datos_definicion["chivas_expectedGoals"].ge(0)
            & datos_definicion["goles_favor"].mod(1).eq(0)
        )

        filas_validas = datos_definicion.loc[fila_valida].copy()

        # Conservar solo partidos con datos válidos en ambas mitades.
        mitades_validas = (
            filas_validas.groupby("partido_id")["periodo"].nunique()
        )

        ids_completos = mitades_validas.loc[
            mitades_validas.eq(2)
        ].index

        total_seleccionados = datos_definicion["partido_id"].nunique()
        total_completos = len(ids_completos)
        excluidos = total_seleccionados - total_completos

        datos_definicion = filas_validas.loc[
            filas_validas["partido_id"].isin(ids_completos)
        ].copy()

        if excluidos:
            st.warning(
                f"Se excluyen {excluidos} partido(s) por datos ausentes "
                "o inválidos en alguna mitad. Los indicadores y las dos "
                "gráficas utilizan únicamente los partidos completos."
            )

        if datos_definicion.empty:
            st.info("No hay partidos con datos completos para comparar.")

        else:
            datos_definicion["goles_menos_xg"] = (
                datos_definicion["goles_favor"]
                - datos_definicion["chivas_expectedGoals"]
            )

            datos_definicion["fecha_texto"] = (
                datos_definicion["fecha"].dt.strftime("%d/%m/%Y")
            )

            st.caption(
                f"Partidos incluidos en cada gráfica: {total_completos}"
                " · Indicadores acumulados para esos partidos."
            )

            # Escala común para los dos gráficos y para ambos ejes.
            maximo_definicion = (
                datos_definicion[
                    ["goles_favor", "chivas_expectedGoals"]
                ].max().max()
            )

            limite_definicion = max(1, maximo_definicion * 1.2)

            panel_1t, panel_2t = st.columns(2)

            for panel, periodo, titulo, color in [
                (panel_1t, "1ST", "Primer tiempo", "#D71920"),
                (panel_2t, "2ND", "Segundo tiempo", "#FF8589"),
            ]:
                with panel:
                    st.subheader(titulo)

                    datos_mitad = datos_definicion.loc[
                        datos_definicion["periodo"].eq(periodo)
                    ].copy()

                    goles_total = datos_mitad["goles_favor"].sum()
                    xg_total = datos_mitad["chivas_expectedGoals"].sum()
                    diferencia_total = goles_total - xg_total

                    tarjeta_goles, tarjeta_xg, tarjeta_diferencia = (
                        st.columns(3)
                    )

                    tarjeta_goles.metric(
                        "Goles",
                        f"{goles_total:.0f}",
                    )

                    tarjeta_xg.metric(
                        "xG",
                        f"{xg_total:.2f}",
                    )

                    tarjeta_diferencia.metric(
                        "Goles − xG",
                        f"{diferencia_total:+.2f}",
                    )

                    datos_mitad["diferencia_texto"] = (
                        datos_mitad["goles_menos_xg"]
                        .map(lambda valor: f"{valor:+.2f}")
                    )

                    fig_definicion = px.scatter(
                        datos_mitad,
                        x="chivas_expectedGoals",
                        y="goles_favor",
                        custom_data=[
                            "rival",
                            "fecha_texto",
                            "localia",
                            "diferencia_texto",
                        ],
                        labels={
                            "chivas_expectedGoals": "xG de Chivas",
                            "goles_favor": "Goles de Chivas",
                        },
                    )

                    fig_definicion.update_traces(
                        marker={
                            "color": color,
                            "size": 13,
                            "opacity": 0.8,
                            "line": {
                                "color": "#FFFFFF",
                                "width": 1,
                            },
                        },
                        hovertemplate=(
                            "Rival: %{customdata[0]}<br>"
                            "Fecha: %{customdata[1]}<br>"
                            "Chivas: %{customdata[2]}<br>"
                            "xG: %{x:.2f}<br>"
                            "Goles: %{y:.0f}<br>"
                            "Goles − xG: %{customdata[3]}"
                            "<extra>" + titulo + "</extra>"
                        ),
                    )

                    # Diagonal: goles anotados iguales al xG.
                    fig_definicion.add_shape(
                        type="line",
                        x0=0,
                        y0=0,
                        x1=limite_definicion,
                        y1=limite_definicion,
                        line={
                            "color": "#CBD5E1",
                            "width": 2,
                            "dash": "dash",
                        },
                        layer="below",
                    )

                    fig_definicion.update_xaxes(
                        range=[0, limite_definicion],
                        tickformat=".2f",
                        constrain="domain",
                    )

                    fig_definicion.update_yaxes(
                        range=[0, limite_definicion],
                        dtick=1,
                        scaleanchor="x",
                        scaleratio=1,
                        constrain="domain",
                    )

                    fig_definicion.update_layout(
                        height=440,
                        showlegend=False,
                        margin={"l": 50, "r": 20, "t": 20, "b": 60},
                    )

                    st.plotly_chart(
                        fig_definicion,
                        use_container_width=True,
                        key=f"goles_vs_xg_{periodo}",
                    )

            st.caption(
                "Diagonal discontinua: mismo número de goles anotados que valor en xG.  \n"
                "Puntos por encima de la diagonal: mayor número de goles anotados que valor en xG.  \n"
                "Puntos por debajo de la diagonal: menor número de goles anotados que valor en xG.  "
            )
            
            st.caption("Fuente: StatsHub · Datos de Chivas por mitad.")        

    st.divider()
    st.subheader("Peligro generado por mitad")
    st.caption(
        "Cada grupo representa un partido: primer tiempo a la izquierda "
        "y segundo tiempo a la derecha.  \n"
        "Chivas se muestra en rojo y sus rivales en gris; "
        "el tono claro corresponde al segundo tiempo.   \n"
        "Ambas gráficas usan la misma escala y los filtros de localía y situación al descanso"
    )

    metrica_resumen = st.selectbox(
        "Selecciona la métrica de peligro",
        options=list(metricas_resumen),
        key="metrica_resumen",
    )

    columna_chivas_resumen, columna_rival_resumen = (
        metricas_resumen[metrica_resumen]
    )

    # Mantener los partidos en orden cronológico
    catalogo = (
        historico[["partido_id", "fecha", "rival", "localia"]]
        .drop_duplicates("partido_id")
        .sort_values(["fecha", "partido_id"])
    )

    # Usar el ID como categoría evita mezclar encuentros repetidos
    orden_partidos = catalogo["partido_id"].astype(str).tolist()

    etiquetas_partidos = [
        f"{fila['rival']}<br>{fila['fecha']:%d/%m/%Y}"
        for _, fila in catalogo.iterrows()
    ]

    historico["partido_eje"] = historico["partido_id"].astype(str)

    historico["mitad"] = historico["periodo"].map({
        "1ST": "Primer tiempo",
        "2ND": "Segundo tiempo",
    })

    columnas_seleccionadas = [
        columna_chivas_resumen,
        columna_rival_resumen,
    ]

    for columna in columnas_seleccionadas:
        historico[columna] = pd.to_numeric(
            historico[columna],
            errors="coerce",
        )

    st.caption(f"Partidos incluidos: {len(catalogo)}")

    hay_duplicados = historico.duplicated(
        ["partido_id", "periodo"]
    ).any()

    if historico.empty:
        st.info("No hay partidos disponibles para mostrar.")

    elif hay_duplicados:
        st.error(
            "Hay registros duplicados por partido y mitad. "
            "Revisa el CSV antes de graficar."
        )

    else:
        # Avisar sobre mitades o valores ausentes sin convertirlos a cero
        periodos_por_partido = historico.groupby(
            "partido_id"
        )["periodo"].nunique()

        if (
            periodos_por_partido.lt(2).any()
            or historico[columnas_seleccionadas].isna().any().any()
        ):
            st.warning(
                "Hay datos faltantes. Las barras correspondientes "
                "no se mostrarán; no representan valores de cero."
            )

        # Calcular un único límite vertical para ambas gráficas
        valores_disponibles = (
            historico[columnas_seleccionadas]
            .stack()
            .dropna()
        )

        if valores_disponibles.empty:
            st.info("No hay valores disponibles para esta métrica.")

        else:
            maximo_compartido = valores_disponibles.max()
            limite_y = max(1, maximo_compartido * 1.25)

            es_xg_resumen = (
                metrica_resumen == "Goles esperados (xG)"
            )
            formato_resumen = ".2f" if es_xg_resumen else ".0f"

            colores_chivas = {
                "Primer tiempo": "#D71920",
                "Segundo tiempo": "#FF8589",
            }

            colores_rivales = {
                "Primer tiempo": "#64748B",
                "Segundo tiempo": "#CBD5E1",
            }
            

            def crear_grafica_historica(columna, titulo,colores):
                datos = historico.loc[
                    historico[columna].notna()
                ].copy()

                figura = px.bar(
                    datos,
                    x="partido_eje",
                    y=columna,
                    color="mitad",
                    text=columna,
                    barmode="group",
                    category_orders={
                        "partido_eje": orden_partidos,
                        "mitad": [
                            "Primer tiempo",
                            "Segundo tiempo",
                        ],
                    },
                    color_discrete_map = colores,
                    custom_data=["rival", "localia"],
                    labels={
                        "partido_eje": "",
                        columna: metrica_resumen,
                        "mitad": "Mitad",
                    },
                    title=titulo,
                )

                figura.update_traces(
                    texttemplate="%{y:" + formato_resumen + "}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "Rival: %{customdata[0]}<br>"
                        "Chivas: %{customdata[1]}<br>"
                        + metrica_resumen
                        + ": %{y:"
                        + formato_resumen
                        + "}<extra>%{fullData.name}</extra>"
                    ),
                )

                figura.update_layout(
                    height=430,
                    bargap=0.25,
                    bargroupgap=0.08,
                    legend_title_text="",
                    legend={
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "right",
                        "x": 1,
                    },
                    margin={
                        "l": 70,
                        "r": 30,
                        "t": 90,
                        "b": 110,
                    },
                )

                figura.update_xaxes(
                    type="category",
                    categoryorder="array",
                    categoryarray=orden_partidos,
                    tickmode="array",
                    tickvals=orden_partidos,
                    ticktext=etiquetas_partidos,
                    range=[-0.5, len(orden_partidos) - 0.5],
                    tickangle=-30,
                )

                figura.update_yaxes(
                    range=[0, limite_y],
                    title_text=metrica_resumen,
                )

                if not es_xg_resumen:
                    figura.update_yaxes(
                        dtick=max(1, int(maximo_compartido / 5))
                    )

                return figura

            fig_chivas_resumen = crear_grafica_historica(
                columna_chivas_resumen,
                "Peligro generado por Chivas",
                colores_chivas,
            )

            fig_rival_resumen = crear_grafica_historica(
                columna_rival_resumen,
                "Peligro generado por los rivales",
                colores_rivales,
            )

            st.plotly_chart(
                fig_chivas_resumen,
                use_container_width=True,
                key="historico_chivas",
            )

            st.plotly_chart(
                fig_rival_resumen,
                use_container_width=True,
                key="historico_rivales",
            )

            st.caption(
                "Valores de cada mitad, sin acumular entre partidos. "
                "Fuente: StatsHub."
            )

    st.divider()
    st.subheader("Participación y recuperación del balón")
    st.caption(
        "Datos de Chivas por partido y mitad. "
        "Se aplican los filtros de localía y situación al descanso "
        "seleccionados arriba."
    )

    metricas_balon_resumen = {
        "Posesión (%)": "chivas_ballPossession",
        "Pases": "chivas_passes",
        "Pases precisos (%)": "chivas_pass_accuracy",
        "Pérdidas de balón (dispossessed)": "chivas_dispossessed",
        "Recuperaciones de balón": "chivas_ballRecovery",
    }

    # Usar los nombres de las columnas como claves evita depender
    # del texto que mostramos en el selector.
    notas_balon_resumen = {
        "chivas_ballPossession": (
            "Una mayor posesión no implica necesariamente más peligro."
        ),
        "chivas_passes": (
            "Cantidad de pases registrados; no indica por sí sola "
            "progresión ni precisión."
        ),
        "chivas_pass_accuracy": (
            "Porcentaje de pases completados. Una mayor precisión "
            "no implica necesariamente más progresión o peligro."
        ),
        "chivas_dispossessed": (
            "Campo dispossessed del proveedor. "
        ),
        "chivas_ballRecovery": (
            "Más recuperaciones no implican necesariamente "
            "un mejor rendimiento."
        ),
    }

    metrica_balon_resumen = st.selectbox(
        "Selecciona la métrica de participación con balón",
        options=list(metricas_balon_resumen),
        key="selector_balon_resumen",
    )

    columna_balon = metricas_balon_resumen[metrica_balon_resumen]

    if historico.empty:
        st.info("No hay partidos que cumplan los filtros seleccionados.")

    elif hay_duplicados:
        st.error(
            "Hay registros duplicados por partido y mitad. "
            "Revisa el CSV antes de graficar."
        )

    elif columna_balon not in historico.columns:
        st.warning(
            f"No se encontró la columna {columna_balon} en el CSV. "
            "Inclúyela en la extracción y vuelve a guardar los datos."
        )

    else:
        datos_balon = historico[
            [
                "partido_id",
                "partido_eje",
                "rival",
                "localia",
                "periodo",
                "mitad",
                columna_balon,
            ]
        ].copy()

        datos_balon = datos_balon.rename(
            columns={columna_balon: "valor"}
        )

        datos_balon["valor"] = pd.to_numeric(
            datos_balon["valor"],
            errors="coerce",
        )

        faltan_mitades = (
            datos_balon.groupby("partido_id")["periodo"]
            .nunique()
            .lt(2)
            .any()
        )

        if faltan_mitades or datos_balon["valor"].isna().any():
            st.warning(
                "Hay datos faltantes. Las barras ausentes "
                "no representan valores de cero."
            )

        datos_balon = datos_balon.dropna(subset=["valor"])

        es_porcentaje_balon = columna_balon in {
            "chivas_ballPossession",
            "chivas_pass_accuracy",
        }

        if datos_balon.empty:
            st.info("No hay valores disponibles para esta métrica.")

        elif (
            es_porcentaje_balon
            and not datos_balon["valor"].between(0, 100).all()
        ):
            st.error(
                "Hay porcentajes fuera del rango 0–100. "
                "Revisa la escala de esta columna en el CSV."
            )

        else:
            formato_balon = ".1f" if es_porcentaje_balon else ".0f"
            sufijo_balon = "%" if es_porcentaje_balon else ""

            fig_balon_resumen = px.bar(
                datos_balon,
                x="partido_eje",
                y="valor",
                color="mitad",
                text="valor",
                barmode="group",
                category_orders={
                    "partido_eje": orden_partidos,
                    "mitad": ["Primer tiempo", "Segundo tiempo"],
                },
                color_discrete_map={
                    "Primer tiempo": "#D71920",
                    "Segundo tiempo": "#FF8589",
                },
                custom_data=["rival", "localia"],
                labels={
                    "partido_eje": "",
                    "valor": metrica_balon_resumen,
                    "mitad": "Mitad",
                },
                title=f"{metrica_balon_resumen} de Chivas por mitad",
            )

            fig_balon_resumen.update_traces(
                texttemplate=(
                    "%{y:" + formato_balon + "}" + sufijo_balon
                ),
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "Rival: %{customdata[0]}<br>"
                    "Chivas: %{customdata[1]}<br>"
                    + metrica_balon_resumen
                    + ": %{y:"
                    + formato_balon
                    + "}"
                    + sufijo_balon
                    + "<extra>%{fullData.name}</extra>"
                ),
            )

            fig_balon_resumen.update_layout(
                height=430,
                bargap=0.25,
                bargroupgap=0.08,
                legend_title_text="",
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "right",
                    "x": 1,
                },
                margin={"l": 70, "r": 30, "t": 90, "b": 110},
            )

            fig_balon_resumen.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=orden_partidos,
                tickmode="array",
                tickvals=orden_partidos,
                ticktext=etiquetas_partidos,
                range=[-0.5, len(orden_partidos) - 0.5],
                tickangle=-30,
            )

            if es_porcentaje_balon:
                fig_balon_resumen.update_yaxes(
                    range=[0, 100],
                    dtick=20,
                    ticksuffix="%",
                )
            else:
                maximo_balon = datos_balon["valor"].max()

                fig_balon_resumen.update_yaxes(
                    range=[0, max(1, maximo_balon * 1.25)],
                    dtick=max(1, int(maximo_balon / 5)),
                )

            st.plotly_chart(
                fig_balon_resumen,
                use_container_width=True,
                key="historico_balon_chivas",
            )

        st.caption(notas_balon_resumen[columna_balon])
        st.caption("Fuente: StatsHub · Valores de cada mitad.")

with tab_detalle:

    # Construir las opciones del selector
    partidos = (
        mitades[["partido_id", "fecha", "rival", "localia"]]
        .drop_duplicates("partido_id")
        .sort_values("fecha", ascending=False)
        .set_index("partido_id")
    )

    etiquetas = {
        partido_id: (
            f"{fila['rival']} · "
            f"{fila['fecha']:%d/%m/%Y} · "
            f"{fila['localia']}"
        )
        for partido_id, fila in partidos.iterrows()
    }

    partido_id = st.selectbox(
        "Selecciona el rival y partido",
        options=partidos.index.tolist(),
        format_func=lambda identificador: etiquetas[identificador],
    )

    # Filtrar el encuentro seleccionado
    seleccion = mitades.loc[
        mitades["partido_id"].eq(partido_id)
    ].copy()

    if (
        len(seleccion) != 2
        or set(seleccion["periodo"]) != {"1ST", "2ND"}
    ):
        st.warning("Este partido no tiene exactamente un registro por mitad.")
        st.stop()

    rival = partidos.loc[partido_id, "rival"]

    # Recuperar todos los periodos del partido seleccionado
    partido = df.loc[
        df["partido_id"].eq(partido_id)
    ].copy()

    def obtener_marcador(periodo):
        filas = partido.loc[partido["periodo"].eq(periodo)]

        if len(filas) != 1:
            return "No disponible"

        goles = pd.to_numeric(
            filas.iloc[0][["goles_favor", "goles_contra"]],
            errors="coerce",
        )

        if goles.isna().any():
            return "No disponible"

        return f"{int(goles['goles_favor'])} – {int(goles['goles_contra'])}"

    st.subheader(f"Chivas vs. {rival}")
    st.caption(
        f"{partidos.loc[partido_id, 'fecha']:%d/%m/%Y}"
        f" · Chivas juega como {partidos.loc[partido_id, 'localia'].lower()}"
        " · Marcadores: Chivas – rival"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Al descanso",
            value=obtener_marcador("1ST"),
        )

    with col2:
        st.metric(
            label="Solo segundo tiempo",
            value=obtener_marcador("2ND"),
        )

    with col3:
        st.metric(
            label="Resultado final",
            value=obtener_marcador("ALL"),
        )

    # st.divider()

    # st.subheader("Errores registrados de Chivas")
    # st.caption(
    #     "Datos del partido completo. "
    #     "La fuente no ofrece el desglose por mitad en nuestra extracción."
    # )

    # 'partido' contiene todos los periodos del encuentro seleccionado.
    # Aquí usamos exclusivamente el registro ALL.
    # registro_completo = partido.loc[
    #     partido["periodo"].eq("ALL")
    # ]

    # if registro_completo.empty:
    #     st.info(
    #         "No hay un registro de partido completo "
    #         "para consultar los errores."
    #     )

    # elif len(registro_completo) > 1:
    #     st.error(
    #         "Hay más de un registro ALL para este partido. "
    #         "Revisa el CSV antes de mostrar los errores."
    #     )

    # else:
    #     def obtener_error_partido(columna):
    #         # Una columna ausente o un valor vacío no equivale a cero.
    #         if columna not in registro_completo.columns:
    #             return "No disponible"

    #         valor = pd.to_numeric(
    #             registro_completo.iloc[0][columna],
    #             errors="coerce",
    #         )

    #         if pd.isna(valor):
    #             return "No disponible"

    #         # Los errores deben ser conteos enteros no negativos.
    #         if valor < 0 or valor % 1 != 0:
    #             return "Dato inválido"

    #         return str(int(valor))

    #     col_error_tiro, col_error_gol = st.columns(2)

    #     with col_error_tiro:
    #         st.metric(
    #             label="Errores que derivan en tiro",
    #             value=obtener_error_partido(
    #                 "chivas_errorsLeadToShot"
    #             ),
    #         )

    #     with col_error_gol:
    #         st.metric(
    #             label="Errores que derivan en gol",
    #             value=obtener_error_partido(
    #                 "chivas_errorsLeadToGoal"
    #             ),
    #         )

    #     st.caption(
    #         "«No disponible» indica que no recibimos un valor; "
    #         "no significa cero errores. Estos registros no permiten "
    #         "determinar en qué mitad ocurrió cada error."
    #     )

    st.divider()

    st.subheader("Peligro generado por Chivas y generado por su rival")

    # Métricas disponibles: columnas de Chivas y del rival
    metricas = {
        "Goles esperados (xG)": (
            "chivas_expectedGoals",
            "rival_expectedGoals",
        ),
        "Tiros totales": (
            "chivas_totalShotsOnGoal",
            "rival_totalShotsOnGoal",
        ),
        "Tiros a puerta": (
            "chivas_shotsOnGoal",
            "rival_shotsOnGoal",
        ),
        "Ocasiones claras creadas": (
            "chivas_bigChanceCreated",
            "rival_bigChanceCreated",
        ),
        "Tiros dentro del área": (
            "chivas_totalShotsInsideBox",
            "rival_totalShotsInsideBox",
        ),
        "Entradas al último tercio": (
            "chivas_finalThirdEntries",
            "rival_finalThirdEntries",
        ),
    }

    # Este selector aparece después del selector de partido
    metrica = st.selectbox(
        "Selecciona la métrica",
        options=list(metricas),
    )

    columna_chivas, columna_rival = metricas[metrica]

    # Transformar las dos columnas seleccionadas a formato largo
    datos_grafica = seleccion.melt(
        id_vars=["periodo"],
        value_vars=[columna_chivas, columna_rival],
        var_name="equipo",
        value_name="valor",
    )

    datos_grafica["equipo"] = datos_grafica["equipo"].map({
        columna_chivas: "Chivas",
        columna_rival: rival,
    })

    datos_grafica["mitad"] = datos_grafica["periodo"].map({
        "1ST": "Primer tiempo",
        "2ND": "Segundo tiempo",
    })

    datos_grafica["valor"] = pd.to_numeric(
        datos_grafica["valor"], errors="coerce"
    )

    if datos_grafica["valor"].isna().any():
        st.warning(f"Faltan valores de {metrica} para este partido.")
        st.stop()

    # xG con dos decimales; los conteos sin decimales
    es_xg = metrica == "Goles esperados (xG)"
    formato = ".2f" if es_xg else ".0f"

    fig = px.bar(
        datos_grafica,
        x="mitad",
        y="valor",
        color="equipo",
        barmode="group",
        text="valor",
        category_orders={
            "mitad": ["Primer tiempo", "Segundo tiempo"],
            "equipo": ["Chivas", rival],
        },
        color_discrete_map={
            "Chivas": "#D71920",
            rival: "#64748B",
        },
        labels={
            "mitad": "",
            "valor": metrica,
            "equipo": "Equipo",
        },
        title=f"{metrica} · Chivas vs. {rival}",
    )

    fig.update_traces(
        texttemplate="%{y:" + formato + "}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "%{x}<br>"
            + metrica
            + ": %{y:"
            + formato
            + "}<extra>%{fullData.name}</extra>"
        ),
    )

    fig.update_layout(
        legend_title_text="",
        yaxis_rangemode="tozero",
    )

    # Dejar espacio sobre las barras para las etiquetas
    maximo = datos_grafica["valor"].max()
    fig.update_yaxes(range=[0, max(1, maximo * 1.2)])

    # Los conteos se muestran con marcas enteras en el eje
    if not es_xg:
        fig.update_yaxes(dtick=max(1, int(maximo / 5)))

    st.plotly_chart(fig, use_container_width=True)

    if es_xg:
        st.caption(
            "El xG resume la calidad de las ocasiones de tiro según el "
            "modelo del proveedor; no representa los goles anotados."
        )

    st.caption("Fuente: StatsHub · Comparación por mitad.")

    st.divider()
    st.subheader("Participación y recuperación del balón")
    st.caption("Comparación de Chivas entre el primer y segundo tiempo.")

    metricas_contexto = {
        "Posesión (%)": "chivas_ballPossession",
        "Pases": "chivas_passes",
        "Pases precisos (%)" : "chivas_pass_accuracy",
        "Pérdidas de Balón (dispossessed)": "chivas_dispossessed",
        "Recuperaciones de balón": "chivas_ballRecovery",
    }

    metrica_contexto = st.selectbox(
        "Selecciona la métrica de contexto",
        options=list(metricas_contexto),
        key="selector_contexto",
    )

    columna_contexto = metricas_contexto[metrica_contexto]

    # Usar el mismo partido seleccionado en la parte superior
    datos_contexto = seleccion[
        ["periodo", columna_contexto]
    ].copy()

    datos_contexto = datos_contexto.rename(
        columns={columna_contexto: "valor"}
    )

    datos_contexto["mitad"] = datos_contexto["periodo"].map({
        "1ST": "Primer tiempo",
        "2ND": "Segundo tiempo",
    })

    datos_contexto["valor"] = pd.to_numeric(
        datos_contexto["valor"],
        errors="coerce",
    )

    if datos_contexto["valor"].isna().any():
        st.warning(
            f"Faltan valores de {metrica_contexto} para este partido."
        )
    else:
        es_porcentaje = columna_contexto in {
            "chivas_ballPossession",
            "chivas_pass_accuracy",
        }

        # La posesión del CSV está en escala 0–100
        formato_contexto = ".1f" if es_porcentaje else ".0f"
        sufijo = "%" if es_porcentaje else ""

        fig_contexto = px.bar(
            datos_contexto,
            x="mitad",
            y="valor",
            text="valor",
            category_orders={
                "mitad": ["Primer tiempo", "Segundo tiempo"],
            },
            labels={
                "mitad": "",
                "valor": metrica_contexto,
            },
            title=f"{metrica_contexto} de Chivas · Partido vs. {rival}",
        )

        fig_contexto.update_traces(
            marker_color="#D71920",
            texttemplate="%{y:" + formato_contexto + "}" + sufijo,
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "%{x}<br>"
                + metrica_contexto
                + ": %{y:"
                + formato_contexto
                + "}"
                + sufijo
                + "<extra>Chivas</extra>"
            ),
        )

        fig_contexto.update_layout(
            showlegend=False,
            bargap=0.5,
        )

        if es_porcentaje:
            fig_contexto.update_yaxes(
                range=[0, 100],
                dtick=20,
                ticksuffix="%",
            )
        else:
            maximo_contexto = datos_contexto["valor"].max()

            fig_contexto.update_yaxes(
                range=[0, max(1, maximo_contexto * 1.2)],
                dtick=max(1, int(maximo_contexto / 5)),
            )

        st.plotly_chart(
            fig_contexto,
            use_container_width=True,
            key="grafica_contexto",
        )

        notas_contexto = {
            "Posesión (%)": (
                "Una mayor posesión indica más participación con balón, "
                "pero no necesariamente más peligro."
            ),
            "Pases": (
                "Cantidad de pases registrados en cada mitad; "
                "no indica por sí sola progresión ni precisión."
            ),

            "Pases precisos (%)": (
                "Porcentaje de pases completados. Una mayor precisión "
                "no implica necesariamente más progresión o peligro."    
            ),
            "Pérdidas de Balón (dispossessed)": (
                "Campo dispossessed del proveedor. "
            ),
            "Recuperaciones de balón": (
                "Más recuperaciones no implican necesariamente "
                "un mejor rendimiento."
            ),
        }

        st.caption(notas_contexto[metrica_contexto])
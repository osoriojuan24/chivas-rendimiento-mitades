# Chivas: rendimiento entre mitades

Dashboard interactivo para explorar cómo cambia el rendimiento ofensivo de
Chivas entre el primer y segundo tiempo en el Apertura 2026 de la Liga MX.

El dashboard pretende responder a la pregunta: **¿empeora el rendimiento ofensivo de Chivas
en el segundo tiempo, especialmente cuando llega ganando al descanso?**

## Qué permite explorar

- Cambio del balance de xG entre mitades, para lo cual se definió Balance = xG de Chivas − xGA (xG del rival)
- Descomposición del cambio: generación de ocasiones y peligro concedido.
- Goles anotados frente al xG en cada mitad.
- Tiros, ocasiones claras y entradas al último tercio.
- Posesión, pases, precisión de pase y recuperaciones.
- Detalle de cada partido y sus marcadores.

El resumen del torneo incluye filtros de localía y situación al descanso.
Los selectores de métricas permiten explorar las estadísticas de cada sección.

## Indicadores principales

**xG:** goles esperados de Chivas.

**xGA:** goles esperados del rival, equivalentes al xG concedido por Chivas.

**Balance de ocasiones:**

```text
Balance = xG − xGA
```

**Cambio del balance entre mitades:**

```text
Cambio del balance = Balance del segundo tiempo − Balance del primero
```

Un cambio positivo indica una mejora relativa del balance;
uno negativo indica deterioro. Mejorar no implica necesariamente
tener un balance favorable en el segundo tiempo ni ganar el partido.

**Goles respecto a Goles Esperados:**

```text
Goles − xG
```

Un valor positivo indica más goles que los estimados por el modelo;
uno negativo indica menos. Este indicador no demuestra por sí solo
una buena o mala capacidad de definición.

## Fuente y limitaciones

Los datos se obtienen de StatsHub mediante consultas de estadísticas
del equipo para el primer tiempo, segundo tiempo y partido completo.

- El proveedor original y la metodología específica del modelo de xG
  no se han confirmado.
- El análisis es exploratorio y corresponde a los partidos disponibles
  en los archivos publicados.
- Las relaciones observadas no demuestran causas tácticas o físicas.
- Los datos ausentes no se interpretan como ceros.
- Las métricas de errores defensivos se conservan en los datos, pero
  no se muestran por su cobertura incompleta y falta de desglose por mitad.

Proyecto independiente, sin afiliación oficial con el club ni con StatsHub.

## Archivos

| Archivo | Contenido |
|---|---|
| `app.py` | Aplicación de Streamlit |
| `extraccion_chivas_statshub.py` | Descarga y transformación de datos |
| `chivas_data_por_tiempo.csv` | Estadísticas por partido y periodo |
| `chivas_balance_xG.csv` | Comparación entre mitades y contexto del marcador |
| `requirements.txt` | Dependencias de Python |
| `.gitignore` | Archivos locales excluidos del repositorio |

## Ejecutar localmente

Desde la carpeta del proyecto, instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

Iniciar el dashboard:

```bash
python -m streamlit run app.py
```

La aplicación lee los CSV incluidos. No es necesario consultar
StatsHub para abrir el dashboard.

## Actualizar los datos

Ejecutar la extracción:

```bash
python extraccion_chivas_statshub.py
```

Este proceso consulta StatsHub y sobrescribe los CSV generados
en la carpeta del script.


## Autor

Juan Jesús Osorio Gatica
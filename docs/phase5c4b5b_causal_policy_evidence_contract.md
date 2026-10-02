# FASE 5C-4B.5B — Causal policy & evidence resolution contract

## Resultado y alcance

La sesión sigue `BLOCKED` con exactamente **19 blockers**. Esta fase no aprobó
ninguna política, no promovió mappings (`mapping_promotions=0`), no hizo
cutover, llamadas al proveedor, probes, descargas, loader, backtest ni
integración runtime. El artefacto canónico machine-readable es
[`phase5c4b5b_causal_policy_docket.json`](evidence/phase5c4b5b_causal_policy_docket.json).
El módulo declarativo es `bot_spx.causal_policy_docket`; sus dataclasses son
`frozen`, sus colecciones canónicas son tuplas o mappings read-only, y cada
promoción automática está deshabilitada.

La base certificada fue `origin/main` en
`4fa705a55411a52d2ce31a72ab0cf4e5a3a58aef`, tree
`c4b8ab82382f871ed93e38a84ddadc14105328e8`, que contiene el checkpoint 5A.
El baseline ejecutado en un worktree detached produjo `666 passed`.

## Dockets y respuesta central

Los dockets B01–B19 conservan separados disponibilidad, correcciones,
missingness, staleness, adquisición y alineación. Cada uno identifica evidencia
persistida y faltante, pregunta humana exacta, clases admisibles y prohibidas,
riesgo de look-ahead, riesgos residuales, implementación y tests posteriores,
dependencias, efectos downstream y precondiciones objetivas. Ningún docket
puede promoverse automáticamente.

* **Quotes (B01–B03):** falta probar `available_time`, semántica de correcciones
  y distribución empírica para un límite de edad. Está prohibido convertir
  `event_time` en disponibilidad, usar latencia promedio, latest-row-wins,
  ticks futuros o inventar un threshold.
* **OI (B04–B06):** el timestamp del mensaje diario no prueba disponibilidad.
  Se requieren semánticas de reemplazo y cobertura; `MISSING`, `ZERO`,
  `NO_MESSAGE` y `UNKNOWN` permanecen distintos. `no row = zero` está prohibido.
* **SPX (B07–B10):** P8 sigue siendo `TRANSPORT_ERROR`, no disponibilidad ni
  denegación. Una observación futura mínima y autorizada debe distinguir cinco
  outcomes. Después aún faltarían disponibilidad, estado unchanged/gap y edad;
  silent forward-fill está prohibido.
* **Alineación (B11):** separa `event_time_skew` de `available_time_skew`.
  `LAST_CAUSALLY_AVAILABLE` puede evaluarse en el futuro, pero no hay máximo
  aprobado; nearest-future, interpolación futura y backfill futuro siguen
  prohibidos.
* **Trades (B12–B14):** `EMPTY_SUCCESS` permanece ambiguo. La secuencia signed
  32-bit con wrap no es global y los cancels no enlazan el original. Sin prueba
  de recepción, el tape histórico no es estado recibido por T. Si no se puede
  resolver, las features dependientes deben declararse no reproducibles o
  excluirse, nunca inventar linkage.
* **Rate y dividend (B15–B16):** hay evidencia suficiente para presentar
  opciones humanas, no para elegirlas. SOFR D publicado D+1 no es causal en D;
  ZERO dividend sigue siendo test-only. Cada clase incluye riesgo,
  implementación y tests propios, y dividend impacta IV, Delta, Gamma, Theta,
  Rho y GEX.
* **Metadata/calendario (B17–B18):** los campos parciales y la regla conservadora
  fecha de expiración=D no resuelven settlement, expiration time, identidad
  temporal ni fechas especiales. Se exige historia versionada de New York/DST,
  sesión, feriados, early closes, SPXW PM y cambios de listings. No se construyó
  calendar engine ni se aplicó el calendario actual al pasado.
* **Depth (B19):** permanece `HUMAN_DECISION_PENDING`; `SINGLE_DATE_ONLY` no
  satisface una longitud todavía indefinida. La decisión debe expresar sesiones,
  span, regímenes, componentes y continuidad/muestreo sin recomendar una cifra.

## Paquetes humanos y adquisición futura

Q1–Q9 agrupan una decisión humana real sin fusionar blockers. Todos están
`PENDING`, requieren autorización futura y registran reversibilidad y riesgo.
E01–E08 son planes, no ejecuciones. Cada request limita llamadas, filas, fechas
y retención; prohíbe bulk/crawler y detiene ante paginación no autorizada,
expansión de scope o volumen inesperado. La anomalía P2 de **17,326 filas** es
la razón explícita para esta minimización. No se introdujeron endpoints ni APIs.

El DAG 5B es complementario y no modifica el DAG 5A. Incluye los 19 IDs,
valida endpoints conocidos y produce orden topológico determinista o falla ante
ciclos. La clasificación distingue resolución desde evidencia persistida
(B15/B16), necesidad de evidencia externa y blockers que esperan upstream. Las
acciones A01–A12 están ordenadas por dependencias, no por preferencia, y todas
llevan `execute_in_this_phase=false`.

## Trades opcionales y cadena de Greeks

Sin trades pueden reconstruirse conceptualmente spot, walls, Gamma Flip,
Static OI/GEX, IV por quotes y Greeks locales, siempre que sus propios blockers
se resuelvan. Dealer flow, aggressor classification, Dynamic GEX y Dealer
Dynamic GEX requieren trades. Omitir esa rama cambiaría las señales a semántica
static-OI/levels sin contribución dealer-flow; esto sólo documenta una
posibilidad y **no** crea un degraded mode ni modifica la estrategia.

La puerta declarada es:

`causal quote + causal SPX + causal rate + approved dividend + causal metadata + approved alignment + approved staleness = eligible local IV input`

`eligible local IV + LOCAL_SPX_BS_V1 = eligible local Greeks`

Actualmente la lista de inputs elegibles está vacía. Provider Greeks/IV siguen
`EXCLUDED`; local Greeks/IV siguen `NEEDS_RECONSTRUCTION`.

## Condición de promoción posterior

Un blocker sólo puede considerarse para promoción cuando se hayan retenido sus
evidencias requeridas, resuelto su packet humano, implementado exclusivamente
la política aprobada y aprobado todos sus tests fail-closed, además de sus
blockers upstream. Aun entonces la promoción requiere una acción humana en una
fase posterior: nunca es automática y 5B no la realiza.

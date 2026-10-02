# Fase 5C-4B.4B — contrato causal de inputs para Greeks locales

## Alcance y semántica temporal

Este contrato es **offline, puro y exclusivamente sintético**. No descarga datos,
no contiene loaders, no ejecuta backtests y no se integra con runtime. Para un
`replay_time=T`, un dato solamente puede ser causal cuando hay evidencia directa
de `available_time <= T`. `event_time <= T`, `source_time <= T`, un tiempo de
descarga retrospectivo o una latencia promedio no demuestran disponibilidad.
Ausencia de esa evidencia produce `BLOCKED_UNRESOLVED_AVAILABILITY`; timestamps
naive producen `INVALID_INPUT`.

Los estados cerrados incluyen `ELIGIBLE`, `MATHEMATICAL_TEST_ONLY`, los bloqueos
de mapping, disponibilidad, evento futuro, disponibilidad futura, correcciones,
alineación, staleness, política, missingness e input inválido. Todo caso no
demostrado falla cerrado.

## Contratos por input

### Quote de opción

Exige bid, ask, identidad contractual, tiempos de evento y disponibilidad,
provenance, calidad y semántica de filtros/correcciones. La evidencia actual de
OPRA NBBO carece de secuencia, receipt time del cliente y cota máxima garantizada.
Por tanto, el mapping real `option_quotes=BLOCKED_UNRESOLVED` nunca es elegible.
Solamente fixtures sintéticos pueden aportar disponibilidad explícita.

### Subyacente SPX

Exige valor, identificador, fuente, ambos tiempos, calidad, relación de
alineación y política de staleness. Cboe Global Indices Feed es separado de OPRA,
sin secuencia compartida ni receipt time probado, y puede no emitir un tick si el
índice no cambia. El mapping real `spx_historical_spot=BLOCKED_UNRESOLVED` sigue
bloqueado. No se permite nearest-future, interpolación futura ni backfill futuro.

### Tasa

`RateValue` conserva tasa, reference time, publication time y versión/política.
Se representan `LATEST_CAUSALLY_PUBLISHED_RATE`, `EXPLICIT_CAUSAL_RATE` y
`VERSIONED_APPROVED_FALLBACK`; el fallback no está aprobado. SOFR de D publicado
en D+1 no es causal intraday D. Una tasa previa es usable solo cuando su
publicación y disponibilidad explícitas anteceden T. Publicación ausente o futura
bloquea el bundle. Esta fase no elige una tasa operativa.

### Dividendo

El valor matemático está separado de su evidencia causal. Se representan `ZERO`,
`EXPLICIT_ANNUAL_DIVIDEND` y `OTHER_VERSIONED_POLICY`. `ZERO` solo se permite por
defecto en `MATHEMATICAL_TEST_ONLY`; no queda aprobado para replay real. Una
política real sin aprobación produce `BLOCKED_UNRESOLVED_POLICY`.

### Metadata contractual

La metadata conserva root, expiración, strike, right, settlement style, identidad,
fuente, reference/event time, available time y provenance. Para la regla
conservadora 0DTE se exige `SPXW` y que la fecha de expiración coincida con la
fecha de replay. `READY_WITH_CONSERVATIVE_RULE / LOW` no elimina el riesgo de
contratos listados inactivos, metadata histórica no versionada ni feriados o
listings especiales; esos casos permanecen explícitamente sin resolver.

## Alineación, skew y staleness

`LAST_CAUSALLY_AVAILABLE` es representable únicamente cuando cada
`available_time` está demostrado. El contrato rechaza `NEAREST_FUTURE`,
`FUTURE_INTERPOLATION` y `FUTURE_BACKFILL`. No fija max quote age, max SPX age ni
max cross-feed skew. Conserva separadamente `event_time_skew` y
`available_time_skew`; timestamps de evento iguales no implican simultaneidad de
feeds.

Las políticas declarativas son `NO_THRESHOLD_APPROVED`,
`EXPLICIT_TEST_THRESHOLD` y `FUTURE_APPROVED_THRESHOLD`. La primera bloquea cuando
staleness es necesaria; la segunda requiere modo y threshold sintéticos. No se
inventa ningún límite operativo.

## Correcciones y missingness

Cada observación declara estado y semántica de corrección, persistencia del
original y existencia de link. `UNRESOLVED` bloquea; el contrato no reconstruye
automáticamente un tape corregido. Distingue `MISSING`, `ZERO`, `NO_MESSAGE` y
`UNKNOWN`: no row no equivale a cero y no existe forward-fill silencioso.

## Bundle y bridge a `LOCAL_SPX_BS_V1`

`build_causal_greeks_input_bundle` recibe únicamente objetos ya cargados en
memoria y devuelve un bundle completo o un resultado estructurado sin bundle. Se
requieren option, SPX, rate, dividend y metadata, y todos deben superar sus gates.
El bridge puro `to_local_greeks_input` transforma solo bundles `ELIGIBLE` o
`MATHEMATICAL_TEST_ONLY`; un bundle bloqueado genera error antes de invocar el
motor. Ningún runtime importa el contrato ni `local_greeks`.

## Compatibilidad con TemporalFirewall

La frontera coincide con 5C-4A: compara timestamps timezone-aware normalizados a
UTC, rechaza eventos futuros y disponibilidad futura, no usa look-ahead y admite
llegadas out-of-order solo si cada registro era causalmente disponible. No se
modificó `historical.py` ni se duplicó un ordenamiento que cambiase sus reglas.

## Validación sintética y blockers restantes

Los tests cubren los 25 escenarios requeridos: bundle matemático, futuros por
cada feed, missingness, ambos órdenes de antigüedad, staleness, métodos futuros,
SOFR retrospectivo, tasa previamente publicada, dividendos, metadata conservadora
y especial, correcciones, zero/no-message, bundle completo y determinismo.
También congelan ausencia de capacidades de red, imports runtime, integridad de
mappings/evidencia y ejecución fail-closed.

Persisten exactamente: provider Greeks/IV `EXCLUDED`, local Greeks/IV
`NEEDS_RECONSTRUCTION`, SPX/OI/trades/quotes `BLOCKED_UNRESOLVED`, universo SPXW
`READY_WITH_CONSERVATIVE_RULE / LOW` y `cutover=NO`. En consecuencia, corrección
matemática de `LOCAL_SPX_BS_V1` **no** hace elegible el replay histórico real.

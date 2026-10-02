# Fase 5C-4B.4C-1 — account entitlement y acquisition readiness

## Alcance y separación obligatoria

Este checkpoint es un **plan offline**. No consulta la cuenta, no lee
credenciales, no llama endpoints, no descarga datos y no habilita replay,
backtest, runtime ni cutover. El contrato mantiene cuatro capas independientes:

1. `PROVIDER_CAPABILITY`: lo que la evidencia escrita afirma que ThetaData ofrece;
2. `ACCOUNT_ENTITLEMENT`: acceso demostrado para nuestra cuenta y dataset;
3. `ACQUISITION_READINESS`: entitlement, schema, resolución y profundidad ya
   verificados para una adquisición futura mínima;
4. `CAUSAL_REPLAY_ELIGIBILITY`: disponibilidad temporal, correcciones, mapping y
   políticas necesarias para replay point-in-time.

Ninguna capa implica la siguiente. En particular, adquirir una respuesta válida
no prueba que el dato fuese observable en el instante histórico representado.
El módulo puro que materializa taxonomías, inventario, acciones y evaluación es
`src/bot_spx/account_entitlement.py`.

## Evidencia y baseline de capability

Las únicas fuentes internas son `raw_response.md`, su `evidence_ledger.json`, la
decisión humana 5C-4B.3 y los contratos 5C-4B, 4A y 4B. No se consultó nueva
documentación pública. La respuesta de Eduardo describe como capacidades del
**proveedor**, no de nuestra cuenta:

|Familia documentada|Resolución/profundidad indicada|
|---|---|
|Options Value|un minuto desde 2020-01-01; quote/OHLC/OI/EOD|
|Options Standard|tick desde 2016-01-01; añade trades, trade_quote, IV y Greeks de primer orden|
|Options Pro|tick desde 2012-06-01; añade Greeks de segundo/tercer orden y trade Greeks|
|Greeks EOD|Gamma incluido en Standard|
|Greeks históricos de opciones sobre índice|desde 2017-01-01|
|Indices Value|un minuto desde 2023-01-01; delay de 15 minutos|
|Indices Standard|venue desde 2022-01-01|
|Indices Pro|venue desde 2017-01-01|

SPX index history exige una suscripción Indices separada. El contexto previo
`CLAIMED_OR_PREVIOUSLY_REPORTED_PLAN=STANDARD` es solamente una afirmación: todos
los datasets continúan `ACCOUNT_UNVERIFIED`, incluso los de Options, y Options
jamás hereda entitlement a Indices.

## Taxonomía e inventario requerido

Los enums cerrados eliminan strings libres: capability/entitlement usa
`PROVIDER_DOCUMENTED`, `ACCOUNT_VERIFIED`, `ACCOUNT_UNVERIFIED`,
`ACCOUNT_DENIED`, `UNKNOWN`, `NOT_REQUIRED`, `EXCLUDED`; readiness usa
`READY_FOR_CONTROLLED_ACQUISITION`, sus cuatro verificaciones pendientes,
`NEEDS_CAUSALITY_RESOLUTION`, `BLOCKED` y `EXCLUDED`. Resolución distingue
`TICK`, `VENUE`, `ONE_MINUTE`, `EOD` y `UNKNOWN`.

El inventario machine-readable incluye contract list, quotes, trades, OI, IV,
Greeks de primer orden, segundo orden/Gamma, EOD Greeks, SPX, rates, metadata y
trade_quote. Cada fila conserva propósito, requisito, ambas capas de capability,
resolución y profundidad requeridas, fecha inicial documentada, fecha más
temprana accesible por cuenta, campos, familia de endpoint, estado causal,
mapping, readiness, referencia y necesidad de verificación. En 4C-1 toda fecha
de cuenta es `UNKNOWN`; los rangos exactos del proyecto permanecen sin resolver.

La matriz de necesidades, derivada de 4A/4B, es:

|Dataset|Necesidad|Razón / límite|
|---|---|---|
|contract list y metadata|`REQUIRED_NOW`|descubrir e identificar de forma acotada SPXW/contrato|
|option quotes|`REQUIRED_NOW`|premium para IV/Greeks locales|
|SPX index|`REQUIRED_NOW`|subyacente del modelo local; suscripción independiente|
|rate history|`REQUIRED_NOW`|tasa publicada causalmente; fuente aún no elegida|
|trades y OI|`REQUIRED_LATER`|estrategia futura; mappings causales bloqueados|
|provider IV/first-order Greeks|`OPTIONAL`|diagnóstico solamente; outputs PIT excluidos|
|provider Gamma intraday|`NOT_REQUIRED`|la reconstrucción matemática local no lo necesita|
|EOD Gamma y trade_quote|`OPTIONAL`|diagnóstico, no promoción causal|

## Contrato de evidencia de entitlement

Solo pueden promover `ACCOUNT_UNVERIFIED` evidencias específicas del dataset y
de nuestra cuenta: metadata oficial de cuenta/suscripción; confirmación escrita
del proveedor específica de la cuenta; probe autenticado mínimo que demuestre
endpoint **y campos**; o error explícito de entitlement, que prueba
`ACCOUNT_DENIED`. Documentación general, memoria del usuario, existencia del
endpoint, éxito de otro endpoint, precio del plan y respuestas históricas
guardadas no bastan.

Los outcomes cerrados son `VERIFIED_AVAILABLE`, `VERIFIED_DENIED`, `AMBIGUOUS`,
`NOT_TESTED` y `ERROR`. `ERROR` no es denial. Una respuesta vacía no es denial.
HTTP success sin campos esperados no verifica schema. Solo un error explícito de
entitlement permite `ACCOUNT_DENIED`.

## Schema, resolución e historia

Campos mínimos (nombres conceptuales, no afirmación de nombres wire):

* quote: timestamp, bid/ask, tamaños, identidad contractual y, cuando estén
  disponibles, condition/exchange;
* trade: timestamp, price, size, condition, sequence cuando aplique e identidad;
* OI: timestamp, value e identidad;
* SPX: timestamp e index value;
* rate: fecha/hora de referencia o publicación y rate value;
* contrato: root, expiration, strike y right.

La verificación se hace por dataset: schema correcto, resolución realmente
accesible y fecha inicial accesible. Las fechas documentadas del proveedor no
son profundidad de nuestra cuenta. `evaluate_acquisition_readiness` falla
cerrado en orden: account, schema, resolution, history depth. Solo las cuatro
pruebas producen `READY_FOR_CONTROLLED_ACQUISITION`; aun entonces no altera el
estado causal.

## Plan mínimo futuro 4C-2 (no ejecutado)

El plan immutable propone: metadata de cuenta si existe; contract list; quote;
trade; OI; IV; first-order Greeks; EOD Gamma; SPX; rates. Son familias
conceptuales porque la evidencia interna no autoriza inventar URLs concretas.
Cada acción registra autenticación, scope, máximo de filas, rango, root/symbol,
campos, evidencia de éxito/denial/ambigüedad, retención y prohibición de payload.

Principio de minimización: un root, un contrato cuando sea posible, un timestamp
o intervalo mínimo; un solo día únicamente cuando el endpoint no permita menos;
sin chain amplia, rango multianual ni bulk export. El límite de un día admite un
tope declarativo de 10.000 filas para no afirmar de antemano la densidad real;
los otros probes admiten una fila. Una futura ejecución sigue siendo read-only.

## Credenciales, autorización y retención

No habrá credenciales, tokens ni auth headers persistidos; no se imprimirán
secretos, no se volcará el environment y account IDs se omitirán o redactarán.
Esta fase no implementa loader. Sus contadores contractuales son: credential
reads 0, authenticated calls 0, provider data calls 0 y datasets downloaded 0.
En una 4C-2 futura solo se leería la credencial estrictamente necesaria tras
mandato humano explícito.

`CONTROLLED_ACCOUNT_VERIFICATION_AUTHORIZED=False` es constante y no existe
mecanismo de promoción automática. Por defecto `raw_payload_may_be_persisted`
es falso. Las clases futuras son `METADATA_ONLY`, `SCHEMA_SAMPLE` y
`CONTROLLED_DATA_SAMPLE`; salvo nuevo mandato se conservarían únicamente status,
schema/field names, row count, cobertura, resolución, metadata de respuesta y
hash, nunca mercado innecesario.

## Gates especiales y replay causal

* **SPX:** Options Standard, aunque fuese verificado, no prueba Indices. SPX
  requiere evidencia independiente de cuenta. Aun verificado, su mapping sigue
  `BLOCKED_UNRESOLVED` por clocks/sincronización.
* **Greeks/Gamma:** provider IV y Greeks continúan `EXCLUDED` como outputs PIT;
  local IV/Greeks continúa `NEEDS_RECONSTRUCTION`. First/second order, EOD Gamma
  y trade Greeks no se mezclan. Gamma del proveedor no es input matemático
  requerido por `LOCAL_SPX_BS_V1`.
* **OI:** entitlement no resuelve publicación exacta, revisiones ni missing-zero;
  mapping permanece `BLOCKED_UNRESOLVED`.
* **Quotes:** entitlement no aporta receipt/availability clock, NBBO ni política
  de correcciones; mapping permanece `BLOCKED_UNRESOLVED`.
* **Rates/metadata/trades:** también conservan los blockers causales declarados
  en 4B; acquisition readiness no los elimina.

Por ello real historical local Greeks replay sigue distinto de `ELIGIBLE`.
Fase 4/Fase 5 y módulos históricos/locales quedan intactos, no hay mapping
promotion, y `cutover=NO`.

## Incógnitas restantes

Quedan desconocidos por cuenta: plan efectivo y add-ons, entitlements dataset a
dataset, schemas devueltos, resolución, profundidad, símbolos exactos admitidos,
retención y mensajes inequívocos de denial. Quedan además sin resolver —aunque
el acceso llegue a verificarse— clocks de disponibilidad, correcciones,
ordenamiento, sincronización OPRA/SPX, política causal de tasas, staleness y
profundidad exacta exigida por el futuro rango de replay. Resolver entitlement
no autoriza adquisición masiva ni replay.

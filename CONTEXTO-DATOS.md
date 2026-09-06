# Contexto de datos — Scope O9

> **Léeme antes de pedirle explicaciones al usuario.** Este archivo describe qué es
> cada dato de las extracciones de O9 con las que trabajamos, cómo se relacionan
> entre sí, y qué sabemos y qué no sabemos de ellos. Si vas a analizar una
> extracción nueva, empieza aquí.

---

## 1 · Quién y qué

El usuario es **demand planner**. Trabaja el forecast de un scope de belleza
(fragancia y color) para el **mercado US**, en la herramienta de planeación **O9**.

Su trabajo es producir cada ciclo el número que se le manda a supply: cuántas
unidades se van a vender de cada código, mes por mes, hacia adelante.

**El fiscal year va de julio a junio.** FY27 = julio 2026 a junio 2027.

---

## 2 · Cómo está organizado el scope

```
House  >  Brand  >  Product Line  >  EAN
```

Y en cruce con eso, el **CFG** (customer group): la agrupación de clientes.
Actualmente hay dos, `P_US_ULTA` y `P_US_ALL_OTHERS`.

- Una **product line** puede existir en uno o en los dos CFG.
- El **EAN** es el nivel más fino (el código de barras del producto individual).
  Las extracciones hasta ahora han sido a nivel product line; a nivel EAN el
  volumen de filas es bastante mayor.

**Convención:** salvo que se pida lo contrario, los análisis van a nivel product
line con los CFG sumados. Se separan por CFG solo cuando el patrón realmente
cambia entre ellos.

---

## 3 · Cómo viene la extracción

Formato largo. Cada fila es una combinación de jerarquía **más una medida**, y las
columnas son meses:

| House | Brand | Product Line | CFG | Data | 2024.M01 | 2024.M02 | … |
|---|---|---|---|---|---|---|---|
| Gucci | Gucci Guilty | Gucci Guilty PH | P_US_ULTA | System FC - Final | 1.200 | 900 | … |
| Gucci | Gucci Guilty | Gucci Guilty PH | P_US_ULTA | Actuals | 1.150 | 880 | … |

Es decir: **una fila por medida**, no una columna por medida. Para analizar hay
que pivotear.

- Los meses vienen como `AAAA.Mnn`.
- Los valores están en **unidades**, no en valor.
- Una celda vacía normalmente significa cero, no "dato faltante" — salvo en las
  medidas que solo existen en el futuro o solo en el pasado (ver abajo).

---

## 4 · Las medidas, una por una

### Las capas del consensus

**El Consensus - Final es la suma de todas las capas de forecast.** Estas son:

#### `System FC - Final`
Lo que calcula el algoritmo estadístico de O9 a partir de la historia.

Es la base del consensus. **Lo que se espera que capture:** nivel base, tendencia
y estacionalidad que se repite. **Lo que NO se espera que capture:** eventos
irrepetibles. Ver la sección 5, que es importante.

#### `Initiative Forecast`
Forecast manual para códigos nuevos, donde el sistema no tiene historia de la
cual aprender. Es la capa de lanzamientos.

#### `Prometheus Fcst Consensus`
Otro tipo de initiative forecast. Funcionalmente parecido al anterior.

> **Ojo:** en la extracción de septiembre 2026 esta capa cargaba cifras brutas
> muy grandes que la capa `Total Demand Assumption` después neteaba hacia abajo,
> en la misma línea y el mismo mes. Se detectaron 98 línea-mes con ese patrón,
> por 3,1M de unidades brutas. **Léelas siempre en neto**, nunca capa por capa,
> o los agregados salen absurdos.

#### `Customer Fcst`
El forecast que carga el cliente directamente.

> En la extracción de septiembre 2026 esta medida estaba **completamente vacía** —
> cero celdas pobladas en las 202 líneas y los 97 meses. No sabemos si es porque
> no se usa en este scope o porque se cayó de la extracción. **Pendiente de
> confirmar.**

#### `Reasonability Adjustment`
Ajustes manuales que hace el equipo de planeación sobre el número del sistema.

#### `Total Demand Assumption`
Insights de mercado y ajustes por eventos que el sistema no puede capturar.
**Esta capa tiene un significado especial — ver la sección 5.**

### Las medidas que NO son capas

#### `EPOS`
Lo que el retailer le vende al **consumidor final** (sell-out).

Es conceptualmente distinto de todo lo demás: es la única señal del dataset que
**no la generamos nosotros con nuestras propias decisiones de embarque**. Todo lo
demás (sell-in, consensus, capas) es consecuencia de lo que nosotros decidimos.

> Cobertura parcial: no todos los retailers reportan. En la extracción de
> septiembre 2026 el EPOS sumaba una mediana de ~52% del sell-in en las líneas
> que sí lo traían, y cubría 140 de 202 líneas. **Úsalo como señal de tendencia y
> de timing, nunca como nivel absoluto contra el sell-in.**
>
> Además va **un mes atrasado** respecto a los actuals.

#### `Actuals`
Lo que realmente embarcamos (sell-in). Lo que le facturamos al cliente.

> **No es lo mismo que demanda.** En un mes con supply cuts, el actual es lo que
> supply nos dejó embarcar, no lo que el cliente pidió. Ver la medida siguiente.

#### `Supply Cuts`
Órdenes que el cliente puso y no pudimos surtir. Es **demanda perdida**.

> **`Actuals + Supply Cuts` es la mejor aproximación a demanda no restringida**
> que hay en este dataset. Si vas a alimentar cualquier modelo o baseline con
> historia, considera usar esa suma en vez de los actuals solos: los actuals
> solos le enseñan al sistema la escasez y la repiten al año siguiente.

#### `Consensus - Final`
El número final. La suma de las capas. **Es lo que se le manda a supply como
compromiso de lo que vamos a vender.**

---

## 5 · Lo que el sistema debe y no debe replicar

Esta es una distinción central y es fácil de pasar por alto.

**El consensus es la suma de las capas, pero no todas las capas representan cosas
que el sistema debería aprender.**

La capa `Total Demand Assumption` (y en menor medida `Reasonability Adjustment`)
carga **excepciones**: una promoción fuerte, una bajada de precio puntual, un
evento de distribución. Son cosas que:

- el System FC **no puede** anticipar, porque no están en la historia como patrón; y
- el System FC **no debe** replicar, porque no se espera que se repitan.

El riesgo concreto: si en septiembre hubo una promo grande, el actual de ese
septiembre sale inflado. El sistema lo aprende y el año siguiente cree que
septiembre es un mes estacionalmente fuerte — cuando en realidad fue un evento de
una sola vez.

**Dos consecuencias prácticas:**

1. **Para juzgar si el System FC es bueno**, hay que neutralizar el efecto de las
   capas de excepción. El System FC no debería ser castigado por no haber
   adivinado una promo que nadie le dijo. Se le juzga contra la parte repetible
   de la demanda, no contra el actual crudo.

2. **Para juzgar si el consensus es bueno**, sí se compara contra el actual crudo
   — porque el consensus es el compromiso completo que se le dio a supply,
   excepciones incluidas.

Son **dos preguntas distintas con dos denominadores distintos**. Confundirlas
lleva a conclusiones equivocadas en las dos direcciones.

**Un uso adicional que vale la pena:** la presencia de `Total Demand Assumption`
en un mes es, de hecho, **una etiqueta gratis de "este mes fue una excepción"**.
Sirve para saber qué meses limpiar de la historia antes de que el motor
estadístico aprenda de ellos, sin tener que reconstruir a mano qué pasó.

---

## 6 · Limitaciones conocidas del dato

### La historia está sobreescrita — esto es lo más importante

En todos los meses cerrados se cumple, celda por celda y al 100%:

```
System FC - Final  =  Consensus - Final  =  Actuals
```

O9 escribe el actual encima del forecast una vez que el mes cierra.

**Consecuencia:** la extracción no guarda memoria de lo que se pronosticó *antes*
de que el mes ocurriera. **MAPE y BIAS no se pueden calcular con este dato**, por
nadie y con ningún esfuerzo. Cualquier cifra de accuracy sacada de aquí estaría
midiendo los actuals contra sí mismos.

**Para poder medir accuracy** hace falta pedir a O9 una extracción distinta: el
`Consensus - Final` **fotografiado con lag** — como estaba a lag-1 (un mes antes
del cierre) y a lag-3 — guardado contra el actual que después ocurrió. Con 24
meses de eso, todo el análisis de accuracy se vuelve posible.

> Mientras tanto hay un arreglo que no cuesta nada y funciona desde hoy: **guardar
> una copia del `Consensus - Final` cada mes antes del cierre.** Un archivo por
> ciclo. En seis meses ya hay con qué medir.

### El consensus no cuadra con la suma de sus capas

Sumando todas las capas extraídas sobre las celdas donde sí existe un consensus,
en la extracción de septiembre 2026 quedaba **un 33% del forward book (6,7M
unidades) sin explicación**.

No sabemos de dónde viene ese remanente. Las dos hipótesis son que falta una capa
en la extracción, o que se están escribiendo números directamente a nivel
consensus saltándose la estructura de capas. **Pendiente de averiguar.** Si
resulta lo segundo, importa: sería un tercio de lo que se le promete a supply sin
dueño ni supuesto declarado.

> Nota de método: al verificar esto, hay que sumar las capas **solo sobre las
> celdas donde el consensus existe**. Si se suman sobre conjuntos de celdas
> distintos, el remanente que sale no significa nada.

### Líneas agrupadoras ("Multiline")

Hay product lines que no son productos sino agrupadores o catch-all. En la
extracción de septiembre 2026, `Gucci Fragrance Multiline (00003484)` sola cargaba
el **37% del volumen** del scope, se movía en bloques (su mes más grande fue 11
veces su propio mes mediano) y casi no registraba EPOS (ratio 0,011).

**Hay que excluirlas de cualquier agregado, promedio o benchmark** y tratarlas
aparte. Si se dejan dentro, dominan todo.

---

## 7 · Reglas de negocio

### Propiedad de las iniciativas

**Una iniciativa no es del usuario hasta que pasa un año entero de envíos.** Antes
de eso el forecast lo lleva otro departamento.

Clasificación por antigüedad del primer envío:

| Primer envío | Clasificación | ¿De quién es? |
|---|---|---|
| Hace menos de 6 meses | Iniciativa - Local | Otro departamento |
| Entre 6 y 12 meses | Iniciativa - Global | Otro departamento |
| Más de 12 meses | Base | Del usuario |

Esto importa para cualquier recomendación: sobre una iniciativa no se dan
consejos de re-pronóstico, se dan consejos de monitoreo y de preparación del
traspaso.

### Salida de licencia de Gucci

**Gucci y Gucci Make up salen de licencia en 2027.M06.** Se deja de embarcar al
cierre del FY27. Son 109 líneas y el 61% del volumen.

Que el forecast de esas líneas termine ahí **es correcto, no es un hueco de
mantenimiento**. No hay que extenderlo ni marcarlo como forecast perdido.

---

## 8 · Lo que se midió en la primera extracción

> Snapshot de la extracción de **septiembre 2026** (historia cerrada hasta
> 2026.M07). Son hallazgos, no definiciones: en una extracción nueva hay que
> volver a calcularlos, no darlos por ciertos.

- 5 houses, 26 brands, 202 product lines (excluyendo la Multiline), 2 CFG.
- 12,26M unidades en los últimos 12 meses cerrados. Forward book de 20,16M.
- **Estacionalidad de sell-in:** picos en marzo (127), junio (134) y septiembre
  (128); piso en noviembre y diciembre (77). Son cierres de trimestre, no demanda
  del consumidor.
- **Estacionalidad de EPOS:** diciembre indexa 269. El consumidor compra en
  Navidad; nosotros embarcamos en el cierre de trimestre.
- **El sell-in se adelanta al EPOS unos 3 meses** (moda de 3 en 125 líneas,
  r = +0,62 a nivel agregado). Lo que el consumidor compra en diciembre se decidió
  con lo que se embarcó en septiembre.
- **Lanzamientos:** el mes 0 es 2,7x un mes promedio del año 1 y carga el 22% del
  año; los meses 0-2 cargan el 46%. El 52% de los lanzamientos nunca supera su
  primer mes. El steady state queda en ~21% del mes de lanzamiento.
- **Los supply cuts en un lanzamiento** son ~1% en los meses 0-2 y saltan a 10%,
  10%, 9% y 15% en los meses 3 a 6 — justo cuando el consumidor empieza a comprar.
- **Demanda perdida por cuts:** 3,1% (2023) → 4,4% (2024) → **11,9% (2025)** →
  8,7% (2026 parcial). Muy concentrada en dos houses.
- **Solo 5 de 202 líneas** son estables y repetibles (7% del volumen). El 43% del
  volumen está en códigos que el sistema no pronostica bien.
- **`Reasonability Adjustment` es negativo el 70% de las veces.** Es el equipo
  corrigiendo el sistema hacia abajo, ciclo tras ciclo.

### Sobre usar "el año pasado" como base

Se hizo un backtest de 18 meses (2025.M02–2026.M07) comparando bases candidatas
contra lo que realmente ocurrió, a nivel product line × mes:

| Base | WMAPE | BIAS |
|---|---|---|
| Mismo mes del año pasado | 108,3% | +13,3% |
| Año pasado × factor de crecimiento perfecto, por línea | 94,5% | −9,6% |
| Promedio de los últimos 6 meses | 67,5% | −2,2% |
| Promedio de los últimos 3 meses | 67,9% | −3,4% |

El promedio simple de los últimos 3 meses le gana al año pasado por ~40 puntos de
WMAPE, y le gana **en todas las bandas y en todos los arquetipos**, incluso en las
líneas clasificadas como estables y repetibles. Corregir el año pasado por
crecimiento casi no ayuda: **el error no está en el nivel, está en la forma** —
el mes en que cae el volumen no se repite.

> Advertencia al leer esto: un WMAPE de 67% es malo en términos absolutos. El
> punto no es "usa el promedio de 3 meses", es que **el año pasado pierde contra
> la alternativa más trivial que existe**. El forecast real debería ganarle a las
> dos, y eso no se puede comprobar por el overwrite.

---

## 9 · Preguntas abiertas

Cosas que no sabemos y que el usuario va a averiguar:

1. **¿De dónde viene el 33% del forward book que no cuadra con las capas?**
   ¿Falta una capa en la extracción, o se escriben números directo a nivel
   consensus?
2. **¿`Customer Fcst` está vacía porque no se usa, o porque se cayó de la
   extracción?**
3. **¿Se puede obtener el extract con fotos a lag-1 y lag-3?** Es lo que
   desbloquea toda la medición de accuracy.
4. **¿Cuál es la cobertura real del EPOS?** Saber qué retailers reportan
   permitiría leer los ratios como niveles y no solo como tendencias.
5. **¿Cuántos EANs son en total?** Define si el análisis a ese nivel es viable
   igual que a nivel product line o necesita otro enfoque.

---

## 10 · Convenciones para analizar

- **Cortar la historia en el último mes completamente cerrado.** El mes en curso y
  el anterior suelen estar facturando todavía y se ven artificialmente bajos.
- **Excluir las líneas agrupadoras** de todo agregado y reportarlas aparte.
- **Sumar los CFG** salvo que la pregunta sea específicamente sobre ellos.
- **Usar `Actuals + Supply Cuts`** cuando lo que interesa es demanda, y `Actuals`
  solos cuando lo que interesa es lo que efectivamente se embarcó.
- **Nunca reportar accuracy** a partir de una extracción sin fotos con lag.
- **Índice estacional:** calcularlo por año calendario y luego promediar los años,
  para que un año grande no domine la forma. Base 100 = mes promedio del propio
  año. Solo con años completos.
- **Definición de lanzamiento:** primer actual dentro de la historia disponible,
  descartando el primer mes del dataset (ahí se acumulan todas las líneas que ya
  existían, y no son lanzamientos).

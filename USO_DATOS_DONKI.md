# Uso de los datos de DONKI en el juego de la base lunar

Este documento explica cómo leer `eventos_juego.json` y cómo ir sacando eventos para que el robot de la base lunar los anuncie.

El JSON solo contiene eventos que **llegan a la Luna**. Como la Luna no tiene campo magnético ni atmósfera, la radiación y el plasma del Sol golpean la base directamente. Todo el contenido del JSON está en inglés.

## 1. Archivos

| Archivo | Qué contiene |
|---|---|
| `eventos_juego.json` | **Lo que lee el juego**: 518 eventos reales, ya curados, con el diálogo del robot, la radiación, el apagón y el tiempo de llegada |
| `donki_data/*.json` | Datos crudos de DONKI (NASA), del 14-nov-2025 al 14-nov-2026. Un archivo por tipo de evento |
| `scripts/fetch_donki.py` | Descarga los datos crudos |
| `scripts/build_game_events.py` | Genera `eventos_juego.json`. Aquí se ajustan los filtros, los textos y las reglas |

Para regenerar todo:

```bash
python -I scripts/fetch_donki.py donki_data
python -I scripts/build_game_events.py donki_data eventos_juego.json
```

Fuente: NASA CCMC DONKI, `https://ccmc.gsfc.nasa.gov/DONKI/WS/get/{TIPO}`

## 2. Tipos de evento

| `type` | Nombre | Eventos | Qué le hace a la base lunar |
|---|---|---|---|
| `FLR` | Solar Flare (llamarada) | 301 | Destello de rayos X. Llega en ~8 minutos. Radiación baja (5 a 15 puntos). Suele ser el **primer aviso** de algo peor |
| `CME` | Coronal Mass Ejection | 147 | Nube de plasma que tarda 1 a 5 días en llegar. Si pega de frente a ≥ 700 km/s, **provoca un apagón** (52 casos) |
| `SEP` | Solar Energetic Particle Event | 6 | Tormenta de protones: **la más peligrosa para la salud** (25 a 60 puntos). Las de > 100 MeV también causan apagón (2 casos) |
| `IPS` | Interplanetary Shock | 16 | Onda de choque en el viento solar. Radiación leve (5) |
| `HSS` | High Speed Solar Wind Stream | 48 | Viento solar rápido. Sin radiación. Carga el polvo lunar, que se pega a los paneles |

Solo se incluyen las llamaradas M y X, las CME que apuntan a la Tierra y la Luna, y lo que midieron los satélites cercanos a la Tierra. Los fenómenos que solo ocurren dentro del campo magnético de la Tierra (tormentas geomagnéticas y cinturones de radiación) no afectan a la Luna, así que no están.

## 3. Estructura de `eventos_juego.json`

```json
{
 "fields": { ... },           // descripción de cada campo (en inglés)
 "radiation_scale": { ... },  // cómo se calcularon los puntos de radiación
 "blackout_rules": { ... },   // qué eventos causan apagón y por qué
 "summary": { ... },          // conteos
 "chains": {                  // cadenas: lista de ids en orden
   "chain-001": ["2025-11-14T07:44:00-FLR-001", "2025-11-14T08:00:00-CME-001", "2025-11-14T09:20:00-SEP-001"],
   ...
 },
 "events": [ ... ]            // los 518 eventos, ordenados por fecha
}
```

### Cada evento

```json
{
 "id": "2026-07-30T18:25:00-SEP-001",
 "type": "SEP",
 "name": "Solar Energetic Particle Event",
 "date": "2026-07-30T18:20Z",
 "dialog": [
  "NOAA's GOES weather satellite and the NASA/ESA SOHO observatory have detected a storm of solar protons with energies above 100 MeV (based on a real event recorded in NASA's DONKI database on July 30, 2026).",
  "A solar energetic particle event is a storm of tiny pieces of atoms, mostly protons, ..."
 ],
 "radiation_points": 60,
 "blackout": true,
 "arrival_minutes": 147,
 "arrival_source": "observed: minutes after its flare/CME began",
 "data": { "max_energy_mev": 100.0, "instruments": ["GOES-P: SEISS >100 MeV", "..."] },
 "link": "https://ccmc.gsfc.nasa.gov/DONKI/view/SEP/47873/-1",
 "chain": { "id": "chain-050", "step": 3, "length": 3 }
}
```

| Campo | Para qué sirve en el juego |
|---|---|
| `dialog` | El arreglo de la caja de diálogo del robot. `[0]` dice quién detectó qué, basado en el evento real y su fecha. `[1]` explica el tipo de evento. Es el mismo texto para todos los eventos del mismo tipo |
| `radiation_points` | Radiación que el evento añade al ambiente, en una escala de juego de 0 a 100. Es 0 si el evento no genera radiación |
| `blackout` | `true` si el evento puede dejar sin energía a la base |
| `arrival_minutes` | Minutos desde el aviso del robot hasta que el evento llega a la base. Es el tiempo que tiene el jugador para prepararse |
| `chain` | `null` si el evento va solo. Si no, indica a qué cadena pertenece y en qué paso va |
| `name` | Nombre del tipo de evento en inglés, útil para títulos o la interfaz |
| `date`, `link`, `data`, `arrival_source` | Referencia: fecha real (UTC), ficha oficial de la NASA, valores originales y de dónde salió el tiempo de llegada. El juego no los necesita |

### Escalas usadas

- **Radiación.** DONKI no mide dosis, así que los puntos salen de lo que sí mide:
  - FLR: según la clase. M1 = 5, X1 = 10, X10 = 15.
  - SEP: según la energía de los protones. > 10 MeV = 25, ~30 MeV = 40, > 100 MeV = 60.
  - CME de impacto directo: 5. Rozón: 0.
  - IPS: 5. HSS: 0.
- **Apagón.** CME de impacto directo a ≥ 700 km/s (el plasma carga eléctricamente la base y las descargas tumban el sistema eléctrico) y SEP de > 100 MeV (fallas en la electrónica).
- **Tiempo de llegada.** Según el caso, es el tiempo real medido, el pronóstico del modelo de la NASA o un estimado. `arrival_source` dice cuál.
  - FLR: de 8 minutos a 1 hora (hasta su pico).
  - SEP: de 40 minutos a 5 horas.
  - CME: de 1 a 5 días.
  - IPS y HSS: unos 2 a 3 días.

## 4. Cadenas de eventos

En el Sol, un evento suele desencadenar otros. DONKI registra esas relaciones y el JSON las agrupa en `chains`. Hay **58 cadenas** y 396 eventos sueltos:

| Cadena | Cuántas | Qué significa |
|---|---|---|
| FLR → CME | 39 | La llamarada avisa, y días después llega la nube de plasma |
| IPS ↔ HSS | 13 | Choque y viento rápido que llegan juntos |
| FLR → CME → SEP | 3 | El "triple golpe": destello, tormenta de radiación y, días después, la CME |
| Otras (FLR → SEP, FLR + FLR → CME, FLR → CME → SEP → FLR) | 3 | Variantes de las anteriores |

Ejemplo real del 14-nov-2025 (`chain-001`):

1. **FLR** X4.0: 13 puntos de radiación, llega a su pico en 46 minutos.
2. **CME** a 1082 km/s: impacto directo, **apagón**, llega en 2492 minutos (~1.7 días).
3. **SEP** de > 15.8 MeV: 25 puntos de radiación, llega en 96 minutos.

Los pasos están ordenados por **cuándo se detectan**, no por cuándo llegan. En el ejemplo, la CME se anuncia antes que la SEP, pero llega mucho después. El jugador tiene que decidir qué atender primero.

## 5. Algoritmo para sacar eventos

### Estado

- `pool`: los eventos que todavía no salieron. Al inicio, todos.
- `queue`: una cola con los eventos pendientes de la cadena actual. Al inicio, vacía.

### `nextEvent(tipoDeseado)`

1. **Si la cola tiene eventos**, saca el primero y devuélvelo. Las cadenas siempre se terminan antes de sortear otro evento.
2. **Elige el tipo.**
   - Si el juego necesita un tipo concreto (por ejemplo, `SEP` para un nivel de radiación), usa `tipoDeseado`.
   - Si no, **sortea el tipo primero** con los pesos de la tabla de abajo.
3. **Filtra** el `pool` para quedarte con los eventos de ese tipo.
4. **Si no quedan eventos de ese tipo**, vuelve a meter en el `pool` todos los de ese tipo (se repiten) y filtra otra vez.
5. **Elige uno al azar** entre los candidatos.
6. **Si el evento tiene `chain`:**
   - Mete en la cola todos los eventos de `chains[chain.id]` que sigan en el `pool`, en orden de `step`.
   - Quítalos todos del `pool`.
   - Saca el primero de la cola y devuélvelo.

   La cadena siempre empieza en el paso 1. Si pediste una `CME` y su cadena empieza con una `FLR`, primero sale la llamarada y luego la CME.
7. **Si no tiene cadena**, quítalo del `pool` y devuélvelo.

### Por qué sortear el tipo primero

Las llamaradas son el 58 % de los eventos. Si eliges al azar entre todos los eventos, el jugador vería casi solo llamaradas y casi nunca una tormenta de radiación. Al sortear primero el tipo, controlas cuánto aparece cada uno.

Pesos sugeridos para empezar (se ajustan jugando):

| Tipo | Peso | Motivo |
|---|---|---|
| FLR | 30 | Común y casi siempre es el inicio de una cadena |
| CME | 30 | Es la fuente principal de apagones |
| HSS | 15 | Evento leve, sirve para el minijuego de limpiar paneles |
| IPS | 10 | Leve |
| SEP | 15 | Solo hay 6, así que se repetirán. Es el evento más peligroso; no conviene que sea muy frecuente |

### Pseudocódigo

```
pool  = copy(json.events)
queue = []

function nextEvent(tipoDeseado = null):
    if queue is not empty:
        return queue.popFront()

    tipo = tipoDeseado ?? weightedRandom(PESOS)
    candidatos = pool.filter(e => e.type == tipo)
    if candidatos is empty:
        pool.addAll(json.events.filter(e => e.type == tipo))   // se repiten
        candidatos = pool.filter(e => e.type == tipo)

    e = randomChoice(candidatos)

    if e.chain == null:
        pool.remove(e)
        return e

    for id in json.chains[e.chain.id]:          // ya vienen en orden de step
        ev = pool.findById(id)
        if ev != null:
            queue.pushBack(ev)
            pool.remove(ev)
    return queue.popFront()
```

## 6. Cómo conectar los campos con las decisiones del jugador

El jugador decide entre priorizar **energía** o **salud**. Cada campo del evento indica qué acciones tienen sentido:

| Si el evento trae... | Acción de **energía** | Acción de **salud** |
|---|---|---|
| `blackout: true` | Activar las baterías de repuesto **antes** de que pasen los `arrival_minutes` | – |
| `radiation_points > 0` | – | Evitar las zonas sin protección; minijuego de mover objetos para hacer un escudo; arreglar el panel electrolítico |
| `type` `SEP` o `HSS` (paneles degradados o cubiertos de polvo) | Limpiar y reemplazar el panel solar (minijuego) | – |

`arrival_minutes` es el reloj de cuenta regresiva. Los rangos reales van de 8 minutos a 5 días, así que conviene comprimirlos. Por ejemplo, 1 minuto real puede equivaler a 1 segundo de juego, con un tope de unos 2 minutos de juego para las CME. Lo importante es conservar el orden: una llamarada llega casi de inmediato y una CME da tiempo para prepararse.

## 7. Limitaciones

- **DONKI mide cerca de la Tierra, no en la Luna.** Suponemos que la Luna recibe lo mismo, porque a escala solar está muy cerca (~384,000 km).
- **Los puntos de radiación y las reglas de apagón son de diseño.** Salen de datos reales (clase de la llamarada, energía de los protones, velocidad de la CME), pero no son una dosis física.
- **Los datos se revisan con el tiempo.** DONKI corrige y añade eventos días después, así que los conteos pueden variar un poco si se vuelven a descargar.
- **2025-2026 es un periodo muy activo**, cerca del máximo solar. DONKI tiene datos desde 2010 por si se quiere un año más tranquilo.

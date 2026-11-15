# Uso de los datos de DONKI en el juego de la base lunar

Este documento explica cómo leer `eventos_juego.json`. El juego recorre los eventos de 2024 en orden, desde enero: la actividad del Sol crece sola hasta la tormenta de mayo, y eso da la curva de dificultad.

El JSON solo contiene eventos que **llegan a la Luna**. Como la Luna no tiene campo magnético ni atmósfera, la radiación y el plasma del Sol golpean la base directamente. Todo el contenido del JSON está en inglés.

## 1. Archivos

| Archivo | Qué contiene |
|---|---|
| `eventos_juego.json` | **Lo que lee el juego**: 1297 eventos reales, ya curados, con el diálogo del robot, la radiación, el apagón y el tiempo de llegada |
| `donki_data/*.json` | Datos crudos de DONKI (NASA), del 1-ene-2024 al 31-dic-2024. Un archivo por tipo de evento |
| `scripts/fetch_donki.py` | Descarga los datos crudos |
| `scripts/build_game_events.py` | Genera `eventos_juego.json`. Aquí se ajustan los filtros, los textos y las reglas |

Para regenerar todo:

```bash
python -I scripts/fetch_donki.py donki_data 2024-01-01 2024-12-31
python -I scripts/build_game_events.py donki_data eventos_juego.json "2024-01-01 to 2024-12-31"
```

Fuente: NASA CCMC DONKI, `https://ccmc.gsfc.nasa.gov/DONKI/WS/get/{TIPO}`

## 2. Tipos de evento

| `type` | Nombre | Eventos | Qué le hace a la base lunar |
|---|---|---|---|
| `FLR` | Solar Flare (llamarada) | 1036 | Destello de rayos X. Llega en ~8 minutos. Radiación baja (5 a 15 puntos). Suele ser el **primer aviso** de algo peor |
| `CME` | Coronal Mass Ejection | 179 | Nube de plasma que tarda 1.5 a 5 días en llegar. Si pega de frente a ≥ 700 km/s, **provoca un apagón** (79 casos) |
| `SEP` | Solar Energetic Particle Event | 25 | Tormenta de protones: **la más peligrosa para la salud** (25 a 60 puntos). Las de > 100 MeV también causan apagón (6 casos) |
| `IPS` | Interplanetary Shock | 29 | Onda de choque en el viento solar. Radiación leve (5) |
| `HSS` | High Speed Solar Wind Stream | 28 | Viento solar rápido. Sin radiación. Carga el polvo lunar, que se pega a los paneles |

Solo se incluyen las llamaradas M y X, las CME que apuntan a la Tierra y la Luna, y lo que midieron los satélites cercanos a la Tierra. Los fenómenos que solo ocurren dentro del campo magnético de la Tierra (tormentas geomagnéticas y cinturones de radiación) no afectan a la Luna, así que no están.

## 3. Estructura de `eventos_juego.json`

```json
{
 "fields": { ... },           // descripción de cada campo (en inglés)
 "radiation_scale": { ... },  // cómo se calcularon los puntos de radiación
 "blackout_rules": { ... },   // qué eventos causan apagón y por qué
 "summary": { ... },          // conteos
 "explanations": {            // una analogía corta por tipo, para la primera vez que aparece
   "SEP": "These particles are tiny bits of atoms, faster than anything people have ever built. ...",
   ...
 },
 "chains": {                  // cadenas: lista de ids en orden
   "chain-001": ["2024-01-20T09:24:00-CME-001", "2024-01-21T00:36:00-CME-001", "2024-01-22T06:09:00-FLR-001", "2024-01-22T13:00:00-SEP-001"],
   ...
 },
 "events": [ ... ]            // los 1297 eventos, ordenados por fecha
}
```

### Cada evento

```json
{
 "id": "2024-05-11T02:10:00-SEP-001",
 "type": "SEP",
 "name": "Solar Energetic Particle Event",
 "date": "2024-05-11T02:10Z",
 "dialog": [
  "Real NASA data! On May 11, 2024, NOAA's GOES weather satellite detected a super strong storm of tiny particles shooting out of the Sun.",
  "It is so strong it can break machines! Stay inside, keep away from radiation zones and check the oxygen machine."
 ],
 "radiation_points": 60,
 "blackout": true,
 "arrival_minutes": 60,
 "arrival_source": "observed: minutes after its flare/CME began",
 "data": { "max_energy_mev": 100.0, "instruments": ["GOES-P: SEISS >100 MeV"] },
 "link": "https://ccmc.gsfc.nasa.gov/DONKI/view/SEP/30714/-1",
 "chain": { "id": "chain-025", "step": 3, "length": 3 }
}
```

| Campo | Para qué sirve en el juego |
|---|---|
| `dialog` | Lo que dice el robot. `[0]` es la alerta real: fecha, quién lo vio y una comparación (por ejemplo, cuánto tardaría la CME en cruzar la Tierra). `[1]` es qué hacer en la base. Los textos son para niños de 6 a 12 años: cortos y sin palabras técnicas |
| `explanations` (arriba, no en cada evento) | Una analogía por tipo de evento ("una llamarada es como el flash de una cámara gigante"). Se dice solo la primera vez que aparece ese tipo, entre `dialog[0]` y `dialog[1]` |
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
  - FLR: de 8 minutos a 2.5 horas (hasta su pico); casi siempre unos 10 minutos.
  - SEP: de 1 hora a 2.5 días; casi siempre unas 4 horas.
  - CME: de 1.5 a 5 días.
  - IPS y HSS: unos 2 a 3 días.

## 4. Cadenas de eventos

En el Sol, un evento suele desencadenar otros. DONKI registra esas relaciones y el JSON las agrupa en `chains`. Hay **84 cadenas** y 1088 eventos sueltos:

| Cadena | Cuántas | Qué significa |
|---|---|---|
| FLR → CME | 55 | La llamarada avisa, y días después llega la nube de plasma |
| IPS ↔ HSS | 7 | Choque y viento rápido que llegan juntos |
| FLR → CME → SEP | 6 | El "triple golpe": destello, tormenta de radiación y, días después, la CME |
| Otras (FLR → SEP, FLR + FLR → CME, FLR → CME → CME, ...) | 16 | Variantes de las anteriores. La más larga es `chain-024`: la tormenta Gannon del 8 al 10 de mayo, con 16 eventos seguidos |

Ejemplo real del 11-may-2024 (`chain-025`):

1. **FLR** X5.8: 14 puntos de radiación, llega a su pico en 13 minutos.
2. **CME** a 1263 km/s: impacto directo, **apagón**, llega en 3083 minutos (~2.1 días).
3. **SEP** de > 100 MeV: 60 puntos de radiación y **apagón**, llega en 60 minutos.

Los pasos están ordenados por **cuándo se detectan**, no por cuándo llegan. En el ejemplo, la CME se anuncia antes que la SEP, pero llega mucho después. El jugador tiene que decidir qué atender primero.

## 5. Cómo conectar los campos con las decisiones del jugador

El jugador decide entre priorizar **energía** o **salud**. Cada campo del evento indica qué acciones tienen sentido:

| Si el evento trae... | Acción de **energía** | Acción de **salud** |
|---|---|---|
| `blackout: true` | Activar las baterías de repuesto **antes** de que pasen los `arrival_minutes` | – |
| `radiation_points > 0` | – | Evitar las zonas sin protección; minijuego de mover objetos para hacer un escudo; arreglar el panel electrolítico |
| `type` `SEP` o `HSS` (paneles degradados o cubiertos de polvo) | Limpiar y reemplazar el panel solar (minijuego) | – |

`arrival_minutes` es el reloj de cuenta regresiva. Los rangos reales van de 8 minutos a 5 días, así que conviene comprimirlos. Por ejemplo, 1 minuto real puede equivaler a 1 segundo de juego, con un tope de unos 2 minutos de juego para las CME. Lo importante es conservar el orden: una llamarada llega casi de inmediato y una CME da tiempo para prepararse.

## 6. Limitaciones

- **DONKI mide cerca de la Tierra, no en la Luna.** Suponemos que la Luna recibe lo mismo, porque a escala solar está muy cerca (~384,000 km).
- **Los puntos de radiación y las reglas de apagón son de diseño.** Salen de datos reales (clase de la llamarada, energía de los protones, velocidad de la CME), pero no son una dosis física.
- **Los datos se revisan con el tiempo.** DONKI corrige y añade eventos días después, así que los conteos pueden variar un poco si se vuelven a descargar.
- **2024 es uno de los años más activos del ciclo solar actual**: incluye la tormenta Gannon (mayo) y la llamarada X9.0 de octubre. Se eligió porque alimenta todas las misiones: 25 tormentas de radiación (contra 6 de nov-2025 a nov-2026) y 85 apagones. DONKI tiene datos desde 2010 por si se quiere un año más tranquilo.

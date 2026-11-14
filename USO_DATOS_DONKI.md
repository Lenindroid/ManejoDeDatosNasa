# Uso de los datos de DONKI en el juego de la base lunar

Este documento explica qué datos de DONKI usamos, cómo los filtramos y cómo los traducimos en eventos que afectan los **dos stats del juego: Energía y Salud**.

## 1. Archivos

| Archivo | Qué contiene |
|---|---|
| `donki_data/*.json` | Datos crudos de DONKI, sin modificar (14-nov-2025 a 14-nov-2026), un archivo por tipo de evento |
| `eventos_juego.json` | **Los eventos útiles para el juego**, filtrados, con severidad y efecto sobre cada stat |
| `scripts/fetch_donki.py` | Descarga los datos crudos (en tramos de 60 días, el máximo que permite la API) |
| `scripts/build_game_events.py` | Genera `eventos_juego.json`. Aquí se ajustan los filtros, la severidad y los efectos. |
| `IDEAS_STATS_DONKI.md` | Lluvia de ideas de stats que se usó para elegir Energía y Salud |

Para regenerar todo (por ejemplo, con otro periodo):

```bash
python -I scripts/fetch_donki.py donki_data
python -I scripts/build_game_events.py donki_data eventos_juego.json
```

Fuente: `https://ccmc.gsfc.nasa.gov/DONKI/WS/get/{TIPO}?startDate=AAAA-MM-DD&endDate=AAAA-MM-DD`

## 2. Stats del juego

| Stat | Clave en el JSON | Qué representa | Qué lo afecta en DONKI |
|---|---|---|---|
| ⚡ **Energía** | `energia` | Producción eléctrica de la base (paneles solares y sistemas) | Llamaradas (FLR), eyecciones de masa coronal (CME), choques (IPS), viento solar rápido (HSS) y tormentas de partículas extremas (SEP) |
| ❤️ **Salud** | `salud` | Salud de la tripulación frente a la radiación | Tormentas de partículas (SEP) y llamaradas de clase X |

Los dos stats están ligados a lo que DONKI realmente mide. Como la Luna **no tiene campo magnético ni atmósfera**, la radiación y el plasma solar golpean la base directamente.

## 3. Qué eventos conservamos y por qué

| Tipo | Nombre | Filtro aplicado | Eventos | Stat que afecta |
|---|---|---|---|---|
| FLR | Llamarada solar | Solo clases **M y X** (se descartan C y B) | 301 | Energía; las de clase X también afectan la Salud |
| CME | Eyección de masa coronal | Solo las que **llegan a la Tierra-Luna** según el modelo WSA-ENLIL, o las de velocidad ≥ 1000 km/s | 198 | Energía |
| SEP | Partículas energéticas solares | Todas | 42 (13 días distintos) | Salud; las extremas (severidad 5) también afectan la Energía |
| IPS | Choque interplanetario | Solo los medidos en `location = "Earth"` | 67 | Energía |
| HSS | Corriente rápida de viento solar | Todas | 75 | Energía (efecto leve) |

**Excluidos:** GST (tormentas geomagnéticas), RBE (aumentos en los cinturones de radiación) y MPC (cruces de la magnetopausa). Son fenómenos del campo magnético de la **Tierra** y solo encajaban con un stat de comunicaciones, que ya no usamos.

**Total: 683 eventos en un año.**
- **Energía:** 657 eventos. Hay de sobra, todos los meses (entre 13 y 113).
- **Salud:** 58 eventos (42 SEP y 16 llamaradas X), repartidos en **24 días distintos**. Son pocos pero muy peligrosos. En octubre y noviembre de 2026 no hay ninguno.

## 4. Estructura de cada evento en `eventos_juego.json`

```json
{
 "id": "2026-02-01T23:44:00-FLR-001",
 "tipo": "FLR",
 "fecha": "2026-02-01T23:57Z",
 "severidad": 5,
 "recursos_afectados": ["energia", "salud"],
 "efectos": { "energia": -50, "salud": -30 },
 "datos": { "clase": "X8.1", "inicio": "2026-02-01T23:44Z", "fin": "2026-02-02T00:04Z", "region": "N13E35" },
 "eventos_vinculados": ["2026-02-02T00:48:00-CME-001"],
 "link": "https://ccmc.gsfc.nasa.gov/DONKI/view/FLR/44361/-1"
}
```

- `fecha`: hora UTC del evento. Para las FLR es la hora del pico.
- `efectos`: cuánto cambia cada stat (ver sección 5).
- `datos`: los valores originales de DONKI que usamos para calcular la severidad.
- `eventos_vinculados`: relaciones causa-efecto registradas por los científicos de DONKI (ver sección 6).
- `link`: ficha oficial del evento, para verificarlo.

El archivo también incluye `resumen`, con conteos por tipo, stat, severidad y mes, y `efecto_por_severidad`, con la tabla de efectos.

## 5. Severidad (1 a 5) y efectos

### Cómo se calcula la severidad

| Tipo | Dato de DONKI | 1 menor | 2 moderado | 3 fuerte | 4 severo | 5 extremo |
|---|---|---|---|---|---|---|
| FLR | `classType` | – | M1–M4.9 | M5–M9.9 | X1–X4.9 | ≥ X5 |
| CME | `speed` (km/s) + si llega a la Tierra-Luna | <500 | 500–699 | 700–999 | ≥1000 | ≥1500 (las que llegan suben +1 nivel) |
| SEP | instrumentos que la detectan | – | – | – | detectada | >10 MeV en GOES o 100 MeV |
| IPS | – | – | siempre 2 | – | – | – |
| HSS | – | siempre 1 | – | – | – | – |

### Efecto sobre los stats

Son valores iniciales para balancear jugando.

| Severidad | ⚡ Energía (% de producción perdida mientras dura el evento) | ❤️ Salud (puntos perdidos si la tripulación está expuesta) |
|---|---|---|
| 1 | −5 % | −1 |
| 2 | −10 % | −3 |
| 3 | −20 % | −8 |
| 4 | −35 % | −15 |
| 5 | −50 % | −30 |

Cada evento aplica estos efectos **solo a los stats de `recursos_afectados`**:

| Evento | Severidad | Energía | Salud |
|---|---|---|---|
| FLR clase M | 2–3 | ✅ | – |
| FLR clase X | 4–5 | ✅ | ✅ |
| CME, IPS, HSS | 1–5 | ✅ | – |
| SEP | 4 | – | ✅ |
| SEP extrema | 5 | ✅ (degrada paneles) | ✅ |

## 6. Cadenas de eventos y decisiones

En el Sol, los eventos ocurren en secuencia. El campo `eventos_vinculados` registra esa secuencia, y eso le da al jugador **tiempo para reaccionar**:

```
FLR (llamarada)  →  SEP (partículas, minutos u horas después)          → ❤️ Salud
      ↓
CME (eyección)   →  IPS (el choque llega 1 a 3 días después, ver "llegada_estimada")  → ⚡ Energía
```

Ejemplo real del 14-nov-2025: llamarada FLR → CME a 1082 km/s → 6 registros SEP ese mismo día → choques IPS el 15 y 16 de noviembre.

### La decisión central: Energía contra Salud

Los dos stats compiten entre sí. Eso genera el dilema principal del juego:

| Acción del jugador | ⚡ Energía | ❤️ Salud |
|---|---|---|
| **Mandar a la tripulación al refugio** | Se detiene el mantenimiento y la producción baja | Se evita (o se reduce mucho) el daño por radiación |
| **Seguir trabajando** | La producción se mantiene y se pueden hacer reparaciones | Se recibe el daño completo de la SEP o la llamarada |
| **Apagar sistemas como protección** antes del impacto de una CME | Se pierde producción ahora, pero el daño es menor | – |

Propuesta de flujo de juego:

1. **Alerta**: llega una llamarada de clase X. Se avisa al jugador: "Llamarada X detectada, posible tormenta de partículas".
2. **Decisión inmediata**: ¿refugio o seguir trabajando?
3. **Pronóstico**: aparece la CME con `llegada_estimada`. El jugador tiene "N turnos" para prepararse: guardar energía o apagar sistemas.
4. **Impacto**: cuando llega la IPS o la CME, se aplican los efectos a la Energía.

## 7. Escala de tiempo y balance

- **Comprimir el tiempo**: 1 día real equivale a 1 turno. Los eventos de severidad 1 y 2 del mismo día se agrupan en uno solo.
- **Elegir un periodo**: por ejemplo, febrero de 2026 (113 eventos, 6 llamaradas X) para un nivel difícil, y octubre de 2026 (35 eventos y ninguno de Salud) para un nivel tranquilo o tutorial.
- **Agrupar las SEP**: hay 42 registros SEP pero solo 13 días distintos, porque varios instrumentos registran la misma tormenta. Conviene agruparlas por día o por `eventos_vinculados`; si no, la salud bajaría varias veces por la misma tormenta.
- **Recuperación de la salud**: como los eventos de Salud son escasos (24 días al año), conviene que la salud no se recupere sola o lo haga muy lento. Así cada tormenta de radiación deja una consecuencia duradera.

## 8. Limitaciones

- **DONKI mide la Tierra, no la Luna.** Suponemos que la Luna recibe lo mismo, porque está a ~384,000 km, muy cerca en escala solar.
- **Los datos se revisan con el tiempo.** Los científicos de DONKI corrigen y añaden eventos días después de que ocurren, así que los conteos pueden variar un poco si se vuelven a descargar.
- **Los efectos son de diseño, no científicos.** Las severidades salen de datos reales, pero los valores de la sección 5 son una propuesta de juego.
- **2025-2026 es un periodo muy activo** porque está cerca del máximo solar. DONKI tiene datos desde 2010, por si queremos años más tranquilos (2018-2020, mínimo solar).

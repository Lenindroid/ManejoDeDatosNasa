# Ideas de stats basados en DONKI

> **Decisión final:** nos quedamos con **Energía** y **Salud** (dosis de radiación de la tripulación). Este documento queda como registro de las opciones que se consideraron. La implementación está en [`USO_DATOS_DONKI.md`](USO_DATOS_DONKI.md).

DONKI mide tres cosas: **radiación**, **plasma/partículas** y **perturbaciones electromagnéticas**. Por eso los stats que mejor encajan son los de **salud, blindaje, electrónica, energía y comunicaciones**, y no los de comida, agua u oxígeno.

Los datos y filtros de los eventos están en [`USO_DATOS_DONKI.md`](USO_DATOS_DONKI.md) y [`eventos_juego.json`](eventos_juego.json).

## Ideas de stats

| # | Stat | Qué representa | Eventos DONKI que lo afectan (y el dato que se usa) | Decisión que genera |
|---|---|---|---|---|
| 1 | **Dosis de radiación de la tripulación** | Radiación acumulada por los astronautas; si pasa un límite, se enferman o mueren | **SEP** (sobre todo >10 MeV y >100 MeV), **FLR** de clase X (`classType`) | ¿Refugiarse y parar la producción, o seguir trabajando expuestos? |
| 2 | **Integridad del blindaje** | Estado de las protecciones de la base | **SEP**, **CME** (`speed`, `llegada_estimada`) | Gastar materiales en reforzar el blindaje antes de un impacto |
| 3 | **Eficiencia de los paneles solares** | Producción eléctrica máxima, que se degrada de forma **permanente** | **SEP** y **CME** fuertes | Reemplazar o limpiar paneles, o aceptar menos energía para siempre |
| 4 | **Energía almacenada (baterías)** | Reserva para sobrevivir a los apagones | **FLR**, **IPS** (llegada del choque), **HSS** | Cargar baterías cuando llega un aviso de CME |
| 5 | **Integridad de la electrónica** | Fallas en las computadoras y el soporte vital por partículas | **SEP**, **FLR** X/M | Apagar sistemas no esenciales como protección, o arriesgarse |
| 6 | **Comunicación con la Tierra** | Calidad del enlace de radio y datos | **FLR** (apagón de radio en minutos), **GST** (`Kp`), **RBE**, **MPC** | Enviar datos o pedir ayuda antes de que se corte el enlace |
| 7 | **Reabastecimiento / logística** | Probabilidad de que lleguen las naves de carga a tiempo | **GST** (`Kp` ≥ 7 retrasa lanzamientos), **CME** que se dirigen a la Tierra | Racionar recursos y reprogramar envíos |
| 8 | **Ventana de actividad exterior (EVA)** | Horas seguras para salir a la superficie, minar o reparar | Se cierra con **SEP** y **CME** en camino; se reabre cuando terminan | Apurar reparaciones antes del impacto |
| 9 | **Carga eléctrica de la superficie / polvo** | El plasma carga el regolito, que se pega a todo y causa descargas | **HSS**, **IPS**, **CME** | Proteger equipos exteriores o aceptar desgaste |
| 10 | **Capacidad de alerta temprana** | Cuánto tiempo de aviso recibe el jugador antes de un evento | Mejora con inversión; usa los avisos de DONKI (`sentNotifications`) y las predicciones del modelo **WSA-ENLIL** | Invertir en sensores o en otros recursos |
| 11 | **Puntos de ciencia** (stat positivo) | Datos valiosos obtenidos al observar los eventos | Cualquier evento grande: **FLR** X, **CME** rápidas, **SEP** | Arriesgar instrumentos en el exterior para ganar más ciencia |
| 12 | **Moral / estrés de la tripulación** | Cansancio por alertas seguidas y tiempo encerrados en el refugio | Cantidad de eventos de severidad ≥ 4 en poco tiempo | Rotar turnos, dar descansos |

### Glosario de eventos

| Sigla | Nombre | Qué es |
|---|---|---|
| FLR | Llamarada solar | Estallido de rayos X; su fuerza se mide por clase (C < M < X) |
| CME | Eyección de masa coronal | Nube de plasma que sale del Sol y tarda de 1 a 3 días en llegar |
| SEP | Partículas energéticas solares | Lluvia de protones de alta energía; el mayor peligro en la Luna |
| IPS | Choque interplanetario | Frente de choque que marca la llegada de una CME |
| GST | Tormenta geomagnética | Tormenta en el campo magnético de la Tierra; se mide con el índice Kp |
| HSS | Corriente rápida de viento solar | Viento solar más rápido de lo normal |
| RBE | Aumento en los cinturones de radiación | Más electrones en los cinturones de la Tierra; afecta a los satélites |
| MPC | Cruce de la magnetopausa | El escudo magnético de la Tierra se comprime y deja expuestos a los satélites |

## Cómo reemplazar lo que ya tenemos

| Stat actual | Reemplazo sugerido | Por qué |
|---|---|---|
| **Energía** | **Se queda**, idealmente dividida en **Eficiencia de paneles (3)** y **Baterías (4)** | Ya encaja directamente; dividirla da decisiones de corto y largo plazo |
| **Oxígeno** | **Integridad de la electrónica / soporte vital (5)** | Las partículas solares no afectan al oxígeno, pero sí a las máquinas que lo producen |
| **Alimentos y agua** | **Dosis de radiación de la tripulación (1)** | Es lo que DONKI mide realmente y genera la decisión más interesante: refugiarse o producir |

## Combinaciones recomendadas

**Opción A (4 stats, sencilla):**
1. Energía
2. Dosis de radiación
3. Integridad de sistemas (electrónica + blindaje)
4. Comunicación / suministros

**Opción B (5 stats, más estratégica):**
1. Baterías
2. Eficiencia de paneles
3. Dosis de radiación
4. Integridad de sistemas
5. Puntos de ciencia (le da al jugador una razón para arriesgarse)

Con cualquiera de las dos, **todos los stats cambian con eventos reales de DONKI**, sin depender de cadenas indirectas.

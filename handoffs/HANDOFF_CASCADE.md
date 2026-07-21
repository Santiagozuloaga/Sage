# HANDOFF_CASCADE.md

**De:** Claude A (rama de núcleo/config/memory/dispatcher/providers)
**Para:** Cascade (integración de runtime vivo: CLI, Event Bus, Recovery, Mission Control, Context Manager, Agent Router, Decision Engine)
**Fecha:** 2026-07-05
**Fuente de este handoff:** trabajé sobre un snapshot de `sage_runtime.zip` que el Arquitecto subió en un punto del tiempo — no tengo acceso a tu copia en vivo en `c:\Users\Admin\Downloads\sage_runtime`. Todo lo de abajo asume que hay que **fusionar**, no sobrescribir en ninguna dirección.

---

## 1. Resumen ejecutivo

Hice una pasada de estabilización sobre 8 archivos: arranque del kernel, configuración, memoria, dispatcher, y la capa de providers. Encontré y corregí 15 problemas reales (todos reproducidos antes del fix y re-verificados después — no son solo lectura de código). El más importante técnicamente: conecté `dispatcher._execute_command()` a `provider_router.generate_text()` de verdad — antes, **ningún comando ejecutaba nada real**, todo era `f"Executed: {command}"` fabricado.

También hice una auditoría funcional completa del flujo (Boot→Event Bus→Recovery→Mission Control→ciclo de comandos) sin arreglar nada de eso — ese trabajo es tuyo. El hallazgo más severo de esa auditoría: **tu `CLIInterface` está completa y funciona, pero `cli.start()` nunca se llama en `main.py`.** Con mi propio fix (hacer el import de `web.server` opcional), esto empeoró en la práctica: el sistema ahora arranca sin crashear en "modo solo CLI"... sin que la CLI corra. Se queda mudo en un loop de `sleep(1)`.

Todo el detalle línea por línea está en `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` (mis fixes) y `AUDITORIA_FUNCIONAL_FLUJO_COMPLETO.md` (lo que audité sin tocar). No los repito acá — este documento es el mapa para fusionar, no el changelog completo.

## 2. Archivos que modifiqué

```
repository_scanner/dependency_graph.py
kernel/core.py
providers/ollama_provider.py       (NUEVO)
providers/provider_router.py
main.py
config/manager.py
memory/engine.py
dispatcher/engine.py
```

Ningún otro archivo del repo fue tocado por mí, en ningún momento.

## 3. Archivos que NO deberías sobrescribir sin revisar el diff primero

Los 8 de arriba. Ninguno debería reemplazarse a ciegas por tu versión en vivo ni la mía — ver sección 4 para el riesgo específico de cada uno.

## 4. Riesgos de merge detectados — de mayor a menor probabilidad de choque real

### 🔴 `dispatcher/engine.py` — CONFLICTO CASI SEGURO
Por tu propio log de PR-014 (que el Arquitecto me pasó completo), estabas editando `_execute_command` — la traza muestra un diff con `agent_results`, `success_rate`, justo antes de un edit a esa función — cuando se cortó por cuota. **Yo reescribí ese mismo método** para llamarlo a `provider_router.generate_text()` de verdad, con manejo de error y un marcador `"stub": False/True` explícito. Si tu edición de PR-014 seguía viva cuando se cortó la sesión, tu copia y la mía van a chocar exactamente en esa función. **No se puede resolver por "quedarte con una versión"** — lo más probable es que la versión final necesite ambas cosas: mi llamada real a `provider_router` MÁS tu lógica de resultados de agentes, combinadas.

### 🔴 `kernel/core.py` — CONFLICTO PROBABLE
Vos lo editaste repetidamente (imports de provider_router/file_processor/repository_scanner/image_analyzer a lo largo de PR-009 a PR-013). Yo reestructuré `_boot_phase()` completo (separé componentes críticos de opcionales, agregué `_init_optional()`, agregué el paso de wiring dispatcher↔provider_router al final). Si tu copia en vivo tiene inits que la mía no vio (o viceversa), hay que fusionar a mano, sección por sección — no reemplazar el archivo entero en ninguna dirección.

### 🟡 `main.py` — CONFLICTO PROBABLE, MENOR ALCANCE
Vos escribiste el wiring original del web server en PR-007 (import directo + `web_task`/`web_server` sin condicional). Yo lo envolví en `try/except` con una bandera `WEB_AVAILABLE` y until lo hice todo condicional. La lógica de fondo (arrancar web server, servir en :8000) es tuya y la preservé — solo la hice opcional. Cuando implementes el arranque de la CLI (hallazgo #1 de la auditoría), va a tocar este mismo archivo otra vez — hacelo dentro de la misma estructura `if WEB_AVAILABLE / else` que ya dejé, no la reviertas.

### 🟢 `providers/provider_router.py` — riesgo bajo-medio
Vos lo creaste en PR-009. Yo agregué el registro de Ollama y corregí un bug real (el `health_check()` de los 3 providers devuelve un dict con `status` en vez de lanzar excepción, y el código original de `initialize()` esperaba que lanzara — nunca detectaba un fallo real). Si tocaste este archivo de nuevo después de PR-009 (no lo vi en tu log), revisá el diff antes de sobrescribir.

### 🟢 `config/manager.py`, `memory/engine.py`, `repository_scanner/dependency_graph.py` — riesgo bajo
Sin evidencia en tu log de que los hayas tocado después de crearlos inicialmente. Deberían fusionar limpio, pero igual recomiendo un diff rápido antes de aceptar, no por desconfianza sino porque no tengo forma de confirmar el estado exacto de tu copia en vivo ahora mismo.

### — `providers/ollama_provider.py` — sin riesgo
Archivo nuevo, no existe en tu copia salvo que lo hayas creado vos también con otro nombre/enfoque — si es así, avisá antes de que yo asuma que el mío es el único.

## 5. Dependencias entre mis cambios y tu trabajo pendiente

- **Context Manager:** cuando lo construyas, no reviertas el wiring `dispatcher → provider_router` que ya dejé. Extendelo: el Context Manager debería ensamblar el prompt/historial y pasárselo a `provider_router.generate_text()` (o `.chat()` si armás mensajes con roles) en el mismo punto donde hoy mando el string crudo del comando.
- **Event Bus:** el lugar más barato para empezar a publicar (según mi propia auditoría) es `kernel.execute_command()` y `dispatcher._execute_command()` — los dos métodos que ya toqué. Agregar `await event_bus.publish(...)` ahí es una extensión de mi código, no un reemplazo.
- **Recovery System:** hoy vive fuera de `kernel._components` (solo existe en `main.py`). Si lo hacés componente del kernel, usá el mismo patrón `_init_optional()` que ya agregué para todo lo demás no-crítico — no inventes un mecanismo de boot paralelo.
- **CLI:** toca `main.py`, que ya reestructuré con la bandera `WEB_AVAILABLE`. Arrancala respetando esa estructura (ver riesgo 🟡 arriba).
- **Agent Router (integración real):** dejé un método `dispatcher.set_provider_router()` como el único punto de entrada de dependencias externas al dispatcher. Si conectás `agent_router`, seguí el mismo patrón (`set_agent_router()` o similar) en vez de pasarlo por otro mecanismo — así queda consistente y es más fácil de auditar después.

## 6. Orden recomendado para integrar

1. **Primero, diff manual de `dispatcher/engine.py` y `kernel/core.py`** contra tu copia en vivo — son los dos de riesgo real. No avances con nada más hasta resolver estos dos.
2. Aceptar `main.py` fusionando tu wiring de web server (ya existente) dentro de mi estructura `WEB_AVAILABLE`.
3. Aceptar `config/manager.py`, `memory/engine.py`, `repository_scanner/dependency_graph.py`, `providers/provider_router.py` tras un diff rápido de confirmación.
4. Agregar `providers/ollama_provider.py` como archivo nuevo.
5. Correr la suite existente (`tests/validate_pr0{09..14}.py`) completa para confirmar que la fusión no rompió nada — deberías ver 5/6 o 6/6 (el sexto depende de si tenés `fastapi` instalado, que vos sí tenés en tu máquina real).
6. Recién ahí, seguir con CLI → Event Bus → Recovery → Mission Control → Context Manager → Agent Router, en ese orden o el que prefieras — mi auditoría solo prioriza CLI primero porque sin eso nada de lo demás es usable.

## 7. Estado de los tests al momento de este cierre

- Suite existente `tests/validate_pr0{09..14}.py`: **5/6 PASA**. El único fallo (`validate_pr009`, "Web API Endpoints") es por falta de `fastapi` en mi sandbox, no una regresión — en tu máquina real (donde ya instalaste fastapi) debería pasar completo.
- 15 tests propios (config: 4, memory: 5, dispatcher: 3, wiring: 3) — **todos PASA**, re-ejecutados en la última verificación antes de este cierre.
- Ningún test roto por mis cambios en ningún momento de la sesión.

## 8. Recomendaciones para no duplicar trabajo ni gastar tokens

- **No re-audites config, memory, dispatcher (la parte que ya conecté a provider_router), repository_scanner ni providers.** Ya está hecho, reproducido y verificado. Leé `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` en vez de re-descubrir los mismos bugs.
- **No re-diagnostiques por qué CLI/Event Bus/Recovery/Mission Control no participan del flujo.** Ya está diagnosticado a fondo, con reproducción, en `AUDITORIA_FUNCIONAL_FLUJO_COMPLETO.md` — andá directo a las opciones de implementación que ya dejé documentadas ahí (sección "Decisiones de arquitectura").
- **Antes de tocar `dispatcher/engine.py` o `kernel/core.py`, hacé el diff de la sección 4 primero.** Evita el escenario de que los dos volvamos a escribir versiones incompatibles del mismo método sin darnos cuenta.
- Si en algún momento no estás seguro de si algo ya fue verificado o solo inspeccionado, buscá la palabra "Verificación" en `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` — todo lo que arreglé tiene su comando/test de verificación documentado al lado.

## 9. Mensaje directo para Cascade

No reescribas `_execute_command` desde cero — ya llama a `provider_router.generate_text()` de verdad y eso está probado (con provider real inyectado y con cero providers, en ambos casos el resultado es correcto). Si tu PR-014 necesitaba agregar resultados de ejecución de agentes ahí, agregalo *sobre* mi versión, no en paralelo. Y antes de tocar `kernel/core.py` para registrar Recovery o Mission Control como componentes, fijate cómo ya usé `_init_optional()` para los últimos 7 componentes — es el mismo patrón, no hace falta inventar otro.

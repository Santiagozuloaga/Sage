# MERGE_AUDIT.md — Auditoría de Integración

**Auditor:** GLM (Integration Auditor)
**Fecha:** 2026-07-05
**Alcance:** Fusión de la Rama Claude A con la Rama Cascade (esta última = baseline + PR-009 a PR-015 + fixes del Runtime Engineer)
**Documentos de referencia utilizados:**
- `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` (Claude A — registro de cambios)
- `HANDOFF_CASCADE.md` (Claude A → Cascade — riesgos de merge detectados por Claude A)
- `HANDOFF_RUNTIME_ENGINEER.md` (Runtime Engineer → Claude A — bugs fixados y no fixados)
- `BUG_REPORT.md` (Runtime Engineer — detalle de cada fix)

**Restricciones cumplidas:**
- No se modificó código.
- No se generaron fixes.
- No se propuso arquitectura nueva.
- No se rehiciéron auditorías ya realizadas (se reutilizan los hallazgos de `AUDITORIA_FUNCIONAL_FLUJO_COMPLETO.md` y `BUG_REPORT.md`).

---

## 1. Resumen Ejecutivo

Se compararon **18 archivos** entre las dos ramas más el baseline. El resultado:

| Categoría | Cantidad |
|---|---|
| Archivos modificados por Claude A solamente | 7 ( + 1 nuevo: `providers/ollama_provider.py`) |
| Archivos modificados por Runtime Engineer solamente | 6 |
| Archivos modificados por AMBAS ramas (conflicto a nivel archivo) | 2 (`kernel/core.py`, `main.py`) |
| Conflictos puntuales identificados (a nivel método/línea) | **10** |
| Conflictos de integración cruzada (entre archivos distintos) | **6** |
| Conflictos que **requieren decisión humana** | **4** |
| Conflictos que **pueden fusionarse automáticamente** | **8** |
| Conflictos que **rompen el sistema** si se fusionan mal | **3** (C7, C8, I2) |

**Hallazgo más severo:** la rama Runtime Engineer se construyó sobre el baseline (`sage_runtime.zip`) **sin incluir los fixes de Claude A**. Esto significa que fusionar `sage_runtime_fixed/` (RE) sobre `cascade_pkg/sage_runtime_handoff/sage_runtime_fixed/` (Claude A) **perdería los 8 fixes de Claude A** en `kernel/core.py`, `config/manager.py`, `memory/engine.py`, `dispatcher/engine.py`, `providers/provider_router.py`, `providers/ollama_provider.py`, `main.py`, `repository_scanner/dependency_graph.py`. La dirección de fusión correcta es **Claude A como base + RE aplicado encima**, no al revés.

**Hallazgo crítico de integración:** el `_init_dashboard()` que el Runtime Engineer asume presente en `kernel/core.py` (línea 117 de su versión) **fue eliminado por Claude A** (líneas 192-198 del diff). El fallback defensivo de RE en `main.py` (líneas 82-88) cubre este caso, pero el resultado neto es que el dashboard pasa a ser responsabilidad de `main.py`, no del kernel — un cambio de diseño que requiere confirmación humana explícita.

---

## 2. Mapeo de Ramas (verificado empíricamente)

| Nombre lógico | Ubicación física en este audit | Marcadores verificados |
|---|---|---|
| **Baseline** (Opal extraction + PR-009 a PR-015 de Cascade) | `upload/sage_runtime.zip` → `work/claude_a_branch/sage_runtime/` | Sin fixes de Claude A ni de RE. `Optional` ya presente en `dependency_graph.py` (1 ocurrencia, no es fix de Claude A). |
| **Rama Claude A** (baseline + 8 fixes de Claude A) | `upload/HANDOFF_CASCADE_PAQUETE.zip` → `work/cascade_pkg/sage_runtime_handoff/sage_runtime_fixed/` | Tiene: `_init_optional`, `_degraded`, `os.replace` en config, `journal_mode=WAL`, `itertools.count`, `set_provider_router`, `ollama_provider.py`, `WEB_AVAILABLE`. **NO tiene**: DLQ en events/bus.py, microsegundos en recovery, `start_time` en mission_control. |
| **Rama Cascade + Runtime Engineer** (baseline + 8 fixes de RE) | `upload/SAGE_Runtime_RuntimeEngineer_Submission.zip` → `work/sage_runtime_fixed/` | Tiene: `_dlq` en events/bus.py, `%Y%m%d_%H%M%S_%f` en recovery, `start_time`/`end_time` en mission_control, `_shutdown_complete` en kernel, `record_error` en kernel/state, `os.replace` en boot/configurator. **NO tiene**: ningún fix de Claude A. |

**Nota sobre el nombre "Rama Cascade":** el usuario agrupa bajo este nombre tanto los PR-009 a PR-015 originales de Cascade (que viven en el baseline) como los fixes del Runtime Engineer. Esto es consistente con el mandato original del RE: "fixing only those that do not conflict with Cascade". En la práctica, la "Rama Cascade" del enunciado equivale físicamente a `SAGE_Runtime_RuntimeEngineer_Submission.zip`.

---

## 3. Catálogo de Conflictos

Cada conflicto está identificado con un código:
- `C#` = conflicto a nivel archivo/método (file-level)
- `I#` = conflicto de integración cruzada (cross-file)

Los códigos de gravedad son: 🔴 CRÍTICO (rompe el sistema) · 🟠 ALTO (pérdida de funcionalidad) · 🟡 MEDIO (degradación) · 🟢 BAJO (cosmético).

---

### C1 — `kernel/core.py` · método `_boot_phase()` · reestructuración mutuamente excluyente

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `_boot_phase()` |
| **Líneas baseline** | 75-112 (38 líneas, secuencia plana) |
| **Líneas Claude A** | 77-127 (51 líneas, con `_init_optional()` y wiring) |
| **Líneas RE** | 77-114 (38 líneas, solo cambios de whitespace) |
| **Ramas afectadas** | Claude A, RE |
| **Tipo de conflicto** | Estructural — ambas ramas reescriben el método, pero Claude A lo reestructura funcionalmente (split critical/optional + wiring dispatcher→provider_router) y RE solo normaliza whitespace. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma la versión de RE, se pierden: (a) la división critical/optional que evita que un bug en un módulo periférico tumbe el kernel, (b) el wiring `dispatcher.set_provider_router(provider_router)` que conecta los comandos al LLM, (c) el reporte de `_degraded`. Si se toma la versión de Claude A, se pierde solo whitespace (sin impacto funcional). |
| **Solución recomendada** | Tomar la versión de Claude A íntegramente. Los cambios de whitespace de RE son cosméticos y no aportan nada. |
| **¿Auto-fusionable?** | Sí, con un merge tool de 3 vías (baseline + Claude A + RE) — la versión de Claude A es superset funcional. |
| **¿Requiere decisión humana?** | No. |

---

### C2 — `kernel/core.py` · método `__init__()` · adición de campos disjuntos

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `__init__()` |
| **Líneas baseline** | 32-38 (sin campos nuevos) |
| **Líneas Claude A** | 37 (`self._degraded: Dict[str, str] = {}`) |
| **Líneas RE** | 44 (`self._shutdown_complete = False`) |
| **Ramas afectadas** | Claude A, RE |
| **Tipo de conflicto** | Aditivo — ambas ramas añaden campos distintos al mismo método. |
| **Gravedad** | 🟢 BAJO |
| **Riesgo** | Ninguno. Los campos son ortogales. |
| **Solución recomendada** | Mantener ambos campos en el `__init__` fusionado. |
| **¿Auto-fusionable?** | Sí. |
| **¿Requiere decisión humana?** | No. |

---

### C3 — `kernel/core.py` · método `execute_command()` · handler de excepciones

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `execute_command()` (bloque `except Exception as e:`) |
| **Líneas baseline** | 232 (`self.context.error_count += 1`) |
| **Líneas Claude A** | 252-258 (cambio en el acceso al dispatcher: `self._components.get('dispatcher')` con None check y mensaje de degradado) |
| **Líneas RE** | 242 (`self.context.record_error(f"Command {command!r} failed: {e}")`) |
| **Ramas afectadas** | Claude A (cambia acceso al dispatcher), RE (cambia manejo de error) |
| **Tipo de conflicto** | Ortogonal — Claude A modifica la línea de acceso al dispatcher (previa al try), RE modifica la línea del handler de excepciones (dentro del try). Líneas distintas, métodos distintos. |
| **Gravedad** | 🟡 MEDIO |
| **Riesgo** | Si se toma la versión de RE sin la de Claude A: el handler de `record_error` funciona, pero el acceso `self._components['dispatcher']` (sin `.get`) sigue siendo un KeyError crudo si el dispatcher está degradado. Si se toma Claude A sin RE: el None check funciona, pero `error_count += 1` no deja breadcrumb en `last_error`. |
| **Solución recomendada** | Fusionar ambas: aplicar el cambio de acceso de Claude A **Y** el cambio de `record_error` de RE. Requiere que `kernel/state.py` tenga el método `record_error` (ver I1). |
| **¿Auto-fusionable?** | Sí, con merge tool de 3 vías — las dos líneas modificadas están a 14 líneas de distancia y no se solapan. |
| **¿Requiere decisión humana?** | No. |

---

### C4 — `kernel/core.py` · método `shutdown()` · aislamiento de fallos + idempotencia

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `shutdown()` |
| **Líneas baseline** | 240-257 (18 líneas, sin try/except por componente, sin idempotencia) |
| **Líneas Claude A** | Sin cambios respecto al baseline (verificado: misma estructura, mismo riesgo de starve componentes). |
| **Líneas RE** | 250-296 (47 líneas, con `_shutdown_complete` guard, per-component try/except, snapshot de keys) |
| **Ramas afectadas** | RE |
| **Tipo de conflicto** | Unilateral — solo RE modifica este método. |
| **Gravedad** | 🟠 ALTO (si no se aplica, el bug K-7 de RE queda sin fix) |
| **Riesgo** | Si se toma la versión de Claude A (== baseline): un componente que falle en `shutdown()` impide que los demás se cierren — resource leak. Si se toma la de RE: el bug queda fixeado. |
| **Solución recomendada** | Tomar la versión de RE para `shutdown()`. Combinar con C2 (campo `_shutdown_complete` en `__init__`) y con el reset en `boot()` (línea 79 de RE). |
| **¿Auto-fusionable?** | Sí (Claude A no tocó el método, no hay conflicto). |
| **¿Requiere decisión humana?** | No. |

---

### C5 — `kernel/core.py` · método `_init_dashboard()` · eliminación vs. retención

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `_init_dashboard()` y su llamada en `_boot_phase()` |
| **Líneas baseline** | 193-199 (método) + 110 (llamada en `_boot_phase`) |
| **Líneas Claude A** | **Eliminado** — ni el método ni la llamada existen. El dashboard ya no es componente del kernel. |
| **Líneas RE** | 200-206 (método conservado) + 117 (llamada en `_boot_phase` conservada) |
| **Ramas afectadas** | Claude A, RE |
| **Tipo de conflicto** | Diseño arquitectónico — Claude A decidió que el dashboard no es componente del kernel (es UI, lo inicializa `main.py`); RE conservó el diseño original (kernel inicializa dashboard). |
| **Gravedad** | 🟠 ALTO |
| **Riesgo** | Si se fusiona Claude A (sin `_init_dashboard`) + RE main.py (`kernel.get_component('dashboard')`): el fallback defensivo de RE main.py líneas 82-88 toma el control y construye el dashboard. **Funciona**, pero el fallback pasa a ser el camino principal, no el excepcional. Si se fusiona RE kernel (con `_init_dashboard`) + Claude A main.py (`dashboard = DashboardMonitor()` sin reuso): doble init, resource leak (bug MAIN-1 que RE ya había fixeado). |
| **Solución recomendada** | **Decisión humana requerida.** Recomendación del auditor: tomar la versión de Claude A (dashboard fuera del kernel) porque: (a) es consistente con la separación critical/optional que Claude A introdujo — dashboard no es crítico para el kernel; (b) el fallback de RE main.py ya cubre el caso; (c) reduce el acoplamiento kernel→dashboard. **Pero** esto deja el método `_init_dashboard` eliminado, lo que rompe cualquier código externo que lo llame directamente (no hay evidencia de eso hoy, pero el auditor no puede garantizar que Cascade no lo llame desde su wiring pendiente). |
| **¿Auto-fusionable?** | No. |
| **¿Requiere decisión humana?** | **SÍ.** Pregunta para el Arquitecto: ¿el dashboard debe ser componente del kernel (lo inicializa `kernel.boot()`) o de `main.py` (lo inicializa el entry point)? |

---

### C6 — `kernel/core.py` · `_init_provider_router()` · `default_provider`

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `_init_provider_router()` |
| **Líneas baseline** | 165 (`default_provider="grok"`) |
| **Líneas Claude A** | 205 (`default_provider="ollama"`) |
| **Líneas RE** | 172 (`default_provider="grok"`) — sin cambio |
| **Ramas afectadas** | Claude A |
| **Tipo de conflicto** | Unilateral con dependencia — Claude A cambia el default, RE no. Pero el cambio de Claude A **depende de** que exista `providers/ollama_provider.py` (que solo Claude A añade). |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma `default_provider="ollama"` sin `providers/ollama_provider.py`: `ProviderRouter.initialize()` intenta registrar Ollama, falla con `ImportError`, el provider_router queda degradado o sin providers. Si se toma `default_provider="grok"` (RE): se pierde el diseño de Claude A de usar Ollama como proveedor local sin API key — Grok requiere API key y en el hardware objetivo (laptop sin GPU, sin budget de nube) SAGE no podría generar texto. |
| **Solución recomendada** | Tomar la versión de Claude A **junto con** `providers/ollama_provider.py` (ver I5). Es un par indivisible. |
| **¿Auto-fusionable?** | Sí, si se mergean también los archivos de providers. No, si se mergea `kernel/core.py` aislado. |
| **¿Requiere decisión humana?** | No, si se sigue la regla "Claude A como base + RE encima". Sí, si se quiere revertir el default a "grok" por alguna razón (p.ej. Ollama no estará disponible en producción). |

---

### C7 — `kernel/core.py` · wiring `dispatcher.set_provider_router()` · ausencia en RE

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `_boot_phase()` (al final, tras los `_init_optional`) |
| **Líneas Claude A** | 110-119 — bloque que obtiene `dispatcher` y `provider_router` de `_components` y llama `dispatcher.set_provider_router(provider_router)` |
| **Líneas RE** | **Ausente** — el bloque no existe. |
| **Ramas afectadas** | Claude A |
| **Tipo de conflicto** | Unilateral — Claude A añade wiring, RE no. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma la versión de RE de `_boot_phase()` (o si se pierde el bloque al fusionar): **ningún comando dispatchado llega a un LLM**. El dispatcher queda con `_provider_router = None` y `_execute_command` devuelve `{"stub": True}` para todo. Este es exactamente el bug que Claude A documenta como "el más importante técnicamente" en `HANDOFF_CASCADE.md` §1. |
| **Solución recomendada** | Tomar la versión de Claude A de `_boot_phase()` (ver C1). El bloque de wiring debe preservarse. |
| **¿Auto-fusionable?** | Sí, si se sigue la regla "Claude A como base". |
| **¿Requiere decisión humana?** | No. |

---

### C8 — `main.py` · import de `WebServer` · ausencia de `WEB_AVAILABLE` en RE

| Campo | Valor |
|---|---|
| **Archivo** | `main.py` |
| **Método** | Import top-level (líneas 34-50) + bloque de init del web server (líneas 103-117) + bloque de shutdown del web server (líneas 141-151) |
| **Líneas baseline** | 37 (`from web.server import WebServer`) — import duro, crash si falta fastapi |
| **Líneas Claude A** | 45-51 (try/except con `WEB_AVAILABLE` flag) + 106-117 (init condicional) + 126-128 (print condicional) + 141-151 (shutdown condicional) |
| **Líneas RE** | 37 (`from web.server import WebServer`) — **sin cambios respecto al baseline** |
| **Ramas afectadas** | Claude A |
| **Tipo de conflicto** | Unilateral — Claude A envuelve el import, RE conserva el import duro. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma la versión de RE de `main.py` (o si se pierde el `WEB_AVAILABLE` al fusionar): en cualquier entorno sin `fastapi`/`uvicorn`/`websockets` instalados, **`python main.py` crashea en la línea 37 con `ImportError`** antes de imprimir siquiera el banner. Esto es exactamente el bug P0 #5 que Claude A fixeó. |
| **Solución recomendada** | Tomar la versión de Claude A del top-level de `main.py` (try/except + `WEB_AVAILABLE`) **Y** aplicar los cambios de RE solo a las secciones que RE modificó (dashboard init, finally block). El merge de 3 vías debería poder hacer esto automáticamente porque las secciones tocadas no se solapan. |
| **¿Auto-fusionable?** | Sí, con merge tool de 3 vías — Claude A toca líneas 45-51 + 106-117 + 126-128 + 141-151; RE toca líneas 75-96 + 131-140. Hay solapamiento solo en el finally block (Claude A líneas 141-151, RE líneas 131-140), que se detalla en C10. |
| **¿Requiere decisión humana?** | No. |

---

### C9 — `main.py` · inicialización del dashboard · reuso vs. doble init

| Campo | Valor |
|---|---|
| **Archivo** | `main.py` |
| **Método** | Sección de init post-`kernel.boot()` |
| **Líneas baseline** | 75-88 (`dashboard = DashboardMonitor()` + init + registro manual en `kernel._components`) |
| **Líneas Claude A** | Sin cambios respecto al baseline — sigue haciendo `dashboard = DashboardMonitor()` directo |
| **Líneas RE** | 75-96 — `dashboard = kernel.get_component('dashboard')` con fallback defensivo a `DashboardMonitor()` si el kernel no lo registró |
| **Ramas afectadas** | RE |
| **Tipo de conflicto** | Unilateral con dependencia — RE cambia el patrón, Claude A no. Pero el cambio de RE **depende de** la decisión sobre `_init_dashboard()` en `kernel/core.py` (ver C5). |
| **Gravedad** | 🟠 ALTO |
| **Riesgo** | Si se toma la versión de Claude A de main.py (`dashboard = DashboardMonitor()` directo) **Y** la versión de Claude A de kernel/core.py (sin `_init_dashboard`): funciona, pero el dashboard se inicializa dos veces si algo del wiring futuro de Cascade asume que el kernel ya lo inicializó (escenario hipotético). Si se toma la versión de RE de main.py (`kernel.get_component('dashboard')`) **Y** la versión de Claude A de kernel/core.py (sin `_init_dashboard`): el fallback de RE construye el dashboard — funciona, pero el fallback se vuelve el camino principal. Si se toma la versión de RE de main.py **Y** la versión de RE de kernel/core.py (con `_init_dashboard`): funciona correctamente, sin doble init. |
| **Solución recomendada** | Tomar la versión de RE de esta sección de `main.py` (reuso vía `kernel.get_component`). El fallback defensivo maneja cualquier combinación de C5. |
| **¿Auto-fusionable?** | Sí, con merge tool de 3 vías — las líneas tocadas por RE (75-96) no se solapan con las de Claude A (45-51, 106-117, 141-151). |
| **¿Requiere decisión humana?** | Solo indirectamente: la decisión sobre C5 afecta qué camino toma el fallback de RE. |

---

### C10 — `main.py` · finally block · shutdown manual vs. delegado al kernel

| Campo | Valor |
|---|---|
| **Archivo** | `main.py` |
| **Método** | `finally:` del `try/except` que mantiene el runtime vivo |
| **Líneas baseline** | 117-130 — `await web_server.stop()` + `web_task.cancel()` + `await dashboard.shutdown()` + `await recovery.shutdown()` + `await command_mode.shutdown()` + `await kernel.shutdown()` |
| **Líneas Claude A** | 141-156 — web_server.stop condicional (`if web_server is not None`) + mismo patrón para dashboard/recovery/command_mode + kernel.shutdown |
| **Líneas RE** | 131-140 — web_server.stop **sin condicional** (línea 128, bug: asume que web_server existe) + **elimina** `dashboard.shutdown()`, `recovery.shutdown()`, `command_mode.shutdown()` (delega todo en `kernel.shutdown()`) |
| **Ramas afectadas** | Claude A, RE |
| **Tipo de conflicto** | Solapamiento — Claude A modifica el bloque web_server (lo hace condicional); RE elimina el bloque dashboard/recovery/command_mode. Ambos tocan el mismo `finally`. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma la versión de RE del finally **sin** el `WEB_AVAILABLE` de Claude A: `web_server.stop()` en línea 128 crashea con `AttributeError: 'NoneType' object has no attribute 'stop'` si fastapi no está instalado. Si se toma la versión de Claude A del finally **sin** los cambios de RE: se mantienen los `dashboard.shutdown()` / `recovery.shutdown()` / `command_mode.shutdown()` manuales, que double-shutdown si `kernel.shutdown()` también los cierra (que lo hace, porque están registrados en `_components`). |
| **Solución recomendada** | **Fusionar ambos:** aplicar el `if web_server is not None` de Claude A **Y** eliminar los `dashboard.shutdown()`/`recovery.shutdown()`/`command_mode.shutdown()` de RE (delegar todo en `kernel.shutdown()`). Esto requiere que `kernel.shutdown()` efectivamente cierre esos tres componentes — lo cual es cierto si están registrados en `kernel._components` (que tanto Claude A como RE hacen en main.py línea 92-96 de RE / equivalente en Claude A). **Y** requiere que `kernel.shutdown()` tenga el aislamiento de fallos de RE (C4), porque si no, un fallo en `dashboard.shutdown()` starvation a `recovery.shutdown()`. |
| **¿Auto-fusionable?** | No con merge tool estándar — las líneas están intercaladas. Requiere edición manual. |
| **¿Requiere decisión humana?** | Sí, implícitamente: confirmar que se quiere delegar todo el shutdown en el kernel (diseño de RE) vs. mantener shutdowns manuales (diseño de Claude A / baseline). Auditor recomienda la delegación de RE porque es más limpia y consistente con el patrón "kernel es el orchestrator". |

---

### I1 — `kernel/state.py` + `kernel/core.py` · dependencia `record_error()`

| Campo | Valor |
|---|---|
| **Archivos** | `kernel/state.py` (define el método) + `kernel/core.py` (lo llama) |
| **Métodos** | `KernelContext.record_error()` (en state.py) + `execute_command()` exception handler (en core.py) |
| **Líneas RE state.py** | 119-140 (método `record_error` + `clear_error` + campo `last_error`) |
| **Líneas RE core.py** | 242 (`self.context.record_error(...)`) |
| **Líneas Claude A state.py** | Sin cambios (state.py == baseline) |
| **Líneas Claude A core.py** | 252-258 — usa `error_count += 1` indirectamente (no llama a `record_error`) |
| **Ramas afectadas** | RE (define + usa), Claude A (no define + no usa) |
| **Tipo de conflicto** | Dependencia cruzada — el método `record_error` solo existe en la rama RE. |
| **Gravedad** | 🟡 MEDIO |
| **Riesgo** | Si se mergea RE core.py (que llama `record_error`) **sin** RE state.py: `AttributeError: 'KernelContext' object has no attribute 'record_error'` en runtime al fallar un comando. Si se mergea RE state.py **sin** RE core.py: el método existe pero no se llama — `last_error` queda siempre `None` (pérdida de funcionalidad pero no crash). |
| **Solución recomendada** | Tomar `kernel/state.py` de RE **íntegramente**. Para `kernel/core.py`, fusionar: usar el acceso al dispatcher de Claude A (C3, con None check) **Y** el handler `record_error` de RE. Esto requiere que `kernel/state.py` tenga el método — lo cual es cierto si se toma la versión de RE. |
| **¿Auto-fusionable?** | Sí para state.py (Claude A no lo modificó). Requiere cuidado para core.py (ver C3). |
| **¿Requiere decisión humana?** | No. |

---

### I2 — `kernel/core.py` + `dispatcher/engine.py` · wiring `set_provider_router()`

| Campo | Valor |
|---|---|
| **Archivos** | `kernel/core.py` (llama al wiring) + `dispatcher/engine.py` (define `set_provider_router()`) |
| **Métodos** | `SageKernel._boot_phase()` wiring block (kernel) + `TaskDispatcher.set_provider_router()` + `_execute_command()` (dispatcher) |
| **Líneas Claude A kernel/core.py** | 110-119 (wiring block) |
| **Líneas Claude A dispatcher/engine.py** | 52-79 (`set_provider_router` method), 270-300 (`_execute_command` rewired to call `provider_router.generate_text`) |
| **Líneas RE kernel/core.py** | Sin wiring block |
| **Líneas RE dispatcher/engine.py** | Sin método `set_provider_router` (RE no modificó dispatcher) |
| **Ramas afectadas** | Claude A |
| **Tipo de conflicto** | Dependencia indivisible — el wiring en kernel/core.py llama a un método que solo existe en la versión de Claude A de dispatcher/engine.py. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma el wiring de Claude A en kernel/core.py **sin** el método en dispatcher/engine.py: `AttributeError: 'TaskDispatcher' object has no attribute 'set_provider_router'` durante el boot. Si se toma el método en dispatcher/engine.py **sin** el wiring en kernel/core.py: el método existe pero nunca se llama — `_provider_router` queda `None`, `_execute_command` devuelve `{"stub": True}` para todo (comando no llega al LLM). |
| **Solución recomendada** | Tomar AMBOS archivos de Claude A. El par kernel/core.py + dispatcher/engine.py es indivisible en lo que respecta al wiring. |
| **¿Auto-fusionable?** | Sí, si se sigue la regla "Claude A como base". |
| **¿Requiere decisión humana?** | No. |

---

### I3 — `kernel/core.py` + `main.py` · ownership del dashboard

| Campo | Valor |
|---|---|
| **Archivos** | `kernel/core.py` (`_init_dashboard()` método + llamada en `_boot_phase()`) + `main.py` (construcción del dashboard) |
| **Métodos** | `SageKernel._init_dashboard()` + `main()` dashboard init section |
| **Líneas Claude A kernel/core.py** | Método **eliminado** (ver C5) |
| **Líneas Claude A main.py** | 75-88 — `dashboard = DashboardMonitor()` directo (sin reuso) |
| **Líneas RE kernel/core.py** | 200-206 (método conservado) + 117 (llamada en `_boot_phase`) |
| **Líneas RE main.py** | 82-88 — `dashboard = kernel.get_component('dashboard')` con fallback |
| **Ramas afectadas** | Claude A, RE |
| **Tipo de conflicto** | Diseño arquitectónico cruzado — la decisión sobre quién inicializa el dashboard afecta tanto a `kernel/core.py` como a `main.py`. |
| **Gravedad** | 🟠 ALTO |
| **Riesgo** | Combinaciones posibles: (a) Claude A kernel + Claude A main: funciona pero sin reuso (doble init siCascade wiring futuro asume kernel lo inicializó). (b) Claude A kernel + RE main: fallback de RE construye el dashboard — funciona. (c) RE kernel + Claude A main: doble init, resource leak (bug MAIN-1 que RE fixeó). (d) RE kernel + RE main: funciona correctamente. |
| **Solución recomendada** | Combinación (b) o (d). (b) es más alineada con el diseño de Claude A (dashboard fuera del kernel). (d) es más alineada con el diseño original (dashboard dentro del kernel). Ver C5 para la pregunta exacta al Arquitecto. |
| **¿Auto-fusionable?** | No. |
| **¿Requiere decisión humana?** | **SÍ.** Es la misma decisión que C5. |

---

### I4 — `main.py` + `kernel/core.py` · dependencia del shutdown aislado

| Campo | Valor |
|---|---|
| **Archivos** | `main.py` (delega shutdown en kernel) + `kernel/core.py` (implementa shutdown aislado) |
| **Métodos** | `main()` finally block + `SageKernel.shutdown()` |
| **Líneas RE main.py** | 131-140 — elimina `dashboard.shutdown()`/`recovery.shutdown()`/`command_mode.shutdown()` manuales, delega en `kernel.shutdown()` |
| **Líneas RE kernel/core.py** | 250-296 — `shutdown()` con per-component try/except |
| **Líneas Claude A main.py** | 141-156 — mantiene shutdowns manuales + condicional para web_server |
| **Líneas Claude A kernel/core.py** | 240-257 — `shutdown()` sin aislamiento (== baseline) |
| **Ramas afectadas** | RE |
| **Tipo de conflicto** | Dependencia de robustez — la delegación de RE en main.py solo es segura si kernel.shutdown() tiene el aislamiento de RE. |
| **Gravedad** | 🟠 ALTO |
| **Riesgo** | Si se toma la delegación de RE en main.py **sin** el shutdown aislado de RE en kernel/core.py: un fallo en `dashboard.shutdown()` starvation a `recovery.shutdown()` y `command_mode.shutdown()` — exactamente el bug K-7 que RE fixeó. Si se toma el shutdown aislado de RE en kernel/core.py **sin** la delegación de RE en main.py: no hay problema, solo se ejecutan shutdowns manuales + kernel.shutdown() (que también los cierra, doble shutdown — no rompe porque el aislamiento de RE captura el segundo fallo). |
| **Solución recomendada** | Tomar AMBOS cambios de RE: la delegación en main.py **Y** el shutdown aislado en kernel/core.py. Si por alguna razón no se quiere tomar uno de los dos, tomar el shutdown aislado de kernel/core.py (más crítico) y mantener los shutdowns manuales de main.py. |
| **¿Auto-fusionable?** | Requiere coordinación pero no decisión humana. |
| **¿Requiere decisión humana?** | No, pero requiere cuidado en la implementación del merge. |

---

### I5 — `kernel/core.py` + `providers/provider_router.py` + `providers/ollama_provider.py` · trío indivisible

| Campo | Valor |
|---|---|
| **Archivos** | `kernel/core.py` (cambia `default_provider="ollama"`) + `providers/provider_router.py` (registra Ollama) + `providers/ollama_provider.py` (NUEVO, define la clase) |
| **Métodos** | `SageKernel._init_provider_router()` + `ProviderRouter.initialize()` + `OllamaProvider` (clase nueva) |
| **Líneas Claude A kernel/core.py** | 205 (`default_provider="ollama"`) |
| **Líneas Claude A providers/provider_router.py** | Import de `OllamaProvider` + bloque try/except que registra Ollama (líneas ~70-90) |
| **Líneas Claude A providers/ollama_provider.py** | Archivo nuevo, 10360 bytes |
| **Ramas afectadas** | Claude A |
| **Tipo de conflicto** | Trío indivisible — los tres archivos se necesitan mutuamente. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se toma `default_provider="ollama"` sin `ollama_provider.py`: `ImportError` en el import de ProviderRouter. Si se toma `ollama_provider.py` sin el registro en `provider_router.py`: el archivo existe pero nadie lo usa — Ollama no está disponible. Si se toma el registro en `provider_router.py` sin `ollama_provider.py`: `ImportError` al cargar `provider_router.py`. |
| **Solución recomendada** | Tomar los TRES archivos de Claude A. Indivisible. |
| **¿Auto-fusionable?** | Sí, si se sigue la regla "Claude A como base". |
| **¿Requiere decisión humana?** | No. |

---

### I6 — `kernel/state.py` + `kernel/core.py` · FSM validation y `_init_optional()`

| Campo | Valor |
|---|---|
| **Archivos** | `kernel/state.py` (FSM con `_ALLOWED_TRANSITIONS`) + `kernel/core.py` (transiciones) |
| **Métodos** | `KernelContext.transition_to()` + `SageKernel._boot_phase()` + `SageKernel.shutdown()` |
| **Líneas RE state.py** | 28-50 (`_ALLOWED_TRANSITIONS` map), 80-110 (`transition_to` con log de warning), 119-140 (`record_error`, `clear_error`) |
| **Líneas Claude A state.py** | Sin cambios (state.py == baseline) |
| **Ramas afectadas** | RE |
| **Tipo de conflicto** | Compatibilidad de comportamiento — la FSM de RE logea warnings en transiciones ilegales. Claude A hace varias transiciones legales (BOOT→KERNEL_READY→COMMAND_MODE→WAITING_FOR_USER_COMMAND→COMMAND_EXECUTION→WAITING_FOR_USER_COMMAND→SHUTDOWN) que no disparan warnings. Pero el shutdown idempotency de RE (C4) transiciona a SHUTDOWN solo la primera vez — si se llama shutdown() dos veces, la segunda es no-op (no transiciona), lo cual es correcto. |
| **Gravedad** | 🟢 BAJO |
| **Riesgo** | Si se toma la FSM de RE **sin** el shutdown idempotency de RE: el segundo `shutdown()` transiciona SHUTDOWN→SHUTDOWN, que es una self-transición permitida (no warning). No rompe. Si se toma el shutdown idempotency de RE **sin** la FSM de RE: el guard `_shutdown_complete` previene la doble transición, no se requiere FSM. Combinación segura en cualquier dirección. |
| **Solución recomendada** | Tomar ambos (son cambios ortogonales de RE). |
| **¿Auto-fusionable?** | Sí. |
| **¿Requiere decisión humana?** | No. |

---

## 4. Archivos SIN Conflicto (fusión limpia)

Estos archivos pueden fusionarse automáticamente tomando la versión modificada de la rama correspondiente:

### De la rama Claude A (RE no los modificó):

| Archivo | Cambios de Claude A | Verificado |
|---|---|---|
| `config/manager.py` | 3 fixes: merge en `load()`, atomic writes en `save()`, `set()` async + persistente | `diff` confirma: RE == baseline |
| `memory/engine.py` | 4 fixes: `_encode_list`/`_decode_list`, `journal_mode=WAL`, try/except en 8 métodos | `diff` confirma: RE == baseline |
| `dispatcher/engine.py` | 2 fixes + 1 wiring: `itertools.count` tie-break, `set_provider_router()`, `_execute_command` llama `generate_text` | `diff` confirma: RE == baseline |
| `providers/provider_router.py` | 2 fixes: registro de Ollama, `health.get("status") == "online"` check | `diff` confirma: RE == baseline |
| `providers/ollama_provider.py` | Archivo NUEVO | No existe en RE |
| `repository_scanner/dependency_graph.py` | 1 fix: `Optional` en import (ya presente en baseline — verificado) | El fix existe en ambos; era un falso positivo del diff |

**Nota sobre `repository_scanner/dependency_graph.py`:** Claude A documenta este fix como crítico (bloqueante total del boot). Sin embargo, el baseline (`sage_runtime.zip`) **ya tiene** `Optional` en el import. Esto significa que el fix ya estaba aplicado en el baseline que Claude A recibió — probablemente aplicado por Cascade en una iteración posterior a la que generó el primer baseline. No hay conflicto, pero el fix efectivamente ya no es necesario. **Acción: ninguna.**

### De la rama RE (Claude A no los modificó):

| Archivo | Cambios de RE | Verificado |
|---|---|---|
| `events/bus.py` | 6 fixes: idempotent start, deque history, DLQ, better logs, defensive publish, type hint | `diff` confirma: Claude A == baseline |
| `events/models.py` | 1 fix: `EventHandler` type hint | `diff` confirma: Claude A == baseline |
| `recovery/system.py` | 3 fixes: checkpoint ID con microsegundos, atomic write, cleanup de corruptos | `diff` confirma: Claude A == baseline |
| `mission_control/controller.py` | 3 fixes: `start_time`, `end_time`+duration, bounded history | `diff` confirma: Claude A == baseline |
| `boot/configurator.py` | 1 fix: atomic save | `diff` confirma: Claude A == baseline |
| `kernel/state.py` | 2 fixes: FSM validation, `last_error` tracking | `diff` confirma: Claude A == baseline |

---

## 5. Resumen de Decisiones Humanas Requeridas

Solo **4 conflictos** requieren decisión humana explícita del Arquitecto:

### Decisión 1 — Ownership del dashboard (C5 + I3)

**Pregunta:** ¿El dashboard debe ser inicializado por `kernel.boot()` (diseño original, RE lo conserva) o por `main.py` (diseño de Claude A, lo elimina del kernel)?

**Opción A (Claude A):** Dashboard fuera del kernel. Pros: menor acoplamiento, consistente con la separación critical/optional. Contras: cualquier código que asuma `kernel.get_component('dashboard')` debe ir al fallback.

**Opción B (RE):** Dashboard dentro del kernel. Pros: consistente con el diseño original. Contras: el dashboard no es crítico para el kernel, contradice la separación de Claude A.

**Recomendación del auditor:** Opción A (Claude A). El fallback de RE en main.py lo cubre.

### Decisión 2 — Default provider (C6)

**Pregunta:** ¿`default_provider` debe ser `"ollama"` (Claude A, local sin API key) o `"grok"` (RE/baseline, requiere API key)?

**Recomendación del auditor:** `"ollama"` (Claude A). Está alineado con el hardware objetivo del proyecto (laptop sin GPU, sin budget de nube garantizado). Requiere que se incluya `providers/ollama_provider.py` (I5).

### Decisión 3 — Shutdown delegation (C10 + I4)

**Pregunta:** ¿El shutdown de dashboard/recovery/command_mode debe ser manual en `main.py` (Claude A/baseline) o delegado en `kernel.shutdown()` (RE)?

**Opción A (RE):** Delegación total. Pros: más limpio, consistente con el patrón "kernel es orchestrator". Contras: requiere que `kernel.shutdown()` tenga aislamiento de fallos (C4), si no, un fallo starvation al resto.

**Opción B (Claude A):** Shutdowns manuales. Pros: no requiere el fix K-7 de RE. Contras: double-shutdown si `kernel.shutdown()` también los cierra.

**Recomendación del auditor:** Opción A (RE) **siempre que** se aplique también C4 (shutdown aislado de RE). El par es indivisible.

### Decisión 4 — Default provider sin Ollama (C6, variante)

**Pregunta condicional:** Si el Arquitecto decide que Ollama NO será el default (porque el entorno de producción sí tendrá API keys), ¿se debe mantener `providers/ollama_provider.py` como proveedor disponible (no default)?

**Recomendación del auditor:** Sí, mantener `ollama_provider.py` aunque no sea default. Es el único proveedor sin API key y es útil para desarrollo/testing. Cambiar `default_provider` a `"grok"` o `"gemini"` según el entorno.

---

## 6. Orden Recomendado de Fusión

### Fase 1 — Establecer la base (Claude A como base)

1. Partir de `cascade_pkg/sage_runtime_handoff/sage_runtime_fixed/` (rama Claude A).
2. Esta base ya tiene: boot phase con `_init_optional`, dispatcher conectado a provider_router, ollama_provider, fixes de config/memory/dispatcher, `WEB_AVAILABLE` en main.py.

### Fase 2 — Aplicar fixes de RE que NO tocan archivos de Claude A

Estos se aplican limpio, sin conflicto:

3. `events/bus.py` ← versión de RE (DLQ, idempotent start, deque history)
4. `events/models.py` ← versión de RE (EventHandler type hint)
5. `recovery/system.py` ← versión de RE (microsecond IDs, atomic write, corrupted cleanup)
6. `mission_control/controller.py` ← versión de RE (start_time, end_time, bounded history)
7. `boot/configurator.py` ← versión de RE (atomic save)
8. `kernel/state.py` ← versión de RE (FSM validation, record_error)

### Fase 3 — Aplicar fixes de RE que tocan archivos de Claude A (con cuidado)

9. `kernel/core.py` ← fusionar:
   - Mantener `_boot_phase()` de Claude A (C1) — incluye wiring `set_provider_router` (C7)
   - Mantener `_init_optional()` de Claude A
   - Mantener `default_provider="ollama"` de Claude A (C6)
   - Añadir campo `_shutdown_complete = False` de RE en `__init__` (C2)
   - Añadir reset `_shutdown_complete = False` en `boot()` de RE
   - Fusionar `execute_command()`: mantener None check de Claude A (C3) + usar `record_error` de RE
   - Reemplazar `shutdown()` con la versión de RE (C4) — per-component try/except + idempotency
   - **Decisión humana pendiente (C5):** mantener `_init_dashboard()` eliminado (Claude A) o restaurarlo (RE)

10. `main.py` ← fusionar:
    - Mantener `WEB_AVAILABLE` flag de Claude A (C8) — crítico
    - Mantener init condicional de web_server de Claude A
    - Aplicar cambio de dashboard de RE: `kernel.get_component('dashboard')` con fallback (C9)
    - **Decisión humana pendiente (C10):** aplicar delegación de shutdown de RE (eliminar `dashboard.shutdown()`/`recovery.shutdown()`/`command_mode.shutdown()` manuales) **si** se aplicó el shutdown aislado de RE en kernel/core.py (C4)

### Fase 4 — Verificación

11. Ejecutar `python scripts/test_runtime_engineer_fixes.py` — esperar 61/61 PASS.
12. Ejecutar `for t in tests/validate_pr*.py; do python "$t"; done` — esperar 6/7 PASS (PR-011 DependencyGraph FAIL es pre-existing, fuera de scope).
13. Ejecutar `python audit_runtime.py` — esperar ≥85% completion.
14. Ejecutar `python main.py` — esperar arranque limpio hasta "SAGE OS v4.5 Runtime Ready" sin crashes.

---

## 7. Riesgos No Resueltos por Este Audit

Estos riesgos están fuera del alcance de un audit de merge (son decisions de arquitectura / wiring futuro):

1. **Cascade's pending wiring work** (CLI start, Event Bus publishing, Recovery auto-trigger, Mission Control registration, Context Manager, Decision Engine). Ninguno de estos conflictos con los fixes de Claude A o de RE — son aditivos. Pero el auditor no puede garantizar que Cascade, al implementarlos, no toque las mismas zonas conflictivas identificadas aquí. **Recomendación:** Cascade debe leer este MERGE_AUDIT.md antes de empezar su wiring.

2. **`execute_command()` devuelve Task, no resultado** (Claude A, hallazgo #12 en `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md`). No es un conflicto de merge — es un bug de diseño pendiente de decisión. Lo menciono porque cualquier wiring futuro de CLI/web que asuma que `execute_command()` devuelve el resultado final se llevará un Task con `status=PENDING`.

3. **Operaciones SQLite bloqueantes sobre el event loop** (Claude A, hallazgo en `memory/engine.py` nota). No es un conflicto — es un tech debt documentado. Mencionado por completitud.

4. **El zip `Kimi_Agent_Planificador_de_Engine_de_Decision.zip`** contiene un sub-directorio `sage_analysis/` que incluye copias de los mismos zips (`HANDOFF_CASCADE_PAQUETE.zip`, `SAGE_Runtime_RuntimeEngineer_Submission.zip`, `sage_runtime.zip`) más un `SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip` que parece ser un aporte de Kimi para el Decision Engine. **Este audit no cubre el contenido de ese zip** porque el Decision Engine está fuera del alcance del mandato (especialización de Kimi, no de Claude A ni de RE). Si el Arquitecto quiere auditar la integración de Kimi también, se requiere un audit separado.

---

## 8. Conclusión

La fusión es **viable** con **decisión humana en 4 puntos** (C5, C6, C10, y la variante de C6). La dirección correcta es **Claude A como base + RE aplicado encima**, no al revés — porque RE se construyó sobre el baseline sin incluir los fixes de Claude A, mientras que Claude A se construyó sobre el mismo baseline sin incluir los fixes de RE. Ambas ramas son complementarias en su mayor parte (15 de 18 archivos no se solapan), pero los 2 archivos solapados (`kernel/core.py` y `main.py`) contienen **3 conflictos críticos** que rompen el sistema si se fusionan mal (C7 wiring perdido, C8 WEB_AVAILABLE perdido, I2 par indivisible).

**Recomendación final al Arquitecto:**

1. Confirmar las 4 decisiones humanas (sección 5).
2. Aplicar el orden de fusión de la sección 6.
3. Antes de hand-off a Cascade, correr la verificación de la fase 4.
4. Comunicar a Cascade que cualquier wiring futuro que toque `kernel/core.py` o `main.py` debe respetar las decisiones 1 y 3 de la sección 5.

— GLM (Integration Auditor)

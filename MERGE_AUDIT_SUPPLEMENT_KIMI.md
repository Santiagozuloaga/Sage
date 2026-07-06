# MERGE_AUDIT_SUPPLEMENT_KIMI.md — Suplemento: Integración de los 12 fixes de Kimi

**Auditor:** GLM (Integration Auditor)
**Fecha:** 2026-07-06
**Tipo:** Suplemento de `MERGE_AUDIT.md` — no reemplaza el audit original, lo extiende
**Documento base:** `/home/z/my-project/download/MERGE_AUDIT.md` (audit Claude A + RE)
**Documento de referencia:** `BUG_REPORT_KIMI.md` (Kimi — 12 fixes, 48/48 tests PASS)
**Formato:** Mismo formato `C#/I#` que MERGE_AUDIT.md, numeración **continua** desde C10/I6

---

## 0. Resumen Ejecutivo del Suplemento

**Hallazgo clave:** Kimi trabajó sobre la rama Claude A (no sobre el baseline), preservando intactos los 8 fixes de Claude A y portando los fixes S-1 y S-2 del Runtime Engineer. Su entrega es un **superset funcional** de Claude A + RE en los 4 archivos que toca.

**Archivos tocados por Kimi:** 4
- `kernel/state.py` — port S-1 + S-2 desde RE (idénticos funcionalmente a la versión de RE)
- `kernel/core.py` — 3 líneas en `execute_command` (cambia `error_count += 1` por `record_error(...)`)
- `dispatcher/engine.py` — 7 fixes nuevos (D-1 a D-7) sobre la base de Claude A
- `agents/router.py` — 3 fixes nuevos (A-1 a A-3), archivo antes no modificado por ninguna rama

**Archivos NO tocados por Kimi:** todos los demás, incluyendo `main.py`, `providers/`, `events/`, `recovery/`, `mission_control/`, `boot/`, `config/`, `memory/`, `repository_scanner/`. Esto significa que **Kimi no introduce conflictos nuevos** en las zonas calientes del MERGE_AUDIT original.

**Nuevos conflictos identificados:** **4** (2 conflictos archivo/método + 2 conflictos de integración cruzada). Solo **1 es crítico** (C12).

**Decisión humana nueva requerida:** **1** — estrategia de fusión del trío `kernel/state.py` (RE vs Kimi, ambos aportan S-1+S-2).

**Fusibilidad limpia con tercera fuente:** **SÍ** para `dispatcher/engine.py` y `kernel/core.py` (las dos zonas calientes que el Arquitecto pidió verificar). Detalle en secciones 4 y 5.

---

## 1. Mapeo Actualizado de Fuentes (4 ramas + baseline)

| Nombre lógico | Ubicación física | Origen | Relación con otras ramas |
|---|---|---|---|
| **Baseline** | `upload/sage_runtime.zip` | Opal extraction + PR-009 a PR-015 | — |
| **Rama Claude A** | `cascade_pkg/sage_runtime_handoff/sage_runtime_fixed/` | Baseline + 8 fixes de Claude A | Superset de baseline |
| **Rama RE** | `SAGE_Runtime_RuntimeEngineer_Submission.zip` | Baseline + 8 fixes de RE | Paralela a Claude A (no incluye sus fixes) |
| **Rama Kimi** | `SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip` | Claude A + 12 fixes de Kimi (incluye port de S-1 y S-2 de RE) | **Superset de Claude A. Comparte S-1/S-2 con RE.** |

**Implicación clave para la fusión final:** dado que Kimi ya es un superset de Claude A, la secuencia de fusión recomendada en MERGE_AUDIT.md §6 se simplifica. En lugar de "Claude A como base + RE encima", ahora es "Kimi como base + RE encima (excluyendo state.py, que Kimi ya tiene)".

---

## 2. Verificación: Kimi preserva los fixes críticos de Claude A

Antes de catalogar conflictos, confirmo empíricamente que la versión final de Kimi contiene **intactos** los fixes críticos de Claude A que MERGE_AUDIT.md marcó como 🔴 CRÍTICOS:

| Fix Claude A | Ubicación | Verificado en Kimi | Método de verificación |
|---|---|---|---|
| `_init_optional()` + `_degraded` (C1) | `kernel/core.py` | ✅ SÍ | `grep -c "_init_optional\|_degraded"` → 17 ocurrencias |
| Wiring `dispatcher.set_provider_router()` (C7) | `kernel/core.py` + `dispatcher/engine.py` | ✅ SÍ | `grep -c "set_provider_router"` → 2 en kernel, 4 en dispatcher |
| `default_provider="ollama"` (C6) | `kernel/core.py` línea 205 | ✅ SÍ | `grep -n 'default_provider'` → `"ollama"` |
| `providers/ollama_provider.py` (I5) | archivo nuevo | ✅ SÍ (no lo toca, lo hereda) | Kimi no modifica `providers/` |
| `WEB_AVAILABLE` en main.py (C8) | `main.py` | ✅ SÍ (no lo toca, lo hereda) | Kimi no modifica `main.py` |
| `itertools.count` tie-break (Claude A dispatcher fix) | `dispatcher/engine.py` | ✅ SÍ | `grep -c "itertools"` → 2 ocurrencias |
| `_execute_command` llamando `generate_text` | `dispatcher/engine.py` | ✅ SÍ | `grep -n "generate_text"` → llamada preservada línea 395 |
| Boot phase split critical/optional | `kernel/core.py` | ✅ SÍ | `_init_optional` + bloque crítico preservados |

**Conclusión:** Kimi es un **superset estricto** de Claude A. Ningún fix crítico de Claude A se pierde al adoptar la versión de Kimi de cualquiera de los 4 archivos que toca.

---

## 3. Catálogo de Conflictos (numeración continua desde MERGE_AUDIT.md)

Recordatorio de códigos: 🔴 CRÍTICO · 🟠 ALTO · 🟡 MEDIO · 🟢 BAJO

---

### C11 — `kernel/state.py` · métodos S-1 + S-2 · duplicación idéntica entre RE y Kimi

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/state.py` |
| **Método** | `_ALLOWED_TRANSITIONS` (mapa), `transition_to()`, `record_error()`, `clear_error()`, campo `last_error` |
| **Líneas RE** | 1-144 (archivo completo reescrito) |
| **Líneas Kimi** | 1-159 (archivo completo reescrito) |
| **Ramas afectadas** | RE, Kimi |
| **Tipo de conflicto** | Duplicación funcional idéntica — ambas ramas implementan el mismo fix (S-1 FSM validation + S-2 last_error) con diferencias puramente cosméticas (comentarios, nombres de imports). |
| **Gravedad** | 🟢 BAJO |
| **Riesgo** | Cero a nivel funcional. Si se intenta un merge de 3 vías (baseline + RE + Kimi), el merge tool marcará conflicto porque las dos versiones difieren en comentarios/whitespace, pero la resolución es trivial: tomar cualquiera de las dos (son equivalentes). |
| **Solución recomendada** | Tomar la versión de **Kimi** porque: (a) ya está alineada con Claude A (Kimi portó S-1/S-2 sobre la base de Claude A); (b) la versión de RE fue escrita sobre el baseline y requiere que el merge posterior aplique los fixes de Claude A por separado. Tomar la versión de Kimi elimina un paso de fusión. |
| **¿Auto-fusionable?** | Sí, con resolución manual trivial (elegir una de las dos versiones idénticas funcionalmente). |
| **¿Requiere decisión humana?** | **SÍ (Decisión K1).** Pregunta: ¿qué versión de `kernel/state.py` se adopta — la de RE o la de Kimi? Auditor recomienda Kimi. |

---

### C12 — `kernel/core.py` · método `execute_command()` · handler de excepciones triplicado

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `execute_command()` (bloque `except Exception as e:`) |
| **Líneas baseline** | 232 (`self.context.error_count += 1`) |
| **Líneas Claude A** | 252-258 (cambio en acceso al dispatcher: `self._components.get('dispatcher')` con None check + mensaje de degradado) |
| **Líneas RE** | 242 (`self.context.record_error(f"Command {command!r} failed: {e}")`) — sobre baseline, no sobre Claude A |
| **Líneas Kimi** | 268-273 (`self.context.record_error(f"Command {command!r} failed: {e}")` + 3 líneas de comentario) — **sobre Claude A** |
| **Ramas afectadas** | Claude A, RE, Kimi |
| **Tipo de conflicto** | Triple origen — Claude A cambia el acceso al dispatcher (None check), RE cambia el handler de error (record_error) sobre baseline, Kimi cambia el mismo handler de error (record_error) **sobre Claude A**. |
| **Gravedad** | 🔴 CRÍTICO |
| **Riesgo** | Si se fusiona mal: (a) tomar el handler de RE sin la base de Claude A → el `self._components['dispatcher']` (sin `.get`) sigue siendo KeyError crudo si dispatcher está degradado; (b) tomar el handler de Kimi sin el None check de Claude A → imposible, porque Kimi ya está sobre Claude A (el None check está presente); (c) tomar ambos handlers (RE y Kimi) → imposible, son la misma línea mutada. |
| **Solución recomendada** | Tomar la versión de **Kimi** íntegramente. Kimi ya resolvió este conflicto: aplicó el None check de Claude A **Y** el `record_error` de RE en la misma versión. Es la fusión manual que MERGE_AUDIT.md C3 recomendaba hacer. |
| **¿Auto-fusionable?** | No con merge tool estándar (3 orígenes sobre la misma línea). Sí con merge tool de 4 vías si Kimi se trata como "la versión ya fusionada". |
| **¿Requiere decisión humana?** | No, si se adopta la regla "Kimi es la base". Sí, si se quiere re-aplicar el handler de RE manualmente sobre la base de Claude A (innecesario — Kimi ya lo hizo). |

---

### I7 — `kernel/state.py` + `kernel/core.py` · dependencia `record_error()` resuelta por Kimi

| Campo | Valor |
|---|---|
| **Archivos** | `kernel/state.py` (define el método) + `kernel/core.py` (lo llama) |
| **Métodos** | `KernelContext.record_error()` + `SageKernel.execute_command()` exception handler |
| **Líneas RE state.py** | 119-140 (método `record_error` + `clear_error` + campo `last_error`) |
| **Líneas RE core.py** | 242 (`self.context.record_error(...)`) — sobre baseline |
| **Líneas Kimi state.py** | 119-140 (método `record_error` + `clear_error` + campo `last_error`) — idéntico funcionalmente |
| **Líneas Kimi core.py** | 268-273 (`self.context.record_error(...)`) — sobre Claude A |
| **Ramas afectadas** | RE, Kimi |
| **Tipo de conflicto** | Dependencia cruzada que ya está resuelta en Kimi. MERGE_AUDIT.md I1 marcaba este conflicto como "si se mergea RE core.py sin RE state.py → AttributeError en runtime". Kimi elimina el riesgo porque su versión de `kernel/core.py` ya viene emparejada con su versión de `kernel/state.py` (ambas incluyen `record_error`). |
| **Gravedad** | 🟢 BAJO (reducido desde MEDIO del MERGE_AUDIT original) |
| **Riesgo** | Cero si se adopta Kimi como base para estos dos archivos. Si se mezcla la versión de RE de `kernel/state.py` con la versión de Kimi de `kernel/core.py` (o viceversa), el método `record_error` sigue existiendo (ambas versiones lo definen idéntico) — no hay AttributeError. |
| **Solución recomendada** | Tomar AMBOS archivos (`kernel/state.py` y `kernel/core.py`) de Kimi. Esto elimina el conflicto I1 del MERGE_AUDIT original. |
| **¿Auto-fusionable?** | Sí. |
| **¿Requiere decisión humana?** | No (mismo que C11 — la decisión K1 los resuelve a ambos). |

---

### I8 — `dispatcher/engine.py` + `agents/router.py` · dependencia futura `release_agent()` (Kimi A-2)

| Campo | Valor |
|---|---|
| **Archivos** | `dispatcher/engine.py` (debería llamar `release_agent` al completar tarea) + `agents/router.py` (define `release_agent` en A-2) |
| **Métodos** | `TaskDispatcher._execute_task()` finally block + `AgentRouter.release_agent()` |
| **Líneas Kimi agents/router.py** | método `release_agent(agent_id)` añadido por fix A-2 |
| **Líneas Kimi dispatcher/engine.py** | `_execute_task` no llama a `release_agent` (Kimi lo documenta como pregunta abierta #2 en BUG_REPORT_KIMI.md) |
| **Ramas afectadas** | Kimi (define el método), Cascade (debería llamarlo en su wiring futuro) |
| **Tipo de conflicto** | Dependencia futura — Kimi añade un método que aún no se invoca desde ningún caller. El propio Kimi lo señala como "Open Question #2: Should this be wired into `dispatcher._execute_task()`'s finally block, or is it Cascade's responsibility?" |
| **Gravedad** | 🟡 MEDIO |
| **Riesgo** | Si Cascade en su wiring futuro decide llamar `release_agent()` desde `_execute_task` **sin saber que Kimi ya lo definió** → puede reimplementar el método o asumir que no existe. Bajo riesgo porque la firma es clara (`release_agent(agent_id: str) -> None`), pero requiere coordinación. Si **nadie** llama a `release_agent` → el contador `_agent_load` crece indefinidamente, pero como A-2 ordena los candidatos por `_agent_load` y el efecto solo es desequilibrar la carga (no rompe nada), es degradación silenciosa, no crash. |
| **Solución recomendada** | Documentar en el handoff a Cascade que `release_agent()` ya existe y debe ser llamado desde `_execute_task()` cuando una tarea completa (status COMPLETED, FAILED, o CANCELLED). NO requiere acción inmediata — el sistema funciona sin esto, solo con desequilibrio de carga potencial. |
| **¿Auto-fusionable?** | N/A (no es un conflicto de fusión, es un wiring pendiente). |
| **¿Requiere decisión humana?** | Sí, pero pospuesta a Cascade. Pregunta para Cascade: ¿`release_agent()` se llama desde `_execute_task()` (responsabilidad del dispatcher) o desde el wiring que Cascade añada entre dispatcher y agent_router? Kimi propone ambas opciones como válidas. |

---

## 4. Foco solicitado: `dispatcher/engine.py` con 3 fuentes

El Arquitecto pidió verificar específicamente si `dispatcher/engine.py` (ya marcado como caliente en MERGE_AUDIT.md §4 🔴) sigue siendo fusionable limpio con una tercera fuente encima.

### Análisis línea por línea

| Sección del archivo | Baseline | Claude A | RE | Kimi | ¿Conflicto? |
|---|---|---|---|---|---|
| Imports top-level | `from collections import deque` | `import itertools` + `from typing import ... List` | sin cambios | `from collections import OrderedDict` (reemplaza `deque`) | 🟢 NO — Kimi hereda `itertools` y `List` de Claude A, solo cambia `deque` por `OrderedDict` (porque D-2 necesita OrderedDict y `deque` ya no se usa después del fix de Claude A) |
| Constantes módulo | (ninguna) | (ninguna) | sin cambios | `DEFAULT_COMPLETED_TASK_LIMIT = 500`, `TASK_EXECUTION_TIMEOUT = 60` | 🟢 NO — aditivo |
| `__init__()` | `_task_counter = 0`, `_completed_tasks: Dict` | `_sequence = itertools.count()`, `_provider_router = None` | sin cambios | `_completed_tasks: OrderedDict` (cambia tipo), preserva `_sequence` y `_provider_router` | 🟢 NO — Kimi preserva los campos de Claude A |
| `set_provider_router()` | (no existe) | método añadido | sin cambios | preservado intacto | 🟢 NO |
| `start()` | sin guard | sin cambios | sin cambios | idempotency guard añadido (D-1) | 🟢 NO — aditivo |
| `stop()` | sin limpieza | sin cambios | sin cambios | limpia `_semaphore` y `_task_queue` (D-3) | 🟢 NO — aditivo |
| `_process_tasks()` | sin `CancelledError` handler | sin cambios | sin cambios | añade `except asyncio.CancelledError: break` | 🟢 NO — aditivo |
| `_execute_task()` | `_execute_command(task.command)` directo | sin cambios al body | sin cambios | branch multi-agent (D-4) + `asyncio.wait_for` timeout (D-6) + `OrderedDict.popitem` (D-2) | 🟢 NO — Kimi envuelve la llamada existente, no la reemplaza |
| `_execute_command()` | placeholder `f"Executed: {command}"` | llamada real a `provider_router.generate_text()` con flag `stub: True/False` | sin cambios | **preservado intacto de Claude A** | 🟢 NO — Kimi no toca este método |
| `dispatch_multi_agent()` | solo encola, no ejecuta multi-agente | sin cambios | sin cambios | `_execute_task` ahora detecta `metadata["multi_agent"]` y rutea a `_execute_multi_agent` (D-4) | 🟢 NO — aditivo, no cambia la API existente |
| `delegate_to_agent()` | devuelve ID stub sin encolar | sin cambios | sin cambios | crea `Task` real y encola con prioridad HIGH (D-5) | 🟢 NO — cambio interno, return type (`str`) preservado |
| `cancel_task()` | (no existe) | (no existe) | sin cambios | método nuevo añadido (D-7) | 🟢 NO — aditivo |
| `aggregate_results()` | sin cambios | sin cambios | sin cambios | sin cambios | 🟢 NO |

### Conclusión sobre `dispatcher/engine.py`

**Fusionable limpio.** No hay conflictos. La versión de Kimi ya contiene todos los fixes de Claude A (preserva `itertools.count`, `set_provider_router`, `generate_text`, `stub: True/False`) y añade 7 fixes propios que son todos aditivos o envolventes (no reemplazan nada existente).

**Acción de fusión:** Tomar la versión de Kimi de `dispatcher/engine.py` íntegramente. No requiere merge de 3 vías porque Kimi ya es un superset de Claude A, y RE no modificó este archivo.

**Verificación empírica:** confirmado vía `diff -u cascade_pkg/.../dispatcher/engine.py kimi_submission/dispatcher/engine.py` — Kimi añade 159 líneas, elimina 7 líneas (todas de la versión de Claude A: `from collections import deque`, `Dict[str, Task]` por `OrderedDict[str, Task]`, el placeholder `# Execute the command (placeholder...)` que ya no aplica). Ninguna línea eliminada es un fix crítico de Claude A.

---

## 5. Foco solicitado: `kernel/core.py` con 3 fuentes

### Análisis sección por sección

| Sección del archivo | Baseline | Claude A | RE | Kimi | ¿Conflicto? |
|---|---|---|---|---|---|
| `__init__()` | sin campos nuevos | añade `_degraded` | añade `_shutdown_complete` | hereda Claude A (`_degraded`), **NO tiene** `_shutdown_complete` | 🟠 VER C13 abajo |
| `boot()` | sin cambios | sin cambios | reset `_shutdown_complete=False` | hereda Claude A, **NO tiene** el reset | 🟠 VER C13 abajo |
| `_boot_phase()` | secuencia plana | reestructurado con `_init_optional` + wiring | solo whitespace | hereda Claude A íntegramente | 🟢 NO |
| `_init_optional()` | (no existe) | método añadido | sin cambios | preservado | 🟢 NO |
| `_init_config/memory/event_bus/...` | secuencia lineal | critical tier + optional tier | sin cambios | preservado | 🟢 NO |
| `_init_provider_router()` | `default_provider="grok"` | `default_provider="ollama"` | sin cambios | `default_provider="ollama"` (hereda Claude A) | 🟢 NO |
| `_init_dashboard()` | existe | **eliminado** | existe (preservado) | **eliminado** (hereda Claude A) | 🟢 NO — consistente con la Decisión 1 del Arquitecto |
| `execute_command()` | `error_count += 1` | None check en acceso al dispatcher | `record_error()` sobre baseline | `record_error()` **sobre Claude A** (incluye None check) | 🔴 VER C12 arriba — RESUELTO por Kimi |
| `shutdown()` | sin aislamiento, sin idempotencia | sin cambios | aislamiento + idempotencia | hereda Claude A, **NO tiene** los fixes de RE | 🟠 VER C13 abajo |
| `degraded_components` / `is_degraded` | (no existen) | propiedades añadidas | sin cambios | preservado | 🟢 NO |

### C13 — `kernel/core.py` · ausencia de los fixes K-7 y K-8 de RE en la versión de Kimi

| Campo | Valor |
|---|---|
| **Archivo** | `kernel/core.py` |
| **Método** | `__init__()` (campo `_shutdown_complete`), `boot()` (reset del flag), `shutdown()` (aislamiento de fallos + idempotencia) |
| **Líneas RE** | campo `_shutdown_complete = False` en `__init__`, reset en `boot()`, reescritura completa de `shutdown()` con per-component try/except + idempotency guard |
| **Líneas Kimi** | **NO contiene** ninguno de estos cambios — Kimi hereda la versión de Claude A de `shutdown()` (== baseline, sin aislamiento ni idempotencia) |
| **Ramas afectadas** | RE, Kimi |
| **Tipo de conflicto** | Asimetría — Kimi portó S-1 y S-2 de RE pero **no** K-7 ni K-8. Probable razón: K-7/K-8 son fixes del módulo kernel core, no de state.py, y Kimi (Scheduler/Decision Engine specialist) priorizó portar los fixes de su especialización. |
| **Gravedad** | 🟠 ALTO |
| **Riesgo** | Si se toma la versión de Kimi de `kernel/core.py` íntegramente (sin re-aplicar K-7/K-8 de RE): (a) un componente que falle en `shutdown()` starvation al resto (resource leak) — bug K-7 queda sin fix; (b) doble `shutdown()` re-transiciona y re-intenta cerrar componentes ya cerrados — bug K-8 queda sin fix. **No rompe el arranque**, pero degrada el cierre limpio. Si se toma la versión de RE de `kernel/core.py` (sin la base de Claude A): se pierden `_init_optional`, `_degraded`, wiring `set_provider_router`, `default_provider="ollama"` — el sistema no arranca o no tiene LLM. |
| **Solución recomendada** | **Tomar la versión de Kimi de `kernel/core.py` como base** (porque incluye los fixes de Claude A) **y re-aplicar manualmente los fixes K-7 y K-8 de RE encima**. Es un cambio de 3 zonas puntuales: (1) añadir `self._shutdown_complete = False` en `__init__`, (2) añadir `self._shutdown_complete = False` en `boot()`, (3) reemplazar el body de `shutdown()` con la versión aislada + idempotente de RE. Las 3 zonas **no se solapan** con ningún cambio de Kimi (Kimi solo tocó `execute_command`). |
| **¿Auto-fusionable?** | Sí con merge tool de 3 vías (baseline + Kimi + RE) — las zonas tocadas por RE (`__init__`, `boot`, `shutdown`) y por Kimi (`execute_command`) están a 50+ líneas de distancia y no se solapan. |
| **¿Requiere decisión humana?** | No, si se sigue la regla "Kimi como base + RE encima para los archivos que Kimi no tocó o no portó". Sí, si se quiere decidir no aplicar K-7/K-8 (no recomendado — son fixes de robustez). |

### Conclusión sobre `kernel/core.py`

**Fusionable limpio con una operación manual.** La versión de Kimi ya resuelve el conflicto C3 del MERGE_AUDIT original (handler `record_error` sobre Claude A), pero deja sin aplicar los fixes K-7 y K-8 de RE. La re-aplicación es trivial (3 zonas puntuales, no solapadas con el trabajo de Kimi).

**Acción de fusión:**
1. Tomar `kernel/core.py` de Kimi íntegramente.
2. Re-aplicar manualmente:
   - `__init__`: añadir `self._shutdown_complete = False`
   - `boot()`: añadir `self._shutdown_complete = False` al final
   - `shutdown()`: reemplazar el body con la versión de RE (per-component try/except + idempotency guard + `self._shutdown_complete = True` al final)
3. Esta re-aplicación es exactamente lo que MERGE_AUDIT.md §6 Fase 3 ya recomendaba para el archivo `kernel/core.py`.

---

## 6. Actualización del cuadro de decisiones humanas

El MERGE_AUDIT original tenía 4 decisiones humanas. El Arquitecto ya las resolvió todas. Este suplemento añade **1 decisión nueva**:

### Decisión K1 — Versión de `kernel/state.py` (C11 + I7)

**Pregunta:** ¿Qué versión de `kernel/state.py` se adopta en la fusión final — la de RE o la de Kimi?

**Contexto:** Ambas implementan los mismos fixes (S-1 FSM validation + S-2 last_error) con diferencias puramente cosméticas. RE la escribió sobre el baseline; Kimi la portó sobre Claude A.

**Recomendación del auditor:** **Versión de Kimi.** Razones:
1. Ya está alineada con Claude A — elimina un paso de fusión.
2. Los comentarios son más completos (documenta que es un port desde RE).
3. Funcionalmente idéntica a la de RE (verificado vía diff de líneas funcionales).

**Impacto de elegir RE en su lugar:** habría que re-aplicar manualmente los fixes de Claude A sobre la versión de RE de `state.py` (en este caso, ninguno, porque Claude A no modificó `state.py`). En la práctica, ambas opciones son equivalentes, pero Kimi requiere menos trabajo.

---

## 7. Actualización del orden de fusión recomendado

El MERGE_AUDIT original §6 recomendaba 4 fases. Con Kimi en el cuadro, se simplifica:

### Fase 1 — Establecer la base (Kimi como base, no Claude A)

1. Partir de `kimi_submission/sage_runtime_fixed/` (rama Kimi).
2. Esta base ya tiene: todos los fixes de Claude A + S-1/S-2 portados de RE + 12 fixes propios de Kimi (D-1 a D-7, A-1 a A-3).

**Nota:** Kimi solo incluye 4 archivos en su zip. El resto del árbol debe venir de Claude A (`cascade_pkg/sage_runtime_handoff/sage_runtime_fixed/`). En la práctica: empezar con el árbol completo de Claude A y sobrescribir los 4 archivos de Kimi encima.

### Fase 2 — Aplicar fixes de RE que Kimi NO portó

Estos se aplican limpio, sin conflicto:

3. `events/bus.py` ← versión de RE (DLQ, idempotent start, deque history)
4. `events/models.py` ← versión de RE (EventHandler type hint)
5. `recovery/system.py` ← versión de RE (microsecond IDs, atomic write, corrupted cleanup)
6. `mission_control/controller.py` ← versión de RE (start_time, end_time, bounded history)
7. `boot/configurator.py` ← versión de RE (atomic save)

### Fase 3 — Re-aplicar K-7 y K-8 de RE sobre `kernel/core.py` de Kimi

8. En `kernel/core.py` (versión Kimi):
   - `__init__`: añadir `self._shutdown_complete = False`
   - `boot()`: añadir `self._shutdown_complete = False` al final
   - `shutdown()`: reemplazar el body con la versión de RE (per-component try/except + idempotency guard)

### Fase 4 — Aplicar decisiones del Arquitecto sobre `main.py`

9. `main.py` ← fusionar según MERGE_AUDIT.md §6 Fase 3 (decisiones ya tomadas por el Arquitecto):
   - Mantener `WEB_AVAILABLE` flag de Claude A
   - Aplicar cambio de dashboard de RE: `kernel.get_component('dashboard')` con fallback
   - Aplicar delegación de shutdown de RE (eliminar shutdowns manuales)
   - **Decisión del Arquitecto confirmada:** dashboard fuera del kernel (consistente con Kimi, que heredó la eliminación de Claude A)

### Fase 5 — Verificación

10. Ejecutar `python scripts/test_runtime_engineer_fixes.py` — esperar 61/61 PASS.
11. Ejecutar `python scripts/test_kimi_fixes.py` — esperar 48/48 PASS.
12. Ejecutar `for t in tests/validate_pr*.py; do python "$t"; done` — esperar 6/7 PASS (PR-011 DependencyGraph FAIL es pre-existing).
13. Ejecutar `python audit_runtime.py` — esperar ≥85% completion.
14. Ejecutar `python main.py` — esperar arranque limpio hasta "SAGE OS v4.5 Runtime Ready" sin crashes.

---

## 8. Resumen de fusibilidad con tercera fuente

| Archivo caliente | ¿Fusionable limpio con 3 fuentes? | Acción requerida |
|---|---|---|
| `dispatcher/engine.py` | ✅ SÍ | Tomar versión de Kimi íntegramente. Superset de Claude A + 7 fixes propios. RE no lo modificó. |
| `kernel/core.py` | ✅ SÍ con 1 paso manual | Tomar versión de Kimi + re-aplicar K-7/K-8 de RE (3 zonas puntuales no solapadas con Kimi). |
| `kernel/state.py` | ✅ SÍ | Tomar versión de Kimi (o RE — son idénticas funcionalmente). |
| `agents/router.py` | ✅ SÍ | Tomar versión de Kimi. Ninguna otra rama lo modificó. |
| `main.py` | ✅ SÍ (sin cambios respecto a MERGE_AUDIT original) | Kimi no lo tocó. Aplicar la Fase 4 del §7. |
| `providers/*` | ✅ SÍ (sin cambios respecto a MERGE_AUDIT original) | Kimi no los tocó. Aplicar I5 (trío indivisible de Claude A). |

**Conclusión final:** la incorporación de Kimi **no introduce conflictos nuevos que rompan el sistema**. El único conflicto crítico (C12) ya está resuelto en la propia versión de Kimi. El resto son conflictos de duplicación funcional (C11) o de dependencia futura para Cascade (I8). La fusión de las 3 fuentes (Claude A + RE + Kimi) es **viable con 1 decisión humana trivial (K1)** y **1 operación manual de re-aplicación (C13)**.

---

## 9. Archivos del suplemento

- Este documento: `MERGE_AUDIT_SUPPLEMENT_KIMI.md`
- Documento base: `MERGE_AUDIT.md` (no modificado, sigue vigente)
- Fuente de los 12 fixes: `BUG_REPORT_KIMI.md` (incluido en el zip de Kimi)

— GLM (Integration Auditor)

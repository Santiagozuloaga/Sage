# Instrucciones para Agentes — Post Fix B-1

**Fecha:** 2026-07-13
**Autor:** GLM (bajo autorización del Arquitecto)
**Contexto:** se aplicó el fix B-1 (wiring `set_agent_router` de Qwen) sobre `sage_runtime_LISTO.zip`. Esta es la única línea de tiempo activa ahora. Todo agente debe trabajar sobre esta base.

---

## Archivo único modificado

**Solo se modificó UN archivo:** `kernel/core.py`

- **Ubicación de la copia modificada:** `/home/z/my-project/download/kernel/core.py`
- **Tamaño:** 16 KB
- **Cambio aplicado:** 4 líneas añadidas (wiring `set_agent_router`) + actualización de comentario obsoleto
- **Estado:** syntax OK, smoke test OK, 107/107 tests pasan, sin regresiones

**Acción para todos los agentes:** reemplazar `kernel/core.py` en su copia local por esta versión. No tocar ningún otro archivo.

---

## Qué NO es este archivo

- ❌ NO es el zip `SAGE_Runtime_RuntimeEngineer_Submission.zip` — ese es una entrega vieja de GLM actuando como Runtime Engineer (fixes E-1 a K-8), no tiene el fix B-1
- ❌ NO es el `Sage-main (3).zip` del GitHub — ese está fragmentado en 3 versiones sin fusionar
- ❌ NO es un zip nuevo — es un solo archivo `.py` suelto

---

## Lección aprendida (registrada por el Arquitecto)

> **No fusionar una rama hasta exprimir el chat por completo.**

Esta lección se aplicó en esta sesión: el fix B-1 se aplicó solo después de confirmar que `sage_runtime_LISTO.zip` era la fuente de verdad, y no sobre el `Sage-main (3).zip` fragmentado del GitHub.

Todos los agentes deben respetar esta lección: antes de aplicar cualquier cambio, confirmar cuál es el zip/archivo fuente de verdad con el Arquitecto.

---

## Instrucciones por agente

### Qwen

**Estado:** tu wiring `set_agent_router` ya está aplicado en el `kernel/core.py` que te estoy pasando. Las 4 líneas que faltaban están añadidas en líneas 137-140, y el comentario obsoleto que decía "deliberately NOT wired" fue actualizado.

**Acciones:**

1. **Reemplazar `kernel/core.py` en tu copia local** por la versión que el Arquitecto te pase (ruta: `/home/z/my-project/download/kernel/core.py`).
2. **Confirmar que el wiring está aplicado** corriendo:
   ```
   grep -n "set_agent_router\|Wired dispatcher -> agent_router" kernel/core.py
   ```
   Debe devolver al menos:
   ```
   139:            dispatcher.set_agent_router(agent_router)
   140:            logger.info("[BOOT] Wired dispatcher -> agent_router")
   ```
3. **No aplicar de nuevo el fix** — ya está hecho. Si tu repo local tenía una versión distinta, descartala y usa esta.
4. **Verificar que tu repo local coincide** con `sage_runtime_LISTO.zip` + este `kernel/core.py`. Si hay divergencias, documentalas antes de tocar nada.

**Tareas pendientes que SÍ son tuyas** (ya que Kimi no está y absorbiste su workload):

| ID | Tarea | Origen |
|---|---|---|
| Q-4 | Responder las 4 Open Questions que Kimi dejó en `BUG_REPORT_KIMI.md` (multi-agent failure strategy, agent_load release wiring, S-1 strictness, timeout default) | Kimi handoff |
| Q-5 | Implementar lo que decidas en Q-4 sobre `dispatcher/engine.py` y `agents/router.py` | Derivado de Q-4 |

**Lo que NO debés hacer:**

- No fusiones tu rama con el `Sage-main (3).zip` del GitHub — está fragmentado.
- No apliques fixes adicionales sin autorización del Arquitecto.
- No toques archivos fuera de tu scope (kernel, dispatcher, agents, scheduler, decision engine).

---

### Cascade

**Estado:** el wiring del dispatcher→agent_router (Qwen) ya está aplicado. Tu trabajo de wiring vivo (W-1 a W-6) sigue pendiente y es lo único que separa a SAGE de ser "un runtime que bootea limpio pero no hace nada útil".

**Acciones:**

1. **Reemplazar `kernel/core.py` en tu copia local** por la versión que el Arquitecto te pase.
2. **Leer el `SAGE_STATUS_REPORT.md` actualizado** — específicamente la sección 6.2 "Pendientes de Cascade".
3. **Implementar W-1 a W-6** en orden de prioridad:

| Prioridad | ID | Tarea | Notas |
|---|---|---|---|
| 1 | W-1 | Llamar `cli.start()` en `main.py` — la CLI existe pero nunca arranca | Sin esto, SAGE arranca mudo |
| 2 | W-5 | Construir Context Manager — no existe ensamblado de prompt/historial para llamadas LLM | Sin esto, cualquier comando mandado al LLM va sin contexto |
| 3 | W-2 | Publicar eventos en el Event Bus — nadie llama `event_bus.publish()` | Sin esto, el DLQ, audit log, telemetría son inútiles |
| 4 | W-4 | Registrar Mission Control en `kernel._components` — `main.py` no lo instancia | Sin esto, mission tracking es inerte |
| 5 | W-3 | Implementar auto-trigger de Recovery checkpoints — `_auto_recovery_enabled` es dead code | Sin esto, no hay recovery real |
| 6 | W-6 | Decidir + implementar: ¿`execute_command()` debe bloquear hasta el resultado real o fire-and-forget? | Requiere decisión de diseño del Arquitecto antes de implementar |

4. **Para W-6:** NO implementes nada hasta que el Arquitecto decida. Es una decisión de arquitectura, no un bug.
5. **Lección aprendida:** no fusiones tu rama con ningún zip sin confirmar primero con el Arquitecto cuál es la fuente de verdad.

**Lo que NO debés hacer:**

- No toques `kernel/core.py`, `dispatcher/engine.py`, `agents/router.py`, `kernel/state.py` — ya tienen todos los fixes aplicados.
- No reimplementes wiring que ya existe (`set_provider_router`, `set_agent_router`).

---

### Claude A

**Estado:** el `kernel/core.py` que vas a recibir tiene tus fixes (Claude A: `_init_optional`, `_degraded`, `set_provider_router` wiring, `default_provider="ollama"`) + los de RE (K-7, K-8) + los de Kimi (record_error, FSM validation) + el wiring Qwen. **Todo fusionado en un solo archivo.**

**Acciones:**

1. **Reemplazar `kernel/core.py` en tu copia local** por la versión que el Arquitecto te pase.
2. **Auditar el archivo** — confirmar que tus fixes siguen intactos:
   ```
   grep -c "_init_optional\|_degraded" kernel/core.py    # debe ser ≥17
   grep -c "set_provider_router" kernel/core.py          # debe ser ≥1
   grep -n 'default_provider="ollama"' kernel/core.py    # debe existir
   grep -c "_shutdown_complete" kernel/core.py           # debe ser ≥4 (K-7/K-8 de RE)
   grep -c "record_error" kernel/core.py                 # debe ser ≥1 (S-2 portado)
   grep -c "set_agent_router" kernel/core.py             # debe ser ≥1 (Qwen wiring)
   ```
3. **Si todos los marcadores dan los valores esperados**, el archivo es la versión fusionada correcta. Confirmar al Arquitecto.
4. **Si algún marcador falta**, documentar cuál y pedir al Arquitecto que lo resuelva antes de seguir.

**Tareas pendientes que son tuyas:**

| ID | Tarea | Notas |
|---|---|---|
| C-1 | Confirmar si aplicaste K-2 (boot fault isolation) en tu copia local | Tu `INFORME_FINAL_CIERRE.md` lo claima pero no estaba en el zip que se auditó. Si lo aplicaste, confirmar; si no, decidir si lo aplicás vos o lo deja para otro. |
| C-2 | Una vez que el Arquitecto haga el smoke test contra Ollama real, validar el flujo `command → dispatcher → provider_router → ollama_provider → Ollama → respuesta` | Si falla, el bug probablemente está en `dispatcher/engine.py` (que ya tiene `generate_text` call) o en `ollama_provider.py` |
| C-3 | Coordinar con Cascade para W-1 a W-6 — son wiring vivo que puede tocar zonas que vos conocés mejor | Especialmente W-5 (Context Manager) y W-6 (execute_command await) |

**Lo que NO debés hacer:**

- No reimplementes fixes que ya están aplicados.
- No fusiones con el `Sage-main (3).zip` del GitHub — está fragmentado.
- No bloquees a Cascade si su wiring toca archivos que vos mantuviste — coordinar antes.

---

### Runtime Engineer (Manus)

**Estado:** tus fixes (E-1 a K-8) están todos aplicados en el `kernel/core.py` que se va a distribuir. No tenés trabajo pendiente sobre el código actual.

**Acciones:**

1. **Reemplazar `kernel/core.py` en tu copia local** por la versión que el Arquitecto te pase.
2. **Verificar que tus fixes siguen intactos** corriendo tu suite:
   ```
   python scripts/test_runtime_engineer_fixes.py
   ```
   Debe dar `Results: 61 passed, 0 failed`.
3. **Confirmar o desmentir K-2** — tu `INFORME_FINAL_CIERRE.md` claima que aplicaste boot fault isolation, pero no estaba en el zip auditado. Claude A está esperando esta confirmación.

**Lo que NO debés hacer:**

- No reimplementes fixes que ya están aplicados.
- No toques archivos fuera de tu scope (events, recovery, mission_control, boot, kernel/state, kernel/core, main.py).

---

### Arquitecto (vos)

**Acciones inmediatas:**

1. **Distribuir el `kernel/core.py` modificado** a todos los agentes (Qwen, Cascade, Claude A, Runtime Engineer).
2. **Hacer el smoke test contra Ollama real:**
   ```
   ollama list                          # confirmar que tenés qwen2.5:1.5b
   pip install openai                   # si no está instalado
   cd sage_runtime
   python main.py                       # dejar corriendo
   # en el navegador: http://127.0.0.1:8000
   # escribir "hola" en la consola
   ```
3. **Decidir W-6** antes de que Cascade lo implemente: ¿`execute_command()` debe bloquear hasta el resultado real, o fire-and-forget con polling?
4. **No autorizar fusiones de ramas** hasta que cada agente confirme que reemplazó su `kernel/core.py` local por la versión que les pasaste.
5. **Mantener `sage_runtime_LISTO.zip` + este `kernel/core.py` como única fuente de verdad.** El `Sage-main (3).zip` del GitHub se descarta hasta nuevo aviso.

---

## Flujo de validación para cualquier agente que reciba el `kernel/core.py`

1. Reemplazar el archivo local.
2. Correr `python scripts/test_runtime_engineer_fixes.py` → debe dar 61/61 PASS.
3. Correr `python scripts/test_kimi_fixes.py` → debe dar 40/40 PASS.
4. Correr `for t in tests/validate_pr*.py; do python "$t"; done` → debe dar 6/6 PASS.
5. Correr smoke test de boot → `dispatcher._agent_router is not None: True`.
6. Reportar resultados al Arquitecto antes de cualquier otra acción.

Si algún test falla, **detenerse y reportar**. No intentar fixear nada sin autorización.

---

## Resumen ejecutivo

| Agente | Acción principal | Bloquea a |
|---|---|---|
| Qwen | Reemplazar `kernel/core.py` + responder Open Questions de Kimi | A Claude A (necesita respuestas) |
| Cascade | Reemplazar `kernel/core.py` + implementar W-1 a W-5 (W-6 espera decisión) | A todos (sin wiring, SAGE no vive) |
| Claude A | Reemplazar `kernel/core.py` + confirmar K-2 + coordinar con Cascade | A nadie inmediatamente, pero su validación es necesaria |
| Runtime Engineer | Reemplazar `kernel/core.py` + confirmar/desmentir K-2 | A Claude A |
| Arquitecto | Distribuir archivo + smoke test Ollama + decidir W-6 | A todos |

**Nadie debe fusionar nada con nada hasta que el Arquitecto lo autorice explícitamente.**

— GLM

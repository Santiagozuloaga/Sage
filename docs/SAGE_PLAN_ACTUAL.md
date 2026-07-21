# SAGE_PLAN_ACTUAL.md

**Único documento de seguimiento del plan SAGE**
**Creado:** 2026-07-18
**Última actualización:** 2026-07-18 (explicaciones detalladas de Fase 0)
**Mantenido por:** GLM (actualiza solo cuando Qwen confirma)
**Reemplaza a:** `SAGE_STATUS_REPORT.md`, `MERGE_AUDIT.md`, `MERGE_AUDIT_SUPPLEMENT_KIMI.md`, `ROADMAP_V2.md`, `NEW_MODULES_PROPOSAL.md`, `PLUGIN_SYSTEM_VISION.md`, `RFC_FUTURE_MODULES.md`, `SAGE_V2_ARCHITECTURE.md`, `SAGE_RUNTIME_STATUS.md`, `CASCADE_PRIORITY_MAP.md`, `CASCADE_INTEGRATION_STATUS.md`, `CASCADE_CONTEXT_REPORT.md`, `CASCADE_NEW_OPPORTUNITIES.md`, `INFRASTRUCTURE_IMPROVEMENTS.md` — todos esos dejan de ser referencia activa.

---

## Reglas de este documento

1. **Estado real, no aspiracional.** Cada ítem dice "verificado por [agente] el [fecha]" o "pendiente". Nunca "implementado" sin verificar.
2. **Solo Qwen confirma.** Reports de Cascade, Devin u otros agentes sin verificar = "claimado, no verificado".
3. **No se agregan más fases.** Esto no es un roadmap nuevo. Es el estado actual de lo que existe y lo que falta.
4. **No se agregan más visiones.** Phase 2/3 queda DIFERIDA explícitamente hasta que se decida lo contrario.
5. **Update protocol:** GLM actualiza este documento únicamente cuando Qwen confirma un ítem con verificación empírica. El Arquitecto puede pedir update; otros agentes no.

---

## Snapshot auditado

| Campo | Valor |
|---|---|
| **Archivo base** | `sage_runtime (2).zip` (subido 2026-07-18 03:53) |
| **Tamaño** | 484 KB |
| **Verificación de boot** | ✅ OK — `WAITING_FOR_USER_COMMAND`, 12 componentes, 0 degraded |
| **Wiring `set_agent_router`** | ✅ Presente (líneas 137-140 de `kernel/core.py`) |
| **Wiring `set_provider_router`** | ✅ Presente (líneas 125-127) |
| **Smoke test Ollama real** | ❌ Pendiente — el Arquitecto no confirmó todavía |
| **Tests de regresión** | Pendiente de re-correr contra este zip |

---

## Fase 0 — Fundamentos pre-Phase-1

Esta fase cubre los cimientos que tienen que estar completos antes de empezar las 13 features de Fase 1. Sin estos, las features de Fase 1 son mentira.

---

### F0-1 — System prompt para llamadas LLM

| Campo | Valor |
|---|---|
| **Estado** | ❌ **PENDIENTE** |
| **Verificado por** | GLM el 2026-07-18 (no existe) |
| **Ubicación esperada** | `dispatcher/engine.py` o `providers/*` o nuevo `context/manager.py` |
| **Verificación empírica** | `grep -rn "system_prompt\|SYSTEM_PROMPT\|system prompt"` en todo el código → solo un comentario en `dispatcher/engine.py:416` que dice literalmente *"What this does NOT do: assemble any system prompt, conversation..."* |
| **Bloquea a** | F1-9 (Context Panel), F1-13 (File Analysis con LLM), cualquier feature que mande prompts al LLM |

#### Cómo funciona hoy

Cuando vos escribís un comando en SAGE — por ejemplo `hola` — el flujo es:

```
tu texto "hola"
    ↓
dispatcher._execute_command("hola")
    ↓
provider_router.generate_text("hola")     ← acá está el problema
    ↓
Ollama recibe EXACTAMENTE el string "hola"
    ↓
Ollama responde con lo que sea
```

El string `"hola"` viaja al LLM **literalmente, sin nada alrededor**. No hay presentación, no hay instrucciones, no hay personalidad.

#### Qué es un system prompt

Un system prompt es un mensaje fijo que se le manda al LLM **antes** de tu comando, para decirle quién es y cómo debe comportarse. Por ejemplo:

```
Sos SAGE, un asistente de ingeniería de software.
Respondé en español, en tono profesional pero directo.
Si te piden código, damelo en bloques markdown.
Si no entendés, pedí aclaración.
Contexto del proyecto: {estado actual de SAGE}
Historial reciente: {últimos N comandos}
```

Ese bloque va **antes** de tu "hola", y el LLM responde en consecuencia. Sin ese bloque, el LLM no sabe que está siendo llamado por SAGE — responde como respondería a un usuario random que escribió "hola" en un chat vacío.

#### Evidencia del problema

Mirá la respuesta que te dio el LLM cuando escribiste `funciones` (la que pegaste en el chat previo):

> "Lo siento por la confusión, pero parece que te mencionas una función y luego no proporcionas suficientes detalles para poder interpretar lo que estás tratando de hacer..."

Esa respuesta **no tiene nada que ver con SAGE**. Es la respuesta genérica que daría cualquier LLM a un usuario random que escribe "funciones" en un chat. El LLM no sabe que:
- Está siendo llamado por SAGE
- Debería listar las funciones de SAGE (no funciones matemáticas)
- Está en un contexto de ingeniería de software
- Debería responder en cierto tono

Si hubiera un system prompt, la respuesta habría sido algo como:

> "Funciones disponibles en SAGE: /scan, /benchmark, /agent list, /provider list, ..."

#### Qué falta concretamente

Hay que crear un módulo (probablemente `context/manager.py` nuevo, o un archivo en `providers/`) que:

1. Tenga un template de system prompt con la personalidad SAGE
2. Mantenga un historial de los últimos N comandos (rollo contexto de conversación)
3. Ensamble: `[system_prompt, ...historial, comando_actual]`
4. Le pase eso al `provider_router` en vez del comando crudo

Y luego modificar `dispatcher/engine.py` línea 416 para que llame a ese módulo en vez de pasar el comando pelado.

#### Una observación importante

Lo que vos llamaste "hermoso funciona" en el chat previo (la respuesta del LLM a "hola" y "funciones") — técnicamente **sí funcionó el cable**: el comando llegó al LLM y volvió respuesta. Pero la calidad de la respuesta es **la de un LLM sin contexto**, no la de SAGE. Para que SAGE sea útil, falta el system prompt.

---

### F0-2 — WebSocket real (eventos del bus, no solo status)

| Campo | Valor |
|---|---|
| **Estado** | ⚠️ **PARCIAL — claimado por Cascade, verificado por GLM como incompleto** |
| **Verificado por** | GLM el 2026-07-18 |
| **Ubicación** | `web/server.py` líneas 704-730 |
| **Verificación empírica** | El endpoint `/ws` existe y funciona. PERO solo envía `status_update` cada 1 segundo con `{state, command_count, error_count, timestamp}`. **NO empuja eventos del EventBus**. No recibe comandos. No soporta filtros. |
| **Bloquea a** | F1-5 (Visual Event Queue), F1-6 (Task Management Panel con updates en tiempo real), F1-10 (Smart Notifications) |

#### Cómo funciona hoy

El WebSocket actual hace esto cada 1 segundo:

```python
# web/server.py línea 711-722 (resumido)
while True:
    await asyncio.sleep(1)
    if self.kernel and self.kernel.context:
        update = {
            "type": "status_update",
            "data": {
                "state": self.kernel.state.value,
                "command_count": self.kernel.context.command_count,
                "error_count": self.kernel.context.error_count,
                "timestamp": datetime.now().isoformat()
            }
        }
        await websocket.send_json(update)
```

Cada 1 segundo manda: "el kernel sigue en estado `WAITING_FOR_USER_COMMAND`, van 5 comandos ejecutados, 0 errores". Nada más. **No manda qué comando se ejecutó, qué evento se publicó, qué agente arrancó, qué tarea completó.**

#### Qué es un WebSocket de eventos

Un WebSocket de verdad debería hacer dos cosas:

1. **Recibir eventos del EventBus en tiempo real.** Cada vez que un componente publica `COMMAND_EXECUTED`, `TASK_COMPLETED`, `AGENT_SPAWNED`, etc., el WebSocket lo empuja a todos los clientes conectados. El frontend lo ve instantáneamente, sin polling.

2. **Recibir comandos del cliente.** Si el frontend quiere ejecutar un comando, mandarlo por el mismo WebSocket en vez de hacer un POST HTTP aparte. Más rápido, una sola conexión.

Hoy hace **ninguna** de las dos. Solo hace heartbeat.

#### Por qué bloquea F1-5, F1-6, F1-10

- **F1-5 (Visual Event Queue):** el plan pide "stream de eventos en tiempo real". Sin WebSocket que empuje eventos del bus, la UI tendría que hacer polling cada N segundos preguntando "¿hubo eventos nuevos?" — lento, ineficiente, y no es tiempo real.
- **F1-6 (Task Management Panel):** el plan pide "updates en tiempo real del estado de tareas". Sin WebSocket que empuje `TASK_STARTED`, `TASK_COMPLETED`, etc., la UI se queda mirando el estado viejo hasta que hacés refresh.
- **F1-10 (Smart Notifications):** el plan pide "alertas inteligentes cuando algo pasa". Sin WebSocket que empuje el evento `TASK_TIMEOUT` o `PROVIDER_ERROR`, la notificación llega tarde o no llega.

#### Qué falta concretamente

1. Suscribir un wildcard handler al `EventBus` del kernel (igual que hace el audit log, el cost tracker, etc.).
2. Cuando llega un evento, serializarlo y mandarlo por todos los WebSocket conectados.
3. Añadir un handler en el WebSocket que reciba mensajes del cliente (para comandos).
4. Soportar filtros via query params: `/ws?event_type=command.failed` para que el cliente solo reciba lo que le interesa.

#### Comentario

El WebSocket actual **existe** porque Cascade lo creó en su PR-007 original. Pero el diseño es de "demo de FastAPI", no de sistema real. No es que esté roto — es que es insuficiente.

---

### F0-3 — `dispatch()` devuelve resultado real (no `Task`)

| Campo | Valor |
|---|---|
| **Estado** | ✅ **VERIFICADO** |
| **Verificado por** | GLM el 2026-07-18 |
| **Ubicación** | `dispatcher/engine.py` líneas 165-180 |
| **Verificación empírica** | `dispatch()` ahora hace `while task.status == PENDING or RUNNING: await asyncio.sleep(0.1)` y devuelve `task.result` cuando completa, o `raise RuntimeError` si falla. Ya no devuelve el `Task` crudo. |
| **Bloquea a** | Nada — desbloquea F1-13 (File Analysis) y cualquier caller que espere el resultado real |

#### Cómo funciona hoy

El código actual de `dispatch()` hace esto:

```python
# dispatcher/engine.py, resumido
async def dispatch(self, command, ...):
    task = Task(...)
    heapq.heappush(self._task_queue, ...)
    
    # Wait for task to complete
    while task.status == TaskStatus.PENDING or task.status == TaskStatus.RUNNING:
        await asyncio.sleep(0.1)
        if task.task_id in self._completed_tasks:
            task = self._completed_tasks[task.task_id]
            break
    
    # Return result or error
    if task.status == TaskStatus.COMPLETED:
        return task.result
    elif task.status == TaskStatus.FAILED:
        raise RuntimeError(f"Task failed: {task.error}")
    else:
        raise RuntimeError(f"Task in unexpected state: {task.status}")
```

Es decir: encola la tarea, y **espera** (con `sleep(0.1)`) hasta que termina. Cuando termina, devuelve `task.result` directamente (el string/dict que devolvió el LLM). Si falló, levanta excepción.

#### Cómo funcionaba antes

Antes devolvía el `Task` inmediatamente, con `status=PENDING`. El caller recibía un objeto con `task_id`, `status`, `result=None` — y tenía que llamar por separado `dispatcher.get_task(task_id)` más tarde para ver si terminó. Eso era un problema porque:

- El caller (CLI, web) recibía un `Task` con `result=None` y no sabía qué hacer.
- Si el caller asumía que `task.result` era la respuesta, la imprimía como `None`.
- No había forma estándar de "esperar al resultado".

#### Por qué esto resuelve W-6

En el MERGE_AUDIT original, Claude A documentó como hallazgo #12: *"`kernel.execute_command()` no espera el resultado real — devuelve un Task con status=PENDING, sin importar cuánto tarde el trabajo real en el background"*. Era una decisión de diseño pendiente: ¿bloquear hasta tener resultado, o fire-and-forget con polling?

La decisión que se tomó (Cascade la implementó) fue **bloquear**. Es la opción más simple y la que esperan la mayoría de callers (CLI quiere imprimir la respuesta, web quiere devolverla en el HTTP response).

#### Trade-off

La desventaja de bloquear: si el LLM tarda 30 segundos, el HTTP request se queda colgado 30 segundos. Para la CLI está bien (el usuario espera). Para el web, el navegador puede mostrar "loading..." mientras tanto. Pero no se pueden hacer comandos en paralelo desde el mismo cliente.

Si en el futuro se quiere paralelismo, la solución es agregar un método `dispatch_async()` que devuelva el `Task` inmediatamente (como antes), y mantener `dispatch()` bloqueante para los callers simples. Pero eso es Fase 2, no ahora.

---

### F0-4 — CLI extrae `output` del dict de respuesta

| Campo | Valor |
|---|---|
| **Estado** | ✅ **VERIFICADO** |
| **Verificado por** | GLM el 2026-07-18 |
| **Ubicación** | `interface/cli.py` línea 91 |
| **Verificación empírica** | `if isinstance(result, dict) and 'output' in result: print(result['output'])` |
| **Bloquea a** | Nada — desbloquea la UX de CLI |

#### Cómo funciona hoy

El código de la CLI hace:

```python
# interface/cli.py línea 88-93 (resumido)
result = await self.kernel.execute_command(command)
# Extract and display only the LLM output if result is a dict
if isinstance(result, dict) and 'output' in result:
    print(f"\n{result['output']}\n")
else:
    print(f"\nResult: {result}\n")
```

Si `result` es un dict con key `output` (que es lo que devuelve `dispatch()` vía `provider_router.generate_text()`), imprime solo el `output`. Si no, imprime el `result` entero.

#### Cómo funcionaba antes

Antes la CLI hacía `print(result)` directo. Y como `dispatch()` devolvía el dict `{"stub": False, "output": "...", "provider": "ollama", "model": "qwen2.5:1.5b", "latency_ms": 4500}`, el usuario veía todo eso en pantalla. No era útil.

#### Por qué es importante

El dict de respuesta tiene metadata útil (`provider`, `model`, `latency_ms`), pero **no es lo que el usuario quiere ver**. El usuario quiere la respuesta del LLM, no el stack técnico. Con este fix, la CLI muestra solo la respuesta, y la metadata queda disponible para logs/debug si hace falta.

#### Nota

`provider_router.generate_text()` sigue devolviendo el dict completo. Lo que cambia es cómo la CLI lo consume. Si en el futuro se quiere mostrar "Respuesta de ollama/qwen2.5:1.5b en 4.5s" en una barra de status, se puede usar la metadata. Pero el output principal sigue siendo solo `result['output']`.

---

### F0-5 — REST API `/api/command/execute` extrae `output`

| Campo | Valor |
|---|---|
| **Estado** | ✅ **VERIFICADO** |
| **Verificado por** | GLM el 2026-07-18 |
| **Ubicación** | `web/server.py` líneas 194-196 |
| **Verificación empírica** | `if isinstance(result, dict) and 'output' in result: display_result = result['output']` |
| **Bloquea a** | Nada — desbloquea la UX del web |

#### Cómo funciona hoy

Igual que F0-4 pero en el web:

```python
# web/server.py línea 188-200 (resumido)
result = await self.kernel.execute_command(cmd)
# Extract only the LLM output if result is a dict
if isinstance(result, dict) and 'output' in result:
    display_result = result['output']
else:
    display_result = str(result)
return {
    "success": True,
    "result": display_result,
    ...
}
```

El endpoint `/api/command/execute` recibe `{"command": "hola"}`, ejecuta el comando, extrae `output` del dict, y devuelve `{"success": True, "result": "Hola! ¿En qué puedo ayudarte?"}`.

#### Cómo funcionaba antes

Antes devolvía `{"success": True, "result": {"stub": False, "output": "...", "provider": "..."}}`. El frontend JavaScript recibía eso y mostraba `[object Object]` o el dict serializado. No era útil.

#### Por qué es importante

Es el mismo fix que F0-4 pero para el navegador. Ahora el frontend puede hacer `data.result` y mostrarlo directo en la consola. La metadata del dict (provider, model, latency) se podría exponer en otro endpoint o en el mismo response, pero por ahora se descarta para mantener la API limpia.

---

### F0-6 — Wiring `set_agent_router` (fix B-1)

| Campo | Valor |
|---|---|
| **Estado** | ✅ **VERIFICADO** |
| **Verificado por** | GLM el 2026-07-18 |
| **Ubicación** | `kernel/core.py` líneas 137-140 |
| **Verificación empírica** | `grep "set_agent_router(agent_router)" kernel/core.py` → 1 ocurrencia. Smoke test confirma `dispatcher._agent_router is not None: True`. |
| **Bloquea a** | Nada — desbloquea el load-aware routing de Kimi A-2 |

#### Cómo funciona hoy

En `kernel/core.py`, después de inicializar todos los componentes, hay un bloque de "wiring" (cableado) que conecta componentes que se necesitan entre sí:

```python
# kernel/core.py, resumido
# Wire dispatcher -> provider_router
dispatcher = self._components.get("dispatcher")
provider_router = self._components.get("provider_router")
if dispatcher is not None and provider_router is not None:
    dispatcher.set_provider_router(provider_router)

# Wire dispatcher -> agent_router (este es el fix B-1)
agent_router = self._components.get("agent_router")
if dispatcher is not None and agent_router is not None:
    dispatcher.set_agent_router(agent_router)
```

El primer bloque (provider_router) lo había puesto Claude A — sin eso, los comandos nunca llegaban al LLM. El segundo bloque (agent_router) es el fix B-1 que GLM aplicó el 2026-07-13 con autorización del Arquitecto.

#### Para qué sirve

Cuando se hace `dispatch_multi_agent(command, agents=["cascade", "jules"])`, el dispatcher ejecuta el comando en paralelo para cada agente. Cuando termina cada subtask, llama `agent_router.release_agent(agent_name)` para decrementar el contador de carga de ese agente.

Sin el wiring, `dispatcher._agent_router` quedaba en `None`, y el guard `if self._agent_router is not None` siempre era `False`. Resultado: el load-aware routing (fix A-2 de Kimi) quedaba inerte — el contador de carga nunca se actualizaba, y el router siempre devolvía el primer candidato sin balancear.

Con el wiring, `release_agent()` se llama correctamente, el contador se actualiza, y el router puede elegir el agente menos cargado la próxima vez.

#### Comentario

Es un fix de 4 líneas pero era importante porque era la última pieza suelta del trabajo de Kimi. Sin esto, todo el esfuerzo de Kimi en `agents/router.py` (load tracking, fallback strategy, empty set cleanup) era código muerto.

---

### F0-7 — Smoke test contra Ollama real del Arquitecto

| Campo | Valor |
|---|---|
| **Estado** | ❌ **PENDIENTE** |
| **Verificado por** | — |
| **Bloquea a** | Todo lo demás. Sin esto no se sabe si SAGE funciona end-to-end. |

#### Qué es

Es la prueba final, la que decide si SAGE es utilizable o no. Consiste en:

1. Tener Ollama corriendo localmente con un modelo (ej. `qwen2.5:1.5b`)
2. Tener `openai` package instalado (`pip install openai`)
3. Ejecutar `python main.py` desde el directorio `sage_runtime/`
4. Abrir `http://127.0.0.1:8000` en el navegador
5. Escribir un comando simple ("hola") en la consola
6. Verificar que vuelve una respuesta del LLM en tiempo razonable (5-30 segundos en hardware sin GPU)

#### Por qué es el más importante

Todo lo demás (F0-1 a F0-6, F1-* a F13-*) es irrelevante si este smoke test no pasa. Si el LLM no responde, SAGE es un caparazón bonito sin cerebro.

#### Estado actual

En el chat de Cascade (pegado en el contexto previo), hay una sesión que muestra:

```
> hola
Hola! ¿En qué puedo ayudarte hoy?
```

Y después:

```
> funciones
Lo siento por la confusión, pero parece que te mencionas una función...
```

Si esa sesión es real y reproducible, **F0-7 está hecho**. Pero:
- GLM no puede verificarlo porque no tiene acceso al Ollama del Arquitecto.
- La respuesta a "funciones" demuestra que el LLM no tiene system prompt (ver F0-1), pero técnicamente responde — el cable funciona.
- El Arquitecto tiene que confirmar: "sí, lo probé en mi máquina, el LLM responde".

Hasta que el Arquitecto no confirme, este ítem queda como pendiente.

#### Qué pasa si no funciona

Si el smoke test falla, los pasos de debugging en orden son:

1. ¿Ollama está corriendo? → `ollama list` debe listar al menos un modelo.
2. ¿El paquete `openai` está instalado? → `pip show openai`.
3. ¿El log de boot dice "Ollama provider initialized"? → si no, revisar `ollama serve`.
4. ¿El comando llega al dispatcher? → revisar log de `[DISPATCHER] Dispatched task`.
5. ¿El LLM devuelve algo? → revisar log de `[PROVIDER_ROUTER]` o errores.
6. ¿La respuesta vuelve al navegador? → revisar `web/server.py` logs.

La causa más probable de fallo es el paso 2 (falta `openai` package). El `ollama_provider.py` usa el cliente de OpenAI para hablar con Ollama (porque Ollama expone una API compatible con OpenAI).

---

## Fase 1 — MVP de 13 capacidades (resecuenciado)

**Origen:** Plan "SAGE OS v0.5 → v1.0 Phase 1 MVP" de Cascade, aprobado con condiciones por el Arquitecto.
**Estado del plan:** ⚠️ **Cascade no ha terminado de pensarlo concretamente** (según Arquitecto, 2026-07-18). Lo que sigue es el resecuenciado que GLM propone basado en dependencias técnicas, no un plan confirmado.

**Principio de resecuenciado:** Brain → Coordination → UI (orden del Arquitecto). Las features backend van primero, las de UI al final. Las que desbloquean otras van antes.

### Orden resecuenciado (propuesta GLM, no confirmada)

| # | Feature original | Dependencia | Estado |
|---|---|---|---|
| **F1-1** | Dynamic Command Registry | Ninguna | ❌ Pendiente |
| **F1-2** | Agent Capabilities System | F1-1 (para invocar via comandos) | ❌ Pendiente |
| **F1-3** | Tools Center | F1-2 (capacidades declaran tools) | ❌ Pendiente |
| **F1-4** | Runtime Status (Kubernetes-style) | Ninguna — lee estado existente | ❌ Pendiente |
| **F1-5** | Visual Event Queue | **F0-2** (WebSocket real) | ❌ Bloqueada por F0-2 |
| **F1-6** | Task Management Panel | **F0-2** (updates tiempo real) | ❌ Bloqueada por F0-2 |
| **F1-7** | Memory Explorer | Ninguna — lee memory existente | ❌ Pendiente |
| **F1-8** | Provider Management Panel | Ninguna — lee providers existentes | ❌ Pendiente |
| **F1-9** | Context Panel | **F0-1** (system prompt) | ❌ Bloqueada por F0-1 |
| **F1-10** | Smart Notifications | **F0-2** (WebSocket) + F1-5 (Event Queue) | ❌ Bloqueada por F0-2 y F1-5 |
| **F1-11** | Mission Control (Enhanced) | Ninguna — extiende mission_control existente | ❌ Pendiente |
| **F1-12** | Decision Center | F1-1 (comandos para aprobar/revertir) | ❌ Pendiente |
| **F1-13** | File Analysis | **F0-1** (system prompt para LLM) + F0-3 (dispatch devuelve resultado) | ⚠️ F0-3 hecho, F0-1 pendiente |

### Notas de resecuenciado

- **F0-2 es bloqueante duro para F1-5, F1-6, F1-10.** Sin WebSocket que empuje eventos del bus, las tres features de UI en tiempo real son mentira. F0-2 debe completarse antes de empezar estas.
- **F0-1 es bloqueante duro para F1-9 y F1-13.** Sin system prompt, el Context Panel no tiene nada que mostrar y File Analysis manda el contenido del archivo crudo al LLM sin instrucciones.
- **F1-1 (Command Registry) es el primer paso real de Fase 1** porque todas las demás features de UI necesitan comandos para interactuar.
- **F1-4 (Runtime Status) y F1-7 (Memory Explorer) y F1-8 (Provider Management) son las más fáciles** — solo leen estado existente, no requieren nuevo backend.

### Lo que NO está en Fase 1

Nada de esto entra en Fase 1:
- Plugin Marketplace
- Model Marketplace
- Monaco Editor completo
- Workspace system complejo
- Review Center completo
- Dependency Scanner empresarial
- Architecture graph D3
- Kanban drag & drop

Estos están en Fase 2/3 (ver abajo), DIFERIDOS.

---

## Fase 2/3 — DIFERIDA

**Estado:** 🚫 **DIFERIDA — sin fecha, sin orden, sin asignatario**

Las 30 features restantes del plan original de 43 quedan explícitamente fuera de scope hasta que el Arquitecto decida lo contrario. No se trabaja en ellas. No se planifican. No se estiman.

**Lista (solo para recordar que existen, no para trabajar):**

1. Git Integration Panel
2. Branch Management System
3. Merge Center
4. Review Center (completo)
5. Agent Conversation History
6. Benchmark Center
7. Session Management
8. Timeline View
9. Kanban View
10. Plugin Marketplace
11. Model Marketplace
12. Workspace System
13. Project System
14. Architecture Graph
15. Advanced Analytics
16. Full IDE Integration
17. Dependencies Panel with Vulnerability Scanning
18. MCP Panel
19. Prompt Queue
20. Agent Metrics System
21. Error Panel
22. Health Check Dashboard
23. Context Monitor (avanzado)
24. GitHub Integration (PR/Issue)
25. Browser Notifications
26. Per-Model Timeout Configuration
27. Knowledge Base
28. Memory Explorer (avanzado con vector search)
29. Simplified Code Editor
30. Configuration Center

**Condición para des-diferir:** el Arquitecto debe confirmar explícitamente que Fase 0 y Fase 1 están completas y verificadas. Hasta entonces, cualquier mención de estas features en cualquier documento se considera ruido.

---

## Documentos anteriores — estado de cada uno

Para evitar confusiones, esto es lo que pasa con los documentos que ya existen:

| Documento | Estado |
|---|---|
| `SAGE_RUNTIME_STATUS.md` (el viejo de julio 2026 que decía "Production Ready 100%") | ❌ Obsoleto — ignorar |
| `SAGE_STATUS_REPORT.md` (GLM 2026-07-13) | ❌ Reemplazado por este documento |
| `SAGE_STATUS_REPORT_GLM.md` (copia en docs/ del zip nuevo) | ❌ Reemplazado por este documento |
| `MERGE_AUDIT.md` | ✅ Referencia histórica — ya no es activa (la fusión se completó) |
| `MERGE_AUDIT_SUPPLEMENT_KIMI.md` | ✅ Referencia histórica — ya no es activa |
| `ROADMAP_V2.md` | ❌ Reemplazado — no aplicar |
| `NEW_MODULES_PROPOSAL.md` | ❌ Reemplazado — no aplicar |
| `PLUGIN_SYSTEM_VISION.md` | ❌ Reemplazado — no aplicar |
| `RFC_FUTURE_MODULES.md` | ❌ Reemplazado — no aplicar |
| `SAGE_V2_ARCHITECTURE.md` | ❌ Reemplazado — no aplicar |
| `CASCADE_PRIORITY_MAP.md` | ❌ Reemplazado — era pre-fusión, ya obsoleto |
| `CASCADE_INTEGRATION_STATUS.md` | ❌ Reemplazado — era pre-fusión |
| `CASCADE_CONTEXT_REPORT.md` | ❌ Reemplazado |
| `CASCADE_NEW_OPPORTUNITIES.md` | ❌ Reemplazado |
| `INFRASTRUCTURE_IMPROVEMENTS.md` | ❌ Reemplazado |
| `COMO_ENCENDER_SAGE.md` | ✅ Vigente — instructivo de uso para el Arquitecto |
| `MULTI_AGENT_REPOSITORY_GUIDE.md` | ⚠️ Sin verificar — no se usa como referencia activa |
| `REPOSITORY_RESTRUCTURE_PLAN.md` | ⚠️ Sin verificar — no se usa como referencia activa |

---

## Próximas actualizaciones de este documento

GLM actualizará este documento **solo** cuando ocurra uno de estos eventos:

1. **Qwen confirma un ítem** con verificación empírica (grep, test, smoke test).
2. **El Arquitecto confirma F0-7** (smoke test contra Ollama real).
3. **Cascade termina de pensar el plan de Fase 1** y el Arquitecto lo aprueba — en ese caso, el resecuenciado de F1 se reemplaza por el plan confirmado.
4. **Se decide des-diferir Fase 2/3** — en ese caso, se crea una nueva sección con fecha y orden.

Hasta que alguno de estos eventos ocurra, este documento no cambia. Cualquier otro reporte de cualquier otro agente se considera no autorizado y se ignora.

---

## Resumen ejecutivo para el Arquitecto

**Lo único que importa ahora:**

1. **Confirmar F0-7** — smoke test contra Ollama real. Si pasa, Fase 0 está 5/7 (faltan F0-1 system prompt y F0-2 WebSocket real).
2. **Pedir a Qwen que confirme** si F0-1 (system prompt) y F0-2 (WebSocket real) están en su radar.
3. **Esperar a Cascade** para el plan de Fase 1 confirmado. Hasta entonces, F1-* queda como propuesta.
4. **Fase 2/3 no existe** hasta nuevo aviso.

**Lo que NO importa ahora:**

- Visiones v2, roadmaps, RFCs, plugin systems, marketplaces — todo diferido.
- Auditorías previas — ya son historia.
- Claims sin verificar de ningún agente.

— GLM

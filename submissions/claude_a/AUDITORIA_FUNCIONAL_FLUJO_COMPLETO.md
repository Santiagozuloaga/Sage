# Auditoría Funcional del Flujo Completo — SAGE OS Runtime

**Tipo de misión:** auditoría pura, sin implementación (según encargo). Nada de lo aquí reportado fue corregido.
**Metodología:** cada hallazgo fue verificado por ejecución real o reproducción forzada, no solo lectura de código.

---

## Hallazgo más severo — léase primero

**`CLIInterface` está completamente implementada y funciona, pero `cli.start()` nunca se llama en `main.py`.** `cli = CLIInterface(kernel)` se construye y nunca se vuelve a referenciar en todo el archivo — confirmado por grep en todo el proyecto: es la única aparición de `cli` que existe. Consecuencia real: con el fix de esta sesión que hace el web dashboard opcional (para que `fastapi` faltante no impida arrancar), el sistema ahora **arranca en modo "solo CLI"... sin que la CLI corra**. `main.py` entra en `while kernel.is_running: await asyncio.sleep(1)` y se queda ahí para siempre. No hay ninguna forma de escribir un comando. El banner dice "CLI Interface: Available (press Ctrl+C to exit)" pero eso es falso — no hay ningún loop de entrada corriendo.

Esto es más grave que cualquier otro hallazgo de esta auditoría porque significa que, en el estado actual, **el sistema no tiene ninguna interfaz funcional cuando `fastapi` no está instalado** — que es exactamente el escenario que mi propio fix de la sesión anterior hizo posible (arrancar sin crashear) sin darme cuenta de que no había nada corriendo del otro lado. Ver la sección de "decisiones de arquitectura" para las opciones, no lo arreglé.

---

## 1. Boot / Inicialización / Registro de componentes

**Estado: sólido**, incluso bajo fallo forzado. Verificado con una prueba nueva: forcé que `memory.engine.MemoryEngine.initialize()` lanzara una excepción real (simulando disco lleno) durante el boot.

| Comportamiento verificado | Resultado |
|---|---|
| `boot()` propaga la excepción del componente crítico | Correcto — lanza `RuntimeError` limpio |
| `context.current_state` tras el fallo | Se queda en `BOOT` (refleja la realidad, no miente) |
| `kernel.is_running` tras el fallo | `False`, correctamente |
| `execute_command()` tras un boot fallido | Rechaza con `RuntimeError("Kernel not running")` — no permite operar en estado inconsistente |
| `shutdown()` tras un boot fallido (con solo `config` inicializado) | Completa sin lanzar, no crashea con componentes parciales |

No encontré un estado imposible aquí. El split crítico/opcional que ya se había hecho sostiene bien incluso el caso no probado antes (fallo real en el nivel crítico, no solo el periférico).

## 2. Event Bus

**Estado: fantasma — inicializa y corre, pero nunca recibe ni transporta un solo evento real.**

- `EventType` define 15 tipos de eventos (`BOOT`, `SHUTDOWN`, `COMMAND_RECEIVED`, `COMMAND_EXECUTED`, `COMMAND_FAILED`, `STATE_CHANGED`, `MEMORY_SAVED`, `MEMORY_LOADED`, `AGENT_SPAWNED`, `AGENT_COMPLETED`, `ERROR`, `CHECKPOINT`, `PR_CREATED`, `PR_UPDATED`, `RFC_SUBMITTED`) — claramente diseñado para capturar cada momento importante del ciclo de vida.
- Búsqueda exhaustiva de `.publish(` en todo el código: **cero resultados fuera de la propia definición del método en `events/bus.py`.** Ni el kernel, ni el dispatcher, ni memory, ni config, ni providers publican nada, nunca.
- `web/server.py` solo *lee* `get_history()` para mostrarla en un dashboard — nunca escribe.
- Verificado por ejecución: arranqué el kernel completo, ejecuté un comando, esperé, y cerré — `event_bus.get_history()` devuelve `0` eventos en cada punto de la prueba.
- El bus en sí está bien construido (pub-sub, wildcard handlers, historial acotado, processor async no bloqueante) — el problema no es la implementación, es que nadie lo alimenta.

## 3. Provider Router

**Estado: funcional**, ya cubierto extensamente en sesiones anteriores (Ollama agregado, bug de registro de health check corregido, default cambiado a Ollama). Sin hallazgos nuevos esta sesión más allá de confirmar que sigue integrando bien con el resto tras los cambios de dispatcher.

## 4. Dispatcher

**Estado: funcional para lo que hace, con un cuello de botella y una limitación documentados.**

- La conexión a `provider_router` (de la sesión anterior) sigue funcionando: verificado de nuevo end-to-end.
- **Cuello de botella menor:** `_process_tasks()` hace polling cada 100ms cuando la cola está vacía (`asyncio.sleep(0.1)` en vez de esperar en un `asyncio.Queue` real). No es grave frente a latencias de LLM (segundos), pero es un patrón de polling donde ya existe la primitiva async correcta (`asyncio.Queue`) para evitarlo del todo. No lo cambié — es una optimización, no un bug, y esta sesión es auditoría de funcionalidad, no de rendimiento.
- Limitación ya documentada la sesión pasada: sin Context Manager, cada comando se manda al provider como texto crudo, sin historial ni system prompt.

## 5. Memory

**Estado: funcional**, ya cubierto extensamente (4 fixes de la sesión anterior). Único pendiente ya documentado: operaciones SQLite bloqueantes sobre el event loop (no arreglado, por tamaño del cambio).

## 6. Config

**Estado: funcional**, ya cubierto extensamente (3 fixes de la sesión anterior). Sin hallazgos nuevos.

## 7. Ciclo completo de ejecución de comandos

**Estado: roto en la práctica, por el hallazgo #1 (CLI nunca arranca), no por el kernel en sí.**

El camino kernel-para-adentro funciona (`execute_command` → `dispatcher.dispatch` → `provider_router.generate_text` → resultado real o falla honesta, todo verificado la sesión pasada y de nuevo hoy). El problema es **la entrada**: sin CLI corriendo y sin `fastapi` instalado, no existe ningún camino para que un comando llegue al kernel en absoluto. El ciclo "completo" nunca se ejecuta de punta a punta en una instalación real sin las dependencias del web server.

Adicionalmente, ya documentado la sesión pasada y sigue vigente: `execute_command()` no espera el resultado real, devuelve la tarea en `PENDING`.

## 8. Manejo de errores

**Estado: sólido en todo lo que toqué (config, memory, dispatcher, kernel boot).** El caso nuevo probado esta sesión (fallo de componente crítico) también se comporta bien. No encontré manejo de errores roto en ningún módulo nuevo revisado hoy (events, recovery, auditor, dashboard, command_mode, mission_control, contracts) — en estos, el "problema" no es manejo de errores incorrecto, es ausencia total de invocación (ver siguiente sección).

## 9. Recuperación ante fallos

**Estado: teatral — la API existe y funciona si se llama a mano, pero nada la dispara nunca.**

- `RecoverySystem.create_checkpoint()` existe, funciona (probado en aislamiento), pero **no lo llama nada, en ningún lugar del código, automáticamente.** Confirmado por grep: la única aparición de `create_checkpoint` es su propia definición.
- `RecoverySystem` ni siquiera es un componente del kernel — se instancia directo en `main.py`, fuera de `kernel._components`. Si usás `SageKernel` programáticamente (como en todas mis pruebas), `RecoverySystem` no existe en absoluto.
- Consecuencia práctica: si el sistema crashea, no hay ningún checkpoint del cual recuperarse, porque nunca se creó ninguno.

## 10. Degradación controlada

**Estado: sólido a nivel kernel (mi propio fix de la sesión anterior, revalidado hoy bajo el caso de fallo crítico real).** El patrón de degradación en sí funciona bien. El problema no es la degradación — es que degrada correctamente *hacia una interfaz que tampoco corre* (hallazgo #1).

---

## Componentes que aparentan funcionar pero no participan del flujo (pedido explícito de esta auditoría)

| Componente | ¿Inicializa sin error? | ¿Es parte de `kernel._components`? | ¿Algo lo invoca en el flujo real, alguna vez? |
|---|---|---|---|
| **Event Bus** | Sí | Sí | Nunca — cero `.publish()` en toda la base de código |
| **Recovery System** | Sí | **No** (vive solo en `main.py`) | Nunca — `create_checkpoint()` jamás se llama automáticamente |
| **Mission Control** | N/A | **No** — no existe `_init_mission_control` en el kernel | `web/server.py` lo busca con `get_component('mission_control')`, siempre recibe `None` |
| **Command Mode** | Sí (en `main.py`) | No es componente del kernel | `execute()`/`activate()` nunca se llaman fuera de tests |
| **Dashboard Monitor** | Sí (en `main.py`) | No es componente del kernel | Solo `get_system_status()` vía `web/server.py` — inerte en modo CLI-only |
| **Integrity Auditor** | Sí, y sí es componente del kernel | Sí | Parcial: `run_full_audit()` es real y funciona, pero solo se alcanza vía un endpoint web manual — cero auditoría periódica/automática |
| **Contracts (validador de RFC)** | N/A | No | Nunca — solo referenciado por `audit_runtime.py`, ningún módulo de runtime lo importa |

---

## Estados imposibles encontrados

Ninguno a nivel de kernel (el manejo de fallo crítico se comporta de forma consistente, ver sección 1). El más cercano a un "estado imposible" es conceptual, no técnico: el banner de arranque declara `"CLI Interface: Available"` cuando, en la práctica, no hay ningún loop de CLI corriendo — el sistema *dice* que algo está disponible cuando no lo está.

## Cuellos de botella

1. Polling de 100ms en `dispatcher._process_tasks()` cuando la cola está vacía (menor, ver sección 4).
2. Operaciones SQLite síncronas sobre el event loop en `memory/engine.py` (ya documentado, no arreglado).

## Bugs funcionales nuevos encontrados esta sesión

Ninguno nuevo a nivel de lógica interna de un módulo — todos los hallazgos de esta pasada son de **integración/invocación** (componentes que no se conectan a nada), no bugs de código dentro de un módulo aislado.

---

## Decisiones de arquitectura — documentadas en detalle, no implementadas

### A. ¿Cuándo debe correr la CLI?

**El problema:** `main.py` construye `CLIInterface` pero nunca llama `.start()`. El README dice explícitamente "web interface is primary, CLI is optional" — sugiriendo que alguien asumió que el web dashboard siempre estaría disponible y la CLI era un extra, no el fallback real.

**Por qué no lo arreglé solo:** technically el fix es una línea (`await cli.start()` en algún punto de `main()`), pero **dónde y cuándo** llamarla es la decisión real, con al menos 3 opciones razonables y distintas:

1. **CLI siempre corre, en paralelo al web server** (si está disponible). Ventaja: nunca depende de si fastapi está instalado. Riesgo: dos superficies de entrada activas simultáneamente compitiendo por la misma sesión de kernel — hay que pensar si eso genera condiciones de carrera en `execute_command`.
2. **CLI corre solo como fallback**, cuando `WEB_AVAILABLE` es `False` (coherente con el propio fix de esta sesión que hizo el web opcional). Ventaja: preserva la intención original ("web es primario") pero sin dejar el sistema mudo. Riesgo: ninguno obvio, es probablemente la opción de menor riesgo.
3. **CLI reemplaza al loop `asyncio.sleep(1)` actual incondicionalmente**, y el web server (si existe) corre en paralelo como hoy. Es funcionalmente similar a la opción 1 pero enmarcado distinto.

No implementé ninguna. Mi lectura es que la opción 2 es la de menor riesgo y más alineada con el texto del propio README, pero es tu decisión, no la mía.

### B. Event Bus: ¿vale la pena conectar 15 tipos de eventos a mano, o hay una forma más barata de darle valor?

**El problema:** conectar el bus "bien" implicaría agregar una llamada `await event_bus.publish(...)` en potencialmente una docena de puntos distintos (boot, shutdown, cada resultado de comando, cada guardado de memoria, cada spawn/completado de agente, cada error, etc.) — es un cambio ancho, no profundo, pero toca casi todos los módulos.

**Alternativa de menor alcance, no implementada, solo señalada:** conectar primero *solamente* `COMMAND_RECEIVED`/`COMMAND_EXECUTED`/`COMMAND_FAILED` desde el propio `kernel.execute_command()` (un solo archivo, 3 líneas), que es lo mínimo para que `get_history()` deje de estar siempre vacía y el dashboard web (cuando exista) muestre algo real. El resto de tipos de eventos quedarían para después.

**No lo hice** porque agregar publicaciones reales, aunque sea solo 3, es una decisión de "qué momentos importan lo suficiente para registrarse" — no un bug fix.

### C. Recovery System: ¿qué debería disparar un checkpoint?

**El problema:** existe la mecánica (crear/restaurar/listar/limpiar checkpoints) pero cero política de cuándo usarla.

**Opciones, no implementadas:**
1. Checkpoint automático antes de cada `execute_command` (costoso si son muchos comandos).
2. Checkpoint periódico por tiempo (ej. cada N minutos).
3. Checkpoint solo ante `COMMAND_FAILED` o excepciones no manejadas (más barato, más dirigido, pero depende de que el Event Bus esté conectado primero — ver B).
4. Checkpoint manual únicamente, vía CLI/comando explícito (más simple, requiere que la CLI corra — ver A).

**No implementé ninguna.** Además, antes de elegir una política, `RecoverySystem` necesitaría entrar a `kernel._components` (hoy vive solo en `main.py`), lo cual es en sí mismo un cambio de arquitectura menor pero real.

### D. Mission Control: ¿registrar en el kernel, o retirar las referencias muertas de `web/server.py`?

**El problema:** `mission_control/controller.py` existe como módulo completo pero el kernel nunca lo instancia. `web/server.py` ya tiene el código para exponerlo (asumiendo que existiría).

**Opciones:** (1) agregar `_init_mission_control()` al kernel, como cualquier otro componente opcional — es mecánicamente idéntico a cómo ya se hizo con Ollama en la sesión anterior; o (2) si `MissionControl` no es prioritario todavía, quitar las referencias muertas de `web/server.py` para que no aparenten una funcionalidad que no existe. Ninguna de las dos es una "arquitectura nueva" realmente — la primera es mecánica, pero la marco igual porque decidir *si* mission_control es prioritario ahora sí es tuyo.

---

## Resumen para decidir

Lo único que yo priorizaría, si tuviera que elegir uno: **A (CLI)**, porque sin eso el sistema no tiene ninguna forma de uso real hoy, independientemente de qué tan bien funcione todo lo de adentro (que, dicho sea de paso, funciona bien — el kernel, dispatcher, provider router, memory y config están sólidos). Los demás (B, C, D) son mejoras reales pero el sistema es usable sin ellos; sin A, no es usable en absoluto en modo CLI.

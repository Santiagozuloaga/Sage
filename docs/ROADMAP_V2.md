# ROADMAP_V2.md — Roadmap de Evolución de SAGE v2

**Autor:** GLM (Arquitecto de Evolución de SAGE)
**Fecha:** 2026-07-06
**Estado:** PLANIFICACIÓN — no implementar
**Alcance:** secuencia de fases, hitos, dependencias, asignación de ingenieros, mitigación de riesgos
**Documentos relacionados:** `SAGE_V2_ARCHITECTURE.md`, `NEW_MODULES_PROPOSAL.md`, `PLUGIN_SYSTEM_VISION.md`, `RFC_FUTURE_MODULES.md`

---

## 1. Premisas del roadmap

1. **El core FROZEN se respeta.** Ninguna fase puede requerir modificar archivos del core.
2. **El equipo core (Claude A + Cascade + Runtime Engineer + Kimi) sigue ocupado** con la fusión de las 3 ramas y el wiring pendiente. El roadmap v2 asume que v2 lo construyen **otros ingenieros/agentes** en paralelo, sin interferir.
3. **Cada fase entrega valor por sí sola.** No hay "big bang" — al final de cada fase hay algo utilizable.
4. **La fusión v1 (Claude A + RE + Kimi) debe estar completa antes de Fase 1.** No se construye v2 sobre un v1 inestable.
5. **Las estimaciones son de esfuerzo, no calendario.** Una "semana" = 5 días-hombre de un ingeniero. Si hay 2 ingenieros en paralelo, una fase de 6 semanas puede tomar 3 semanas calendario.

---

## 2. Vista global

```
v1.x (en fusión)  ─────────────────────────────────────────────────────►
                  │
                  │ fusión completa
                  ▼
v2.0 ─── Fase 1 ─── Fase 2 ─── Fase 3 ─── Fase 4 ──────────────────►
        (cimientos) (capacidades) (interfaces) (operaciones)
        4-6 sem     6-8 sem       6-8 sem     4-6 sem
                                                            │
                                                            │ release v2.0
                                                            ▼
v2.1 ─── Fase 5 ─── Fase 6 ──────────────────────────────────►
        (experiencia) (operaciones avanzadas)
        8-12 sem      4-6 sem
                                                            │
                                                            │ release v2.1
                                                            ▼
v3.0 ─── Fase 7 ──────────────────────────────────────────────►
        (distribución)
        12+ sem
```

| Release | Fases incluidas | Duración calendario (2-3 ingenieros) |
|---|---|---|
| **v2.0** | Fases 1-4 | 16-22 semanas (~4-5 meses) |
| **v2.1** | Fases 5-6 | 10-14 semanas (~3 meses) |
| **v3.0** | Fase 7 | 12+ semanas (~3+ meses) |

**Total a v3.0:** 38-48 semanas (~10-12 meses).

---

## 3. Pre-requisitos (antes de Fase 1)

Antes de iniciar v2, deben cumplirse:

| Pre-requisito | Estado actual | Responsable | Bloquea |
|---|---|---|---|
| Fusión de las 3 ramas (Claude A + RE + Kimi) | Pendiente — ver `MERGE_AUDIT.md` | Arquitecto + Claude A | Todo v2 |
| Wiring pendiente de Cascade (CLI start, Event Bus publishing, Recovery auto-trigger, Mission Control registration, Context Manager) | Pendiente | Cascade | Fase 1 (Event Bridge necesita eventos reales publicados) |
| Tests de regresión de las 3 ramas pasando | Pendiente | Claude A | Todo v2 |
| `audit_runtime.py` mostrando ≥85% completion | Confirmado en auditoría previa | — | No bloquea pero recomienda |
| `python main.py` arrancando limpio hasta `WAITING_FOR_USER_COMMAND` | Pendiente (Cascade está fixeando CLI) | Cascade | Fase 1 |

**Si Cascade no publica eventos reales en el Event Bus antes de Fase 1,** el Event Bridge puede desarrollarse contra eventos sintéticos (un mock del bus) y se integra cuando los eventos reales estén listos. No es bloqueante estricto.

---

## 4. Fase 1 — Cimientos (4-6 semanas)

**Objetivo:** establecer la capa 1 (adaptadores) que permite que todo lo demás se construya sin tocar el core.

### 4.1 Entregables

| Módulo | Archivos nuevos | Semanas |
|---|---|---|
| M01 Plugin Runtime | `plugins/runtime.py`, `plugins/manifest.py`, `plugins/sandbox.py`, `plugins/loader.py`, `plugins/contracts.py`, `plugins/exceptions.py` | 3 |
| M02 Event Bridge | `extensions/event_bridge.py`, `extensions/event_schemas.py`, `extensions/internal_bus.py` | 1.5 |
| M03 Lateral Component Registry | `extensions/registry.py`, `extensions/interfaces.py` | 1 |
| Tests de capa 1 | `tests/test_plugin_runtime.py`, `tests/test_event_bridge.py`, `tests/test_registry.py` | 1 (en paralelo) |

### 4.2 Hito de Fase 1: "Plugin hola mundo"

Al final de Fase 1, debe existir un plugin de ejemplo `./plugins/hello_world/` que:

1. Se cargue en el arranque del Plugin Runtime.
2. Se suscriba a `sage.command.executed` via Event Bridge.
3. Imprima "Hello from plugin!" en el log.
4. Sea activable/desactivable via CLI.

Si esto funciona, los cimientos están listos.

### 4.3 Criterios de aceptación

- `python main.py` arranca sin errores.
- `sage plugin list` muestra el plugin hola mundo.
- `sage plugin enable hello_world` y `disable` funcionan.
- El plugin recibe eventos del Event Bridge.
- Un plugin que falla en `on_load` no rompe el arranque del core.
- Tests de capa 1 pasan 100%.

### 4.4 Riesgos de Fase 1

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| El sandbox de permisos no es suficientemente hermético | Media | Empezar con permisos best-effort; plan de endurecimiento en Fase 4. |
| El Event Bridge introduce latencia visible en el bus | Baja | Fire-and-forget async; medir en tests. |
| El Lateral Registry compite con `kernel._components` | Baja | Comunicación clara: registry lateral es para v2; `kernel._components` es para v1. |

### 4.5 Ingenieros asignables

- 1 ingeniero Python senior (preferiblemente agente nuevo, no del equipo core).
- 1 ingeniero Python mid (tests + plugins builtin).

---

## 5. Fase 2 — Capacidades base (6-8 semanas)

**Objetivo:** entregar las capacidades funcionales core de v2: Knowledge Base, Skills, Cache, Rate Limiter.

### 5.1 Entregables

| Módulo | Archivos nuevos | Semanas | Dependencia |
|---|---|---|---|
| M04 Knowledge Base | `knowledge_base/` (8 archivos) | 3 | Fase 1 |
| M05 Skills System | `skills/` (7 archivos + skills builtin) | 2 | Fase 1 + M04 (para skills RAG) |
| M06 Cache Layer | `cache/` (5 archivos) | 1.5 | Fase 1 |
| M07 Rate Limiter | `rate_limiter/` (4 archivos) | 1 | Fase 1 |
| Tests de capa 2 | `tests/test_knowledge_base.py`, etc. | 1 (paralelo) | — |

### 5.2 Hito de Fase 2: "Skill end-to-end"

Al final de Fase 2, debe existir:

1. Un plugin `web_search_skill` que registra la skill `web_search.search` en el Lateral Registry.
2. La skill puede invocarse via `registry.get("skill:web_search.search").invoke({"query": "SAGE OS"})`.
3. La skill consulta la Knowledge Base si hay documentos relevantes (cacheado por M06).
4. Rate Limiter protege contra abuso (max 10 invocaciones/minuto).
5. Todo esto funciona sin tocar el core.

### 5.3 Criterios de aceptación

- Knowledge Base puede ingerir 1000 documentos sin degradación.
- Skills System puede invocar skills con timeout de 60s.
- Cache Layer logra hit rate ≥30% en benchmark de comandos repetidos.
- Rate Limiter bloquea al 11º comando en una ventana de 1 minuto con política de 10/min.
- Tests de capa 2 pasan 100%.

### 5.4 Riesgos de Fase 2

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| ChromaDB/Qdrant pesa demasiado para hardware objetivo | Media | Permitir SQLite como vector store fallback (más lento pero sin dependencias). |
| Embeddings locales son lentos en CPU | Alta | Default a `all-MiniLM-L6-v2` (384 dim, rápido en CPU); permitir override. |
| Cache invalidation incorrecta | Media | Suite de tests de invalidación por evento; revisión manual de reglas. |

---

## 6. Fase 3 — Interfaces (6-8 semanas)

**Objetivo:** exponer capacidades v2 via REST API v2 + WebSocket Hub + SDK Python.

### 6.1 Entregables

| Módulo | Archivos nuevos | Semanas | Dependencia |
|---|---|---|---|
| M09 REST API v2 + WS Hub | `api_v2/` (15+ archivos) | 4 | Fase 1 + Fase 2 |
| SDK Python (paquete `sage-sdk`) | repo separado `sage-sdk-python/` | 2 | M09 |
| Documentación OpenAPI | generada por FastAPI + custom | 1 | M09 |
| Tests de API | `tests/test_api_v2.py` | 1 (paralelo) | — |

### 6.2 Hito de Fase 3: "SDK funcional"

Al final de Fase 3:

1. `pip install sage-sdk` funciona.
2. `from sage_sdk import SageClient; client = SageClient("http://localhost:8000")`.
3. `client.plugins.list()` devuelve los plugins instalados.
4. `client.knowledge.search("query")` funciona.
5. `client.skills.invoke("web_search.search", {"query": "..."})` ejecuta la skill.
6. WebSocket Hub empuja eventos en tiempo real al SDK.

### 6.3 Criterios de aceptación

- OpenAPI spec completa publicada en `/api/v2/openapi.json`.
- Auth JWT + API key implementada.
- SDK Python tiene 90%+ cobertura de tests.
- WebSocket Hub soporta 100+ clientes concurrentes sin degradación.
- Latencia p99 de endpoints REST < 100ms.

### 6.4 Riesgos de Fase 3

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Montar routers v2 en el app FastAPI existente requiere tocar `web/server.py` | Alta | **Alternativa A:** plugin "api_v2_mount" que obtiene `kernel.get_component('web_server')` y llama `mount()` en `on_load`. **Alternativa B:** FastAPI app v2 separado en puerto 8001 (sidecar). Recomendamos A primero. |
| Auth JWT rompe clientes existentes | Baja | Auth opt-in; v1 endpoints no la requieren. |
| SDK se desincroniza de la API | Media | Generar SDK desde OpenAPI spec (openapi-generator). |

---

## 7. Fase 4 — Operaciones (4-6 semanas)

**Objetivo:** observabilidad, cost tracking, backup.

### 7.1 Entregables

| Módulo | Archivos nuevos | Semanas | Dependencia |
|---|---|---|---|
| M10 Telemetry & Audit | `telemetry/`, `audit/` | 2 | Fase 1 (Event Bridge) |
| M11 Cost Tracker | `costs/` | 1 | Fase 1 |
| M12 Backup System | `backup/` | 1.5 | Fase 1 |
| Endpoints v2 de operaciones | extiende `api_v2/routers/` | 0.5 | Fase 3 |
| Tests de capa 4 | `tests/test_telemetry.py`, etc. | 1 (paralelo) | — |

### 7.2 Hito de Fase 4: "v2.0 release candidate"

Al final de Fase 4:

1. Prometheus scrapea métricas en `/api/v2/telemetry/metrics`.
2. Audit Log append-only funcional, con rotación.
3. Cost Tracker reporta gastos por usuario y provider.
4. Backup System crea snapshot consistente sin detener el kernel.
5. Todas las APIs v2 documentadas y con tests.

### 7.3 Criterios de aceptación (release v2.0)

- 100% de tests de Fases 1-4 pasan.
- `audit_runtime.py` sigue mostrando ≥85% (no se rompió nada del core).
- `python main.py` arranca en < 5s con todos los plugins builtin activos.
- Documentación completa: arquitectura, API, guía de plugins, guía de desarrollo.
- Al menos 3 plugins builtin funcionando (notion_sync, slack_notify, web_search_skill).

### 7.4 Riesgos de Fase 4

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Telemetry introduce overhead visible | Media | Sampling configurable; default 10% traces. |
| Audit Log crece sin bound | Alta | Rotación por tamaño (default 100MB); retención 90 días. |
| Backup durante operación corrompe memory.db | Media | Usar `VACUUM INTO` de SQLite (snapshot consistente sin pausa). |

---

## 8. Fase 5 — Experiencia (8-12 semanas)

**Objetivo:** reemplazar la UI v1 con dashboard moderno, añadir voice interface, workflow builder.

### 8.1 Entregables

| Módulo | Stack | Semanas | Dependencia |
|---|---|---|---|
| Dashboard Web v2 | React/Vue + Vite + Tailwind | 5 | Fase 3 |
| Admin Panel | integrado en Dashboard v2 | 2 | Fase 3 |
| Visual Workflow Builder | React Flow o similar | 4 | Fase 3 + M05 Skills |
| Voice Interface | Whisper + TTS | 2 | Fase 3 |

### 8.2 Hito de Fase 5: "UI reemplaza a v1"

- Dashboard v2 en `http://localhost:3000` (servido por Node) habla con API v2 en `http://localhost:8000/api/v2/`.
- Soporta: gestión de plugins, knowledge base, skills, monitoring, costos, audit log, backups.
- Visual Workflow Builder permite componer pipelines de skills drag-and-drop.
- Voice Interface permite hablar comandos via micrófono.

### 8.3 Riesgos de Fase 5

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Dashboard v2 es más lento que la SPA v1 | Media | Lazy-load de componentes; memoización. |
| Workflow Builder genera pipelines inválidas | Alta | Validación en frontend + backend antes de ejecutar. |
| Voice Interface depende de servicios externos | Baja | Default a Whisper local; fallback a cloud. |

---

## 9. Fase 6 — Operaciones avanzadas (4-6 semanas)

**Objetivo:** multi-usuario, permisos, perfiles, actualizaciones.

### 9.1 Entregables

| Módulo | Archivos nuevos | Semanas |
|---|---|---|
| Sistema de Permisos (RBAC) | `auth/` | 2 |
| Gestión Multiusuario | `users/` | 2 |
| Sistema de Perfiles | `profiles/` | 1 |
| Sistema de Actualizaciones | `updates/` | 1 |

### 9.2 Hito de Fase 6: "v2.1 release"

Multiusuario con permisos granulares; perfiles por usuario; auto-update de plugins.

---

## 10. Fase 7 — Distribución (12+ semanas, v3.0)

**Objetivo:** SAGE distribuido en múltiples nodos.

### 10.1 Entregables

| Componente | Semanas |
|---|---|
| Gateway distribuido (Nginx + FastAPI) | 3 |
| Pub-sub distribuido para Event Bridge (Redis Streams o NATS) | 3 |
| Plugin Pool (K8s deployment) | 3 |
| Knowledge Base distribuida (Qdrant cluster) | 3 |
| State sync entre nodos core | 3 |

### 10.2 Riesgo mayor

Esta fase puede requerir reescribir partes del core (kernel, dispatcher) para soportar coordinación distribuida. Esto rompería la premisa "FROZEN". Decisión diferida a v3.0 — el Arquitecto decidirá si vale la pena.

---

## 11. Paralelización entre fases

```
                Semana:  1----2----3----4----5----6----7----8----9---10---11---12---13---14---15---16---17---18---19---20
                ───────────────────────────────────────────────────────────────────────────────────────────────────────►
Fase 1 (Cimientos)       [████████████]                                                                                       
Fase 2 (Capacidades)                    [████████████████]                                                                   
Fase 3 (Interfaces)                                      [████████████████]                                  
Fase 4 (Operaciones)                                                       [████████████]                     
                                                                                                             
                                                                          RELEASE v2.0 (semana 18-22)
                                                                                                             
Fase 5 (Experiencia)                                                                         [████████████████████]
Fase 6 (Operaciones avanzadas)                                                                                          [████████████]
                                                                                                                                         
                                                                                                              RELEASE v2.1 (semana 32-36)
                                                                                                                                         
Fase 7 (Distribución)                                                                                                                    [████████████████████]
                                                                                                                                         
                                                                                                              RELEASE v3.0 (semana 44+)
```

**Paralelizaciones posibles:**

- Fase 1 y Fase 2 pueden solaparse 2 semanas (M04 Knowledge Base puede empezar cuando M01 Plugin Runtime esté en beta).
- Fase 3 (SDK) puede empezar 2 semanas antes del final de Fase 2 (el SDK se desarrolla contra la API spec, no contra la implementación).
- Fase 4 puede solaparse con Fase 3 (Cost Tracker y Backup no dependen de la API v2, solo del Event Bridge).
- Fase 5 (Dashboard v2) puede empezar en paralelo con Fase 4 si la API spec de Fase 3 está congelada.

**Secuencia estrictamente serial** (recomendada para equipo pequeño de 2-3 ingenieros):

- Fase 1 → Fase 2 → Fase 3 → Fase 4 (v2.0)
- Fase 5 → Fase 6 (v2.1)
- Fase 7 (v3.0)

---

## 12. Asignación de ingenieros

| Rol | Fases | Notas |
|---|---|---|
| **Ingeniero v2 Senior** (Python) | Fases 1-4 | Lidera arquitectura de cada módulo. |
| **Ingeniero v2 Mid** (Python) | Fases 1-4 | Tests, plugins builtin, integración. |
| **Ingeniero Frontend** | Fases 5-6 | Dashboard v2, Workflow Builder, Admin Panel. |
| **Ingeniero DevOps** | Fases 4, 7 | Telemetry, Backup, Distribución. |
| **Ingeniero SDK** | Fase 3 | SDK Python + JavaScript. |
| **Equipo core (Claude A + Cascade + RE + Kimi)** | Continúan en v1.x | No tocan v2. Coordinan handoff de APIs del core. |

**Importante:** el equipo core NO trabaja en v2. Su única responsabilidad con v2 es:

- Responder preguntas sobre el core (cómo funciona el Event Bus, qué eventos emite cada componente, etc.).
- Estabilizar el core (fusionar ramas, completar wiring).
- Aprobar los contratos de la capa 1 (Event Bridge, Plugin Runtime) para asegurar que no introduzcan acoplamiento no deseado.

---

## 13. Hitos y entregables por release

### v2.0 (semana 18-22)

**Entregables:**

- Capa 1 completa (Plugin Runtime, Event Bridge, Lateral Registry).
- Capa 2 completa (Knowledge Base, Skills, Cache, Rate Limiter).
- Capa 3 parcial (REST API v2 + WS Hub + SDK Python).
- Capa 4 completa (Telemetry, Audit, Cost Tracker, Backup).
- 3+ plugins builtin.
- Documentación completa.

**Criterio de salida:**

- Todos los tests pasan.
- `audit_runtime.py` sigue mostrando ≥85%.
- `python main.py` arranca limpio con todos los plugins activos.
- Al menos 1 caso de uso end-to-end documentado (ej. "notificar por Slack cuando un comando falle").

### v2.1 (semana 32-36)

**Entregables:**

- Dashboard Web v2 (reemplaza UI v1).
- Visual Workflow Builder.
- Voice Interface.
- Sistema de Permisos + Multiusuario.
- Sistema de Actualizaciones.
- 10+ plugins en el marketplace.

**Criterio de salida:**

- Dashboard v2 soporta todas las funcionalidades de la UI v1.
- Workflow Builder puede ejecutar pipelines de 5+ skills.
- Multiusuario con 3 usuarios concurrentes sin interferencia.

### v3.0 (semana 44+)

**Entregables:**

- SAGE distribuido en múltiples nodos.
- Gateway + Pub-sub distribuido.
- Plugin Pool en K8s.

**Criterio de salida:**

- 3 nodos core sirven 100+ comandos/minuto sin degradación.
- Failover de nodo core en < 30s.
- Plugins distribuidos balancean carga.

---

## 14. Riesgos globales del roadmap

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| El equipo core no libera el wiring pendiente a tiempo | Alta | Alto | Fase 1 puede desarrollarse contra mocks; integración real pospuesta. |
| El Plugin Runtime requiere modificaciones al core que el equipo core rechaza | Media | Crítico | Validar contratos de la capa 1 con el equipo core antes de programar. |
| El marketplace nunca despega | Alta | Bajo | MVP funciona sin marketplace (instalación local). |
| ChromaDB/Qdrant no funcionan bien en hardware objetivo | Media | Medio | Fallback a SQLite vector store. |
| Dashboard v2 requiere reescribir web server | Baja | Alto | Dashboard v2 habla con API v2, no con la API v1. No toca `web/server.py`. |
| Distribución (Fase 7) rompe el contrato FROZEN | Alta | Crítico | Decisión diferida a v3.0 — evaluar costo/beneficio cuando se acerque. |

---

## 15. Métricas de progreso

Para cada fase, medir:

| Métrica | Target |
|---|---|
| % tests pasando | 100% |
| % cobertura de código | ≥80% |
| `audit_runtime.py` completion | ≥85% (no debe bajar) |
| Latencia p99 de API v2 | <100ms |
| Tiempo de boot de `python main.py` | <5s |
| Plugins builtin funcionando | ≥3 al final de v2.0 |
| Documentación actualizada | Sí (cada release) |

---

## 16. Dependencias críticas entre fases

```
Fase 1 ────────► Fase 2 ────────► Fase 3 ────────► Fase 4
  │                 │                 │                 │
  │                 │                 │                 ├──► v2.0
  │                 │                 │                 │
  │                 └──► Fase 5 ──► Fase 6 ──────► v2.1
  │
  └──► (cualquier fase puede comenzar solo si Fase 1 está completa)
                                              │
                                              └──► Fase 7 ──► v3.0
```

**Dependencias duras:**

- Fase 2 → Fase 1 (Plugin Runtime y Event Bridge son prerrequisito).
- Fase 3 → Fase 1 + Fase 2 (API v2 expone módulos de Fase 2).
- Fase 4 → Fase 1 (Telemetry consume Event Bridge).
- Fase 5 → Fase 3 (Dashboard habla con API v2).
- Fase 6 → Fase 3 + Fase 5 (multiusuario requiere auth de Fase 3 + UI de Fase 5).
- Fase 7 → v2.1 estable.

**Dependencias blandas:**

- Fase 4 puede empezar antes de que Fase 3 termine (si la API spec está congelada).
- Fase 5 puede empezar en paralelo con Fase 4 (frontend y backend separados).

---

## 17. Plan de comunicación

| Stakeholder | Cadencia | Canal |
|---|---|---|
| Arquitecto | Semanal | Sync directo |
| Equipo core (Claude A, Cascade, RE, Kimi) | Quincenal | Doc compartido (handoff v2 → v1) |
| Ingenieros v2 | Diario | Standup |
| Operadores (cuando v2.0 esté cerca) | Mensual | Demo + release notes |
| Comunidad (cuando v2.1 esté cerca) | Trimestral | Blog post + Discord |

---

## 18. Plan de rollback

Si v2.0 resulta inestable después del release:

1. **Hot-fix:** parche sobre v2.0 sin nuevo release.
2. **Patch release:** v2.0.1 con fix.
3. **Rollback de módulo:** desactivar el módulo problemático via feature flag (sin reinstalar).
4. **Rollback de release:** volver a v1.x (los datos de v2 en `~/.sage_os/` se preservan; el core v1 los ignora).

La arquitectura en capas hace que el rollback sea trivial: desactivar capas 4, 3, 2, 1 en orden revierte a v1.

---

## 19. Conclusión

El roadmap v2 es **realista y progresivo**. La clave del éxito es:

1. **No empezar hasta que v1 esté fusionado y estable.** Construir sobre arena cuesta más caro después.
2. **Fase 1 (cimientos) es lo más crítico.** Si la capa 1 está mal diseñada, todo lo demás arrastra el problema.
3. **El equipo core debe quedar libre** para sus tareas de v1.x. v2 lo construye otro equipo.
4. **Cada fase entrega valor.** Si el proyecto se cancela después de Fase 2, ya hay capacidades nuevas utilizables.
5. **Distribución (Fase 7) es opcional.** Si el caso de uso no lo requiere, v2.1 puede ser el release final durante años.

La próxima acción concreta es: **abrir los RFCs formales** (ver `RFC_FUTURE_MODULES.md`) y **validar los contratos de la capa 1 con el equipo core** antes de programar la primera línea de Fase 1.

— GLM, Arquitecto de Evolución de SAGE

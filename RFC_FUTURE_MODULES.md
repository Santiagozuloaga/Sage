# RFC_FUTURE_MODULES.md — RFCs para Módulos Futuros de SAGE v2

**Autor:** GLM (Arquitecto de Evolución de SAGE)
**Fecha:** 2026-07-06
**Estado:** BORRADOR — para revisión del Arquitecto
**Alcance:** 12 RFCs formales (uno por módulo de `NEW_MODULES_PROPOSAL.md`) + 8 RFCs ligeros (módulos v2.1+)
**Convención:** cada RFC sigue el formato SAGE RFC (Title, Status, Summary, Motivation, Design, Dependencies, Risks, Open Questions)

---

## Tabla de RFCs

| RFC | Módulo | Estado | Prioridad |
|-----|--------|--------|-----------|
| RFC-001 | Plugin Runtime | Borrador | Alta |
| RFC-002 | Event Bridge | Borrador | Alta |
| RFC-003 | Lateral Component Registry | Borrador | Alta |
| RFC-004 | Knowledge Base | Borrador | Alta |
| RFC-005 | Skills System | Borrador | Alta |
| RFC-006 | Cache Layer | Borrador | Media |
| RFC-007 | Rate Limiter | Borrador | Media |
| RFC-008 | Notification System | Borrador | Media |
| RFC-009 | REST API v2 + WS Hub | Borrador | Alta |
| RFC-010 | Telemetry & Audit | Borrador | Media |
| RFC-011 | Cost Tracker | Borrador | Media |
| RFC-012 | Backup System | Borrador | Baja |
| RFC-013 | Voice Interface | Borrador | Baja |
| RFC-014 | Visual Workflow Builder | Borrador | Baja |
| RFC-015 | Admin Panel | Borrador | Baja |
| RFC-016 | Multi-User & Permissions | Borrador | Baja |
| RFC-017 | Distributed Agents | Borrador | Baja |
| RFC-018 | Search Engine | Borrador | Baja |
| RFC-019 | Cron Scheduler | Borrador | Baja |
| RFC-020 | Profile System | Borrador | Baja |

---

# RFC-001 — Plugin Runtime

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Sistema de carga, validación y supervisión de extensiones (plugins) que viven en archivos nuevos y se comunican con el core FROZEN vía Event Bridge + Lateral Registry. Habilita extensión sin modificación del core.

## Motivation

SAGE v1 es FROZEN. Cualquier capacidad nueva requiere modificar archivos del core, lo que choca con la regla arquitectural y obliga a coordinar merges entre múltiples ingenieros. Un sistema de plugins resuelve esto al establecer un contrato estable entre el core y las extensiones.

Sin este RFC, todos los demás RFCs de v2 tendrían que modificar el core, violando la restricción FROZEN.

## Design

### Arquitectura

El Plugin Runtime es el **único punto de contacto** entre v2 y el core v1. Obtiene referencias read-only al `EventBus` y a `kernel.get_component()`, y las expone a los plugins bajo contrato.

### Componentes

1. **Manifest Parser** (`plugins/manifest.py`)
   - Lee `sage-plugin.toml` con `tomli`.
   - Valida contra JSON schema de manifest.
   - Extrae permisos, eventos suscritos/publicados, entrypoint.

2. **Loader** (`plugins/loader.py`)
   - Escanea `~/.sage_os/plugins/`, `/etc/sage/plugins/`, `./plugins/`.
   - Para cada directorio con `sage-plugin.toml`, lo registra como DISCOVERED.
   - No importa código hasta que el plugin esté ENABLED.

3. **Runtime** (`plugins/runtime.py`)
   - Estado: DISCOVERED → INSTALLED → ENABLED → RUNNING → DISABLED → UNINSTALLED.
   - Llama a `importlib.import_module(entrypoint.module)` cuando pasa a ENABLED.
   - Instancia la clase entrypoint, llama `on_load()`, suscribe handlers al Event Bridge.
   - Llama `on_unload()` al desactivar; desuscribe handlers.

4. **Sandbox** (`plugins/sandbox.py`)
   - Aplica permisos del manifest: filesystem, network, subprocess, env.
   - Para plugins untrusted: ejecuta en subproceso con comunicación JSON-RPC.

5. **Contracts** (`plugins/contracts.py`)
   - Clase base `SagePlugin` con métodos: `on_load`, `on_unload`, `on_event`, `on_config_change`, `get_metadata`, `health_check`.
   - Clase `PluginContext` con recursos: `event_bridge`, `registry`, `kernel` (proxy), `config`, `logger`, `metrics`, `get_secret`.

### Permisos

Cada permiso es opt-in:

- `core_read` — acceso read-only a `kernel.get_component()`.
- `filesystem` — lista de paths permitidos.
- `network` — lista de hosts permitidos.
- `subprocess` — booleano.
- `env` — lista de variables de entorno legibles.

### Hot-load

Las transiciones ENABLED ↔ DISABLED son en caliente. No requieren reiniciar el kernel. El Event Bridge gestiona suscripción dinámica.

## Dependencies

- **v1 core read-only:** `EventBus.subscribe_wildcard()`, `kernel.get_component()`.
- **Externos:** `tomli` (parseo TOML), `pydantic` (validación), `importlib` (stdlib).
- **v2 internos:** ninguno (es fundación).

## Risks

- **Plugin malicioso escapa del sandbox:** mitigación — plugins untrusted en subproceso; plugins trusted se auditan antes de bundlear.
- **Conflictos de versión entre plugins:** mitigación — resolver por `manifest.requires` con semver; rechazar conflictos.
- **Plugin rompe contrato en update:** mitigación — `contract_version` en manifest; runtime rechaza cargar plugins con major distinto.

## Open Questions

1. ¿Soporte para plugins en lenguajes distintos a Python (Node, Rust)? Diferido a v2.1.
2. ¿Sandbox basado en `ast` (Python) o `cgroups` (OS)? Recomendación: `ast` para trusted, `cgroups` para untrusted.
3. ¿Cómo se firma un plugin? GPG o sigstore. Pendiente decisión.

---

# RFC-002 — Event Bridge

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Puente unidireccional core→v2 que suscribe un wildcard handler al `EventBus` del core, transforma eventos v1 en eventos v2 con schema canónico, y publica en un bus interno v2 para consumo de plugins y módulos v2.

## Motivation

El `EventBus` del core es v1-centric: enum cerrado de tipos, sin schema estricto, sin correlation ID enriquecido. Los plugins v2 necesitan un bus con schema canónico, eventos tipados, y soporte para tracing distribuido. Sin Event Bridge, cada plugin tendría que suscribirse directamente al bus del core, acoplándose al enum v1.

## Design

### Flujo

1. Event Bridge se suscribe al `EventBus` del core via `subscribe_wildcard(handler)`.
2. Cada evento v1 llega al handler.
3. El handler transforma el `Event` v1 en `SageEventV2` (pydantic):
   - `event_id` (uuid v4)
   - `event_type_v1` (original, ej. `EventType.COMMAND_EXECUTED`)
   - `event_type_v2` (canonical, ej. `sage.command.executed`)
   - `source`, `correlation_id`, `timestamp` (preservados de v1)
   - `payload` (data original)
   - `extension_metadata` (tags añadidos por plugins)
4. Publica el `SageEventV2` en el `internal_bus`.
5. Plugins suscritos reciben el evento v2.

### Mapping v1 → v2

Tabla de mapping (extracto):

| EventType v1 | SageEventV2 type |
|---|---|
| `BOOT` | `sage.kernel.boot` |
| `SHUTDOWN` | `sage.kernel.shutdown` |
| `COMMAND_RECEIVED` | `sage.command.received` |
| `COMMAND_EXECUTED` | `sage.command.executed` |
| `COMMAND_FAILED` | `sage.command.failed` |
| `STATE_CHANGED` | `sage.kernel.state_changed` |
| `MEMORY_SAVED` | `sage.memory.saved` |
| `MEMORY_LOADED` | `sage.memory.loaded` |
| `AGENT_SPAWNED` | `sage.agent.spawned` |
| `AGENT_COMPLETED` | `sage.agent.completed` |
| `ERROR` | `sage.error` |
| `CHECKPOINT` | `sage.recovery.checkpoint` |

### Bus interno v2

- `internal_bus.py` es un pub-sub similar al del core pero con schema pydantic.
- Soporta wildcard subscription.
- Tiene su propio DLQ (no comparte con el del core).
- NO publica en el bus del core — es unidireccional core→v2.

### Latencia

- El handler del Event Bridge es fire-and-forget async.
- Los handlers v2 corren en su propio `asyncio.Task`.
- Latencia añadida: <1ms por evento (medición target).

## Dependencies

- **v1 core read-only:** `EventBus.subscribe_wildcard()`.
- **Externos:** `pydantic`.
- **v2 internos:** M01 (Plugin Runtime — para entregar eventos a plugins).

## Risks

- **Latencia visible en el bus:** mitigación — fire-and-forget; medir en tests.
- **Bridge cae, plugins pierden eventos:** mitigación — DLQ propio; eventos v1 siguen en history del core.
- **Duplicación si plugin se suscribe directamente al bus del core:** mitigación — Plugin Runtime bloquea acceso directo al bus del core.

## Open Questions

1. ¿Event Bridge también publica eventos v2 → core? No por defecto; v2 es lateral. Pero si un plugin quiere hacer algo en el core (ej. emitir un comando), ¿cómo? Respuesta: via REST API v2 → web server → kernel.execute_command (sin tocar el bus).
2. ¿Serializar eventos v2 a JSON para sidecars (Telemetry, Cost Tracker)? Sí — pydantic lo hace nativamente.

---

# RFC-003 — Lateral Component Registry

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Registro separado de `kernel._components` donde los módulos v2 se registran y se descubren entre sí. Mantiene limpio el registry del core y habilita lookups type-safe via interfaces declaradas.

## Motivation

`kernel._components` es el registry del core. Los módulos v2 no deberían registrarse ahí porque: (a) contaminarían el core; (b) el shutdown loop del kernel los cerraría, rompiendo el aislamiento; (c) no hay forma de distinguir "componente core" de "componente v2". Sin un registry lateral, los módulos v2 no pueden encontrarse.

## Design

### Interfaz

```python
class LateralRegistry:
    def register(self, name: str, component: Any, interface: Type) -> None
    def unregister(self, name: str) -> None
    def get(self, name: str) -> Optional[Any]
    def get_typed(self, name: str, interface: Type) -> Optional[interface]
    def list(self) -> Dict[str, Type]
    def list_by_interface(self, interface: Type) -> List[str]
```

### Interfaces declaradas

Cada tipo de componente v2 tiene una interfaz abstracta en `extensions/interfaces.py`:

- `IKnowledgeBase` — métodos `query`, `add_document`, `list_documents`.
- `ICache` — métodos `get`, `set`, `invalidate`.
- `ISkill` — métodos `invoke`, `metadata`.
- `INotificationChannel` — métodos `send`, `health_check`.
- `ISearchIndexer` — métodos `index`, `search`.
- `IWorkflowNode` — métodos `execute`, `inputs`, `outputs`.

### Registro

- Los módulos v2 se registran en su `on_load`.
- El registry valida que el componente implemente la interfaz declarada.
- Nombres jerárquicos: `knowledge_base`, `cache.l1`, `cache.l2`, `skill:web_search.search`.
- Conflictos de nombre: rechazado con error explícito.

### Dependencias

- Si el módulo A depende del módulo B, A declara `requires=["B"]` en su manifiesto.
- El registry rechaza activar A si B no está registrado.
- Si B se desactiva, A pasa a estado BLOCKED.

## Dependencies

- **v1 core:** ninguno (totalmente lateral).
- **Externos:** ninguno.
- **v2 internos:** M01 (Plugin Runtime).

## Risks

- **Conflicto de nombres:** mitigación — namespacing por plugin (`@author/plugin_name`).
- **Dependencias circulares:** mitigación — validación topológica al registrar.
- **Módulo se desactiva con dependientes vivos:** mitigación — registry rechaza desactivar; pide desactivar dependientes primero.

## Open Questions

1. ¿Soporte para hot-swap (reemplazar un componente sin desactivar dependientes)? Diferido a v2.1.
2. ¿Versiones de interfaz? Si `IKnowledgeBase` cambia, ¿cómo se versiona? Recomendación: `IKnowledgeBaseV1`, `IKnowledgeBaseV2`.

---

# RFC-004 — Knowledge Base

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Almacenamiento durable de conocimiento semántico (documentos, FAQs, código de referencia) separado del memory del core. Soporta ingestión multi-formato, embeddings locales, vector store, y retrieval con reranking. Habilita RAG.

## Motivation

`memory/engine.py` es para estado de sesión (registros de ingeniería, PRs, sesiones). No sirve para conocimiento durable: no tiene embeddings, no hace retrieval semántico, no escala a miles de documentos. Cada agente hoy reinicia sin contexto acumulado.

## Design

### Arquitectura

```
Documento → Ingestor → Chunks → Embeddings → Vector Store
                                                │
                                                ▼
                                          Retrieval ← Query
                                                │
                                                ▼
                                            Reranker
                                                │
                                                ▼
                                          Resultados
```

### Componentes

1. **Ingestor** (`knowledge_base/ingestor.py`)
   - Pipelines por formato: texto, markdown, código, PDF.
   - Chunking: por tokens (default 512) con overlap (default 64).
   - Metadata: source, format, ingested_at, session_id (opcional).

2. **Embeddings** (`knowledge_base/embeddings.py`)
   - Default: `sentence-transformers/all-MiniLM-L6-v2` (384 dim, rápido en CPU).
   - Configurable: cualquier modelo HuggingFace, o API (OpenAI, Cohere).
   - Cache de embeddings en SQLite para evitar recálculo.

3. **Vector Store** (`knowledge_base/vector_store.py`)
   - Default: ChromaDB (embedded, sin servidor).
   - Alternativas: Qdrant, SQLite vector store (fallback sin dependencias).
   - Operaciones: insert, query (top-k), delete by metadata filter.

4. **Retriever** (`knowledge_base/retriever.py`)
   - Query: texto → embeddings → top-k del vector store.
   - Filtros: por metadata (source, format, session_id, date_range).
   - Reranking: opcional, vía cross-encoder (`ms-marco-MiniLM-L-12-v2`).

5. **Metadata Store**
   - SQLite en `~/.sage_os/knowledge_meta.db` para metadata no-vectorial.
   - Tablas: `documents`, `chunks`, `embeddings_cache`.

### API pública (registrada en Lateral Registry como `knowledge_base`)

- `add_document(content, metadata)` → document_id
- `add_documents_batch(items)` → list[document_id]
- `query(text, top_k=5, filters=None)` → list[SearchResult]
- `get_document(id)` → Document
- `delete_document(id)` → bool
- `list_documents(filters)` → list[Document]
- `stats()` → {document_count, chunk_count, total_tokens}

### Eventos v2 publicados

- `sage.knowledge.document_added`
- `sage.knowledge.document_deleted`
- `sage.knowledge.search_performed`

## Dependencies

- **v1 core read-only:** `memory.engine` (para correlacionar knowledge con session_id).
- **Externos:** `chromadb` (o `qdrant-client`), `sentence-transformers`, `PyPDF2`, `tiktoken`.
- **v2 internos:** M01, M02, M03.

## Risks

- **Tamaño sin bound:** mitigación — política de retención + TTL por documento.
- **Costo de embeddings online:** mitigación — default a `sentence-transformers` local.
- **Contaminación por conocimiento erróneo:** mitigación — scoring de confianza + revisión humana opcional.
- **ChromaDB pesado para hardware objetivo:** mitigación — fallback a SQLite vector store.

## Open Questions

1. ¿Multilingüe? `all-MiniLM-L6-v2` es multilingüe pero no excelente en español. ¿Modelo específico para español? Pendiente benchmark.
2. ¿Re-ranking por defecto o opcional? Recomendación: opcional (off por defecto; on para queries críticas).
3. ¿Cómo manejar documentos actualizados? Insertar nueva versión + marcar vieja como `superseded` (no borrar).

---

# RFC-005 — Skills System

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Sistema de capacidades modulares invocables por agentes y workflows. Cada skill es un módulo Python con contrato claro. Habilita un ecosistema de skills reutilizables sin modificar el enum `AgentCapability` del core.

## Motivation

`agents/models.py` define `AgentCapability` como un enum cerrado (`CODE_GENERATION`, `DEBUGGING`, etc.). No hay forma de añadir capacidades nuevas sin modificar el enum y los agentes. Las skills v2 son un concepto paralelo: modular, plugable, versionada.

## Design

### Contrato

```python
class Skill(ABC):
    @abstractmethod
    def metadata(self) -> SkillMetadata: ...
    
    @abstractmethod
    async def invoke(self, params: Dict, context: SkillContext) -> SkillResult: ...
```

### SkillMetadata

- `id` — único (ej. `web_search.search`).
- `name` — humano-legible.
- `description` — para LLM (puede usarse como system prompt).
- `version` — semver.
- `params_schema` — JSON schema de parámetros.
- `result_schema` — JSON schema del resultado.
- `timeout_seconds` — default 60.
- `requires` — permisos y dependencias (knowledge_base, etc.).

### SkillContext

Recursos disponibles para la skill:

- `context.knowledge_base` (si la skill declara `requires=["knowledge_base"]`).
- `context.cache` (si declara `requires=["cache"]`).
- `context.memory_read` — acceso read-only a `memory.engine`.
- `context.logger` — logger con tag de la skill.
- `context.metrics` — counter / histogram.

### Registro

- Las skills se registran en el Lateral Registry como `skill:<plugin_name>.<skill_id>`.
- Namespacing previene conflictos.
- El Skills System expone `invoke(skill_id, params)` que cualquier plugin puede llamar.

### Invocación

- `skills.invoke("web_search.search", {"query": "SAGE OS"})`
- Validación de params contra schema.
- Timeout (default 60s, configurable por skill).
- Resultado validado contra `result_schema`.
- Eventos: `sage.skill.invoked`, `sage.skill.completed`, `sage.skill.failed`.

### Skills builtin

- `skills/builtin/web_search.py` — búsqueda web (SearXNG o DuckDuckGo).
- `skills/builtin/code_review.py` — revisión de código vía LLM.
- `skills/builtin/sql_query.py` — ejecución de SQL contra SQLite.
- `skills/builtin/file_read.py` — lectura de archivos con permisos.

## Dependencies

- **v1 core read-only:** `agents.router` (para skills que necesitan buscar agentes por capacidad).
- **Externos:** stdlib.
- **v2 internos:** M01, M02, M03, M04 (para skills RAG).

## Risks

- **Skill mal implementada cuelga al agente:** mitigación — timeout por invocación.
- **Conflicto de nombres:** mitigación — namespacing por plugin.
- **Permisos peligrosos (`filesystem.write`):** mitigación — declarar permisos en metadata; Skills System los aplica.

## Open Questions

1. ¿Las skills pueden invocar a otras skills? Sí, pero con profundidad máxima (default 5) para prevenir recursión infinita.
2. ¿Las skills pueden publicar eventos? Sí, via `context.event_bridge.publish()`.
3. ¿Cómo se discoveran skills para un agente v2? Via `registry.list_by_interface(ISkill)` o via manifest del agente.

---

# RFC-006 — Cache Layer

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Cache L1 (memoria LRU) + L2 (SQLite) para respuestas de providers y resultados de skills. Reduce costo y latencia. Invalidación por evento.

## Motivation

Cada llamada a un provider cuesta dinero y tiempo. No hay cache — si dos comandos son idénticos, se pagan dos veces. Para comandos repetitivos, hit rate puede ser 30-60%.

## Design

### Arquitectura

```
Query → Key Builder → L1 lookup → L2 lookup → Miss → Provider call
                ↓ hit                ↓ hit              ↓
              Return              Return              Set L1 + L2
```

### Capas

1. **L1 Memory** (`cache/l1_memory.py`)
   - LRU con bound configurable (default 1000 entradas).
   - TTL por entrada.
   - Hit time: <1ms.

2. **L2 SQLite** (`cache/l2_sqlite.py`)
   - Persistente en `~/.sage_os/cache.db`.
   - TTL por entrada.
   - Hit time: <10ms.

### Key Builder

La clave de cache es:

```
key = sha256(
    prompt +
    context_hash +
    user_id +
    provider +
    model
)
```

`context_hash` es un hash del contexto relevante (knowledge base results, session history hash). Si el contexto cambia, la clave cambia, evitando cache staling.

### Invalidación

El `invalidator.py` suscribe al Event Bridge:

- `sage.knowledge.document_added` → invalidar caches de RAG (prefix `rag:`).
- `sage.memory.saved` → invalidar caches de sesión (prefix `session:`).
- `sage.plugin.config_changed` → invalidar caches del plugin (prefix `plugin:<name>:`).

### API pública (registrada como `cache`)

- `get(key)` → Optional[value]
- `set(key, value, ttl_seconds=None)`
- `invalidate(key)`
- `invalidate_prefix(prefix)`
- `stats()` → {l1_hits, l1_misses, l2_hits, l2_misses, size}

## Dependencies

- **v1 core read-only:** ninguno.
- **Externos:** `cachetools`, `sqlite3`.
- **v2 internos:** M02 (Event Bridge — para invalidación).

## Risks

- **Cache staling:** mitigación — clave incluye contexto relevante; invalidación por evento.
- **Memoria L1 sin bound:** mitigación — LRU con bound configurable.
- **Privacidad (dos usuarios, mismo prompt):** mitigación — `user_id` parte de la clave.

## Open Questions

1. ¿L2 encriptada? Pendiente — si los prompts contienen PII, sí.
2. ¿Compartir cache entre usuarios (opt-in)? Para prompts genéricos ("¿qué es SAGE?"). Diferido a v2.1.

---

# RFC-007 — Rate Limiter

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Token bucket rate limiter para proteger providers y recursos de abuso. Configurable por usuario, provider, y ventana. Fail-open si el limiter cae.

## Motivation

Los providers tienen rate limits (Grok, Gemini). Hoy no hay protección — un usuario puede disparar 100 comandos y agotar la cuota. El dispatcher encola pero todas se ejecutan.

## Design

### Algoritmo

Token bucket:

- Cada bucket tiene `capacity` y `refill_rate` (tokens por segundo).
- Cada consumo resta `cost` tokens (default 1).
- Si no hay tokens suficientes, se deniega hasta el próximo refill.

### Políticas

Definidas en `rate_limiter/policies.py`:

- Por usuario: `user:<id>` → 100 req/min.
- Por provider: `provider:<name>` → 60 req/min (limites reales de API).
- Por skill: `skill:<id>` → 30 req/min.
- Global: `*` → 1000 req/min (protección sistémica).

Políticas configurables en `~/.sage_os/rate_limits.json`.

### Storage

- Default: in-memory (dict de buckets).
- Distribuido: Redis (para multi-nodo en v3.0).

### Fail-open

Si el limiter no responde (caída, timeout interno), se permite el comando y se loguea. Razonamiento: mejor permitir un comando de más que bloquear el sistema.

### Integración

El Rate Limiter NO intercepta el dispatcher ni el provider_router. Expone `check_and_consume(key, cost=1)` que los plugins llaman antes de invocar un provider.

### Eventos

Suscribe al Event Bridge para trackear uso: cada `sage.provider.call` consume tokens del bucket del usuario.

Publica `sage.rate_limit.threshold_reached` cuando un bucket está al 80% (warning) y al 100% (block).

## Dependencies

- **v1 core read-only:** ninguno.
- **Externos:** `redis` (opcional), `asyncio_throttle` o implementación propia.
- **v2 internos:** M02 (Event Bridge).

## Risks

- **Limiter muy estricto bloquea comandos legítimos:** mitigación — configuración por usuario/provider; bypass para admin.
- **Limiter cae, bloquea sistema:** mitigación — fail-open.

## Open Questions

1. ¿Burst o steady rate? Token bucket permite burst hasta `capacity`; steady rate es `refill_rate`. Configurable.
2. ¿Chargeback de costos al usuario excedido? Integrar con Cost Tracker (M11). Diferido a v2.1.

---

# RFC-008 — Notification System

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Sistema de notificaciones multi-canal (email, webhook, Slack, desktop, in-app). Motor de reglas evento → canal + template. Modo digest para evitar spam.

## Motivation

No hay forma de que SAGE avise a un humano cuando algo importante pasa. El dashboard muestra estado pero no envía alertas. Sin notificaciones, SAGE requiere atención constante.

## Design

### Arquitectura

```
Evento v2 → Rule Engine → Canal matching → Cola de envío → Channel Adapter → Destinatario
                                ↓
                            Digest (opcional)
```

### Componentes

1. **Dispatcher** (`notifications/dispatcher.py`)
   - Suscribe al Event Bridge con wildcard.
   - Cada evento pasa por el Rule Engine.
   - Si matchea, encola para envío.

2. **Rule Engine** (`notifications/rules.py`)
   - Reglas en `~/.sage_os/notifications/rules.json`.
   - Sintaxis: `{"event_type": "sage.command.failed", "channel": "slack", "template": "command_failed", "throttle_minutes": 5}`.
   - Soporta filtros por metadata (`{"event_type": "sage.command.failed", "filter": {"error_code": "provider_unavailable"}}`).

3. **Channels** (`notifications/channels/`)
   - `email.py` — SMTP via `aiosmtplib`.
   - `webhook.py` — HTTP POST via `httpx`.
   - `slack.py` — Slack Web API via `slack-sdk`.
   - `desktop.py` — OS notification (DBus on Linux, NotificationCenter on macOS, Win10 API on Windows).
   - `in_app.py` — push al WebSocket Hub para mostrar en dashboard.

4. **Templates** (`notifications/templates/`)
   - Jinja2 por tipo de evento.
   - Variables: `{{ event.source }}`, `{{ event.payload.command }}`, etc.

5. **Digest** (`notifications/digest.py`)
   - Modo digest: agrupa notificaciones por ventana (default 15 min) y envía un solo mensaje.
   - Configurable por canal y por regla.

### Credenciales

- En `~/.sage_os/notifications/credentials.enc`, cifradas con clave derivada de un master key.
- El master key vive en `~/.sage_os/master.key` (permisos 0600).
- Plugins acceden via `context.get_secret("slack_token")`.

### Throttling

Cada regla tiene `throttle_minutes` (default 5). Si la misma regla se dispara N veces en la ventana, solo se envía la primera. Las demás se cuentan en `throttle_count` pero no se envían.

### Retry

Si un canal falla:

- Retry con backoff exponencial (1s, 5s, 30s, 5min, 30min).
- Tras 5 fallos, desactivar canal y notificar via canal alternativo.

### Eventos v2 publicados

- `sage.notification.dispatched`
- `sage.notification.failed`
- `sage.notification.channel_disabled`

## Dependencies

- **v1 core read-only:** ninguno.
- **Externos:** `aiosmtplib`, `httpx`, `slack-sdk`, `pywebpush`, `jinja2`.
- **v2 internos:** M01, M02, M03.

## Risks

- **Spam:** mitigación — digest mode, throttle por regla, suppress duplicates.
- **Credenciales comprometidas:** mitigación — cifradas en reposo; permisos 0600.
- **Fallos silenciosos:** mitigación — retry + desactivación + notificación por canal alternativo.

## Open Questions

1. ¿Soporte para SMS (Twilio)? Diferido a v2.1.
2. ¿Notificaciones push móviles (FCM/APNs)? Diferido a v2.1.
3. ¿Cómo manejar múltiples destinatarios por canal? Lista de destinatarios en la regla.

---

# RFC-009 — REST API v2 + WebSocket Hub

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

API REST versionada, documentada (OpenAPI), autenticada (JWT + API key) y WebSocket Hub para eventos en tiempo real. Expone todas las capacidades v2. Montada sin modificar `web/server.py` (via plugin "api_v2_mount").

## Motivation

La API v1 actual es mínima, sin versión, sin auth, sin documentación OpenAPI. No hay forma de exponer capacidades v2 sin ensuciar el server.py existente. SDKs y dashboard v2 necesitan una superficie API estable y documentada.

## Design

### Montaje

Dos opciones:

**Opción A (preferida):** Plugin "api_v2_mount" que obtiene `kernel.get_component('web_server')` en `on_load` y llama `app.mount("/v2", v2_app)`. No toca `web/server.py`. Requiere que el web server exponga `app` (lo hace, es FastAPI).

**Opción B (fallback):** FastAPI app v2 separado en puerto 8001 (sidecar). Útil si la opción A no funciona por permisos del plugin.

### Estructura

```
api_v2/
├── app.py              # FastAPI app v2
├── routers/
│   ├── plugins.py
│   ├── knowledge.py
│   ├── skills.py
│   ├── cache.py
│   ├── notifications.py
│   ├── profiles.py
│   ├── audit.py
│   ├── telemetry.py
│   ├── costs.py
│   ├── backups.py
│   ├── workflows.py
│   ├── admin.py
│   └── search.py
├── auth.py             # JWT + API key
├── schemas.py          # pydantic models
├── middleware.py       # auth, rate limit, request ID
└── openapi_tags.py     # Swagger metadata
```

### Autenticación

- **JWT** para sesiones de usuario (login → token → header `Authorization: Bearer <token>`).
- **API key** para service-to-service (header `X-API-Key: <key>`).
- Endpoints v2 requieren auth; endpoints v1 no (compatibilidad).

### Endpoints (extracto)

Ver `SAGE_V2_ARCHITECTURE.md` §6.1 para tabla completa.

### WebSocket Hub

- Endpoint: `/ws/v2` (montado en el mismo app v2).
- Suscribe al `internal_bus` del Event Bridge.
- Pushea eventos a clientes conectados.
- Soporta filtros via query params: `/ws/v2?event_type=sage.command.failed&source=dispatcher`.

### Rate limiting

Middleware que aplica el Rate Limiter (M07) por API key.

### Request ID

Cada request recibe un `X-Request-ID` (generado o propagado del cliente). Se incluye en logs y en responses. Permite tracing.

## Dependencies

- **v1 core read-only:** `kernel.get_component('web_server')` (para Opción A).
- **Externos:** `fastapi`, `pyjwt`, `pydantic`.
- **v2 internos:** M01, M02, M03, M04, M05, M06, M07, M08 (todos los que expone).

## Risks

- **Montar routers v2 rompe v1:** mitigación — sub-app FastAPI separado via `app.mount("/v2", ...)`; aislamiento de errores.
- **Auth rompe clientes existentes:** mitigación — auth opt-in; v1 endpoints no la requieren.
- **Documentación desactualizada:** mitigación — OpenAPI generada automáticamente por FastAPI.

## Open Questions

1. ¿Opción A o B? Recomendación: A primero; B si A falla.
2. ¿GraphQL además de REST? Diferido a v2.1.
3. ¿Webhooks salientes (SAGE notifica a servicios externos via API v2)? Cubierto por Notification System (M08).

---

# RFC-010 — Telemetry & Audit

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Sistema de observabilidad con métricas Prometheus, traces OpenTelemetry, y audit log append-only. Proceso aislado (sidecar) que lee del Event Bridge.

## Motivation

No hay métricas, no hay traces, no hay log de auditoría. Debuggear un comando fallido requiere reproducirlo. Auditar quién hizo qué es imposible.

## Design

### Componentes

1. **Metrics** (`telemetry/metrics.py`)
   - Prometheus client.
   - Métricas: `sage_commands_total`, `sage_command_duration_seconds`, `sage_provider_calls_total`, `sage_memory_records_total`, `sage_event_bus_handlers_active`, `sage_plugin_load_seconds`, `sage_dispatcher_queue_depth`.
   - Exportadas en `/api/v2/telemetry/metrics` (Prometheus exposition format).

2. **Tracer** (`telemetry/tracer.py`)
   - OpenTelemetry SDK.
   - Span por comando: `command_execution` → `dispatcher_dispatch` → `task_execute` → `provider_call` → `provider_generate_text`.
   - Exportado via OTLP a un collector configurable (Jaeger, Tempo, Honeycomb).

3. **Sampling** (`telemetry/sampling.py`)
   - Traces: sampling configurable (default 10%, 100% para errores).
   - Métricas: siempre 100%.

4. **Audit Log** (`audit/log.py`)
   - SQLite WAL append-only en `~/.sage_os/audit/audit.log.db`.
   - Eventos auditados: `command_executed`, `command_failed`, `plugin_loaded`, `plugin_unloaded`, `config_changed`, `user_login`, `user_logout`, `permission_granted`, `permission_revoked`.
   - Redacción de PII via `redactor.py` (regex-based, configurable).

5. **Rotator** (`audit/rotator.py`)
   - Rotación por tamaño (default 100MB).
   - Retención configurable (default 90 días).
   - Archivos rotados: `audit.log.db.1`, `audit.log.db.2`, etc.

### Proceso aislado

Telemetry corre como proceso separado (sidecar):

- Lee eventos del Event Bridge via WebSocket (suscribe al WS Hub o al internal_bus via IPC).
- No comparte memoria con el core.
- Si cae, el core sigue; se pierden métricas/traces durante el downtime.

### Endpoints v2

- `GET /api/v2/telemetry/metrics` — Prometheus format.
- `GET /api/v2/telemetry/traces?limit=100` — JSON con traces recientes.
- `GET /api/v2/audit?limit=100&event_type=...` — JSON con entradas de audit log.

## Dependencies

- **v1 core read-only:** `~/.sage_os/memory.db` (solo lectura para correlación).
- **Externos:** `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`.
- **v2 internos:** M02 (Event Bridge).

## Risks

- **Overhead:** mitigación — sampling configurable.
- **Tamaño del audit log:** mitigación — rotación + retención.
- **Privacidad en audit log:** mitigación — redacción de PII por defecto.

## Open Questions

1. ¿Backend de traces recomendado? Jaeger (self-hosted) o Honeycomb (SaaS). Pendiente decisión operativa.
2. ¿Audit log en SQLite o en archivo de texto append-only? SQLite para queries; archivo para compliance estricto. Recomendación: SQLite + export a archivo bajo demanda.

---

# RFC-011 — Cost Tracker

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Contabilidad de uso de API por provider, usuario, sesión, y skill. Tabla de precios actualizable. Alertas de presupuesto.

## Motivation

SAGE llama a providers pagos (Grok, Gemini) sin trackear costo. No hay forma de saber cuánto se gastó por usuario, por sesión, por skill. Sin esto, no hay chargeback ni control de presupuesto.

## Design

### Componentes

1. **Tracker** (`costs/tracker.py`)
   - Suscribe al Event Bridge.
   - Cada `sage.provider.call` con metadata de tokens (input, output) → lookup de precio → inserta en DB.

2. **Pricing** (`costs/pricing.py`)
   - Tabla de precios en `~/.sage_os/costs/pricing.json`:
     ```json
     {
       "grok": {
         "grok-2": {"input_per_1k": 0.005, "output_per_1k": 0.015, "currency": "USD"},
         "grok-3": {"input_per_1k": 0.012, "output_per_1k": 0.036, "currency": "USD"}
       },
       "gemini": { ... },
       "ollama": { "default": {"input_per_1k": 0, "output_per_1k": 0, "currency": "USD"} }
     }
     ```
   - Versionado por fecha (precios cambian).
   - Descarga automática desde un endpoint central (opcional).

3. **Aggregator** (`costs/aggregator.py`)
   - Agregaciones por user / session / skill / período.
   - Materialized views en SQLite para queries rápidas.

4. **Alerts** (`costs/alerts.py`)
   - Budgets por usuario (configurable).
   - Publica `sage.cost.threshold_reached` (80% warning, 100% block).

### DB Schema

Tabla `cost_events`:

- `id` (PK), `timestamp`, `user_id`, `session_id`, `provider`, `model`, `tokens_input`, `tokens_output`, `cost_usd`, `skill_id` (nullable), `command_id` (nullable).

### Endpoints v2

- `GET /api/v2/costs?period=daily&from=2026-07-01&to=2026-07-31` — costos por día.
- `GET /api/v2/costs/by_user?user_id=...` — desglose por usuario.
- `GET /api/v2/costs/by_skill?skill_id=...` — desglose por skill.
- `POST /api/v2/costs/budgets` — set budget for user.

## Dependencies

- **v1 core read-only:** ninguno.
- **Externos:** `sqlite3`, `pydantic`.
- **v2 internos:** M02 (Event Bridge).

## Risks

- **Precios desactualizados:** mitigación — `pricing.json` versionado; descarga opcional desde endpoint central.
- **Tracker cae, se pierden eventos de costo:** mitigación — DLQ del Event Bridge; replay cuando vuelve.
- **Currency fluctuation:** mitigación — registrar moneda; conversión bajo demanda.

## Open Questions

1. ¿Chargeback real (cobrar a usuarios)? Diferido a v2.1 (requiere Stripe integration).
2. ¿Budgets globales vs por usuario? Ambos; configurable.

---

# RFC-012 — Backup System

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Snapshots periódicos y on-demand de todo el estado de SAGE (`~/.sage_os/`). Restauración point-in-time. Sin detener el kernel.

## Motivation

`~/.sage_os/` contiene memory.db, knowledge_db, audit log, configs — todo el estado. No hay backup automático. Un fallo de disco pierde todo.

## Design

### Componentes

1. **Manager** (`backup/manager.py`)
   - Programa backups automáticos (cron interno).
   - Ejecuta backups on-demand via API.
   - Mantiene índice de backups.

2. **Snapshot** (`backup/snapshot.py`)
   - Captura consistente de:
     - `memory.db` via `VACUUM INTO` (snapshot atómico sin pausa).
     - `knowledge_db/` via pausa breve del Event Bridge + copia.
     - `audit/audit.log.db` via `VACUUM INTO`.
     - `config.json`, `boot_config.json` via copia.
     - `plugins/.installed.json` y configs de plugins via copia.
   - Comprime en `.tar.gz`.
   - Hash SHA256 para verificación.

3. **Restore** (`backup/restore.py`)
   - Restauración point-in-time.
   - NO restaura en caliente — requiere SAGE detenido.
   - Validación de hash antes de restaurar.
   - Backup del estado actual antes de sobrescribir (por si se quiere revertir).

4. **Retention** (`backup/retention.py`)
   - Política: mantener N diarios + M semanales + K mensuales.
   - Defaults: 7 diarios + 4 semanales + 12 mensuales.

5. **Scheduler** (`backup/scheduler.py`)
   - Cron interno (no depende del Cron Scheduler v2.1).
   - Defaults: diario a las 03:00, semanal los domingos.

### Storage

- Default: `~/.sage_os/backups/`.
- Remoto (S3, SFTP): configurable.

### Endpoints v2

- `GET /api/v2/backups` — lista backups.
- `POST /api/v2/backups` — crea backup on-demand.
- `GET /api/v2/backups/{id}` — metadata.
- `POST /api/v2/backups/{id}/restore` — restaura (requiere SAGE detenido; endpoint rechaza si está corriendo).

## Dependencies

- **v1 core read-only:** filesystem de `~/.sage_os/`.
- **Externos:** `tarfile`, `sqlite3`, `hashlib`.
- **v2 internos:** M02 (Event Bridge — para pausa breve durante snapshot).

## Risks

- **Backup durante operación corrompe datos:** mitigación — `VACUUM INTO` para SQLite; pausa breve del Event Bridge para ChromaDB.
- **Tamaño sin bound:** mitigación — compresión + retención.
- **Restauración en caliente corrompe:** mitigación — endpoint rechaza si SAGE está corriendo.

## Open Questions

1. ¿Backup incremental o solo full? Full por simplicidad; incremental diferido a v2.1.
2. ¿Cifrado de backups? Pendiente — si contiene PII, sí. Cifrar con master key.
3. ¿Backup remoto por defecto? No — el usuario debe configurar destino remoto explícitamente.

---

# RFC-013 — Voice Interface (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Interfaz de voz: speech-to-text (Whisper) + text-to-speech (TTS). Habla con API v2 como un cliente más.

## Motivation

Algunos casos de uso (asistencia en movimiento, accesibilidad) se benefician de voz. Sin esto, SAGE requiere teclado.

## Design

- ASR: Whisper local (small model) o API (OpenAI Whisper).
- TTS: Piper local o API (OpenAI TTS, ElevenLabs).
- Pipeline: audio → texto → API v2 → respuesta texto → audio.
- Activación por palabra clave ("Hey SAGE") o push-to-talk.

## Dependencies

- API v2 (M09).
- `openai-whisper` o `faster-whisper`; `piper-tts` o API.

## Risks

- Latencia ASR local en CPU puede ser >2s. Mitigación: modelo small; fallback a API.
- Privacidad del audio. Mitigación: procesamiento local por defecto.

## Open Questions

1. ¿Detección de palabra clave local o en servidor? Local (Vosk o Picovoice).
2. ¿Multi-idioma? Sí, configurable.

---

# RFC-014 — Visual Workflow Builder (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Editor drag-and-drop de pipelines de skills. Genera JSON que se ejecuta via API v2.

## Motivation

Componer skills en pipelines requiere código hoy. Un builder visual baja la barrera.

## Design

- Frontend: React Flow o similar.
- Nodos: skills registradas + operadores (if/else, loop, parallel).
- Output: JSON workflow spec.
- Ejecución: backend en API v2 recibe el JSON y lo ejecuta.
- Persistencia: workflows en `~/.sage_os/workflows/`.

## Dependencies

- API v2 (M09).
- Skills System (M05).
- React Flow (frontend).

## Risks

- Workflows inválidos. Mitigación: validación frontend + backend.
- Loops infinitos. Mitigación: max iterations configurable.

## Open Questions

1. ¿Versionado de workflows? Sí, semver.
2. ¿Sharing de workflows (marketplace)? Diferido a v2.2.

---

# RFC-015 — Admin Panel (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Interfaz de administración integrada en Dashboard v2: gestión de usuarios, permisos, plugins, configuración global.

## Motivation

Operar SAGE en multiusuario requiere UI de admin. Hoy no existe.

## Design

- Integrado en Dashboard v2 (no es app separada).
- Roles: admin, operator, user, viewer.
- Acciones: crear/editar/eliminar usuarios, asignar permisos, activar/desactivar plugins, ver audit log, configurar rate limits y budgets.

## Dependencies

- Dashboard v2.
- Multi-User & Permissions (RFC-016).
- API v2 (M09).

## Risks

- Acciones destructivas. Mitigación: confirmación + audit log.

## Open Questions

1. ¿MFA obligatorio para admin? Sí, recomendación.
2. ¿Self-service para usuarios (cambiar su propia password)? Sí.

---

# RFC-016 — Multi-User & Permissions (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Sistema de usuarios, roles (RBAC), permisos granulares, y sesiones concurrentes.

## Motivation

SAGE v1 es single-user. Multiusuario es necesario para uso en equipo.

## Design

- Usuarios: tabla `users` en `~/.sage_os/users.db`.
- Roles: admin, operator, user, viewer.
- Permisos: por recurso (knowledge_base, skills, plugins) y acción (read, write, execute, admin).
- Sesiones: JWT con expiración; refresh tokens.
- Concurrencia: sin límite (cada usuario tiene su propia sesión).

## Dependencies

- API v2 (M09).
- Audit Log (M10).

## Risks

- Privilege escalation. Mitigación: validación en cada endpoint; audit log.

## Open Questions

1. ¿LDAP/SSO? Diferido a v2.2.
2. ¿Permisos por plugin? Sí, configurable.

---

# RFC-017 — Distributed Agents (v3.0)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Agentes distribuidos en múltiples nodos. Coordinación via pub-sub distribuido (Redis Streams o NATS).

## Motivation

Escalar SAGE más allá de un solo nodo para alta disponibilidad y throughput.

## Design

- Cada nodo core corre un kernel completo.
- Event Bridge distribuido via Redis Streams.
- Knowledge Base distribuida via Qdrant cluster.
- Memory: sincronización eventual via CRDTs o particionado por session_id.

## Dependencies

- Fase 7 del roadmap.
- Redis o NATS.

## Risks

- Particionamiento de red. Mitigación: quorum + eventual consistency.
- Latencia inter-nodo. Mitigación: cache local + invalidación.

## Open Questions

1. ¿Particionado por session_id o por user_id? Por session_id (cada sesión es local a un nodo).
2. ¿Failover automático? Sí, via heartbeat + leader election.

---

# RFC-018 — Search Engine (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Búsqueda full-text sobre memory + knowledge base + audit log. Indexado incremental.

## Motivation

Encontrar un comando específico ejecutado hace meses requiere log traversal manual.

## Design

- Indexer: SQLite FTS5 (built-in) para memory + audit log.
- Indexer: ChromaDB para knowledge base (ya indexado por embeddings).
- API unificada: `/api/v2/search?q=...&sources=memory,knowledge,audit`.

## Dependencies

- M04 Knowledge Base.
- M10 Audit Log.
- API v2 (M09).

## Risks

- Tamaño del índice FTS5. Mitigación: index selectivo (no indexar payloads grandes).

## Open Questions

1. ¿Soporte para regex? Sí, via FTS5 syntax.
2. ¿Búsqueda por rango de fechas? Sí.

---

# RFC-019 — Cron Scheduler (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Programación calendaria de tareas (cron-style). Complementa al priority dispatcher (que es on-demand).

## Motivation

Backups, reportes diarios, syncs periódicos requieren scheduling calendar, no priority queue.

## Design

- Sintaxis cron estándar (`*/5 * * * *`).
- Persistencia: `~/.sage_os/cron/jobs.db`.
- Ejecución: llama API v2 en el momento programado.
- Timezone-aware.

## Dependencies

- API v2 (M09).
- APScheduler o implementación propia.

## Risks

- Jobs solapados. Mitigación: lock por job_id.
- Drift de reloj. Mitigación: NTP sync obligatorio.

## Open Questions

1. ¿Max jobs por usuario? Configurable, default 100.
2. ¿Retry en fallo? Sí, configurable.

---

# RFC-020 — Profile System (v2.1)

**Status:** Borrador
**Author:** GLM
**Created:** 2026-07-06

## Summary

Preferencias de usuario: idioma, personalidad del agente, preferencias de UI, atajos.

## Motivation

Cada usuario tiene preferencias distintas. Hoy no hay forma de persistirlas.

## Design

- Tabla `profiles` en `~/.sage_os/users.db`.
- Schema flexible (JSON).
- API: `GET/PUT /api/v2/profiles/{user_id}`.

## Dependencies

- Multi-User (RFC-016).
- API v2 (M09).

## Risks

- Conflictos entre perfiles. Mitigación: merge por clave.

## Open Questions

1. ¿Perfiles por dispositivo? Diferido a v2.2.

---

## Apéndice: Convención de RFCs

Cada RFC en SAGE v2 sigue este formato:

1. **Title** — `RFC-NNN — Module Name`
2. **Status** — Borrador / Discusión / Aceptado / Rechazado / Implementado
3. **Author** — autor del RFC
4. **Created** — fecha ISO
5. **Summary** — 2-3 frases
6. **Motivation** — por qué existe
7. **Design** — cómo se diseña (sin código)
8. **Dependencies** — qué necesita
9. **Risks** — qué podría romper
10. **Open Questions** — decisiones pendientes

Para proponer un nuevo RFC, crearlo en este documento y marcarlo como `Borrador`. El Arquitecto lo revisa y lo promueve a `Discusión`. Tras consenso, `Aceptado`. Tras implementación, `Implementado`.

— GLM, Arquitecto de Evolución de SAGE

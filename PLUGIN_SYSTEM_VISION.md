# PLUGIN_SYSTEM_VISION.md — Visión del Sistema de Plugins de SAGE

**Autor:** GLM (Arquitecto de Evolución de SAGE)
**Fecha:** 2026-07-06
**Estado:** DISEÑO — no implementar
**Alcance:** visión completa del sistema de plugins: lifecycle, manifest, isolation, discovery, marketplace, security, versioning
**Documentos relacionados:** `SAGE_V2_ARCHITECTURE.md`, `NEW_MODULES_PROPOSAL.md` (M01), `RFC_FUTURE_MODULES.md` (RFC-001)

---

## 1. Por qué un sistema de plugins

SAGE v1 es **FROZEN**. Cualquier capacidad nueva requiere modificar archivos del core, lo que choca con la regla arquitectural y obliga a coordinar merges entre múltiples ingenieros (Claude A, Cascade, Runtime Engineer, Kimi). El costo de añadir una feature pequeña es desproporcionado respecto a su valor.

Un sistema de plugins resuelve esto al establecer un **contrato estable** entre el core y las extensiones:

- **Para el core:** sigue FROZEN. No se modifican archivos existentes.
- **Para la extensión:** vive en un módulo nuevo, declara qué eventos consume y qué publica, y se carga dinámicamente en runtime.
- **Para el operador:** puede activar/desactivar/instalar/desinstalar plugins sin reiniciar el core (hot-load).
- **Para el ecosistema:** terceros pueden distribuir plugins sin pasar por el equipo core.

La metáfora es la de un navegador: el core es el motor Chromium; los plugins son extensiones que viven en la Chrome Web Store. Sin extensiones, el navegador funciona; con extensiones, hace cosas que el motor nunca previó.

---

## 2. Principios del sistema de plugins

| # | Principio | Implicación |
|---|---|---|
| 1 | **Manifest-first** | Todo plugin se describe en `sage-plugin.toml` antes de cualquier código. |
| 2 | **Capability-scoped** | Un plugin solo puede hacer lo que su manifest declara. Permisos no otorgados son denegados. |
| 3 | **Lateral registration** | Los plugins no se registran en `kernel._components`; viven en el Lateral Component Registry. El core los ignora. |
| 4 | **Event-driven** | Los plugins reaccionan a eventos del Event Bridge; no hay llamadas directas al core salvo via contrato read-only. |
| 5 | **Isolated failure** | Un plugin que crashea es desactivado automáticamente; no arrastra al core ni a otros plugins. |
| 6 | **Hot-loadable** | Instalación, activación, desactivación y desinstalación en runtime. No requiere reiniciar el kernel. |
| 7 | **Versioned** | Cada plugin declara su versión y la versión del contrato SAGE contra el que fue probado. |
| 8 | **Distributable** | Un plugin es un directorio o un `.zip` autocontenido, instalable via CLI, REST API, o marketplace. |

---

## 3. Anatomy de un plugin

Un plugin es un directorio con la siguiente estructura mínima:

```
my_plugin/
├── sage-plugin.toml          # manifest (obligatorio)
├── __init__.py               # entrypoint Python (obligatorio)
├── README.md                 # documentación
├── LICENSE                   # licencia
├── src/                      # código del plugin
│   ├── handlers.py
│   └── skills/
│       └── my_skill.py
├── tests/                    # tests del plugin
│   └── test_my_plugin.py
└── config/                   # config por defecto
    └── default.json
```

### 3.1 Manifest `sage-plugin.toml`

El manifest es la **única fuente de verdad** sobre qué hace el plugin. El Plugin Runtime lo parsea antes de cargar cualquier código. Si el manifest es inválido, el plugin no se carga.

Campos del manifest (diseño, no código):

```toml
[plugin]
name = "my_plugin"                    # identificador único, snake_case
version = "1.0.0"                     # semver
author = "Jane Doe <jane@example.com>"
license = "MIT"
description = "Does X for SAGE"
homepage = "https://github.com/jane/sage-my-plugin"
contract_version = "2.0"              # versión del contrato SAGE contra el que fue probado

[plugin.entrypoint]
module = "my_plugin"                  # importable Python module
class = "MyPlugin"                    # clase que implementa SagePlugin

[plugin.permissions]
core_read = true                      # puede leer kernel.get_component()
filesystem = ["~/.sage_os/my_plugin/"] # paths permitidos
network = ["api.openai.com"]          # hosts permitidos
subprocess = false                    # puede spawn procesos
env = ["OPENAI_API_KEY"]              # vars de entorno que puede leer

[plugin.events]
subscribed = [                        # eventos v2 que recibe
    "sage.command.executed",
    "sage.knowledge.document_added"
]
published = [                         # eventos v2 que puede emitir
    "sage.my_plugin.action_performed"
]

[plugin.components_provided]          # entradas en el Lateral Registry
skills = ["my_plugin.my_skill"]       # skills que registra
knowledge_providers = []              # knowledge providers
notification_channels = []            # canales de notificación
workflow_nodes = []                   # nodos de workflow

[plugin.config_schema]                # JSON schema de su config
type = "object"
properties = { api_key = { type = "string" } }
required = ["api_key"]

[plugin.dependencies]                 # otros plugins que requiere
sage = ["knowledge_base >= 1.0"]
plugins = []
```

### 3.2 Clase base `SagePlugin`

Todo plugin debe implementar una clase que herede de `SagePlugin` (definida en `plugins/contracts.py`). El contrato (diseño, no código):

- `__init__(self, manifest, context)` — recibe su manifest parseado y un `PluginContext` con recursos.
- `async on_load(self)` — llamado al activar el plugin. Setup inicial.
- `async on_unload(self)` — llamado al desactivar. Cleanup.
- `async on_event(self, event)` — llamado por cada evento suscrito.
- `async on_config_change(self, new_config)` — llamado cuando su config cambia.
- `get_metadata(self)` — devuelve info para el dashboard (status, métricas, etc.).

El `PluginContext` expone:

- `context.event_bridge` — para publicar eventos v2.
- `context.registry` — para descubrir otros componentes v2.
- `context.kernel` (solo si `core_read: true`) — proxy read-only a `kernel.get_component()`.
- `context.config` — config del plugin parseada contra `config_schema`.
- `context.logger` — logger con tag del plugin.
- `context.metrics` — contador / gauge / histogram con tag del plugin.

---

## 4. Lifecycle de un plugin

```
DISCOVERED → INSTALLED → ENABLED → RUNNING → DISABLED → UNINSTALLED
     ↑            │          │         │          │           │
     │            ↓          ↓         ↓          ↓           ↓
     │         (manifest  (loaded,  (handlers   (handlers    (archivos
     │          parsed)   waiting   active)     removed)     borrados)
     │            │          for
     │            │          event)
     └────────────┴──────────┴──── scan periódico de ~/.sage_os/plugins/
```

### 4.1 Estados

| Estado | Significado | Acción permitida |
|---|---|---|
| **DISCOVERED** | El Plugin Runtime detectó el directorio pero no lo ha validado. | Solo metadata. |
| **INSTALLED** | El manifest pasó validación; el código no se ha importado. | Lookup de metadata. |
| **ENABLED** | El usuario (o policy) activó el plugin. | El código se carga en el siguiente ciclo. |
| **RUNNING** | El código está cargado; los handlers están suscriptos. | Recibe eventos, publica eventos. |
| **DISABLED** | El usuario lo desactivó. El código sigue cargado pero no recibe eventos. | Lookup de metadata. |
| **UNINSTALLED** | Se eliminó del filesystem. | Ninguna. |
| **ERROR** | Falló al cargar, al ejecutar handler, o crasheó N veces. | Auto-disabled; requiere intervención manual. |

### 4.2 Transiciones

- **DISCOVERED → INSTALLED**: validación de manifest (sintaxis + schema).
- **INSTALLED → ENABLED**: llamada del usuario via CLI / REST API / auto-enable si `manifest.auto_enable = true`.
- **ENABLED → RUNNING**: `importlib.import_module(manifest.entrypoint.module)`, instanciación de la clase, llamada a `on_load()`, suscripción al Event Bridge.
- **RUNNING → DISABLED**: llamada del usuario, o auto-disable tras N fallos consecutivos en handlers.
- **DISABLED → ENABLED**: llamada del usuario.
- **RUNNING → ERROR**: excepción en `on_load` o N fallos consecutivos en `on_event`.
- **ERROR → ENABLED**: intervención manual (reset del contador de errores).
- **cualquier estado → UNINSTALLED**: llamada del usuario; cleanup de archivos.

### 4.3 Hot-load

Las transiciones ENABLED ↔ DISABLED son **en caliente**: no requieren reiniciar el kernel. El Event Bridge gestiona la suscripción/desuscripción dinámica.

Para UNINSTALL se requiere que el plugin esté DISABLED primero (no se puede borrar código en uso).

---

## 5. Discovery y carga

### 5.1 Directorios de discovery

El Plugin Runtime escanea en orden:

1. `~/.sage_os/plugins/` — plugins instalados por el usuario.
2. `/etc/sage/plugins/` — plugins instalados por el admin del sistema (Linux).
3. `./plugins/` (relativo al directorio del repo) — plugins bundled con SAGE.

Cada directorio que contenga un `sage-plugin.toml` es considerado un plugin candidato.

### 5.2 Validación de manifest

Al descubrir un plugin, el runtime:

1. Parsea el `sage-plugin.toml` con `tomli`.
2. Valida contra un JSON schema de manifiesto (campos obligatorios, tipos, semver).
3. Verifica `contract_version` — si no coincide con la versión del runtime, lo marca como incompatible.
4. Verifica `dependencies` — si un plugin depende de otro que no está instalado, queda en estado BLOCKED.
5. Crea entrada en `~/.sage_os/plugins/.installed.json` con estado inicial `INSTALLED`.

### 5.3 Carga diferida

El código del plugin **no se importa** hasta que se activa (ENABLED). Esto significa:

- Plugins instalados pero deshabilitados no consumen memoria.
- Un plugin con un bug de importación no rompe el arranque del core.
- El tiempo de boot del core es independiente del número de plugins instalados.

### 5.4 Resolución de entrypoint

El campo `[plugin.entrypoint]` declara:

- `module` — nombre importable (debe estar en `sys.path`).
- `class` — nombre de la clase que implementa `SagePlugin`.

El runtime añade el directorio del plugin a `sys.path`, importa el módulo, y obtiene la clase via `getattr(module, class_name)`. La clase debe heredar de `SagePlugin` o el plugin queda en estado ERROR.

---

## 6. Aislamiento y seguridad

### 6.1 Modelo de permisos

Cada permiso del manifest es **opt-in**. Lo no declarado está denegado.

| Permiso | Default | Efecto si se concede |
|---|---|---|
| `core_read` | false | El plugin recibe `context.kernel` (proxy read-only). |
| `filesystem` | [] | El plugin puede leer/escribir solo en los paths listados. |
| `network` | [] | El plugin puede conectarse solo a los hosts listados. |
| `subprocess` | false | El plugin puede spawn procesos. |
| `env` | [] | El plugin puede leer solo las vars listadas. |

### 6.2 Aplicación de permisos

#### Para plugins Python puros
- **Filesystem:** se envuelve `open()` con un proxy que valida el path.
- **Network:** se envuelve `socket.socket()` con un proxy que valida el host.
- **Subprocess:** se envuelve `subprocess.Popen()` con un guard.
- **Env:** se envuelve `os.environ` con un proxy de solo lectura filtrado.

Estos proxies se instalan en el módulo del plugin via import hooks. No son perfectos (un plugin malicioso puede usar `ctypes` para bypassearlos) pero cubren el caso común de plugins bien intencionados con bugs.

#### Para plugins no confiables
- Se ejecutan en un **subproceso separado** (sin acceso al proceso del kernel).
- Comunicación via JSON-RPC over stdin/stdout.
- Recursos limitados via cgroups (Linux) o Job Objects (Windows).

La distinción "confiable vs no confiable" se hace en el manifest: `plugin.trust = "trusted"` (default si viene de `./plugins/`) o `"untrusted"` (default si viene de `~/.sage_os/plugins/` o vía marketplace).

### 6.3 Fallos aislados

- Cada handler de un plugin se ejecuta en un `asyncio.Task` propio.
- Si el handler lanza excepción, se captura, se loguea con correlation_id, y se envía al DLQ del Event Bridge.
- Tras 5 fallos consecutivos (configurable), el plugin se auto-desactiva (estado ERROR).
- El plugin NO puede:
  - Llamar a `sys.exit()` (envuelto).
  - Modificar `kernel._components` (no tiene la referencia).
  - Publicar en el bus del core (solo en el Event Bridge v2).
  - Importar módulos del core directamente (solo via `context.kernel` proxy).

### 6.4 Revisión de seguridad

Para plugins distribuidos via marketplace (sección 9), se requiere:

- **Firma:** el `.zip` del plugin debe estar firmado (GPG o sigstore).
- **Hash:** el manifest incluye un hash de cada archivo de código.
- **Auditoría:** un CI del marketplace ejecuta `bandit`, `semgrep`, y chequea imports peligrosos.
- **Sandbox de prueba:** el plugin se ejecuta en un entorno aislado con eventos sintéticos antes de aprobarse.

---

## 7. Comunicación plugin ↔ core

### 7.1 Diagrama de capas

```
┌──────────────────────────────────────────────────┐
│  Plugins                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ plugin_a │  │ plugin_b │  │ plugin_c │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼──────────────┼──────────────┼────────────┘
        │              │              │
        ▼              ▼              ▼
┌──────────────────────────────────────────────────┐
│  Plugin Runtime (capa 1 v2)                      │
│  - context.kernel proxy (read-only)              │
│  - context.event_bridge                          │
│  - context.registry                              │
│  - context.config / logger / metrics             │
└───────┬──────────────────────────────────────────┘
        │
        ├──────────────┐
        │              │
        ▼              ▼
┌──────────────┐  ┌────────────────────────────────┐
│ Event Bridge │  │ kernel.get_component()         │
│  (v2 → v1)   │  │  (read-only proxy)             │
└──────┬───────┘  └────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│  EventBus del core (v1)                          │
│  - wildcard subscriber: Event Bridge             │
└──────────────────────────────────────────────────┘
```

### 7.2 Lo que un plugin PUEDE hacer

- Reaccionar a eventos del core (via Event Bridge).
- Publicar eventos v2 (via `context.event_bridge.publish()`).
- Descubrir otros plugins y componentes v2 (via `context.registry`).
- Leer estado del core (via `context.kernel.get_component()`, si tiene permiso).
- Registrar skills, canales de notificación, etc. (según `components_provided`).
- Leer/escribir en su propio directorio de datos (`~/.sage_os/plugins/<name>/data/`).
- Llamar a otros plugins via `context.registry.get(...)`.

### 7.3 Lo que un plugin NO puede hacer

- Modificar archivos del core.
- Registrar componentes en `kernel._components`.
- Publicar en el bus del core directamente.
- Llamar a métodos que muten el estado del core (kernel.shutdown, kernel.execute_command, etc.).
- Importar módulos internos del core (kernel.core, dispatcher.engine, etc.) — el runtime bloquea estos imports via `sys.meta_path`.
- Acceder a variables de entorno no declaradas.
- Spawn procesos no declarados en `subprocess: true`.

---

## 8. Versioning y compatibilidad

### 8.1 Semver en plugins

Cada plugin declara su versión en `plugin.version` (semver). El Plugin Runtime trackea:

- Versión instalada.
- Versión disponible en marketplace.
- Versión del contrato SAGE contra el que fue probado (`plugin.contract_version`).

### 8.2 Contrato SAGE

El `contract_version` es una promesa de compatibilidad. Cambios en el contrato:

- **Major** (2.0 → 3.0): breaking changes en `SagePlugin`, `PluginContext`, o eventos v2. Plugins existentes deben actualizar.
- **Minor** (2.0 → 2.1): nuevas capacidades, sin breaks. Plugins existentes siguen funcionando.
- **Patch** (2.0.1 → 2.0.2): bug fixes en el runtime.

El runtime rechaza cargar plugins con `contract_version` incompatible (major distinto).

### 8.3 Dependencias entre plugins

El campo `[plugin.dependencies]` declara:

- `sage` — versiones del contrato SAGE compatibles (ej. `>= 2.0, < 3.0`).
- `plugins` — otros plugins requeridos (ej. `["knowledge_base >= 1.0"]`).

El runtime resuelve dependencias en orden topológico al activar. Si una dependencia se desactiva, los plugins dependientes se pausan (estado BLOCKED) hasta que se reactive.

### 8.4 Actualizaciones

Cuando se actualiza un plugin (versión más alta disponible):

- El runtime lo marca como `UPDATE_AVAILABLE`.
- El usuario decide cuándo actualizar via CLI / REST API / dashboard.
- La actualización es atómica: descarga a temp, validación, swap atómico del directorio.
- Si la nueva versión falla al cargar, se hace rollback automático a la versión anterior.

---

## 9. Marketplace

### 9.1 Visión

El SAGE Plugin Marketplace es un repositorio central (público o self-hosted) donde los desarrolladores publican plugins y los operadores los instalan con un comando.

### 9.2 Comandos (CLI design)

- `sage plugin search <query>` — busca en el marketplace.
- `sage plugin install <name>@<version>` — instala desde el marketplace.
- `sage plugin install /path/to/local/plugin` — instala desde filesystem local.
- `sage plugin enable <name>` — activa.
- `sage plugin disable <name>` — desactiva.
- `sage plugin uninstall <name>` — desinstala.
- `sage plugin list` — lista instalados.
- `sage plugin update <name>` — actualiza a última versión compatible.
- `sage plugin update --all` — actualiza todos.
- `sage plugin publish` — publica en el marketplace (requiere cuenta).
- `sage plugin info <name>` — metadata detallada.

### 9.3 Estructura del marketplace

- **Index:** índice JSON con todos los plugins publicados (name, version, description, author, downloads, rating).
- **Storage:** los `.zip` de plugins, servidos via HTTPS.
- **API REST:** endpoints para search, info, download, publish.
- **Web UI:** navegador en `https://plugins.sage-os.org` (futuro).

### 9.4 Publicación

Flujo para un desarrollador:

1. Empaqueta su plugin como `.zip` (con `sage plugin package`).
2. Firma el `.zip` con su clave GPG.
3. `sage plugin publish` — sube al marketplace via API REST.
4. El marketplace CI ejecuta:
   - Validación de manifest.
   - Tests en sandbox.
   - Análisis estático (bandit, semgrep).
   - Verificación de firma.
5. Si pasa, el plugin queda `pending_review`. Un humano (o auto-policy) lo aprueba.
6. Una vez aprobado, queda `published` y es visible en `sage plugin search`.

### 9.5 Reviews y ratings

- Usuarios pueden calificar plugins (1-5 estrellas) + review textual.
- El marketplace calcula un score agregado.
- Plugins con score < 2.5 tras 50+ reviews se marcan con warning.
- Plugins con reportes de seguridad se deslistan automáticamente.

---

## 10. Configuración de plugins

### 10.1 Config por plugin

Cada plugin tiene su propia config, validada contra `plugin.config_schema` (JSON schema en el manifest). La config vive en:

- `~/.sage_os/plugins/<name>/config.json` — config del usuario.
- `<plugin_dir>/config/default.json` — defaults del plugin.

El runtime mergea: `{**default, **user}` (igual que `config/manager.py` hace para el core).

### 10.2 Cambios en caliente

Cuando la config cambia (via REST API o filesystem watcher), el runtime:

1. Re-valida contra el schema.
2. Llama `plugin.on_config_change(new_config)`.
3. Publica `sage.plugin.config_changed`.

### 10.3 Secretos

Variables sensibles (API keys, tokens) se guardan en:

- `~/.sage_os/plugins/<name>/secrets.enc` — cifrado con clave derivada de un master key.
- El master key vive en `~/.sage_os/master.key` (permisos 0600).
- Plugins acceden a sus secretos via `context.get_secret("api_key")` — nunca ven el archivo directamente.

---

## 11. Observabilidad de plugins

### 11.1 Métricas automáticas

El runtime expone métricas Prometheus por plugin:

- `sage_plugin_loaded{plugin}` — gauge (0/1).
- `sage_plugin_events_processed_total{plugin,event_type}` — counter.
- `sage_plugin_events_failed_total{plugin,event_type}` — counter.
- `sage_plugin_handler_duration_seconds{plugin,event_type}` — histogram.
- `sage_plugin_memory_bytes{plugin}` — gauge (aproximado).

### 11.2 Logs

Cada plugin tiene su logger con tag `plugin.<name>`. Logs van a:

- `~/.sage_os/plugins/<name>/logs/plugin.log` — archivo propio.
- El log agregado del sistema (si el plugin lo permite via `plugin.log_to_aggregate`).

### 11.3 Health checks

El runtime llama `plugin.health_check()` cada 60s. Si devuelve `{"status": "unhealthy", "reason": "..."}` tres veces seguidas, el plugin se auto-desactiva.

### 11.4 Auditoría

Toda acción administrativa sobre plugins (install, enable, disable, uninstall, update, config change) se registra en el Audit Log (M10):

```
2026-07-06T10:00:00Z plugin=knowledge_base action=enabled user=admin reason="initial setup"
```

---

## 12. Plugins builtin (bundled con SAGE)

SAGE v2 distribuye algunos plugins por defecto en `./plugins/`:

- `notion_sync` — sincroniza knowledge base con Notion.
- `slack_notify` — canal de notificación Slack.
- `github_skill` — skill para interactuar con GitHub.
- `web_search_skill` — skill de búsqueda web.
- `pdf_ingestor` — ingesta de PDFs a knowledge base.
- `prometheus_exporter` — exporta métricas a Prometheus.

Estos plugins son "trusted" y se cargan por defecto, pero pueden desactivarse.

---

## 13. Casos de uso ejemplo

### 13.1 "Quiero que SAGE me avise por Slack cuando un comando falle"

1. `sage plugin install slack_notify`
2. Configurar webhook Slack via `sage plugin config slack_notify webhook_url=...`
3. `sage plugin enable slack_notify`
4. El plugin se suscribe a `sage.command.failed` y envía mensaje a Slack.

No se tocó el core. No se reinició el kernel.

### 13.2 "Quiero añadir una skill de búsqueda web"

1. `sage plugin install web_search_skill`
2. El plugin registra `web_search.search` en el Lateral Registry.
3. Otros plugins o el Context Manager pueden invocar la skill via `registry.get("skill:web_search.search").invoke({"query": "..."})`.
4. Los agentes v2 (cuando existan) pueden declarar esta skill en su manifiesto.

### 13.3 "Quiero que SAGE aprenda de mis documentos"

1. `sage plugin install pdf_ingestor`
2. `sage plugin install notion_sync`
3. Configurar ambos con sus credenciales.
4. El plugin `notion_sync` se suscribe a `sage.knowledge.document_added` para sincronizar bidireccionalmente.
5. El plugin `pdf_ingestor` registra una skill `pdf_ingestor.ingest(path)` que se puede invocar via REST API.

### 13.4 "Quiero trackear costos por usuario"

1. `sage plugin install cost_tracker` (o ya viene bundled).
2. El plugin se suscribe a `sage.provider.call` con metadata de tokens.
3. Lookup de precios en `~/.sage_os/costs/pricing.json`.
4. Publica `sage.cost.threshold_reached` cuando un usuario supera su budget.
5. `slack_notify` (del caso 13.1) se suscribe y avisa.

---

## 14. Riesgos del sistema de plugins

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Plugin malicioso escapa del sandbox | Baja | Crítico | Plugins untrusted corren en subproceso; trusted se audita antes de bundlear. |
| Explosión de dependencias | Alta | Medio | Resolver transitivamente; rechazar conflictos de versión. |
| Plugin rompe contrato en update | Media | Alto | Contract testing en CI del marketplace; rollback automático. |
| Marketplace caído | Media | Medio | Cache local de índice; instalación desde `.zip` local sin marketplace. |
| Plugin consume demasiada memoria | Media | Bajo | Cuota por plugin (configurable); kill si excede. |
| Plugins duplicates (mismo nombre) | Baja | Alto | Namespacing por autor (`@author/plugin_name`). |

---

## 15. Roadmap del sistema de plugins

| Fase | Duración | Entregable |
|---|---|---|
| MVP runtime | 4 semanas | Plugin Runtime + Event Bridge + Lateral Registry. Plugins builtin cargan. |
| Manifest + permissions | 2 semanas | Validación completa de manifest; sandbox de permisos. |
| Hot-load + lifecycle | 2 semanas | Enable/disable/uninstall en caliente. |
| Marketplace API | 4 semanas | Search, install, publish, signing. |
| Web UI del marketplace | 4 semanas | Navegador web en `https://plugins.sage-os.org`. |
| SDK para desarrolladores | 2 semanas | `sage plugin init` (scaffold), `sage plugin test`, `sage plugin package`. |
| Review process | 2 semanas | CI automático + aprobación manual. |

**Total MVP:** 8 semanas. **Total completo:** 20 semanas.

---

## 16. Conclusión

El sistema de plugins es la **piedra angular** de SAGE v2. Sin él, cualquier capacidad nueva sigue requiriendo modificar el core FROZEN, lo que perpetúa el cuello de botella de coordinación entre ingenieros. Con él, el ecosistema puede crecer orgánicamente: terceros aportan, el marketplace distribuye, el operador instala lo que necesita.

El diseño respeta todas las restricciones:

- **No toca el core.** El Plugin Runtime es el único punto de contacto, via Event Bridge (suscriptor wildcard) y `kernel.get_component()` (proxy read-only).
- **Todo en archivos nuevos.** `plugins/`, `extensions/`, `~/.sage_os/plugins/`.
- **Fallos aislados.** Un plugin que crashea no afecta al core ni a otros plugins.
- **Versión y distribución.** Semver + contract versioning + marketplace + signing.

El siguiente paso es abrir los RFCs formales (ver `RFC_FUTURE_MODULES.md` § RFC-001) y prototipar el MVP del runtime para validar los contratos.

— GLM, Arquitecto de Evolución de SAGE

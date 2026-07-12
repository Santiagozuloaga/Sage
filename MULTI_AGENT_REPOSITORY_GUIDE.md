# MULTI_AGENT_REPOSITORY_GUIDE.md

**Autor:** Qwen (Validation & Repository Organization Engineer)  
**Fecha:** 2026-07-06  
**Versión:** 1.0  
**Propósito:** Guía para coordinación de trabajo simultáneo de múltiples agentes en el repositorio Sage

---

## 1. Visión General

Este documento establece las reglas, convenciones y flujos de trabajo para que los siguientes agentes colaboren simultáneamente sin conflictos:

- **Claude A** — Kernel, Config, Memory, Dispatcher, Providers
- **Cascade** — CLI, Event Bus, Recovery, Mission Control, Context Manager, Agent Router integration
- **Runtime Engineer** — Infrastructure fixes (EventBus, Recovery, MissionControl, Boot, Kernel shutdown)
- **Kimi** — Decision Engine, Scheduler, Task prioritization, Load balancing, FSM validation
- **GLM** — Integration auditing, Merge conflict resolution
- **Qwen** — Validation, Repository organization, Test verification
- **Manus** — (pendiente de especialización)
- **futuros agentes** — Nuevas especializaciones según necesidades del proyecto

---

## 2. Territorios por Agente

### 2.1 Claude A

| Área | Archivos | Responsabilidades |
|------|----------|-------------------|
| Kernel Core | `kernel/core.py` | Boot sequence, component initialization, shutdown, command execution |
| Config | `config/manager.py`, `config/provider_config.py` | Configuration loading, saving, atomic writes |
| Memory | `memory/engine.py` | SQLite operations, journaling, encoding/decoding |
| Dispatcher | `dispatcher/engine.py` | Task queue, execution, provider routing wiring |
| Providers | `providers/provider_router.py`, `providers/ollama_provider.py` | Provider registration, health checks, text generation |
| Main Entry | `main.py` | Web server init, conditional imports, shutdown coordination |

**Límites:** No modifica Event Bus, Recovery System, Mission Control, CLI, Agent Router logic (solo wiring)

### 2.2 Cascade

| Área | Archivos | Responsabilidades |
|------|----------|-------------------|
| CLI | `interface/cli.py` | Command-line interface, start(), user input loop |
| Event Bus | `events/bus.py`, `events/models.py` | Event publishing, subscription, history, DLQ |
| Recovery | `recovery/system.py` | Checkpointing, restore, cleanup |
| Mission Control | `mission_control/controller.py` | Mission tracking, start/end times, history |
| Context Manager | (nuevo) `context/manager.py` | Conversation context, prompt assembly |
| Agent Router Integration | `agents/router.py` | Agent selection, capability matching (wiring only) |

**Límites:** No modifica kernel core boot logic (usa `_init_optional()`), no modifica dispatcher execution logic (solo publica eventos)

### 2.3 Runtime Engineer

| Área | Archivos | Responsabilidades |
|------|----------|-------------------|
| EventBus Fixes | `events/bus.py`, `events/models.py` | Idempotent start, bounded history, DLQ, type hints |
| Recovery Fixes | `recovery/system.py` | Microsecond IDs, atomic writes, corrupted checkpoint cleanup |
| Mission Control Fixes | `mission_control/controller.py` | start_time, end_time+duration, bounded history |
| Boot Configurator | `boot/configurator.py` | Atomic save |
| Kernel State | `kernel/state.py` | FSM validation, last_error tracking |
| Kernel Shutdown | `kernel/core.py` (shutdown method) | Per-component try/except, idempotency |
| Dashboard Reuse | `main.py` (dashboard init) | Reuse kernel dashboard, avoid double-init |

**Límites:** No modifica dispatcher execution logic, no modifica provider routing, no modifica agent router logic

### 2.4 Kimi

| Área | Archivos | Responsabilidades |
|------|----------|-------------------|
| Dispatcher Extensions | `dispatcher/engine.py` | Multi-agent execution, delegation, timeout, cancellation, bounded completed tasks |
| Agent Router Logic | `agents/router.py` | Fallback strategy, load tracking, index cleanup |
| FSM Port | `kernel/state.py` | Port S-1/S-2 from RE to Claude-A branch |
| Decision Tree | (futuro) `decision/tree.py` | Priority calculation, budget tracking, autonomy levels |
| Scheduler | (futuro) `scheduler/engine.py` | Task prioritization, human override, deadline management |

**Límites:** No modifica kernel boot sequence, no modifica event bus, no modifica recovery/mission control internals

### 2.5 GLM

| Área | Archivos | Responsabilidades |
|------|----------|-------------------|
| Merge Audit | `audits/MERGE_AUDIT_*.md` | Conflict detection, resolution recommendations |
| Integration Validation | `scripts/validate_integration.py` | Post-merge verification |
| Dependency Graph | `repository_scanner/dependency_graph.py` | Import analysis, circular dependency detection |

**Límites:** No modifica código de producción, solo auditoría y validación

### 2.6 Qwen

| Área | Archivos | Responsabilidades |
|------|----------|-------------------|
| Test Validation | `tests/`, `scripts/test_*.py` | Test execution, result verification |
| Repository Organization | `REPOSITORY_RESTRUCTURE_PLAN.md`, estructura de directorios | Organization, deduplication, documentation structure |
| Handoff Templates | `handoffs/TEMPLATE_HANDOFF.md` | Standardization of handoffs |
| Bug Reproduction | Scripts de reproducción de bugs | Verify bug reports empirically |

**Límites:** No modifica código de producción (salvo bugs críticos documentados), no reescribe arquitectura

### 2.7 Manus

*(Pendiente de definición — espacio reservado)*

### 2.8 Futuros Agentes

Cada nuevo agente debe:
1. Leer esta guía antes de empezar
2. Definir su territorio explícitamente en un handoff inicial
3. Identificar conflictos potenciales con agentes existentes
4. Crear subdirectorio en `experiments/<nombre_agente>/`

---

## 3. Documentos por Agente

Cada agente mantiene los siguientes documentos en su área de responsabilidad:

| Documento | Ubicación | Propósito |
|-----------|-----------|-----------|
| `HANDOFF_<AGENTE>.md` | `handoffs/` | Transferencia formal al siguiente agente |
| `BUG_REPORT_<AGENTE>.md` | `submissions/<agente>/` | Bugs identificados y estado de fixes |
| `CHANGES.diff` | `submissions/<agente>/` | Diff unificado de cambios aplicados |
| `README_SUBMISSION.md` | `submissions/<agente>/` | Instrucciones específicas de la submission |

### Plantilla de Handoff

Ver `handoffs/TEMPLATE_HANDOFF.md` para formato estándar.

---

## 4. Entregables por Agente

Al finalizar una tarea, cada agente entrega:

1. **Código fuente** en `experiments/<agente>/<tarea>/` → tras validación → `src/sage_runtime/`
2. **ZIP de submission** en `submissions/<agente>/<nombre_proyecto>.zip`
3. **Handoff** en `handoffs/HANDOFF_<ORIGEN>_TO_<DESTINO>.md`
4. **Bug report** (si aplica) en `submissions/<agente>/BUG_REPORT_<AGENTE>.md`
5. **Diff** en `submissions/<agente>/CHANGES.diff`

### Checklist de Entrega

- [ ] Todos los tests relevantes pasan
- [ ] Handoff sigue la plantilla oficial
- [ ] BUG_REPORT lista severidad y estado de cada bug
- [ ] CHANGES.diff es aplicable sin conflictos
- [ ] ZIP contiene estructura completa y funcional
- [ ] Conflictos con otros agentes están documentados explícitamente
- [ ] Tests de regresión incluidos (si aplica)

---

## 5. Flujo de Trabajo Multi-Agente

### 5.1 Ciclo de Vida de una Tarea

```
┌─────────────────────────────────────────────────────────────┐
│ 1. AGENTE RECIBE PROMPT                                     │
│    - Lee handoff previo en `handoffs/`                      │
│    - Identifica territorio y límites                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CREA RAMA GIT                                            │
│    - Nombre: feature/<agente>/<descripcion>                 │
│    - Base: develop (no main directamente)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. TRABAJA EN EXPERIMENTO                                   │
│    - Directorio: experiments/<agente>/<tarea>/              │
│    - Commit frecuente con mensajes descriptivos             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. EJECUTA TESTS                                            │
│    - Unitarios: `python -m pytest tests/unit/`              │
│    - Integración: `python -m pytest tests/integration/`     │
│    - Regresión: `python scripts/test_<agente>_fixes.py`     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. GENERA SUBMISSION                                        │
│    - ZIP en `submissions/<agente>/`                         │
│    - Incluye código, docs, tests, handoff                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. CREA HANDOFF                                             │
│    - Documento en `handoffs/`                               │
│    - Sigue TEMPLATE_HANDOFF.md                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. ABRE PULL REQUEST                                        │
│    - De: feature/<agente>/<tarea>                           │
│    - A: develop                                             │
│    - Requiere: 1 auditor + 1 validador                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. AUDITOR VALIDA                                           │
│    - Revisa MERGE_AUDIT.md para conflictos                  │
│    - Ejecuta tests de integración                           │
│    - Aprueba o solicita cambios                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. MERGE COMPLETADO                                         │
│    - Código va a `develop`                                  │
│    - Tras validación final → `main`                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. SIGUIENTE AGENTE CONTINÚA                               │
│     - Lee handoff recién creado                             │
│     - Reinicia ciclo desde paso 1                           │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Comunicación Entre Agentes

**Canales oficiales:**
1. **Handoffs** (`handoffs/`) — Comunicación asíncrona formal
2. **Issues de GitHub** — Seguimiento de bugs y tareas
3. **Pull Request Comments** — Discusión técnica específica
4. **MERGE_AUDIT.md** — Advertencias de conflictos

**No usar:**
- Comentarios en código para comunicación entre agentes (usar handoffs)
- Mensajes fuera del repositorio (todo debe quedar registrado)

---

## 6. Resolución de Conflictos

### 6.1 Tipos de Conflicto

| Tipo | Descripción | Ejemplo | Resolución |
|------|-------------|---------|------------|
| **File-level** | Dos agentes modifican el mismo archivo | Claude A y RE modifican `kernel/core.py` | Merge de 3 vías + decisión humana si es crítico |
| **Method-level** | Dos agentes modifican el mismo método | Claude A y Kimi modifican `dispatcher._execute_command()` | Fusionar lógica ortogonal, decidir prioridad si hay solapamiento |
| **Cross-file** | Cambios en archivo A dependen de cambios en archivo B | `kernel/core.py` default_provider="ollama" requiere `providers/ollama_provider.py` | Tomar ambos archivos como unidad indivisible |
| **Architectural** | Decisiones de diseño incompatibles | Dashboard: ¿componente del kernel o de main.py? | Decisión humana del Arquitecto (RFC required) |

### 6.2 Proceso de Resolución

1. **Detección:** GLM ejecuta análisis de conflictos antes de merge
2. **Clasificación:** Se asigna gravedad (CRÍTICO/ALTO/MEDIO/BAJO)
3. **Documentación:** Se registra en `MERGE_AUDIT.md`
4. **Decisión:**
   - Baja/Media gravedad → Merge automático con revisión
   - Alta/Crítica gravedad → Escalar a Arquitecto vía RFC
5. **Implementación:** Se aplica resolución documentada
6. **Validación:** Tests post-merge confirman que no hay regresión

### 6.3 Conflictos Conocidos (Estado Actual)

Ver `MERGE_AUDIT.md` sección 3 para catálogo completo.

Resumen:
- **C5 (Dashboard ownership)** — Requiere decisión humana
- **C6 (Default provider)** — Requiere decisión humana
- **C10 (Shutdown delegation)** — Requiere decisión humana
- **I3 (Dashboard-main coupling)** — Depende de C5

---

## 7. Convenciones de Código

### 7.1 Imports

```python
# Imports estándar primero
import asyncio
import logging
from typing import Dict, List, Optional

# Imports de terceros segundo
import aiofiles

# Imports internos tercero (relativos al paquete)
from .models import Task, TaskStatus
from ..kernel.state import KernelContext
```

### 7.2 Logging

```python
logger = logging.getLogger(__name__)

# Usar f-strings con nombre del módulo
logger.info(f"[DISPATCHER] Task {task_id} started")
logger.warning(f"[KERNEL_FSM] Illegal transition {from_state} -> {to_state}")
logger.error(f"[EVENT_BUS] Handler failed for event: {event}")
```

### 7.3 Type Hints

Todos los métodos públicos deben tener type hints completos:

```python
async def dispatch_multi_agent(
    self,
    subtasks: List[Dict[str, Any]],
    parent_task_id: Optional[str] = None
) -> Dict[str, Any]:
    ...
```

### 7.4 Docstrings

Google style para funciones públicas:

```python
def route_to_agent(self, capability: str, use_fallback: bool = True) -> Optional[str]:
    """Route a capability to an enabled agent.
    
    Args:
        capability: The capability string to match (e.g., 'code_generation')
        use_fallback: If True, fall back to SAGE if no agent found
        
    Returns:
        Agent ID if found, None otherwise (or fallback if enabled)
        
    Raises:
        ValueError: If capability is empty
    """
```

---

## 8. Testing Requirements

### 8.1 Por Tipo de Cambio

| Tipo de Cambio | Tests Requeridos |
|----------------|------------------|
| Bug fix | Test de regresión que reproduce el bug + verifica el fix |
| Nueva funcionalidad | Tests unitarios + tests de integración |
| Refactor | Todos los tests existentes deben pasar |
| Performance optimization | Benchmark antes/después + tests funcionales |

### 8.2 Cobertura Mínima

- **Módulos críticos** (kernel, dispatcher, events): ≥80% cobertura
- **Módulos de soporte** (config, memory): ≥70% cobertura
- **Módulos experimentales**: ≥50% cobertura

### 8.3 Ejecución de Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Solo tests de un agente
python -m pytest tests/regression/test_runtime_engineer_fixes.py -v

# Tests con coverage
python -m pytest tests/ --cov=sage_runtime --cov-report=html
```

---

## 9. Versionado y Releases

### 9.1 Semantic Versioning

El proyecto sigue [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (X.0.0): Cambios incompatibles hacia atrás
- **MINOR** (x.Y.0): Nuevas funcionalidades compatibles
- **PATCH** (x.y.Z): Bug fixes compatibles

### 9.2 Proceso de Release

1. Crear rama `release/vX.Y.Z` desde `develop`
2. Ejecutar suite completa de tests
3. Actualizar `CHANGELOG.md` con cambios
4. Crear tag `vX.Y.Z`
5. Merge a `main` y `develop`
6. Publicar release en GitHub

### 9.3 Releases Históricas

| Versión | Fecha | Notas |
|---------|-------|-------|
| v4.5.0-stable | 2026-07-05 | Baseline actual |
| v4.5.1-dev | En desarrollo | Fixes de Claude A + RE + Kimi |

---

## 10. Onboarding de Nuevos Agentes

### 10.1 Primeros Pasos

1. **Leer documentación esencial:**
   - `README.md` (raíz)
   - `CONTRIBUTING.md`
   - Este documento (`MULTI_AGENT_REPOSITORY_GUIDE.md`)
   - Handoff más reciente en `handoffs/`

2. **Configurar entorno:**
   ```bash
   git clone <repo_url>
   cd sage-os
   git checkout develop
   pip install -r src/sage_runtime/requirements.txt
   ```

3. **Ejecutar tests iniciales:**
   ```bash
   python -m pytest tests/ -v
   ```

4. **Definir territorio:**
   - Crear documento `handoffs/HANDOFF_INIT_<AGENTE>.md`
   - Listar archivos bajo responsabilidad
   - Identificar dependencias con otros agentes

5. **Crear primer experimento:**
   ```bash
   mkdir -p experiments/<nombre_agente>/<primera_tarea>
   git checkout -b feature/<agente>/<primera_tarea>
   ```

### 10.2 Mentoria

Cada nuevo agente es emparejado con un agente experimentado para:
- Revisar el primer handoff
- Validar la primera submission
- Resolver dudas sobre territorios y límites

---

## 11. Métricas de Salud del Proyecto

### 11.1 Métricas Técnicas

| Métrica | Objetivo | Estado Actual |
|---------|----------|---------------|
| Tests passing | 100% | 61/61 RE + 40/40 Kimi + 5/6 Claude A |
| Coverage | ≥75% promedio | Pendiente medición |
| Conflictos sin resolver | 0 | 4 requieren decisión humana |
| Handoffs completos | 100% de transiciones | 3/4 completados |

### 11.2 Métricas de Proceso

| Métrica | Objetivo | Estado Actual |
|---------|----------|---------------|
| Tiempo promedio de review | <24 horas | Pendiente medición |
| PRs abiertos >7 días | 0 | 0 |
| Documentación actualizada | 100% de cambios | Pendiente auditoría |

---

## 12. Apéndice: Lista de Agentes Activos

| Agente | Especialización | Estado | Última Actividad |
|--------|-----------------|--------|------------------|
| Claude A | Kernel/Config/Memory/Dispatcher | Activo | 2026-07-05 |
| Cascade | CLI/Events/Recovery/MissionControl | Activo | 2026-07-05 |
| Runtime Engineer | Infrastructure Fixes | Completado | 2026-07-06 |
| Kimi | Decision Engine/Scheduler | Completado | 2026-07-06 |
| GLM | Integration Audit | Completado | 2026-07-06 |
| Qwen | Validation/Organization | Activo | 2026-07-06 |
| Manus | (pendiente) | Inactivo | - |

---

**FIN DE LA GUÍA MULTI-AGENTE**

*Este documento es vivo. Actualizar cuando:*
- *Se incorpore un nuevo agente*
- *Cambien los territorios*
- *Se modifiquen los flujos de trabajo*
- *Se resuelvan conflictos arquitectónicos*

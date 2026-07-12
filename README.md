# SAGE Runtime

**Sistema de Agentes Autónomos con Arquitectura Modular**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Descripción

SAGE es un runtime engine para sistemas multi-agente que proporciona:

- **Kernel centralizado** con gestión de estado y ciclo de vida
- **Dispatcher de tareas** con priorización y ejecución asíncrona
- **Router de agentes** con balanceo de carga y fallback automático
- **EventBus** para comunicación entre componentes
- **Sistema de recuperación** con checkpoints atómicos
- **Mission Control** para tracking de operaciones
- **Dashboard** para monitoreo en tiempo real
- **Modo comando** para interacción directa

## Estructura del Proyecto

```
sage_runtime/
├── kernel/          # Core del sistema (state, core.py)
├── dispatcher/      # Engine de dispatch y cola de tareas
├── agents/          # Router y registro de agentes
├── events/          # EventBus y sistema de eventos
├── recovery/        # Checkpoints y recuperación
├── mission_control/ # Tracking de misiones
├── dashboard/       # Monitoreo y métricas
├── command_mode/    # Ejecución de comandos
├── providers/       # Integración con LLMs
├── config/          # Configuración y boot
├── contracts/       # Validación de contratos
├── file_processor/  # Procesamiento de archivos
├── image_analysis/  # OCR y análisis de imágenes
├── repository_scanner/ # Escaneo de repositorios
├── auditor/         # Auditoría de integridad
├── memory/          # Gestión de memoria
├── interface/       # Interfaces CLI/Web
├── web/             # Servidor Flask (opcional)
├── tests/           # Suite de tests
└── scripts/         # Scripts de validación
```

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/Santiagozuloaga/Sage.git
cd Sage

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Uso Básico

```python
from kernel.core import Kernel
from kernel.configurator import BootConfigurator

# Inicializar kernel
config = BootConfigurator.load_default()
kernel = Kernel(config)

# Boot del sistema
kernel.boot()

# Ejecutar comando
result = kernel.execute_command("tu comando aquí")

# Shutdown graceful
kernel.shutdown()
```

## Ejecutar Tests

```bash
# Suite completa del Runtime Engineer
python scripts/test_runtime_engineer_fixes.py

# Tests de Kimi (Decision Engine & Scheduler)
python scripts/test_kimi_fixes.py

# Tests específicos de PR
python tests/validate_pr009.py
python tests/validate_pr010.py
# ... etc
```

## Documentación

| Documento | Descripción |
|-----------|-------------|
| `HANDOFF_CASCADE.md` | Handoff del agente Cascade |
| `HANDOFF_RUNTIME_ENGINEER.md` | Handoff del Runtime Engineer |
| `BUG_REPORT.md` | Reporte de bugs del Runtime Engineer |
| `CHANGES.diff` | Diff de cambios propuestos |
| `MERGE_AUDIT.md` | Auditoría de merges entre agentes |
| `REPOSITORY_RESTRUCTURE_PLAN.md` | Plan de reorganización |
| `MULTI_AGENT_REPOSITORY_GUIDE.md` | Guía para trabajo multi-agente |

## Estado Actual

### ✅ Fixes Implementados

| Agente | Bugs Fixeados | Tests PASS |
|--------|---------------|------------|
| Runtime Engineer | 18 | 61/61 |
| Kimi | 12 | 40/40 |
| Cascade | Ver HANDOFF_CASCADE.md | - |
| Claude A | Ver documentación | - |

### ⚠️ Decisiones Pendientes

4 conflictos críticos requieren decisión humana antes del merge final:
1. Dashboard initialization (kernel vs main.py)
2. Default provider (ollama vs configurable)
3. Dispatcher→provider_router wiring
4. WEB_AVAILABLE conditional

Ver `MERGE_AUDIT.md` para detalles.

## Contribuir

1. Leer `MULTI_AGENT_REPOSITORY_GUIDE.md` para entender territorios de agentes
2. Revisar `REPOSITORY_RESTRUCTURE_PLAN.md` para estructura objetivo
3. Crear handoff documentado en `docs/handoffs/`
4. Incluir tests de regresión en `scripts/`
5. Actualizar `CHANGELOG.md` con cambios

## Agentes Activos

| Agente | Territorio | Estado |
|--------|------------|--------|
| Claude A | Kernel core, providers, wiring | Activo |
| Cascade | FSM, state management | Activo |
| Runtime Engineer | Events, Recovery, MissionControl, Boot | Activo |
| Kimi | Dispatcher, Router, Decision Engine | Activo |
| Qwen | Auditoría, reestructuración | Activo |
| GLM | Por definir | - |

## Licencia

MIT License - ver LICENSE para detalles.

## Contacto

Repositorio: https://github.com/Santiagozuloaga/Sage

# SAGE OS - Organización del Repositorio

## Guía Oficial para Agentes Colaboradores

**Versión:** 1.0  
**Última actualización:** 2026-07-20  
**Estado:** ✅ Fase 0 Completada - Lista para continuación de agentes

---

## 📁 Estructura del Repositorio

```
/workspace/
├── README.md                          # Documentación principal del proyecto
├── REPOSITORY_RESTRUCTURE_PLAN.md     # Plan de reestructuración (referencia)
├── REPOSITORY_ORGANIZATION.md         # Este documento - Guía de organización
├── __init__.py                        # Package initializer
├── main.py                            # Punto de entrada principal
├── audit_runtime.py                   # Script de auditoría
├── requirements.txt                   # Dependencias Python
│
├── src/
│   └── sage_runtime/                  # 🎯 CÓDIGO PRINCIPAL ÚNICO
│       ├── agents/                    # Sistema de agentes
│       ├── kernel/                    # Kernel core (core.py aquí)
│       ├── dispatcher/                # Dispatcher de tareas
│       ├── web/                       # Interfaz web
│       ├── interface/                 # CLI y interfaces
│       ├── memory/                    # Sistema de memoria
│       ├── events/                    # Event bus
│       ├── mission_control/           # Control de misiones
│       ├── commands/                  # Registry de comandos
│       ├── tools/                     # Tools center
│       ├── runtime/                   # Runtime status
│       ├── context/                   # Context management
│       ├── notifications/             # Smart notifications
│       ├── decisions/                 # Decision center
│       ├── file_analysis/             # File analysis service
│       ├── providers/                 # Provider management
│       ├── contracts/                 # Agent contracts
│       ├── config/                    # Configuración
│       ├── scripts/                   # Scripts utilitarios
│       └── tests/                     # Tests del sistema
│
├── submissions/                       # 📦 ENTREGAS POR AGENTE
│   ├── cascade/                       # Entregas de Cascade
│   │   └── HANDOFF_CASCADE_PAQUETE.zip
│   ├── claude_a/                      # Entregas de Claude A
│   │   └── HANDOFF_CASCADE_PAQUETE.zip
│   ├── glm/                           # Entregas de GLM
│   │   └── GLM_Entregables_Nuevos_2026-07-18.zip
│   ├── kimi/                          # Entregas de Kimi
│   │   ├── Kimi_Agent_Planificador de Engine de Decisión.zip
│   │   └── SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip
│   └── runtime_engineer/              # Entregas de Runtime Engineer
│       └── SAGE_Runtime_RuntimeEngineer_Submission.zip
│
├── handoffs/                          # 🤝 HANDOFFS OFICIALES (MD únicos)
│   ├── HANDOFF_CASCADE.md
│   └── HANDOFF_RUNTIME_ENGINEER.md
│
├── baseline/                          # 📸 SNAPSHOTS HISTÓRICOS
│   ├── sage_runtime_original.zip      # Original histórico
│   ├── claude_a_snapshot/             # Snapshot de entrega Claude A
│   ├── kimi_snapshot/                 # Snapshot de entrega Kimi
│   └── runtime_engineer_snapshot/     # Snapshot de entrega Runtime Engineer
│
├── archive/                           # 🗄️ ARCHIVOS HISTÓRICOS/DUPLICADOS
│   ├── ZIPs_duplicados/               # ZIPs duplicados archivados
│   │   ├── SAGE_Runtime_RuntimeEngineer_Submission (1).zip
│   │   ├── SAGE_Runtime_RuntimeEngineer_Submission (2).zip
│   │   └── sage_runtime (2).zip
│   ├── SAGE_Runtime_v4.5_Documentation_V2.zip
│   ├── AUDIT_REPORT.html
│   ├── AUDIT_REPORT_V1_TO_V2.md
│   ├── DOCUMENTATION_MANIFEST.md
│   ├── README.md
│   └── README_PROJECT.md
│
├── docs/                              # 📚 DOCUMENTACIÓN
│   ├── architecture/                  # Documentos de arquitectura
│   ├── api/                           # Documentación de API
│   ├── rfc/                           # RFCs y propuestas
│   └── user_guide/                    # Guías de usuario
│
├── audits/                            # 🔍 AUDITORÍAS
│   ├── audit_*.md                     # Reports de auditoría
│   └── MERGE_AUDIT.md                 # Auditoría de merges
│
├── experiments/                       # 🧪 EXPERIMENTOS/PRUEBAS
│   └── [experiment_name]/             # Experimentos temporales
│
├── image_analysis/                    # 🖼️ Análisis de imágenes
├── file_processor/                    # 📄 Procesamiento de archivos
│   └── parsers/                       # Parsers especializados
├── repository_scanner/                # 🔎 Scanner del repositorio
├── boot/                              # 🚀 Scripts de boot
├── contracts/                         # 📋 Contracts (raíz, legacy)
├── command_mode/                      # ⌨️ Command mode (raíz, legacy)
├── providers/                         # 🔌 Providers (raíz, legacy)
├── interface/                         # 🖥️ Interface (raíz, legacy)
├── memory/                            # 🧠 Memory (raíz, legacy)
├── events/                            # ⚡ Events (raíz, legacy)
├── kernel/                            # ⚙️ Kernel (raíz, legacy)
├── agents/                            # 🤖 Agents (raíz, legacy)
├── mission_control/                   # 🎯 Mission Control (raíz, legacy)
├── config/                            # ⚙️ Config (raíz, legacy)
├── scripts/                           # 📜 Scripts (raíz, legacy)
└── tests/                             # ✅ Tests (raíz, legacy)
```

---

## 🎯 Reglas de Organización

### 1. Código Principal Único
- **TODO el código activo** debe estar en `src/sage_runtime/`
- Las carpetas en raíz (`kernel/`, `agents/`, etc.) son **LEGACY** y se mantienen solo para referencia histórica
- **NO crear** nuevas versiones de `core.py` fuera de `src/sage_runtime/kernel/`

### 2. Entregas de Agentes
- Cada agente tiene su carpeta en `submissions/{agent_name}/`
- Los ZIPs de entrega se mantienen en su carpeta correspondiente
- Los handoffs oficiales (`.md`) se mueven a `handoffs/`

### 3. Handoffs Oficiales
- Solo archivos `.md` en `handoffs/`
- Formato: `HANDOFF_{AGENT_NAME}.md`
- Deben incluir: contexto, estado actual, próximos pasos, archivos modificados

### 4. Snapshots Históricos
- `baseline/` contiene snapshots inmutables de entregas importantes
- NO modificar contenido de `baseline/`
- Usar para referencia histórica y auditoría

### 5. Archivos Duplicados
- ZIPs duplicados → `archive/ZIPs_duplicados/`
- Documentación duplicada → `archive/`
- Versiones antiguas de código → `baseline/` o `archive/`

### 6. Documentación
- Documentación principal → `README.md` (raíz)
- Documentación técnica → `docs/` con subdirectorios temáticos
- RFCs y propuestas → `docs/rfc/`
- Auditorías → `audits/`

### 7. Archivos Temporales
- Eliminar después de usar: `_temp_*`, `*_temp/`
- Experimentos → `experiments/{nombre}/`
- Limpiar experiments completados

---

## 📋 Checklist para Agentes

### Antes de Empezar
- [ ] Leer `README.md` y este documento
- [ ] Verificar handoffs en `handoffs/`
- [ ] Identificar código activo en `src/sage_runtime/`

### Durante el Trabajo
- [ ] Trabajar solo en `src/sage_runtime/`
- [ ] NO crear copias de `core.py` u otros archivos críticos
- [ ] Documentar cambios en el handoff correspondiente

### Antes de Entregar
- [ ] Crear handoff en `handoffs/HANDOFF_{TU_NOMBRE}.md`
- [ ] Empaquetar entrega en `submissions/{tu_nombre}/`
- [ ] Incluir: ZIP con código, handoff MD, lista de cambios
- [ ] Verificar que no hay archivos temporales

### Después de Entregar
- [ ] Esperar verificación del coordinador
- [ ] Responder preguntas de auditoría si las hay
- [ ] Actualizar handoff si se solicitan cambios

---

## 🔍 Ubicación de Archivos Clave

| Archivo | Ubicación Correcta | Estado |
|---------|-------------------|--------|
| `core.py` | `src/sage_runtime/kernel/core.py` | ✅ Activo |
| `engine.py` | `src/sage_runtime/dispatcher/engine.py` | ✅ Activo |
| `server.py` | `src/sage_runtime/web/server.py` | ✅ Activo |
| `cli.py` | `src/sage_runtime/interface/cli.py` | ✅ Activo |
| `control.py` | `src/sage_runtime/mission_control/control.py` | ✅ Activo |
| Handoffs | `handoffs/HANDOFF_*.md` | ✅ Organizados |
| ZIPs Entrega | `submissions/{agent}/` | ✅ Organizados |
| Documentation | `docs/` + `README.md` | ✅ Organizada |

---

## ⚠️ Errores Comunes a Evitar

1. ❌ Crear `kernel/core.py` en raíz (ya existe como legacy)
2. ❌ Crear carpetas `sage_runtime_*` nuevas en raíz
3. ❌ Dejar ZIPs sueltos en raíz
4. ❌ Modificar archivos en `baseline/`
5. ❌ Olidar mover handoffs a `handoffs/`
6. ❌ Dejar archivos temporales (`_temp_*`)
7. ❌ Crear documentación duplicada

---

## 🔄 Flujo de Trabajo Recomendado

```
1. Leer handoffs en handoffs/
   ↓
2. Identificar tarea asignada
   ↓
3. Trabajar en src/sage_runtime/
   ↓
4. Testear cambios
   ↓
5. Crear handoff en handoffs/HANDOFF_{TU_NOMBRE}.md
   ↓
6. Empaquetar en submissions/{tu_nombre}/entrega.zip
   ↓
7. Notificar al coordinador
   ↓
8. Esperar verificación
   ↓
9. Responder auditoría si corresponde
   ↓
10. ¡Completado!
```

---

## 📞 Contacto y Coordinación

- **Coordinador:** Qwen (verificación y consolidación)
- **Agentes Activos:** Cascade, Claude A, GLM, Kimi, Runtime Engineer
- **Verificación:** Todos los fixes deben ser verificados antes de consolidación
- **Consolidación:** PR único después de verificación completa

---

## 📊 Estado Actual del Repositorio

| Componente | Estado | Notas |
|------------|--------|-------|
| Estructura de directorios | ✅ Completa | Fase 0 organizada |
| Código principal | ✅ En `src/sage_runtime/` | Único árbol de código |
| Handoffs | ✅ En `handoffs/` | 2 handoffs oficiales |
| Submissions | ✅ Organizadas | 5 agentes con entregas |
| Baseline | ✅ Completo | 4 snapshots históricos |
| Archive | ✅ Limpio | Duplicados archivados |
| Documentación | ✅ Organizada | `docs/` con subdirs |
| ZIPs duplicados | ✅ Archivados | 3 ZIPs en `archive/ZIPs_duplicados/` |
| Archivos temporales | ✅ Eliminados | `sage_runtime_fixed/` removido |

---

## 🎯 Próximos Pasos Globales

1. **Verificación de Fixes** (Pendiente)
   - Identidad (Cascade): Verificar respuestas en español/inglés
   - WebSocket (Devin): Verificar sesión sostenida 10+ min

2. **Consolidación Final** (Esperando señal)
   - PR único con toda la organización
   - Eliminación de carpetas legacy en raíz (si corresponde)
   - Actualización de `CONTRIBUTING.md` y `CHANGELOG.md`

3. **Fase 1 MVP** (En preparación)
   - 12 capacidades de liderazgo operacional
   - Implementación por módulos
   - Integración UI en tiempo real

---

**Nota Importante:** Este documento es la fuente de verdad para la organización del repositorio. Cualquier discrepancia entre este documento y el estado real debe ser reportada inmediatamente al coordinador.

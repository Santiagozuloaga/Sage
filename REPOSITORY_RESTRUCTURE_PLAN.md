# REPOSITORY_RESTRUCTURE_PLAN.md

**Autor:** Qwen (Validation & Repository Organization Engineer)  
**Fecha:** 2026-07-06  
**Propósito:** Plan de reorganización profesional del repositorio Sage para trabajo multi-agente sostenible

---

## 1. Estado Actual

### 1.1 Estructura de Carpetas en `/workspace`

```
/workspace/
├── .git/                          # Repositorio Git
├── .gitignore                     # Ignorados de Git
├── HANDOFF_CASCADE_PAQUETE.zip    # ZIP de Claude A (156 KB)
├── Kimi_Agent_Planificador de Engine de Decisión.zip  # ZIP de Kimi (1.4 MB)
├── MERGE_AUDIT.md                 # Auditoría de integración de GLM (42 KB)
├── Prompt para Kimi.txt           # Prompt histórico
├── README.md                      # README minimalista (9 bytes)
├── SAGE_Runtime_RuntimeEngineer_Submission (1).zip  # Duplicado
├── SAGE_Runtime_RuntimeEngineer_Submission.zip      # Submission de Runtime Engineer
├── SAGE_Runtime_v4.5_Documentation_V2.zip  # Documentación V2
├── kimi_submission/               # Directorio de análisis de Kimi
│   ├── SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip
│   └── sage_analysis/             # Copias anidadas de todos los ZIPs
│       ├── HANDOFF_CASCADE_PAQUETE/
│       ├── HANDOFF_CASCADE_PAQUETE.zip
│       ├── SAGE_Runtime_RuntimeEngineer_Submission/
│       ├── SAGE_Runtime_RuntimeEngineer_Submission.zip
│       ├── SAGE_Runtime_v4.5_Documentation_V2.zip
│       ├── kimi_submission/       # Submission de Kimi (descomprimida)
│       │   ├── BUG_REPORT_KIMI.md
│       │   ├── CHANGES.diff
│       │   ├── agents/
│       │   ├── dispatcher/
│       │   ├── kernel/
│       │   ├── sage_runtime_fixed/
│       │   └── scripts/
│       └── sage_runtime_original/
│           └── sage_runtime/
├── sage_runtime.zip               # Baseline original
├── sage_runtime_submission/       # Submission de Runtime Engineer (descomprimida)
│   ├── BUG_REPORT.md
│   ├── CHANGES.diff
│   ├── HANDOFF_RUNTIME_ENGINEER.md
│   ├── README.md
│   ├── SAGE_RUNTIME_STATUS.md
│   ├── __init__.py
│   ├── agents/
│   ├── audit_runtime.py
│   ├── auditor/
│   ├── boot/
│   ├── command_mode/
│   ├── config/
│   ├── contracts/
│   ├── dashboard/
│   ├── dispatcher/
│   ├── docs/
│   ├── events/
│   ├── file_processor/
│   ├── image_analysis/
│   ├── interface/
│   ├── kernel/
│   ├── main.py
│   ├── memory/
│   ├── mission_control/
│   ├── providers/
│   ├── recovery/
│   ├── repository_scanner/
│   ├── requirements.txt
│   ├── scripts/
│   ├── tests/
│   └── web/
└── second promt                   # Archivo histórico sin uso
```

### 1.2 Problemas Encontrados

| ID | Problema | Severidad | Impacto |
|----|----------|-----------|---------|
| P1 | ZIPs duplicados en raíz y anidados | ALTA | Confusión, desperdicio de espacio |
| P2 | Documentación dispersa en múltiples niveles | ALTA | Difícil encontrar handoffs oficiales |
| P3 | README.md de 9 bytes (vacío) | ALTA | Sin onboarding para nuevos agentes |
| P4 | Sin CONTRIBUTING.md | MEDIA | Sin guía de contribución |
| P5 | Sin CHANGELOG.md | MEDIA | Sin historial de versiones |
| P6 | Sin estructura de RFCs | MEDIA | Decisiones arquitectónicas no documentadas centralmente |
| P7 | Handoffs mezclados con código | MEDIA | Difícil distinguir entregables de trabajo en progreso |
| P8 | Múltiples copias de sage_runtime (original, fixed, submission) | BAJA | Necesario para diffs pero debe organizarse |
| P9 | Archivos temporales en raíz (`second promt`, `Prompt para Kimi.txt`) | BAJA | Suciedad visual |
| P10 | Sin convención de nombres para ramas | ALTA | Confusión en integración |
| P11 | Sin directorio para auditorías | MEDIA | Auditorías dispersas |
| P12 | ZIPs de submission dentro de directorios de análisis | MEDIA | Estructura confusa |

---

## 2. Nueva Estructura Propuesta

### 2.1 Principios de Diseño

1. **Separación clara entre código fuente, documentación y entregables**
2. **Un solo lugar para cada tipo de artefacto** (no duplicados)
3. **Handoffs como documentos oficiales**, no como ZIPs sueltos
4. **Auditorías consolidadas** en un directorio dedicado
5. **Ramas con convención de nombres** por agente/tipo
6. **Documentación jerárquica** con índices claros
7. **Preservar todo el contenido** (nada se elimina, solo se mueve)

### 2.2 Estructura Propuesta

```
/workspace/sage-os/
├── README.md                        # Onboarding principal (nuevo)
├── CONTRIBUTING.md                  # Guía de contribución (nuevo)
├── CHANGELOG.md                     # Historial de versiones (nuevo)
├── CODE_OF_CONDUCT.md               # Normas de colaboración (nuevo)
│
├── src/                             # CÓDIGO FUENTE PRINCIPAL
│   └── sage_runtime/                # Versión fusionada lista para producción
│       ├── __init__.py
│       ├── main.py
│       ├── agents/
│       ├── auditor/
│       ├── boot/
│       ├── command_mode/
│       ├── config/
│       ├── contracts/
│       ├── dashboard/
│       ├── dispatcher/
│       ├── events/
│       ├── file_processor/
│       ├── image_analysis/
│       ├── interface/
│       ├── kernel/
│       ├── memory/
│       ├── mission_control/
│       ├── providers/
│       ├── recovery/
│       ├── repository_scanner/
│       ├── web/
│       ├── requirements.txt
│       └── scripts/
│
├── docs/                            # DOCUMENTACIÓN OFICIAL
│   ├── INDEX.md                     # Índice de documentación
│   ├── architecture/                # Arquitectura del sistema
│   │   ├── OVERVIEW.md
│   │   ├── KERNEL_DESIGN.md
│   │   ├── DISPATCHER_DESIGN.md
│   │   ├── EVENT_BUS_DESIGN.md
│   │   └── AGENT_ROUTER_DESIGN.md
│   ├── api/                         # API Reference
│   │   └── ...
│   ├── user_guide/                  # Guía de usuario
│   │   └── ...
│   └── rfc/                         # Requests for Comments (decisiones)
│       ├── RFC-001_PROVIDER_ROUTING.md
│       ├── RFC-002_DASHBOARD_OWNERSHIP.md
│       └── ...
│
├── handoffs/                        # HANDOFFS OFICIALES ENTRE AGENTES
│   ├── HANDOFF_CLAUDE_A_TO_CASCADE.md
│   ├── HANDOFF_CASCADE_TO_RUNTIME_ENGINEER.md
│   ├── HANDOFF_RUNTIME_ENGINEER_TO_CLAUDE_A.md
│   ├── HANDOFF_KIMI_DECISION_ENGINE.md
│   └── TEMPLATE_HANDOFF.md          # Plantilla para futuros handoffs
│
├── audits/                          # AUDITORÍAS Y VALIDACIONES
│   ├── MERGE_AUDIT_GLM.md           # Auditoría de integración (GLM)
│   ├── VALIDATION_REPORT_QWEN.md    # Este informe
│   ├── FUNCTIONAL_AUDIT_CASCADE.md  # Auditoría funcional de Cascade
│   └── SECURITY_AUDIT.md            # (futuro)
│
├── submissions/                     # ENTREGABLES DE AGENTES (inmutables)
│   ├── claude_a/
│   │   ├── HANDOFF_CASCADE_PAQUETE.zip
│   │   ├── CAMBIOS_INGENIERIA_SAGE_RUNTIME.md
│   │   ├── AUDITORIA_FUNCIONAL_FLUJO_COMPLETO.md
│   │   └── INFORME_FINAL_CIERRE.md
│   ├── cascade/
│   │   └── ...
│   ├── runtime_engineer/
│   │   ├── SAGE_Runtime_RuntimeEngineer_Submission.zip
│   │   ├── BUG_REPORT.md
│   │   ├── HANDOFF_RUNTIME_ENGINEER.md
│   │   └── CHANGES.diff
│   ├── kimi/
│   │   ├── SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip
│   │   ├── BUG_REPORT_KIMI.md
│   │   └── CHANGES.diff
│   └── glm/
│       └── MERGE_AUDIT.md
│
├── baseline/                        # VERSIONES BASELINE PARA DIFFS
│   ├── sage_runtime_original.zip    # Snapshot inicial
│   ├── claude_a_snapshot/           # Código de Claude A descomprimido
│   ├── runtime_engineer_snapshot/   # Código de RE descomprimido
│   └── kimi_snapshot/               # Código de Kimi descomprimido
│
├── experiments/                     # TRABAJO EN PROGRESO / EXPERIMENTOS
│   └── (cada agente crea su subdirectorio temporal aquí)
│
├── scripts/                         # SCRIPTS DE AUTOMATIZACIÓN
│   ├── run_tests.sh
│   ├── generate_diff.sh
│   ├── validate_handoffs.py
│   └── ...
│
├── tests/                           # TESTS CENTRALIZADOS
│   ├── test_runtime_engineer_fixes.py
│   ├── test_kimi_fixes.py
│   ├── validate_pr009.py
│   ├── validate_pr010.py
│   ├── validate_pr011.py
│   ├── validate_pr012.py
│   ├── validate_pr013.py
│   ├── validate_pr014.py
│   └── validate_pr015.py
│
└── archive/                         # ARCHIVOS HISTÓRICOS (no eliminar)
    ├── Prompt_para_Kimi.txt
    ├── second_promt
    └── ZIPs_duplicados/
        ├── SAGE_Runtime_RuntimeEngineer_Submission_(1).zip
        └── ...
```

---

## 3. Archivos que Mover

### 3.1 Raíz → Subdirectorios

| Archivo Original | Destino | Justificación |
|------------------|---------|---------------|
| `MERGE_AUDIT.md` | `audits/MERGE_AUDIT_GLM.md` | Auditoría de GLM |
| `HANDOFF_CASCADE_PAQUETE.zip` | `submissions/claude_a/HANDOFF_CASCADE_PAQUETE.zip` | Submission de Claude A |
| `SAGE_Runtime_RuntimeEngineer_Submission.zip` | `submissions/runtime_engineer/SAGE_Runtime_RuntimeEngineer_Submission.zip` | Submission de RE |
| `SAGE_Runtime_RuntimeEngineer_Submission (1).zip` | `archive/ZIPs_duplicados/SAGE_Runtime_RuntimeEngineer_Submission_(1).zip` | Duplicado |
| `Kimi_Agent_Planificador de Engine de Decisión.zip` | `submissions/kimi/Kimi_Agent_Planificador_de_Engine_de_Decision.zip` | Submission de Kimi |
| `SAGE_Runtime_v4.5_Documentation_V2.zip` | `archive/documentation/SAGE_Runtime_v4.5_Documentation_V2.zip` | Documentación histórica |
| `sage_runtime.zip` | `baseline/sage_runtime_original.zip` | Baseline para diffs |
| `Prompt para Kimi.txt` | `archive/Prompt_para_Kimi.txt` | Histórico |
| `second promt` | `archive/second_promt` | Histórico |
| `README.md` (9 bytes) | `src/sage_runtime/README.md` | Reemplazar con README completo en raíz |

### 3.2 `kimi_submission/` → Desmantelar

| Contenido Original | Destino | Justificación |
|--------------------|---------|---------------|
| `kimi_submission/SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip` | `submissions/kimi/SAGE_DecisionEngine_Scheduler_Kimi_Submission.zip` | Submission oficial |
| `kimi_submission/sage_analysis/HANDOFF_CASCADE_PAQUETE/` | `baseline/claude_a_snapshot/` | Snapshot de Claude A |
| `kimi_submission/sage_analysis/SAGE_Runtime_RuntimeEngineer_Submission/` | `baseline/runtime_engineer_snapshot/` | Snapshot de RE |
| `kimi_submission/sage_analysis/kimi_submission/` | `baseline/kimi_snapshot/` | Snapshot de Kimi |
| `kimi_submission/sage_analysis/sage_runtime_original/sage_runtime/` | Eliminar (redundante con `sage_runtime.zip`) | Duplicado |
| `kimi_submission/sage_analysis/*.zip` | Eliminar (ya movidos a submissions/) | Duplicados |

### 3.3 `sage_runtime_submission/` → Integrar o Archivar

| Contenido | Acción | Destino |
|-----------|--------|---------|
| `BUG_REPORT.md`, `HANDOFF_RUNTIME_ENGINEER.md`, `CHANGES.diff` | Mover | `submissions/runtime_engineer/` |
| `docs/`, `web/README.md` | Mover | `archive/documentation/runtime_engineer_docs/` |
| `agents/`, `dispatcher/`, `kernel/`, etc. (código) | Fusionar | `src/sage_runtime/` (tras merge) |
| `scripts/test_runtime_engineer_fixes.py` | Mover | `tests/` |
| `tests/validate_pr*.py` | Mover | `tests/` |
| `audit_runtime.py` | Mover | `scripts/` |
| `requirements.txt` | Fusionar | `src/sage_runtime/requirements.txt` |

---

## 4. Archivos que Eliminar (Solo Duplicados Exactos)

| Archivo | Razón | Alternativa |
|---------|-------|-------------|
| `kimi_submission/sage_analysis/sage_runtime_original/` | Redundante con `sage_runtime.zip` | Usar `baseline/sage_runtime_original.zip` |
| `kimi_submission/sage_analysis/*.zip` (copias) | Ya existen en submissions/ | Usar versiones en `submissions/` |
| `SAGE_Runtime_RuntimeEngineer_Submission (1).zip` | Duplicado numérico | Usar versión sin `(1)` |
| `__pycache__/` en todos lados | Generados por Python | Se regeneran automáticamente |

**Nota:** No se elimina ningún documento, handoff, auditoría o código fuente. Solo duplicados exactos y archivos generados.

---

## 5. Archivos que Conservar (Sin Modificar)

| Archivo/Directorio | Ubicación Actual | Razón |
|--------------------|------------------|-------|
| `MERGE_AUDIT.md` | Contenido íntegro | Auditoría oficial de GLM |
| `HANDOFF_CASCADE.md` | En `HANDOFF_CASCADE_PAQUETE.zip` | Handoff oficial de Claude A |
| `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` | En `HANDOFF_CASCADE_PAQUETE.zip` | Changelog de Claude A |
| `AUDITORIA_FUNCIONAL_FLUJO_COMPLETO.md` | En `HANDOFF_CASCADE_PAQUETE.zip` | Auditoría funcional |
| `INFORME_FINAL_CIERRE.md` | En `HANDOFF_CASCADE_PAQUETE.zip` | Informe de cierre de Claude A |
| `BUG_REPORT.md` (RE) | En `sage_runtime_submission/` | Bug report de Runtime Engineer |
| `HANDOFF_RUNTIME_ENGINEER.md` | En `sage_runtime_submission/` | Handoff de RE |
| `BUG_REPORT_KIMI.md` | En `kimi_submission/sage_analysis/kimi_submission/` | Bug report de Kimi |
| Todos los `.py` source files | En sus respectivos módulos | Código fuente |
| Todos los `.md` en `docs/` | En submissions/ | Documentación técnica |

---

## 6. Flujo Recomendado para Futuros Agentes

### 6.1 Onboarding de Nuevo Agente

1. Leer `README.md` (raíz) — visión general del proyecto
2. Leer `CONTRIBUTING.md` — normas de contribución
3. Leer `handoffs/TEMPLATE_HANDOFF.md` — formato esperado para handoffs
4. Revisar `docs/INDEX.md` — documentación relevante a su especialización
5. Clonar rama correspondiente (ver sección 7)
6. Crear subdirectorio en `experiments/<nombre_agente>/` para trabajo en progreso
7. Al completar tarea:
   - Generar ZIP en `submissions/<nombre_agente>/`
   - Crear handoff en `handoffs/`
   - Actualizar `CHANGELOG.md`

### 6.2 Ciclo de Vida de una Tarea

```
1. Agente recibe prompt → lee handoff previo en `handoffs/`
2. Crea rama feature/<agente>/<tarea>
3. Trabaja en `experiments/<agente>/<tarea>/`
4. Ejecuta tests en `tests/`
5. Genera submission en `submissions/<agente>/`
6. Crea handoff en `handoffs/`
7. Abre PR para merge a `main`
8. Auditor valida (usa `audits/`)
9. Merge completado → código va a `src/sage_runtime/`
10. Agente siguiente lee handoff y continúa
```

### 6.3 Convención de Handoffs

Cada handoff debe contener:
- De/Para/Fecha
- Resumen ejecutivo (máx 10 líneas)
- Archivos modificados (lista)
- Riesgos de merge detectados
- Dependencias con trabajo de otros agentes
- Orden recomendado de integración
- Estado de tests
- Recomendaciones para el siguiente agente

Plantilla disponible en `handoffs/TEMPLATE_HANDOFF.md`.

---

## 7. Organización de Ramas Git

### 7.1 Ramas Principales

| Rama | Propósito | Protectores |
|------|-----------|-------------|
| `main` | Código production-ready (fusionado y validado) | Requiere 1 auditor + 1 validación |
| `develop` | Integración continua (pre-producción) | Requiere tests passing |
| `baseline` | Snapshots históricos inmutables | Solo append, no overwrite |

### 7.2 Ramas por Agente (Feature Branches)

Convención: `<tipo>/<agente>/<descripcion>`

| Tipo | Ejemplo | Uso |
|------|---------|-----|
| `feature/` | `feature/claude-a/provider-router` | Nueva funcionalidad |
| `fix/` | `fix/runtime-engineer/event-bus-dlq` | Bug fix |
| `audit/` | `audit/glm/merge-conflicts` | Auditoría |
| `experiment/` | `experiment/kimi/decision-tree` | Experimento no crítico |
| `handoff/` | `handoff/cascade-to-re` | Preparación de handoff |

### 7.3 Tags de Versión

Convención: `v<major>.<minor>.<patch>-<estado>`

- `v4.5.0-stable` — Versión actual estable
- `v4.5.1-rc1` — Release candidate
- `v4.6.0-dev` — En desarrollo

---

## 8. Organización de Documentación

### 8.1 Jerarquía

```
docs/
├── INDEX.md                     # "Mapa" de toda la documentación
├── getting_started/             # Para nuevos colaboradores
│   ├── installation.md
│   ├── quickstart.md
│   └── faq.md
├── architecture/                # Decisiones de diseño
│   ├── overview.md
│   ├── kernel.md
│   ├── dispatcher.md
│   ├── event-bus.md
│   ├── agent-router.md
│   └── decisions/               # ADRs (Architecture Decision Records)
│       └── adr-001-dashboard-ownership.md
├── api/                         # Referencia de API
│   ├── kernel.md
│   ├── dispatcher.md
│   └── ...
├── guides/                      # Guías prácticas
│   ├── adding-a-provider.md
│   ├── implementing-an-agent.md
│   └── debugging-fsm.md
└── rfc/                         # Requests for Comments
    ├── rfc-001-provider-routing.md
    ├── rfc-002-agent-load-balancing.md
    └── template.md
```

### 8.2 Documentos Críticos a Preservar

| Documento | Ubicación Propuesta | Prioridad |
|-----------|---------------------|-----------|
| `HANDOFF_CASCADE.md` | `handoffs/HANDOFF_CLAUDE_A_TO_CASCADE.md` | CRÍTICA |
| `HANDOFF_RUNTIME_ENGINEER.md` | `handoffs/HANDOFF_RUNTIME_ENGINEER_TO_CLAUDE_A.md` | CRÍTICA |
| `BUG_REPORT_KIMI.md` | `submissions/kimi/BUG_REPORT_KIMI.md` | ALTA |
| `MERGE_AUDIT.md` | `audits/MERGE_AUDIT_GLM.md` | ALTA |
| `CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` | `submissions/claude_a/CAMBIOS_INGENIERIA_SAGE_RUNTIME.md` | ALTA |
| `AUDITORIA_FUNCIONAL_FLUJO_COMPLETO.md` | `audits/FUNCTIONAL_AUDIT_CASCADE.md` | ALTA |

---

## 9. Organización de Ingeniería

### 9.1 Código Fuente (`src/sage_runtime/`)

- **Un solo árbol de código** tras el merge
- Sin duplicados de módulos
- Imports relativos consistentes
- `__init__.py` en todos los paquetes

### 9.2 Scripts (`scripts/`)

| Script | Propósito |
|--------|-----------|
| `run_all_tests.sh` | Ejecuta toda la suite de tests |
| `generate_diff.sh <branch1> <branch2>` | Genera diff unificado |
| `validate_handoffs.py` | Verifica que todos los handoffs sigan la plantilla |
| `check_conflicts.py` | Detecta conflictos potenciales antes de merge |

### 9.3 Tests (`tests/`)

Organizados por tipo:

```
tests/
├── unit/                    # Tests unitarios
│   ├── test_dispatcher.py
│   ├── test_kernel.py
│   └── ...
├── integration/             # Tests de integración
│   ├── test_boot_sequence.py
│   └── test_event_flow.py
├── regression/              # Tests de regresión por agente
│   ├── test_runtime_engineer_fixes.py
│   ├── test_kimi_fixes.py
│   └── test_claude_a_fixes.py
└── validation/              # Validación de PRs
    ├── validate_pr009.py
    └── ...
```

---

## 10. Organización de Entregables

### 10.1 Estructura de Submission por Agente

Cada agente entrega:

```
submissions/<nombre_agente>/
├── <nombre_proyecto>.zip          # Paquete completo
├── BUG_REPORT_<AGENTE>.md         # Bugs identificados y fixeados
├── CHANGES.diff                   # Diff unificado de cambios
├── HANDOFF_<AGENTE>.md            # Handoff al siguiente agente
└── README_SUBMISSION.md           # Instrucciones específicas de esta submission
```

### 10.2 Checklist de Submission

Antes de entregar, cada agente verifica:

- [ ] Todos los tests pasan
- [ ] Handoff sigue la plantilla
- [ ] BUG_REPORT lista bugs con severidad y estado
- [ ] CHANGES.diff es aplicable limpio
- [ ] ZIP contiene estructura completa
- [ ] No hay conflictos no documentados con otros agentes

---

## 11. Próximos Pasos (Post-Reestructuración)

1. **Fase 1:** Crear nueva estructura de directorios (sin mover nada aún)
2. **Fase 2:** Mover archivos según plan (sección 3)
3. **Fase 3:** Crear documentos nuevos (README, CONTRIBUTING, CHANGELOG)
4. **Fase 4:** Configurar ramas Git según convención (sección 7)
5. **Fase 5:** Ejecutar validación post-movimiento (todos los tests deben pasar)
6. **Fase 6:** Comunicar nueva estructura a todos los agentes

---

## 12. Métricas de Éxito

La reestructuración se considera exitosa si:

- [ ] Un nuevo agente puede encontrar el handoff relevante en < 2 minutos
- [ ] Todos los tests pasan tras la reestructuración
- [ ] No hay archivos duplicados (verificado con script)
- [ ] La estructura de ramas es clara y seguida
- [ ] Cada submission tiene su handoff correspondiente
- [ ] El README permite onboarding autónomo

---

**FIN DEL PLAN DE REESTRUCTURACIÓN**

*Nota: Este documento NO mueve archivos todavía. Solo planifica. La ejecución requiere aprobación del Arquitecto.*

# Decyzje dotyczące kontraktów domenowych

## Modele będące źródłem prawdy

- Task: app/models/task.py
- ApprovalRequest: app/models/approval.py
- AuditEvent: app/models/audit.py
- Department: app/domain/contracts/department.py
- MemoryRecord: app/domain/contracts/memory.py
- Tool: app/tools/base.py

## Modele do utworzenia

- Manager
- Risk
- Report

## Modele pomocnicze do ujednolicenia

- Agent / AgentProfile
- Decision
- BrainTask / Task
- TaskStage

## Zasada

Modele domenowe nie powinny być reprezentowane jako luźne słowniki.
Słowniki pozostają dopuszczalne na granicach systemu:
- API,
- integracje z LLM,
- zapis JSON,
- eksport raportów.

## Plan

1. Ustalić jeden model Task.
2. Ustalić jeden model ApprovalRequest.
3. Utworzyć Decision.
4. Utworzyć Risk.
5. Utworzyć Report.
6. Utworzyć Manager.
7. Wydzielić TaskStage.
8. Zaktualizować testy.

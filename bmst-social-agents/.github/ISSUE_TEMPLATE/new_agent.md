---
name: New agent proposal
about: Propose a new agent to add to the pipeline
title: "[AGENT] "
labels: enhancement, new-agent
assignees: ''
---

## Agent name

<!-- e.g. ANALYTICS, SCHEDULER, TRANSLATOR -->

## Purpose

What problem does this agent solve? Why does the pipeline need it?

## Pipeline position

Where does this agent fit in the pipeline?

```
SCOUT → WRITER → CAROUSEL → REVISOR → PUBLISHER
                    ↑
              Insert here? (example)
```

## AOS Identity Contract (draft)

```yaml
id: MY_AGENT
name: "MY_AGENT"
description: ""
scope: |
  What this agent is allowed to do.
authority_levels:
  autonomous: []
  requires_approval: []
  prohibited: []
inputs: []
outputs: []
fault_contract:
  EXECUTION_FAULT: ""
  CONFIDENCE_FAULT: ""
hard_limits: []
```

## External dependencies

List any new APIs, credentials, or infrastructure this agent requires.

- [ ] API 1: 
- [ ] API 2: 

## Test cases (draft)

Describe at least 3 scenarios to cover:
1. Happy path: 
2. Edge case: 
3. Fault scenario: 

## Acceptance criteria

- [ ] AOS contract defined in `aos-contracts.yaml`
- [ ] Node function in `src/agents/<name>/node.py`
- [ ] Registered in `src/orchestrator/graph.py`
- [ ] Routing logic in `src/orchestrator/router.py`
- [ ] YAML dataset in `tests/datasets/<name>_cases.yaml` (≥6 cases)
- [ ] Parametrized test in `tests/test_<name>.py`
- [ ] README updated
- [ ] All 92+ tests pass

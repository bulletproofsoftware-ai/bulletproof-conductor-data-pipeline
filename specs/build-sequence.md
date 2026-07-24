# Build Sequence — Conductor Data Pipeline

## Dependency Graph

```
TODO-001 (JSON Schemas)
  │
  ├──▶ TODO-002 (Masking Engine Core)
  │      │
  │      ├──▶ TODO-003 (NER Integration)
  │      │
  │      ├──▶ TODO-004 (Synthetic Generation)
  │      │
  │      └──▶ TODO-011 (Docker Compose) ◀── TODO-003
  │
  ├──▶ TODO-005 (Lineage Emitter)
  │
  ├──▶ TODO-006 (Quality Assertion Engine)
  │
  ├──▶ TODO-008 (Contract Enforcement) ◀── TODO-005, TODO-007
  │
  └──▶ TODO-007 (MCP Tool Layer) ◀── TODO-002, TODO-005, TODO-006
         │
         └──▶ TODO-010 (Agent Definitions) ◀── TODO-008, TODO-009
                │
                └──▶ TODO-012 (Integration Testing) ◀── ALL

TODO-009 (Quality Gate) ◀── TODO-002, TODO-003, TODO-005, TODO-006, TODO-008
```

## Build Phases

### Phase 1: Foundation (no dependencies)
| TODO | Component | Est. Complexity | Parallelizable |
|------|-----------|-----------------|----------------|
| TODO-001 | JSON Schema Definitions | M | Yes (first) |

**Rationale**: Every other component validates against these schemas. Must be complete before anything else starts.

### Phase 2: Core Services (depends on Phase 1)
| TODO | Component | Est. Complexity | Parallelizable |
|------|-----------|-----------------|----------------|
| TODO-002 | Masking Engine Core | L | Yes |
| TODO-005 | Lineage Emitter | L | Yes |
| TODO-006 | Quality Assertion Engine | L | Yes |

**Rationale**: These three are independent of each other. All depend only on TODO-001 schemas. Maximum parallelism — assign 3 builders simultaneously.

### Phase 3: Extensions (depends on Phase 2 core components)
| TODO | Component | Est. Complexity | Parallelizable |
|------|-----------|-----------------|----------------|
| TODO-003 | NER Integration | M | Yes |
| TODO-004 | Synthetic Generation | M | Yes |
| TODO-007 | MCP Tool Layer | L | Partially (depends on 002, 005, 006) |

**Rationale**: NER and synthetic are masking engine extensions (depend on TODO-002 only). MCP tool layer depends on masking engine, lineage, AND quality engine — all three Phase 2 deliverables must be complete.

### Phase 4: Governance Layer (depends on Phases 2-3)
| TODO | Component | Est. Complexity | Parallelizable |
|------|-----------|-----------------|----------------|
| TODO-008 | Contract Enforcement | M | Yes |
| TODO-009 | Quality Gate | L | Yes |

**Rationale**: Contract enforcement needs schemas + lineage + MCP tools. Quality gate needs masking engine + NER + lineage + quality engine + contract enforcement. These two can be built in parallel once their dependencies are met, but TODO-009 has more dependencies than TODO-008.

### Phase 5: Agent & Infrastructure (depends on Phase 4)
| TODO | Component | Est. Complexity | Parallelizable |
|------|-----------|-----------------|----------------|
| TODO-010 | Agent Definitions | M | Yes |
| TODO-011 | Docker Compose | M | Yes |

**Rationale**: Agent definitions need tools, contracts, and gates to be defined. Docker compose needs the masking engine Dockerfile and Presidio dependency. These two are independent of each other.

### Phase 6: Integration (depends on ALL)
| TODO | Component | Est. Complexity | Parallelizable |
|------|-----------|-----------------|----------------|
| TODO-012 | Integration Testing | L | No (needs everything) |

**Rationale**: Integration tests exercise the complete system end-to-end. Every other TODO must be complete.

## Recommended Build Order (Serial)

If only one builder is available:

```
1. TODO-001  →  JSON Schemas
2. TODO-002  →  Masking Engine Core
3. TODO-005  →  Lineage Emitter
4. TODO-006  →  Quality Assertion Engine
5. TODO-003  →  NER Integration
6. TODO-004  →  Synthetic Generation
7. TODO-007  →  MCP Tool Layer
8. TODO-008  →  Contract Enforcement
9. TODO-009  →  Quality Gate
10. TODO-010 →  Agent Definitions
11. TODO-011 →  Docker Compose
12. TODO-012 →  Integration Testing
```

## Recommended Build Order (3 Parallel Builders)

```
Sprint 1: Builder-A: TODO-001 (schemas)
Sprint 2: Builder-A: TODO-002, Builder-B: TODO-005, Builder-C: TODO-006
Sprint 3: Builder-A: TODO-003+004, Builder-B: TODO-007, Builder-C: TODO-008
Sprint 4: Builder-A: TODO-009, Builder-B: TODO-010, Builder-C: TODO-011
Sprint 5: Builder-A: TODO-012 (all builders review)
```

## Critical Path

```
TODO-001 → TODO-002 → TODO-007 → TODO-009 → TODO-012
```

The longest dependency chain runs through schemas → masking engine → MCP tools → quality gate → integration testing. This is the critical path — delays here delay the entire project.

## Risk Hotspots

1. **TODO-007 (MCP Tool Layer)** is the biggest dependency bottleneck — 3 predecessors must complete before it can start, and 4 successors depend on it.
2. **TODO-002 (Masking Engine Core)** is the most complex single component. If it slips, NER, synthetic, tools, and gate all slip.
3. **TODO-009 (Quality Gate)** has the most dependencies (6 TODOs). It cannot start until late in the build.
4. **TODO-011 (Docker Compose)** is low-risk technically but blocks integration testing.

## Complexity Summary

| Complexity | Count | TODOs |
|------------|-------|-------|
| Small (S) | 0 | — |
| Medium (M) | 5 | 001, 003, 004, 008, 010 |
| Large (L) | 5 | 002, 005, 006, 007, 009 |
| Large (L) | 2 | 011 (M), 012 (L) |

Total: 5 Medium + 7 Large = significant engineering effort. Estimated 2-3 weeks with 3 parallel builders.

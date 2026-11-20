# aerarium

This project uses the AIWG SDLC Complete framework.

## Getting Started

### 1. Fill Intake Forms

Start by completing the intake forms in the `.aiwg/intake/` directory:

- `.aiwg/intake/project-intake.md` - Project overview, stakeholders, constraints
- `.aiwg/intake/solution-profile.md` - Technical requirements, architecture preferences
- `.aiwg/intake/option-matrix.md` - Solution alternatives and evaluation criteria

### 2. Skills and Provider Adapters

Canonical SDLC skills are discovered through the AIWG kernel/index surface. Provider-specific commands, when deployed, are compatibility adapters rather than workflow definitions.

### 3. Start SDLC Flow

Once intake forms are complete, kick off the Concept → Inception flow:

```bash
# Find and inspect the canonical workflow
aiwg discover "SDLC concept to inception"
aiwg show skill flow-concept-to-inception

# Find project intake guidance
aiwg discover "create or complete project intake"
```

### 4. SDLC Framework Documentation

Supported providers can discover the complete SDLC framework documentation at:

`/home/pino/.hermes/node/lib/node_modules/aiwg/agentic/code/frameworks/sdlc-complete/`

This includes templates, flows, add-ons, and artifacts for all SDLC phases.

## Framework Components

- **Agents** (51): Specialized SDLC role agents (Requirements Analyst, Security Gatekeeper, etc.)
- **Skills**: Canonical flow orchestration and workflow contracts
- **Provider adapters**: Optional generated command/invocation surfaces
- **Templates**: Intake, requirements, architecture, test, security, deployment
- **Flows**: Phase-based workflows (Inception → Elaboration → Construction → Transition)
- **Add-ons**: GDPR compliance, legal frameworks

## Key Skills

Use `aiwg discover "<need>"` and `aiwg show skill <name>` to select current behavior. Common canonical skills include `flow-concept-to-inception`, `flow-discovery-track`, `flow-delivery-track`, `flow-iteration-dual-track`, `flow-gate-check`, and `flow-handoff-checklist`.

For more information, see the [SDLC Complete Framework documentation](/home/pino/.hermes/node/lib/node_modules/aiwg/agentic/code/frameworks/sdlc-complete/README.md).

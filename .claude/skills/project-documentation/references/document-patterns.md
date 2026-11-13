# Document patterns

Choose one primary reader and job for each document. Follow existing paths; create the minimum new structure necessary.

## Decisions and plans
For a material architecture decision, record status, context, selected approach, consequences, alternatives, and related evidence. Do not reopen the approved choices (React/Vite + React Three Fiber, FastAPI, LangGraph with OpenAI models, LangSmith, static replay site) merely to fill a template.
Once accepted, preserve the historical reasoning; make a superseding decision when the architecture changes. Correct factual mistakes transparently.
Use an RFC when an unresolved decision benefits from discussion. Routine reversible implementation choices can be resolved with judgment inside the approved design.
Keep implementation sequencing in the existing plan and update its tasks. An ADR is not a task checklist.

## Architecture
A context view names users and external services (OpenAI, LangSmith, Open-Meteo, Carbon Mapper, Vercel). A container view names independently runnable processes and data stores (FastAPI backend with simulator and engineering, LangGraph agents running in the backend process, local Supabase Postgres holding runs/decisions and LangGraph checkpoints, the Vite frontend, and the static Vercel replay build with its trace files).
Add a component view only where it improves understanding. Annotate important protocols (REST, WebSocket), the live-versus-replay boundary, and durable versus transient state.
The LangGraph checkpoint is not the approval record shown to users, and LangSmith is not the replay source. Make those distinctions visible in diagrams.
Do not draw unimplemented integrations as verified. Keep Mermaid or other editable source alongside any rendered asset.

## Engineering references
For each physics model: purpose, equations (with symbols and units), assumptions, validity range (e.g. stability classes, distance range), constants with citations, known limitations, and the tests that check it. State plainly where the model is a simplification (Gaussian plume, no CFD).

## Runbooks
Name the actual symptom, affected environment (local live mode or static replay), diagnostic commands, remediation options, verification, and recovery. Use commands that match the current shell. Clearly identify destructive operations; resetting the checkpointer database or regenerating traces needs an explicit step.

## Setup and public case studies
Link to `docs/LOCAL_DEVELOPMENT.md` instead of duplicating its commands and ports. Use `.env.example` as the safe configuration reference.
Portfolio copy (README, LinkedIn posts) explains the real industry problem, what is implemented, and the actual validation (benchmark numbers exactly as produced). Label the fictional station and simulated data; never present simulated results as field results.
Keep screenshots and recordings free of credentials.

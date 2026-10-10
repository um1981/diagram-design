# State Machine

**Best for:** finite state logic — order status, auth state, connection lifecycle, form wizard, job queue status — and the [`Lifecycle phase map`](semantic-patterns.md#9-lifecycle-phase-map) pattern when one subject's progress, waits, retries, cancellation, and outcomes are the story.

## Routing distinctions

- Use **Sequence** for time-ordered messages between actors, including request/message lifecycles.
- Use ordinary **State Machine** for dense transition logic where events, guards, and legal transitions dominate.
- Use the **Lifecycle phase map** semantic pattern for one subject moving through 4–5 primary phases with separate wait/recovery and terminal-outcome bands. With 6+ primary states (typical ERP document lifecycles: Draft → … → Closed) use the ordinary State Machine grammar in two rows instead.

## Layout conventions
- States are rounded rectangles (`rx=8` — the one place a node uses 8, so a state reads differently from an `rx=6` process step), labeled in Sarabun 600 (13px for Thai).
- **Start**: filled ink dot (`r=6`). **End**: ringed dot (outer `r=8` outline, inner filled `r=5`).
- Transitions: orthogonal connectors (straight, or `r=8` elbows — SKILL §6 rule 1; no free curves), labeled `event [guard] / action` (omit sections you don't need). Latin labels: Sarabun 9px tracked caps (Geist Mono only for code-like guards); Thai labels: Sarabun 12px 500 on a 24px mask.
- Self-loops are a three-segment orthogonal loop above the state (up, across, down) with `r=8` corners.
- Orient along the dominant flow direction (left→right or top→down); rearrange before crossing transitions.
- Coral on the state the reader should notice — typically the error state, or "happy completion".

- **Theme v2 status colours:** ordinary states white + `ink`; colour only states whose status is the message (waiting = warning amber, cancelled/failed = error red, closed/done = success green); rejection paths red dashed. No orange in a status diagram — focal = 2px stroke. Reference: `assets/example-th-state.html`.

## Anti-patterns
- More transitions than states × 2 → likely two state machines.
- "From any state" transitions drawn from every state — use a single annotation (`* → Error on timeout`) instead.
- Unlabeled transitions (the whole point is *what triggers this*).

## Examples
- `assets/example-state.html` — minimal light
- `assets/example-state-lifecycle.html` — lifecycle phase map, minimal light

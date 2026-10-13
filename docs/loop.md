# The agent loop

iconpilot is agent-driven: the AI (with the `iconpilot` skill loaded) is the
drafter, the screener, and the orchestrator. The CLI is deterministic tools +
state. One round:

```
1. CONTEXT   iconpilot context <pack> --icon hut --variant mono
2. DRAFT     agent writes candidates to .runs/<round>/<variant>/<icon>/<cand>.svg
3. GATE      iconpilot gate .runs/<round> --pack <pack>     (writes .gate.json)
4. SCREEN    iconpilot contact-sheet .runs/<round> --pack <pack>
5. DECIDE    the user approves/keeps/rejects (page or text) → iconpilot decide
6. REPEAT    until every variant is approved → iconpilot export
```

## Roles, mapped to your harness

| Role | Realization |
|---|---|
| drafter | cheapest capable model you can spawn; feed it the `context` output verbatim |
| screener | any vision-capable model, shown the contact-sheet PNG |
| reviewer / advisor | your strongest model, on the whole sheet (set consistency) or for twice-rejected icons |
| designer | the agent writing briefs — then `iconpilot check` |

Craft guidance for every drafting model: read `craft.md` (shipped beside the
skill) — grid, stroke discipline, 16px legibility, silhouette-first.

## Decision grammar

One icon per line (multiple icons may share a line, separated by `·` or `;`):

```
hut/mono: a2 keep "thinner roof" · b1 no · more 2
lake/mono: a1 ok
peak/color: * no · restart "too abstract"
```

| Item | Effect |
|---|---|
| `<cand> ok ["c"]` | approve → materialize to `icons/`, freeze |
| `<cand> keep ["c"]` | materialize as working copy, stays `in_review` |
| `<cand> no ["c"]` | drop candidate |
| `* no` | reject all → back to `todo` |
| `more <N>` / `like <cand> <N>` | recorded request for the next round |
| `restart ["note"]` | back to concept; comments + rejected ideas carry forward |
| `note "text"` | icon-level comment |

`<variant>` defaults to the icon's single non-approved variant, else `mono`.
The CLI is the only parser — agents pass user text through **verbatim**.

## Hand-tweaking between rounds

`icons/*.svg` are yours: edit in Inkscape, VS Code, or an agent, then

```bash
iconpilot gate icons/hut/mono.svg --pack <pack>
```

Small fixes never need a full round; the next drafting pass refines from your
edited file.

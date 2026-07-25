# Independent Audit Checklist

Confirm directly from source:

- one observable, achievable goal and explicit non-goals;
- user requirements, repository instructions, and precedence conflicts;
- current-state evidence and cited paths;
- architecture, API/contracts, data/storage, failure/recovery, and boundary behavior;
- material product/security/tenant/billing/cost/destructive-data decisions;
- required design evidence and accessibility/interaction states;
- task ordering, target repository, likely files, dependencies, and bounded ownership;
- acceptance criteria mapped to meaningful local tests and real runtime paths;
- distinct pre-implementation audit, exact-diff code review, runtime QA, and docs gates;
- documentation impact, observability, rollout/rollback, migration, and residual risk;
- completion boundary, changed-file scope, and explicit publication authority;
- current artifact layout or explicitly recorded historical read fallback.

Classify findings P1/P2/P3 with exact evidence. Any P1/P2 fails the gate. Never relax a safety floor because a plan or task copied weaker language.

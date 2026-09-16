# Decision process for significant decisions

Written for this harness. Inspired by the advice process (Harmel-Law, martinfowler.com), Michael Nygard's
ADRs and Sonya Natanzon's work on architectural decision making (see ACKNOWLEDGEMENTS.md).

1. **Frame the problem.** Outcome needed, constraints, and what happens if nothing changes.
2. **Decide when to decide.** Identify the last responsible moment: which deadline or dependency forces the choice.
   If it is not now, record the question and the trigger to revisit it.
3. **Set weighted criteria before looking at options.** Derive them from the spec's non-functional requirements
   and the organization's principles (e.g. operability, security, cost, portability, team skills, time to market).
4. **Generate real options.** Two or three that differ in approach, plus "do nothing / defer".
5. **Seek advice.** Name the affected parties and experts; record their advice verbatim or summarized
   in the ADR, including dissent. Advice is not a veto.
6. **Analyze trade-offs.** Score each option per criterion with a short justification; highlight what you give up.
7. **Decide and record.** Accountable person, date, consequences (positive and negative), and follow-up actions.
8. **Define revisit triggers.** Measurable signals that would reopen the decision (cost, scale, incidents, new constraints).

Lifecycle: `Proposed -> Accepted | Rejected`, later `Deprecated` or `Superseded by NNNN`.
Never delete or rewrite an accepted ADR; supersede it.

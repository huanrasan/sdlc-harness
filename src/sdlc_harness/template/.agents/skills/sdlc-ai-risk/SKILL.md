---
name: sdlc-ai-risk
description: Assess and control risks of features that use LLMs, ML models or agents - use case and autonomy, regulatory classification, OWASP LLM and Agentic risks, evaluations with thresholds, human oversight and monitoring. Use in the design phase when the change declares the ai scope, or when adding prompts, models, RAG, tools or agents to a product.
license: MIT
metadata:
  harness-phase: design
---
# AI feature risk

Goal: `ai-risk.md` that makes the AI component's behaviour measurable and its failure modes controlled.

## Steps

1. Describe the use case, models and providers, and autonomy level (suggest, act with approval, act autonomously).
2. Classify risk with your organization's tiers and any applicable regulation (for example the EU AI Act categories);
   justify the classification. Higher autonomy or impact demands stronger oversight.
3. Enumerate risks with ids R-n using the OWASP Top 10 for LLM Applications and for Agentic Applications: prompt and
   goal injection, sensitive information disclosure, excessive agency and tool misuse, insecure output handling,
   supply chain of models and tools, memory/context poisoning, unbounded consumption, misinformation.
4. For each risk, a mitigation and how it is verified (test, eval, policy, monitoring).
5. Define evaluations before building: scenarios or datasets, metric, pass threshold. Record results before review;
   a result below threshold blocks release.
6. Human oversight: where people review, override or stop the system, and the escalation path.
7. Data: what prompts, context and outputs are stored, for how long, and whether providers may train on them.
8. Monitoring: quality, drift, abuse, latency and cost signals with incident triggers.

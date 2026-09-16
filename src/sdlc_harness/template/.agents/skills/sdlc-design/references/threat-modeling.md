# Lightweight threat modeling

Answer the four questions (Threat Modeling Manifesto): what are we working on, what can go wrong,
what are we going to do about it, did we do a good enough job.

1. **Model**: data-flow sketch with actors, processes, data stores, and trust boundaries
   (internet/VPC/on-prem, tenant, service-to-service, CI/CD, third parties, AI agents and their tools).
2. **Enumerate** with STRIDE per element crossing a boundary: Spoofing, Tampering, Repudiation,
   Information disclosure, Denial of service, Elevation of privilege.
3. **If the system includes LLMs or agents**, also review the OWASP Top 10 for LLM Applications and the
   OWASP Top 10 for Agentic Applications: prompt/goal injection, tool misuse, excessive agency and privilege,
   memory/context poisoning, supply chain of models/tools/MCP servers, unexpected code execution.
4. **Mitigate**: one owner and one verifiable control per accepted threat (test, policy, config, monitoring).
   Controls that can be tested must appear in `plan.md` and later in `verification.md`.
5. **Record residual risk** and who accepted it.

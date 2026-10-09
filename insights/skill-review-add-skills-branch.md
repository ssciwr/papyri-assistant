# Review of the papyrological skills (add-skills branch)

Date: 2026-10-09
Scope: the four skills in `backend/skills/` (question-interpretation, papyrological-research, report-writing, report-review), their reference files, and `backend/configs/default_langchain_agent.yaml`, compared with published best practices for agent skills and for LLM research agents in the humanities. Nothing was changed.

**Verdict:** the skills are too rigid, but length isn't the problem. The problem is that every question goes through the same full process, and too many rules dictate how the model should reason rather than what the result must satisfy.

## What the best-practice guidance says

**Anthropic's skill-authoring guide:**

- **Match the strictness to the risk.** Where there's only one safe way forward, give exact steps. Where many approaches work, give general direction and let the model choose.
- **Templates:** use strict templates for formats that software or other agents consume. For output a human reads, give a default the model can adapt.
- **Only include what the model can't already know or work out.** Keep each skill file under about 500 lines and link to reference files one level deep.
- **Measure first:** run representative questions without the skill, then write just enough instructions to fix the failures you saw.

**Humanities research specifically:**

- The main risk is invented or unsupported evidence. HistBench and the citation-integrity work both report this as the dominant failure.
- So the strictness belongs at grounding and source verification, not at how the research is organised.
- The closest comparable system, SPIRE, fixes the evidence handling (every claim tied to a stable evidence id). It leaves breaking the question into sub-questions, interpreting and writing to the model, and caps review at 2 rounds.

## Where the skills are too tight

1. **Questions get either a single lookup or the full process.** Every question that isn't a single lookup goes through interpretation file → research record → report → up to 5 review rounds ([report-review/SKILL.md:32](../backend/skills/report-review/SKILL.md#L32)). A medium question like "which papyri from Karanis mention camels?" gets the same treatment as the witchcraft question. A middle tier, with depth scaled to the question, is missing.

2. **Acceptance criteria say "every" where it gets expensive.** Examples:
   - every document goes through the 7-point source criticism;
   - every claim needs a falsification search;
   - every candidate needs a recorded decision;
   - the review must list alternatives for every main-question claim.

   For 47 libelli that's hundreds of required entries. The review skill already has the better pattern: check the claims the answer depends on and trust the rest to the recorded methods ([report-review/SKILL.md:70](../backend/skills/report-review/SKILL.md#L70)). The research skill doesn't apply that idea.

3. **Interpretation isn't allowed to use any knowledge** ([question-interpretation/SKILL.md:38](../backend/skills/question-interpretation/SKILL.md#L38)): no database queries and no background knowledge. As a result, "when was the Decian persecution?" becomes a sub-question to research. The research skill already allows a looser version: knowledge "can suggest where to search". A middle ground would let interpretation state such knowledge as a labelled assumption that a sub-question then tests, plus a quick look at the database's vocabulary.

4. **The steps are fixed, not the outcomes.** The 11 research steps in a set order, and the required four-axes table with primary/auxiliary/not-involved roles for every question ([question-interpretation/SKILL.md:53](../backend/skills/question-interpretation/SKILL.md#L53)), tell the model how to think. The goals (grounded, triangulated, counter-evidence sought, limits stated) are what matter; the axes would work better as an optional aid.

5. **The report is a fixed template.** The report structure ([report-writing/SKILL.md:37](../backend/skills/report-writing/SKILL.md#L37)) is fixed even though a person in a chat reads it. A simple answer still comes out as long as the 2,800-word example. The research record is passed between agents, so a strict template is justified there; the report should be a default the model adapts.

6. **All the examples come from one question.** The research record and both report examples all answer the Decian libelli count. The model is likely to treat every question as a counting job. The witchcraft example only covers interpretation.

7. **Repetition and prohibitions.**
   - The source-criticism list, the claim definitions and the criteria are repeated across skills.
   - Interpretation and review link into other skills' files, two levels deep.
   - Many instructions are phrased as "do not…", which tends to draw attention to the forbidden behaviour; stating what to do instead works better.

## Where the strictness is right (keep it)

- **Grounding and no invented sources:** this is the main humanities failure mode.
- **Verifying every cited source with `query_sql`.**
- **[database.md](../backend/skills/papyrological-research/references/database.md):** this is the most valuable part. It contains exactly what the model can't know: count `DISTINCT tm_id`, editor-supplied text hidden in `text`, German keywords, `dupl` editions, date ranges. Building links and source entries always works the same way, so it could even become a tool instead of instructions.
- **Triangulation and searching for counter-evidence as ideas.** Only the "every" in the criteria is the problem, not the ideas.

## Caveat: the model

`.env` runs **Qwen3.6-35B-A3B**, which has only about 3B active parameters. Anthropic's guide notes that smaller models need more guidance, not less, so stripping everything out is the wrong move. But the full process loads about 15k words, roughly 20k+ tokens (more with Greek text). Holding 11 steps and about 12 "every" criteria in view is where a small model is likely to rush and claim it met the criteria. That's a risk to expect, not something that was measured: the branch has no evaluations or traces.

## Suggested direction

1. **Measure first.** Run 3–5 representative questions (a lookup, a medium question, the libelli count, witchcraft) with and without the skills, and see where it actually fails.
2. **Turn rules into outcomes.** Keep the grounding rules and the database pitfalls strict. Turn the step lists and table requirements into goals plus a default approach.
3. **Scale the effort.** Add a middle tier, focus the "every" requirements on the documents and claims the answer depends on, and cut review to 2 rounds.
4. **Add examples of other question types.**

## Sources

- [Anthropic – Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [SPIRE: multi-agent framework for evidence-grounded humanities scholarship](https://arxiv.org/html/2605.30947)
- [HistBench (arXiv 2505.20246)](https://arxiv.org/pdf/2505.20246)
- [Benchmarking as Source Criticism (JOHD)](https://openhumanitiesdata.metajnl.com/articles/10.5334/johd.489)
- [Generative AI as a historical source: citation integrity](https://acnsci.org/journal/index.php/cte/article/view/1438)
- [Made by Many – What makes a good agentic skill](https://agentic.madebymany.com/positions/agentic-skills.md)

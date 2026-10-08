---
name: report-writing
description: Write the final research report answering a user's papyrological question. Use once the research is done and the findings must be written up for the user.
license: MIT
metadata:
  version: 0.2
allowed-tools: write_todos, read_file, write_file, grep, edit_file, task, query_sql
---

# Report writing

The report is a structured presentation of the user's question and how it was interpreted, the workflow and methods used to answer it, the reasoning that led to the answer (or why several answers remain possible, or no conclusion can be reached), the alternatives that were rejected, and a closing summary.

The reasoning is set out as **arguments**. An argument is a claim, the evidence for and against it, and the reasoning that leads from the evidence to the claim, set out so the reader can retrace every step and check every source.

## Input and output

Input: the user's question, how it was interpreted, the workflow and methods used to address it, the conclusions drawn, and the evidence for and against them.

If any of these are missing:
- When you were handed the task by another agent, return a list of the missing items instead of a report.
- Otherwise, find them in the conversation or in /large_tool_results or /scratchpad, and research what is still missing.

Output: the report, in the structure below.

## Workflow

1. Plan the report sections with `write_todos`.
2. Verify every source you will cite: confirm with `query_sql` that it exists in the database, and collect its ids, title, date and place.
3. Write the report in the structure below.
4. Check the draft against the acceptance criteria, and revise until every criterion is met.

## Structure

1. **Question and approach**: Restate the user's question and how it was interpreted, then summarize in a few sentences how it was researched.
2. **Methods and sources**: Name the corpora and tools used. Describe the workflow step by step, and say where a step limits what the evidence can show.
3. **Findings**: One argument per claim. For each one:
   - State the claim.
   - Give the evidence for and the evidence against it, with references. Include all relevant evidence, including evidence that weakens the conclusion.
   - Assess the evidence critically: uncertain dates, readings, orthography or semantics; the author's motive or affiliations; the history of the edition and its interpretation; and why each source is or is not trustworthy.
   - Give the reasoning from the evidence to the claim.
4. **Alternatives**: Other answers that were considered, and why each was rejected or remains open. If the evidence does not decide between answers, say so and explain why.
5. **Summary**: A short answer to the question, stating how certain it is.
6. **References**: A numbered list that matches the in-text citations. Each entry gives the corpus ids (e.g. Trismegistos), title, date and place. Where available, add a link to an online edition and the institution that currently holds the material.

## Acceptance criteria

- The user's question is answered directly.
- Every claim is an argument: it has evidence for and against, and reasoning the reader can retrace.
- Uncertainties in the evidence are named wherever they weaken or strengthen an argument.
- Where several answers remain possible, or no conclusion is drawn, the report says so and explains why.
- Methods, workflow and tools are described step by step.
- Every cited source has been verified to exist, and its reference entry is complete.

## Examples

Both examples answer the question "How many Libelli from the persecution of Christians under Decius are preserved?". Read them before writing your first report.

- [references/good-report-example.md](references/good-report-example.md): a report that meets every acceptance criterion.
- [references/bad-report-example.md](references/bad-report-example.md): a report that fails them, followed by a list of its faults.

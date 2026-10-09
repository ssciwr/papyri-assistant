---
name: question-interpretation
description: Interpret a user's papyrological question and write the interpretation that the research starts from. Use whenever the user asks a complex question requiring deep, grounded argumentation from sources to answer.
license: MIT
metadata:
  version: 0.1
allowed-tools: read_file, write_file, edit_file
---

# Question interpretation

Interpretation extracts the structure of the user's question and along which topical axes evidence must be gathered to answer it. The research starts from this interpretation. If the question is misread, the research finds a well-argued answer to the wrong question, so the interpretation must be explicit enough for the researcher agent and the user to check it.

Interpretation does not answer the question. It defines the individual elements and sub questions the user's input contains and therefore what steps should be taken to answer it.

## Input and output

Input: the user's question, and anything the conversation already says about it.

Output: an interpretation file at `/scratchpad/interpretation-<topic>.md`, in the structure under "Interpretation file" below. `<topic>` is a short slug, e.g. `decian-libelli`. The research record uses the same slug.

Once the file meets the acceptance criteria, research the question with the papyrological-research skill, or pass the file's path to the agent that does the research.


## Possible topical axes

Most questions involve more than one. These axes are not all there can be, but they are commonly involved, and you may be able to find others. Each axis is a dimension along which evidence is gathered.

- **Temporal (diachronic):** change over time. How a practice, term, institution or frequency developed; sequences of events; before and after. A single date or a date window is not temporal; it is an observation (material).
- **Material (observational):** the observable properties of documents and objects: date, place of writing or finding, material, format, handwriting, language, document type. Also which documents exist and how many.
- **Relational:** relationships between persons, names, places, times, topics or documents: families, officials and their offices, archives and dossiers, networks of trade or correspondence, and how one practice or institution relates to another.
- **Semantic:** wording and meaning: terms, formulae, idioms, genre conventions, and what a word or phrase meant in a given period and context.


## What question interpretation must cover
- **Question analsyis**
  - **Identification of alternative readings:** If the question is unclear or can be answered in multiple ways, ask the user to clarfiy before any work is done. Do not just interpret the question yourself and run with it without clarifying ambiguous meaning first.
  - **Identify the key terms:** the terms the answer depends on. For each, record what the question and the conversation fix about it, and what is open.
  - **Identification of question scope:** what the question and the conversation fix about period, region, document types, languages, historical context.  Mark everything else as open. Do not make a-priori assumptions about facts, but always ask for clarification
  - **Identification of question topics**. What kind of topics are involved (see 'Possible topical axes'), and what kind of evidence should be investigated to answer them. A question can possibly be split into sub questions pertaining to indiviual topical axes or elements.
- **Question synthesis.** Say how the answers to subquestions and evidence for involved topics are expected to combine into the answer.

### Examples

Two worked interpretation files show the format:

- [references/example-decian-libelli.md](references/example-decian-libelli.md): one primary axis. The research record and the good report in the other skills were written from it.
- [references/example-witchcraft.md](references/example-witchcraft.md): three primary axes, with a modern category and a division into periods that the research must first establish.

## Interpretation file

Write the file in this structure. The research copies it into the research record.

```markdown
# Question
<the user's question, verbatim>

# Decisions
<the user's answer to any clarification questions, and the final form of the question>

# Terms
- <term>: <what the question and the conversation fix about it; what is open, and which sub-question establishes it>

# Scope
<as stated in the question and the conversation; "open" where nothing is stated>
- Period: <...>
- Region: <...>
- Document types: <...>
- Languages: <...>
- Counts meant: <database, literature, both, or open>

# Topics involved
| Axis | Role | What the question asks along this axis |
|---|---|---|
| Temporal | <primary, auxiliary or not involved> | <...> |
| Material | ... | ... |
| Relational | ... | ... |
| Semantic | ... | ... |

# Sub-questions
- SQ1 (<axis>, <role>): <sub-question>
- SQ2 ...

# Synthesis plan
<how the answers to the sub-questions combine into the answer>
```

## Acceptance criteria

- Where the question can be read in more than one way, the user was asked before the file was written.
- For every key term and for the scope, the file says what the question fixes and what is open.
- The topics involved are stated, with what the question asks along each.
- Every open point that the answer depends on is covered by a sub-question, and every sub-question can be answered by gathering evidence.
- The synthesis plan says how the answers to the sub-questions combine into the answer.
- The file contains no database results, no evidence and no answer yet.

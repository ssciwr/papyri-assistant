---
name: question-interpretation
description: Interpret a user's papyrological question and write the interpretation that the research starts from. Use first for every question that must be answered from the papyri, before any research.
license: MIT
metadata:
  version: 0.1
allowed-tools: read_file, write_file, edit_file, query_sql
---

# Question interpretation

Interpretation decides what the user's question asks, and along which axes evidence must be gathered to answer it. The research starts from the interpretation. If the question is misread, the research finds a well-argued answer to the wrong question, so the interpretation must be explicit enough for the researcher and the user to check it.

Interpretation does not answer the question. It defines what has to be found and how the findings are expected to fit together. Gathering and weighing evidence is the research's task and is not part of this workflow.

## Input and output

Input: the user's question, and anything the conversation already says about it.

Output:
- For a simple retrieval question: the answer itself (see "Simple retrieval questions").
- For any other question: an interpretation file at `/scratchpad/interpretation-<topic>.md`, in the structure under "Interpretation file" below. `<topic>` is a short slug, e.g. `decian-libelli`. The research record uses the same slug.

Once the file meets the acceptance criteria, research the question with the papyrological-research skill, or pass the file's path to the agent that does the research.

## Workflow

1. **Triage.** Decide whether the question is a simple retrieval question. If it is, answer it and stop.
2. **Restate the question** in precise terms, so that it can be answered by gathering evidence. Add nothing that the question and the conversation do not contain.
3. **Identify the key terms:** the terms the answer depends on. For each, record what the question and the conversation fix about it, and what is open. Do not define a term yourself. What a term such as "libellus" or "witchcraft" covers in the sources is something the research establishes from evidence; where the answer depends on it, make it a sub-question.
4. **Record the scope as stated:** what the question and the conversation fix about period, region, document types, languages, and which counts are meant (the documents in the database, the published documents, or both). Mark everything else as open. Do not fill the gaps yourself.
5. **List the readings.** Where the question can be read in more than one way, list the readings, choose one and say why. If the readings would lead to very different research, and the conversation does not settle which one is meant, ask the user before you write the file. Asking costs one message; researching the wrong reading costs the whole research.
6. **Classify the question along the four axes** (see "The four axes"). Give each axis a role: primary, auxiliary or not involved, and say in one sentence what the question asks along it.
7. **Split the question into sub-questions.** Each primary axis needs at least one sub-question. An auxiliary axis needs one only when its evidence must be gathered separately. Each sub-question names its axis and role, and must be answerable by gathering evidence.
8. **Plan the synthesis.** Say how the answers to the sub-questions are expected to combine into the answer, and state the expected form of the answer in one line.
9. **Write the file**, check it against the acceptance criteria, and hand it over to the research.

Use only the question and what the conversation says about it. Do not add definitions, dates, periods, facts or expectations from your own knowledge, and do not query the database. Anything added here is an assumption the research has not tested, and it would steer the research toward confirming it. Where the answer needs such knowledge, make it a sub-question, so that the research establishes it from evidence.

## Simple retrieval questions

A question is a simple retrieval question when one lookup answers it and no evidence has to be weighed. Examples:

- What is the Trismegistos number of P.Wisc. II 87?
- When and where was P.Oxy. IV 658 written?
- Show me the text of P.Mich. III 157.
- Is P.Ryl. II 112A in the database?

It needs no interpretation. Answer it directly with a single lookup (`query_sql`), and cite the source with its Trismegistos id, edition and link (see "Building source entries" in [../papyrological-research/references/database.md](../papyrological-research/references/database.md)). Write no interpretation file, and do not start a research.

If the lookup shows that the answer is not simple, for example because the papyrus has conflicting dates, several records or a disputed reading, give what the lookup shows, name the complication, and offer to research it.

## The four axes

Each axis is a dimension along which evidence is gathered. Most questions involve more than one. Where several axes are primary, the answer must bring their evidence together, and that is where the synthesis happens.

- **Temporal (diachronic):** change over time. How a practice, term, institution or frequency developed; sequences of events; before and after. A single date or a date window is not temporal; it is an observation (material).
- **Material (observational):** the observable properties of documents and objects: date, place of writing or finding, material, format, handwriting, language, document type. Also which documents exist and how many.
- **Relational:** relationships between persons, names, places, times, topics or documents: families, officials and their offices, archives and dossiers, networks of trade or correspondence, and how one practice or institution relates to another.
- **Semantic:** wording and meaning: terms, formulae, idioms, genre conventions, and what a word or phrase meant in a given period and context.

Each axis has one of three roles:

- **Primary:** the answer is about it. The answer is incomplete without it.
- **Auxiliary:** needed to reach the answer, as a means of finding, dating or identifying evidence, or as context, but not itself part of the answer.
- **Not involved.**

**Edition history and research history are not an axis.** They concern the evidence, not antiquity, and the research checks them for every piece of evidence it uses. Only when the question is itself about them, as in "How has the reading of line 5 of P.Oxy. I 119 changed?", are they its subject. Then classify the question along the axes as usual, with the editions and studies as the documents: here temporal (how the reading changed) and semantic (what the readings say).

### Examples

| Question | Primary | Auxiliary | Sub-questions |
|---|---|---|---|
| How many Libelli from the persecution of Christians under Decius are preserved? | material | semantic | What is a libellus of this persecution, and how can one be recognized? Which database documents are such libelli, and how many? How many does the literature count? |
| What was the role of fishing in the Egyptian economy of the 1st century AD? | relational, material | semantic | Which documents attest fishing, and from where and when? Who fished, leased, taxed and traded fish, and how were they connected? What do the terms for fishermen, fishing rights and fish taxes mean? |
| What can we learn about the 2nd Syrian War from the papyri? | temporal, relational | material, semantic | When did the war take place, and which documents refer to it or can be linked to it? What sequence of events and effects do they show? Which persons, places and institutions were involved? |
| How is witchcraft attested in the papyri, and how does it relate to religion in pre-Christian and Christian times? | semantic, relational, temporal | material | Which practices and documents correspond to "witchcraft"? Where does the boundary between the two periods lie? What terms and formulae do the texts use? Which powers do they invoke, and how do these relate to the religious practice of their time? How does this change between the periods? |

Two worked interpretation files show the format:

- [references/example-decian-libelli.md](references/example-decian-libelli.md): one primary axis. The research record and the good report in the other skills were written from it.
- [references/example-witchcraft.md](references/example-witchcraft.md): three primary axes, with a modern category and a division into periods that the research must first establish.

## Interpretation file

Write the file in this structure. The research copies it into the research record.

```markdown
# Interpretation: <short title>

## Question
<the user's question, verbatim>

## Restatement
<the question in precise terms>

## Terms
- <term>: <what the question and the conversation fix about it; what is open, and which sub-question establishes it>

## Scope
<as stated in the question and the conversation; "open" where nothing is stated>
- Period: <...>
- Region: <...>
- Document types: <...>
- Languages: <...>
- Counts meant: <database, literature, both, or open>

## Readings
- <reading>: <chosen, or not chosen, and why>
- <questions asked to the user, and the answers>

## Axes
| Axis | Role | What the question asks along this axis |
|---|---|---|
| Temporal | <primary, auxiliary or not involved> | <...> |
| Material | ... | ... |
| Relational | ... | ... |
| Semantic | ... | ... |

## Sub-questions
- SQ1 (<axis>, <role>): <sub-question>
- SQ2 ...

## Synthesis plan
<how the answers to the sub-questions combine into the answer>

## Expected answer
<one line: the form of the answer>
```

## Acceptance criteria

- Simple retrieval questions are answered directly, without a file.
- The question is restated without additions. For every key term and for the scope, the file says what the question fixes and what is open.
- Every reading is listed, and the choice between them is justified. Where the choice would change the research substantially and the conversation does not settle it, the user was asked.
- Every axis has a role and a sentence saying what the question asks along it.
- Every primary axis is covered by at least one sub-question. Every sub-question names its axis and role and can be answered by gathering evidence.
- The synthesis plan and the expected form of the answer are stated.
- Every open point that the answer depends on is covered by a sub-question.
- The file contains nothing that is not in the question or the conversation: no definitions, facts or expectations from your own knowledge, no database results, no evidence and no answer.

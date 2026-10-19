---
name: reasoning-about-uncertainty
description: Assess uncertainties in papyrological records and explain how they affect an interpretation or answer. Use when dates, places, readings, meanings or attributions materially affect a conclusion.
license: MIT
metadata:
  version: 0.2
allowed-tools: write_todos, read_file, write_file, edit_file, grep
---

# Reasoning about uncertainty

Use uncertainty to calibrate an answer, not to prevent one. Explain what the records support, what requires interpretation, and which doubts actually change the conclusion. A brief qualification is often enough; a decisive damaged reading may need closer analysis.

Prefer plain-language assessments with reasons to numerical confidence without a defensible basis. Do not require a grade, an axis label or a full catalogue of alternatives for every statement.

## Working approach

1. **Identify the conclusion at stake.** Which date, place, reading, meaning or attribution does it depend on?
2. **Inspect the relevant evidence.** Use the supplied records, read as the database-content-interpretation skill describes. Consult fuller fields or passages where the derived value hides a distinction that matters; there is no need to inspect every field in every document.
3. **Consider plausible alternatives.** Ask whether another reading would change the answer. Develop competing branches only when they are credible and consequential.
4. **State the effect.** Give the best-supported interpretation and its basis, or explain why the evidence does not decide. Suggest a further check only when it could materially improve the answer.

Work directly in the answer or existing research record. This skill does not require a separate file or a new research cycle. When missing evidence matters, use the [papyrological-research skill](../papyrological-research/SKILL.md) to obtain it, or give a qualified conclusion with the limitation visible.

## Observation and interpretation

Distinguish **what the record reports**, **how it was established**, and **what you infer from it**. A findspot, a measurement or clearly legible wording is different from a proposed provenance, a restored word or an explanation of the writer's intentions. But observation and interpretation are not opposites: reading letters, converting dates and reporting measurements all involve methods and assumptions.

The records usually transmit an editor's assessment, not your own inspection of the object. Attribute that assessment accurately without treating mediation as a reason to distrust it automatically. Interpretation can be secure; a preserved statement can still be misleading about what happened.

## Describing confidence

Use these terms when helpful, or an equivalent plain-language assessment. They are a vocabulary, not a mandatory scoring system.

| Term | Typical basis |
|---|---|
| attested | The document or record explicitly reports it. Specify whether this means preserved wording, an editorial reading or metadata; attestation of a statement does not establish its truth. |
| secure inference | The evidence strongly constrains the conclusion, with no plausible alternative that materially changes it. A well-supported date conversion or formulaic restoration may qualify. |
| probable | Evidence favors this interpretation over credible alternatives. |
| possible | Compatible with the evidence, but not clearly established or favored. |
| conjectural | A proposed explanation with limited support, relying substantially on assumptions, analogy or background knowledge. |

"Attested" describes the kind of support, not necessarily a higher confidence than "secure inference". A claim may combine preserved text and a secure restoration. Judge the support as a whole rather than assigning a grade mechanically from one marker or from the number of inferential steps.

For a conclusion the answer depends on, explain the basis of confidence briefly. Identify temporal, material, relational or semantic distinctions only when they help locate the uncertainty. Avoid claims of scholarly consensus unless you have support for them.

## Uncertainty and the answer

- **Localize the doubt.** A damaged name need not weaken a secure date or the identification of a document type.
- **Check sensitivity.** If all plausible readings lead to the same answer, say so briefly and move on. If they change it, explain the relevant branches: "if A, then …; if B, then …".
- **Assess the combined support.** An uncertain premise limits a conclusion when that premise is essential. Independent evidence may sustain the conclusion despite it; do not mechanically give the whole answer the weakest grade anywhere in the record.
- **Separate precision from confidence.** A broad date range can be securely established, while a precise-looking year can be doubtful. Preserve ranges rather than inventing exact dates.
- **Allow useful partial answers.** State what can be concluded even when a narrower claim remains unresolved. Missing information is a limit, not evidence against the claim.

Counts and absences describe the searched corpus, not automatically ancient prevalence or the total preserved. When uncertain inclusions affect a count, distinguish secure cases from possible ones or give a supported range. Explain the relevant coverage or retrieval limit rather than attaching a general disclaimer to every figure.

## Meaning and background knowledge

Interpret wording in its document context. Useful support includes comparable database passages, available editions or commentaries, and your linguistic and historical knowledge. These are not a rigid hierarchy: a superficial verbal parallel may be less useful than a well-supported contextual explanation.

- Cite retrieved parallels when they carry the interpretation, and explain why their date, genre or context makes them comparable. Do not demand a new parallel search for ordinary wording whose meaning is not at issue.
- Attribute scholarly interpretations to sources you have actually consulted. A remembered reference is a lead, not verified scholarship; do not invent quotations, bibliographic details or consensus.
- Use background knowledge to explain and propose meanings. Label it where it supplies a substantive interpretive premise, and distinguish it from what the retrieved record establishes. Routine language understanding does not need a disclaimer for every word.

Recurring administrative formulae can strongly constrain restorations and meanings, but formulaic wording does not by itself establish what happened. Religious or magical language may echo another tradition; distinguish a plausible textual parallel from evidence of borrowing, authorial intention or a user's beliefs when that distinction matters. Where a modern category such as magic, medicine or religion affects selection or interpretation, explain the working definition and any consequential borderline cases.

## Examples of proportionate assessment

- A name is restored, but the preserved wording establishes a receipt: note the name's uncertainty only if identity matters to the question.
- Two proposed dates both fall in the period under study: preserve both in the source entry, but do not treat the period attribution as unresolved merely because the exact year is.
- An institutional identification depends on a supplied title: inspect the passage and the basis of the restoration, then state whether the identification is secure, probable or only possible. Other explicit evidence may resolve it.

## Reading the record

To read uncertainty markers and notation in retrieved data, such as editorial markup in the XML, qualifiers in date texts, date certainty and precision, and place relations, use the database-content-interpretation skill ([../database-content-interpretation/SKILL.md](../database-content-interpretation/SKILL.md)).

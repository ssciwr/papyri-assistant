# Example research record

This record starts from the example interpretation file `example-decian-libelli.md` in the question-interpretation skill, and the good report in the report-writing skill was written from it. It meets every acceptance criterion. Read it for how a record is built: the open points of the interpretation established from evidence first, steps recorded with their sub-question and exact queries, every candidate decided, a search for counter-evidence that changes the answer, and a sub-question that the database cannot answer, recorded as a gap instead of being filled from memory.

Its counts come from the database as it was on 8 October 2026. If a user asks this question, do the research again: the database may have changed.

---

# Research record: Decian libelli

## Question
How many Libelli from the persecution of Christians under Decius are preserved?

## Interpretation
Interpretation file: /scratchpad/interpretation-decian-libelli.md

- Restatement: How many libelli connected with the persecution of Christians under the emperor Decius are preserved?
- Terms: what kind of document a libellus is, how one is recognized, and when the persecution took place are open (SQ1). "Preserved": see Readings.
- Scope: period of the persecution (open, SQ1); region, languages and counts open; document type: libelli.
- Readings: "preserved" in the database and in all published papyri, both kept (SQ2, SQ3). "Libelli from the persecution of Christians" read as libelli issued in the course of the persecution; whether they can be read as libelli issued to Christians is tested by SQ4.
- Axes: material primary; semantic auxiliary; relational auxiliary (reading b); temporal not involved.

### Sub-questions
- SQ1 (semantic, auxiliary): What kind of document is a libellus of the Decian persecution, when were such libelli issued, and by which features can one be recognized?
- SQ2 (material, primary): Which documents in the database are such libelli, and how many distinct papyri are they?
- SQ3 (material, primary): How many such libelli does the scholarly literature count, and how does that compare with SQ2?
- SQ4 (relational, auxiliary): Do the libelli show whether their holders were Christians?

### Revisions
- None. The certificates found only by the search for counter-evidence (Step 5) are tagged `Opfer` with `Bescheinigung` or `Bestätigung` instead of `Libellus`. That changed the search vocabulary, not the interpretation.

## Steps

### Step 1 (SQ1): Read the documents that their editors call Decian libelli
- Tool: `query_sql`
- Query: `SELECT DISTINCT p.tm_id, p.title FROM papyri p JOIN transcriptions t USING (tm_id) WHERE t.type = 'transcription' AND p.title ILIKE '%libell%' AND (p.title ILIKE '%deci%' OR p.title ILIKE '%dezi%')`, then the dates and texts of the results.
- Result: 14 documents, all dated 250 CE. The complete texts share one form: an address to the commission for the sacrifices (τοῖς ἐπὶ τῶν θυσιῶν ᾑρημένοις), a declaration that the declarant has always sacrificed to the gods, a statement that the declarant has now sacrificed, poured a libation and tasted the offerings in the commission's presence (P.Mich. III 157: ἐθύσαμεν καὶ ἐσπείσαμεν καὶ τῶν ἱερείων ἐγευσάμεθα), a request for the commission's signature (ἀξιοῦμεν ὑμᾶς ὑποσημειώσασθαι), the officials' confirmation (εἴδαμεν ὑμᾶς θυσιάζοντας) and a date in the first year of Decius (ἔτους α ... Τραιανοῦ Δεκίου, Παῦνι κγ).
- Limitation: the starting set rests on the editors' titles, so a libellus of unusual form would not shape the pattern. Steps 3 and 5 search beyond these titles.

### Step 2 (SQ2): Keyword search
- Tool: `query_sql`
- Query: `SELECT DISTINCT tm_id FROM keywords WHERE keyword ILIKE 'libell%'`
- Result: 29 documents.
- Limitation: the word may name other kinds of document, so the search can return false positives. It misses certificates not tagged `Libellus`.

### Step 3 (SQ2): Formula search
- Tool: `query_sql`
- Query:
  ```sql
  WITH t AS (SELECT tm_id, regexp_replace(text, '\s+', '', 'g') AS s
             FROM transcriptions WHERE type = 'transcription')
  SELECT DISTINCT tm_id FROM t
  WHERE ((s LIKE '%ἐπὶτῶνθυσιῶν%')::int
       + (s LIKE '%σπείσ%' OR s LIKE '%σπεισ%')::int
       + (s LIKE '%ἐγευσ%')::int
       + (s LIKE '%ἔθυσα%' OR s LIKE '%ἐθύσαμεν%' OR s LIKE '%θύων%' OR s LIKE '%θύοντ%')::int) >= 2
  ```
  The four elements are those found in Step 1: the address to the commission, the libation, the tasting of the offering and the sacrifice. The stems cover singular and plural forms (ἔσπεισα / ἐσπείσαμεν, ἐγευσάμην / ἐγευσάμεθα). A first run with singular forms only found 28 documents and missed plural certificates such as P.Mich. III 157.
- Result: 33 documents, all dated 250 CE.
- Limitation: misses fragments that preserve fewer than two elements, and texts whose wording differs. `text` includes editorial supplements, so a match can rest on restored text.

### Step 4 (SQ2): Combination and check
- Tool: `query_sql` (dates, places, titles and editions of the 45 documents found by Step 2 or 3; 17 were found by both).
- Result: 35 certificates, 10 false positives (see Candidates).
- Limitation: readings were not checked against photographs.

### Step 5 (SQ2): Counter-evidence: certificates that both routes missed
- Tool: `query_sql`
- Query: documents dated to overlap 249–251 (`not_before_year <= 251 AND not_after_year >= 249`) whose title matches `libell`, `sacrific` or `opfer`, or whose keyword matches `libell%` or `opfer%`, or whose text contains at least one formula element; minus the 35 from Step 4.
- Result: 12 more Decian certificates (P.Hamb. I 61a and 61b; SB I 4437, 4438, 4441, 4442, 4443, 4446, 4447, 4449, 4453, 4454). Each is a short fragment, often only the date formula with Decius's titulature. All are tagged `Opfer` with `Bescheinigung` or `Bestätigung`, not `Libellus`. The other hits were literary texts, a lease, a letter and a list of articles for a sacrifice (P.Oxy. XXXVI 2797), none of them certificates.
- Limitation: a certificate with no date in 249–251, no matching title, keyword or formula element is still missed.

### Step 6 (SQ2): Third route: keyword `Opfer`
- Tool: `query_sql`
- Query: `SELECT DISTINCT k.tm_id FROM keywords k JOIN orig_dates d USING (tm_id) WHERE k.keyword = 'Opfer' AND d.not_before_year <= 251 AND d.not_after_year >= 249`
- Result: 38 documents: 37 of the 47 certificates and P.Oxy. XXXVI 2797.
- Limitation: depends on the date range, so a certificate dated only to the 3rd century is missed (e.g. P.Oxy. XLI 2990).

### Step 7 (SQ2): Duplicate check
- Tool: `query_sql` on `papyri.ddb_hybrid_id` and `transcriptions.text` for the two `dupl` records.
- Result: SB I 4440dupl (TM 13941) and SB I 5943dupl (TM 14001) have the same text: the certificate of Aurelia Charis of Theadelphia, 16 June 250. No record without `dupl` exists for either.
- Limitation: other duplicates under different ids were checked only by Trismegistos id.

### Step 8 (SQ4): Statements about the holders' religion
- Tool: `query_sql`
- Query: the texts of the 47 certificates, searched for `χριστ` and `χρηστιαν`, and for the declaration of sacrifice to the gods (`θεοῖς`, whitespace removed); then the text of Chrest.Wilck. 125.
- Result: no certificate mentions Christians. 32 texts contain the declaration of sacrifice to the gods. In Chrest.Wilck. 125 the declarant is Aurelia Ammonous, priestess of Petesouchos (ἱερείας Πετεσούχου θεοῦ μεγάλου).
- Limitation: fragments may have lost a statement about the holder.

## Candidates

Found by: F = formula (Step 3), K = keyword `libell%` (Step 2), C = counter-evidence (Step 5). Rows that group several documents are shortened for this example. A real record has one row per document.

| TM | Edition | Date | Place | Found by | Decision | Reason |
|---|---|---|---|---|---|---|
| 9033 | Chrest.Wilck. 124 | 26 June 250 | Alexandrou Nesos, Arsinoites | F, K | include | full formula, Decian date |
| 11954 | P.Meyer 15 | 27 June 250 | Theadelphia | F, K | include | full formula, Decian date |
| 11955 | P.Meyer 16 | 250 | Theadelphia | F, K | include | formula |
| 11956 | P.Meyer 17 | 250 | Theadelphia | F, K | include | formula |
| 11977 | P.Mich. III 157 | 17 June 250 | Theadelphia | F, K | include | formula in the plural |
| 11978 | P.Mich. III 158 | 21 June 250 | Theadelphia | F, K | include | formula |
| 12907–12909 | P.Ryl. II 112A–C | 20 June, 250, 22 June 250 | Theadelphia | F | include | formula; untagged |
| 13730 | P.Wisc. II 87 | 4 June 250 | Narmuthis | F, K | include | formula; earliest firm date |
| 13780 | PSI V 453 | 14–23 June 250 | Theadelphia | F, K | include | formula |
| 13792 | PSI VII 778 | 26 June 250 | Arsinoites (?) | K | include, less certain | fragment; classed by the editor's title |
| 13936, 13937, 13940, 13945, 13946, 13949, 13951–13953, 13956 | SB I 4435, 4436, 4439, 4444, 4445, 4448, 4450–4452, 4455 | 26 May–14 July 250 | Theadelphia | F | include | formula; tagged `Opfer`, not `Libellus` |
| 13941 | SB I 4440dupl | 16 June 250 | Theadelphia | F | include, possible duplicate | same text as TM 14001 (Step 7) |
| 14001 | SB I 5943dupl | 16 June 250 | Theadelphia | F | include, possible duplicate | same text as TM 13941 (Step 7) |
| 14005, 14006 | SB III 6827, 6828 | 21 June 250, 250 | Theadelphia | F, K | include | formula |
| 14104 | SB VI 9084 | 17 June 250 | Theadelphia (?) | F, K | include | formula |
| 15151 | Chrest.Wilck. 125 | 250 | Ptolemais Euergetis | F, K | include | formula; holder is a priestess of Petesouchos |
| 17912 | P.Oxy. LVIII 3929 | 25 June–24 July 250 | Thosbis, Oxyrhynchites | F | include | formula |
| 20403 | P.Oxy. IV 658 | 14 June 250 | Oxyrhynchos | F, K | include | formula |
| 21866 | P.Oxy. XII 1464 | 27 June 250 | Oxyrhynchos | F, K | include | formula |
| 30379 | P.Oxy. XLI 2990 | 3rd century | Oxyrhynchos | K | include, less certain | only the witnesses' signatures survive (εἶδον ὑμᾶς θύοντας καὶ γευομένους); date not firm |
| 44425 | P.Lips. II 152 | 16 June 250 | Euhemeria | F, K | include | formula |
| 56431 | P.Ryl. I 12 | 14 June 250 | Ptolemais Euergetis | F, K | include | formula |
| 699682 | Tyche 30 no. 16 | ca. 4 June–14 July 250 | Theadelphia | F, K | include | formula |
| 11404, 11405 | P.Hamb. I 61a, 61b | 13 June, 21 June 250 | Theadelphia | C | include, less certain | fragments with Decian date; tagged `Opfer`, `Bestätigung`, `Christenverfolgung` |
| 13938, 13939, 13942–13944, 13947, 13948, 13950, 13954, 13955 | SB I 4437, 4438, 4441–4443, 4446, 4447, 4449, 4453, 4454 | 14–23 June 250, 250 | Theadelphia | C | include, less certain | fragments with Decian date or end of formula; tagged `Opfer`, `Bescheinigung` |
| 20620 | P.Oxy. III 484 | 28 Jan. 138 | Oxyrhynchites | K | exclude | petition; before Decius |
| 18374 | SB XVIII 13769 | 345–352 (?) | Hermopolites | K | exclude | petition about land |
| 22012–22015 | P.Oxy. XVI 1876–1879 | 434–488 | Oxyrhynchos, Herakleopolis | K | exclude | reports of proceedings for debt |
| 34835, 34836 | CPR VII 24 r/v | 5th–6th century | Oxyrhynchos | K | exclude | court proceedings |
| 37323 | P.Mich. XI 624 | early 6th century | – | K | exclude | letter |
| 67419 | – (DCLP) | 775–820 | Kochel; Munich, BSB Clm 6333 | K | exclude | Latin liturgical book (`Libellus missae`) |

## Claims

### Claim 1 (SQ1): A libellus of the Decian persecution is a certificate of sacrifice, issued in 250 CE and recognizable by a fixed formula.
- Evidence for: the 14 documents of Step 1 share the form described there: declaration of sacrifice before a commission, request for signature, the officials' confirmation, and a date in the first year of Decius. Their firm dates, and those of the other certificates found, fall between 4 June and 14 July 250 (Claim 2).
- Evidence against and uncertainties: the form was derived from documents that their editors had already called libelli. The keyword search shows that *libellus* also names other documents, mostly petitions and court records from the 2nd to the 6th century (Claim 3).
- Reasoning: the shared form, together with the shared date, defines the group; the formula elements can therefore serve as search criteria for SQ2.
- Certainty: high.

### Claim 2 (SQ2): The database holds 47 records of Decian certificates, probably 46 distinct certificates.
- Evidence for: the 35 certificates of Steps 2–4 and the 12 of Step 5 (Candidates). All are dated to 250 CE except P.Oxy. XLI 2990 [30379] (3rd century). Firm dates run from 4 June 250 (P.Wisc. II 87 [13730]) to 14 July 250 (SB I 4450 [13951]). 43 come from the Arsinoite nome (37 of them from Theadelphia) and 4 from the Oxyrhynchite nome.
- Evidence against and uncertainties: TM 13941 and 14001 have the same text (Step 7) and are probably one certificate. The 12 documents of Step 5, PSI VII 778 [13792] and P.Oxy. XLI 2990 [30379] are fragments; they are classed by their date, the editor's title and the HGV keywords, not by a full formula. P.Oxy. XLI 2990 is dated only to the 3rd century.
- Reasoning: three routes (keyword, formula, keyword `Opfer` with date) agree on the core. Every document found by one route only has a specific reason why the others missed it: German tagging, a fragmentary text, or a vague date. All included documents fall in the window established in Claim 1, or, in one case, are compatible with it.
- Certainty: high for the 33 documents with formula and date; medium for the 14 fragments; the duplicate lowers the count of distinct certificates to 46.

### Claim 3 (SQ2): The `libell%` keyword search alone gives a wrong count.
- Evidence for: it returns 29 documents, of which 10 are not certificates (Candidates, "exclude"), and it misses 28 certificates that are tagged only in German or not at all.
- Evidence against and uncertainties: none found.
- Reasoning: in the excluded documents *libellus* means "petition", or names a liturgical book in the Latin codex; their dates and contents rule them out.
- Certainty: high.

### Claim 4 (SQ2): The database count is a lower bound for what is preserved.
- Evidence for: the database holds the papyri.info data, not every published papyrus. Within it, a certificate without a transcription, a matching keyword or a date in 249–251 is found by none of the routes (Steps 2–6).
- Evidence against and uncertainties: none found. How far the count falls short of the published total cannot be measured in the database (SQ3, Gaps).
- Reasoning: a count from a partial corpus, found by routes that each miss some documents, can only be lower than or equal to the published total.
- Certainty: high.

### Claim 5 (SQ4): The libelli do not show whether their holders were Christians.
- Evidence for: no certificate mentions Christians (Step 8). The certificates record a sacrifice to the gods, not the holder's religion before it. At least one holder was a priestess of Petesouchos (Chrest.Wilck. 125 [15151]), so the certificates were not issued only to Christians.
- Evidence against and uncertainties: fragments may have lost a statement about the holder.
- Reasoning: since the documents do not record the holder's religion, reading (b) of the question cannot be answered from them, and the count is given for reading (a).
- Certainty: high.

### Claim 6 (main question): At least 46 Decian libelli are preserved; the database holds 46 distinct certificates.
- Evidence for: Claim 2 (47 records, 46 distinct certificates) and Claim 4 (the database count is a lower bound). Claim 1 gives the criteria, and Claim 5 shows that the count cannot be narrowed to certificates issued to Christians.
- Evidence against and uncertainties: the published total (SQ3) could not be established from the database, so the answer gives a minimum, not a total.
- Reasoning: the synthesis plan sets the database count beside the literature's count. With SQ3 unanswered, the database count answers the question as a lower bound.
- Certainty: high for the database count and for it being a minimum.

## Alternatives
- **29** (keyword count): rejected; 10 false positives and 28 misses (Claim 3).
- **35** (keyword and formula combined, without Step 5): rejected; it misses 12 fragments tagged only in German.
- **Certificates issued to Christians only**: cannot be counted (Claim 5).

## Draft answer
The database holds 47 records of certificates of sacrifice from the Decian persecution, which are probably 46 distinct certificates, since two records share one text. All come from Egypt, 43 from the Arsinoite and 4 from the Oxyrhynchite nome, and their firm dates fall between 4 June and 14 July 250. The count is certain for 33 documents with formula and date; 14 are fragments classed by date and metadata. It is a minimum: the published total could not be established from the database. Whether any holder was a Christian cannot be read from the certificates.

## Gaps
- SQ3 (the count in the scholarly literature) cannot be answered from the database. A published list of the Decian libelli would answer it, and comparing that list with the 47 records would show which certificates the database lacks.
- Readings of the fragments were not checked in `xml_content` for supplied text.
- Semantic search on `translations` was not used; only a few of the certificates have translations, so it could not have changed the count.

## Sources

Link pattern: `https://papyri.info/editions/` + edition id with `;` replaced by `/`. Current location is recorded only for Tyche 30 no. 16 (Decorah). This example shows four entries. A real record has an entry for every cited document, here all 47.

| TM | Edition | Title | Date | Place | Link | Current location |
|---|---|---|---|---|---|---|
| 11977 | P.Mich. III 157 | Libellus of the Decian Persecution | 17 June 250 | Theadelphia (Arsinoites) | https://papyri.info/editions/p.mich/3/157 | not recorded |
| 13941 | SB I 4440dupl | Opferbescheinigungen | 16 June 250 | Theadelphia (Arsinoites) | https://papyri.info/editions/sb/1/4440dupl | not recorded |
| 30379 | P.Oxy. XLI 2990 | – | 3rd century | Oxyrhynchos | https://papyri.info/editions/p.oxy/41/2990 | not recorded |
| 699682 | Tyche 30 no. 16 | Decian Libellus | ca. 4 June–14 July 250 | Theadelphia (Arsinoites) | https://papyri.info/editions/tyche/30/16 | Decorah |

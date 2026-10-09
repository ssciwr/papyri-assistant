# Example of a good report

This report meets every acceptance criterion. It was written from the example research record in the papyrological-research skill and adds nothing to it. It answers the question directly, gives the database count as a minimum, and names the part of the question the database cannot answer. It says how the corpus was searched and what that search can miss. It discards false positives and says why. Each reference can be checked.

---

## Question and approach

**Question:** How many libelli from the persecution of Christians under Decius are preserved?

**Interpretation:** The question does not say what kind of document a libellus is, or when the persecution took place; both were established from the documents themselves (Finding 1). "Preserved" can mean preserved in the database this assistant can search, or preserved in all published papyri; both readings were kept. "Libelli from the persecution of Christians" was read as libelli issued in the course of the persecution, and the research tested whether it can also be read as libelli issued to Christians. The interpretation was not revised during the research.

**Sub-questions:**
1. What kind of document is a libellus of the Decian persecution, when were such libelli issued, and how can one be recognized?
2. Which documents in the database are such libelli, and how many distinct papyri are they?
3. How many such libelli does the scholarly literature count?
4. Do the libelli show whether their holders were Christians?

**Approach:** The form of a libellus was taken from the documents that their editors call Decian libelli. Candidates were then found in two independent ways, by keyword metadata and by the Greek formula of the certificates, combined, and checked one by one. A further search looked for certificates that both ways had missed, and a third route confirmed the result. Finally, the texts were searched for statements about the holders' religion.

## Methods and sources

Corpus: the papyri.info data (DDbDP texts, HGV metadata, Trismegistos ids) as loaded into the assistant's PostgreSQL database. Tool: `query_sql`.

1. **Reading the editors' libelli.** The 14 documents whose titles call them libelli of the Decian persecution, and their texts and dates.
   *Limitation:* this starting set rests on the editors' titles, so a libellus of unusual form would not shape the pattern found.
2. **Keyword search.** `keywords.keyword ILIKE 'libell%'`. Result: 29 documents.
   *Limitation:* the word can name other kinds of document, and certificates not tagged `Libellus` are missed.
3. **Formula search.** In `transcriptions` (type `transcription`), with whitespace removed so that words split across lines still match, the text was searched for the four elements of the form found in step 1: the address to the commission (ἐπὶ τῶν θυσιῶν), the libation (stem σπεισ-), the tasting of the offering (stem ἐγευσ-) and the sacrifice (ἔθυσα, ἐθύσαμεν, θύων, θύοντες). A document counted as a hit if at least two of the four elements were present. Result: 33 documents.
   *Limitation:* a fragment that preserves fewer than two elements is missed, and so is a text whose wording departs from the patterns. The searchable text includes the editors' supplements, so a match can rest on restored text.
4. **Combination and check.** The 45 documents found by step 2 or 3 were checked for date, place, title and content. Result: 35 certificates and 10 false positives.
   *Limitation:* the readings were not checked against photographs.
5. **Search for missed certificates.** Documents dated to overlap 249–251 whose title contains *libell*, *sacrific* or *opfer*, whose keyword begins with `libell` or `Opfer`, or whose text contains at least one formula element, minus the 35 already found. Result: 12 more certificates.
   *Limitation:* a certificate without a date in 249–251, and without a matching title, keyword or formula element, is still missed.
6. **Third route.** The keyword `Opfer` combined with a date in 249–251. Result: 38 documents, 37 of them among the certificates found.
   *Limitation:* a certificate dated more vaguely than 249–251 is missed.
7. **Duplicate check.** The two records with `dupl` in their edition id were compared.
8. **Holders' religion.** The texts of all certificates were searched for mentions of Christians and for the declaration of sacrifice to the gods.
   *Limitation:* fragments may have lost a statement about the holder.

## Findings

### Sub-question 1

#### Finding 1: A Decian libellus is a certificate of sacrifice, issued in 250 CE and recognizable by a fixed formula.

**Evidence for:**
- The 14 documents that their editors call Decian libelli [2–5, 7, 11, 20, 28–30, 33, 35–37] share one form: an address to the commission for the sacrifices (τοῖς ἐπὶ τῶν θυσιῶν ᾑρημένοις); a declaration that the declarant has always sacrificed to the gods; a statement that the declarant has now sacrificed, poured a libation and tasted the offerings in the commission's presence (P.Mich. III 157 [5]: ἐθύσαμεν καὶ ἐσπείσαμεν καὶ τῶν ἱερείων ἐγευσάμεθα); a request for the commission's signature; the officials' confirmation (εἴδαμεν ὑμᾶς θυσιάζοντας); and a date in the first year of Decius.
- All 14 are dated to 250 CE. The firm dates of all certificates found run from 4 June 250 (P.Wisc. II 87 [6]) to 14 July 250 (SB I 4450 [16]).

**Evidence against / uncertainties:**
- The form was derived from documents that their editors had already called libelli, so the editors' classification shapes it.
- The word *libellus* also names other documents, mostly petitions and court records from the 2nd to the 6th century (Finding 3).

**Reasoning:** The shared form, together with the shared date, defines the group. The formula elements can therefore serve as criteria for finding further libelli.

**Certainty:** high.

### Sub-question 2

#### Finding 2: The database contains 47 records of Decian libelli, probably 46 distinct certificates.

**Evidence for:**
- The formula search finds 33 documents [1–19, 21–23, 25–35]. All of them are dated to 250 CE or, for P.Oxy. LVIII 3929 [21], to 25 June–24 July 250.
- The keyword search adds two documents that the formula search misses:
  - PSI VII 778 [20] is a fragment, too damaged for two formula elements to survive.
  - P.Oxy. XLI 2990 [24] preserves only the witnesses' signatures (εἶδον ὑμᾶς θύοντας καὶ γευομένους).
- The search for missed certificates adds 12 documents [36–47]. All are fragments from Theadelphia dated to 250, often preserving only the date with Decius's titulature. HGV tags them `Opfer` with `Bescheinigung` or `Bestätigung`, not `Libellus`, and their text preserves fewer than two formula elements.
- The third route, by the keyword `Opfer`, finds 37 of the 47.
- 43 come from the Arsinoite nome (37 of them from Theadelphia) and 4 from the Oxyrhynchite nome.

**Evidence against / uncertainties:**
- P.Oxy. XLI 2990 [24] is dated only to the 3rd century. It belongs to the group by its form, but its date does not show that on its own.
- PSI VII 778 [20] and the documents [36–47] are fragments. They are classed as libelli by their date, the editor's title and the HGV keywords, not by formula elements in their preserved text.
- SB I 4440dupl [12] and SB I 5943dupl [22] have distinct Trismegistos ids but the same text, the certificate of Aurelia Charis of Theadelphia of 16 June 250. They are probably one certificate.

**Reasoning:** Three routes agree on the core of the group. The documents found by one route alone, or only by the search for missed certificates, each have a specific reason why the others missed them: a fragmentary text, a vague date, or tagging only in German. Every included document falls within the dates established in Finding 1, or, in one case, is compatible with them.

**Certainty:** high for the 33 documents with formula and date; medium for the 14 fragments [20, 24, 36–47]. The duplicate lowers the count of distinct certificates to 46.

#### Finding 3: The keyword search alone gives a wrong count.

**Evidence for:** 10 of the 29 keyword hits are not certificates: a petition from 138 CE (P.Oxy. III 484), a petition about landholding from about 345–352 (SB XVIII 13769), reports of proceedings for debt from the 5th century (P.Oxy. XVI 1876–1879), court proceedings from the 5th–6th century (CPR VII 24 r/v), a letter from the 6th century (P.Mich. XI 624) and a Latin liturgical book from 775–820 tagged *Libellus missae* (TM 67419). The keyword search also misses 28 of the 47 certificates, which are tagged only in German or not at all.

**Evidence against / uncertainties:** none found.

**Reasoning:** In the excluded documents *libellus* means "petition", or names a liturgical book; their dates and contents rule them out.

**Certainty:** high.

#### Finding 4: The database count is a lower bound for what is preserved.

**Evidence for:** The database holds the papyri.info data, not every published papyrus. Within it, a certificate without a transcription, a matching keyword or a date in 249–251 is found by none of the routes (Methods 2–6).

**Evidence against / uncertainties:** How far the count falls short of the published total cannot be measured in the database (sub-question 3, see Summary).

**Reasoning:** A count from a partial corpus, found by routes that each miss some documents, can only be lower than or equal to the published total.

**Certainty:** high.

### Sub-question 4

#### Finding 5: The libelli do not show whether their holders were Christians.

**Evidence for:** No certificate mentions Christians. 32 of the texts declare a sacrifice to the gods, and none records the holder's religion. At least one holder was a priestess: in Chrest.Wilck. 125 [31] the declarant is Aurelia Ammonous, priestess of Petesouchos (ἱερείας Πετεσούχου θεοῦ μεγάλου). The certificates were therefore not issued only to Christians.

**Evidence against / uncertainties:** fragments may have lost a statement about the holder.

**Reasoning:** Since the documents do not record the holder's religion, the reading "libelli issued to Christians" cannot be answered from them, and the count is given for libelli issued in the course of the persecution.

**Certainty:** high.

### Main question

#### Finding 6: At least 46 Decian libelli are preserved; the database holds 46 distinct certificates.

**Evidence for:** Finding 2 (47 records, 46 distinct certificates) and Finding 4 (the database count is a lower bound). Finding 1 gives the criteria, and Finding 5 shows that the count cannot be narrowed to certificates issued to Christians.

**Evidence against / uncertainties:** The published total (sub-question 3) could not be established from the database, so the answer gives a minimum, not a total.

**Reasoning:** With the published total unknown, the database count answers the question as a lower bound.

**Certainty:** high for the database count and for its being a minimum.

## Alternatives

- **"29 libelli"** (the keyword count): rejected. It includes 10 documents that are not certificates and misses 28 certificates (Finding 3).
- **"35 libelli"** (keyword and formula searches combined): rejected. It misses 12 fragments tagged only in German [36–47].
- **Counting only certificates issued to Christians:** this cannot be done from the documents (Finding 5).

## Summary

The assistant's database holds **47** records of Decian certificates of sacrifice, which are probably **46** distinct certificates, since two records share one text [12, 22]. All come from Egypt, 43 from the Arsinoite nome (37 of them from Theadelphia) and 4 from the Oxyrhynchite nome, and their firm dates fall between 4 June and 14 July 250. The count is certain for 33 documents with formula and date; 14 are fragments classed by date and metadata [20, 24, 36–47]. It is a minimum: **at least 46** Decian libelli are preserved.

The database could not answer how many libelli the scholarly literature counts in total (sub-question 3). A published list of the Decian libelli would answer it, and comparing that list with the 47 records would show which certificates the database lacks. Whether any holder was a Christian cannot be read from the certificates.

## References

The current holding institution is recorded in the database only for [35] (Decorah).

| # | TM | Edition | Date | Place | Link |
|---|----|---------|------|-------|------|
| 1 | 9033 | Chrest.Wilck. 124 | 26 June 250 | Alexandrou Nesos, Arsinoites | https://papyri.info/editions/chrest.wilck/124 |
| 2 | 11954 | P.Meyer 15 | 27 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.meyer/15 |
| 3 | 11955 | P.Meyer 16 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.meyer/16 |
| 4 | 11956 | P.Meyer 17 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.meyer/17 |
| 5 | 11977 | P.Mich. III 157 | 17 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.mich/3/157 |
| 6 | 13730 | P.Wisc. II 87 | 4 June 250 | Narmuthis, Arsinoites | https://papyri.info/editions/p.wisc/2/87 |
| 7 | 11978 | P.Mich. III 158 | 21 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.mich/3/158 |
| 8 | 12907 | P.Ryl. II 112A | 20 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.ryl/2/112A |
| 9 | 12908 | P.Ryl. II 112B | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.ryl/2/112B |
| 10 | 12909 | P.Ryl. II 112C | 22 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.ryl/2/112C |
| 11 | 13780 | PSI V 453 | 14–23 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/psi/5/453 |
| 12 | 13941 | SB I 4440 (dupl) | 16 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4440dupl |
| 13 | 13936 | SB I 4435 | 12 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4435 |
| 14 | 13937 | SB I 4436 | 14 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4436 |
| 15 | 13940 | SB I 4439 | 26 May–24 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4439 |
| 16 | 13951 | SB I 4450 | 14 July 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4450 |
| 17 | 13945 | SB I 4444 | 21 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4444 |
| 18 | 13946 | SB I 4445 | 22 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4445 |
| 19 | 13949 | SB I 4448 | 23 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4448 |
| 20 | 13792 | PSI VII 778 | 26 June 250 | Arsinoites | https://papyri.info/editions/psi/7/778 |
| 21 | 17912 | P.Oxy. LVIII 3929 | 25 June–24 July 250 | Thosbis, Oxyrhynchites | https://papyri.info/editions/p.oxy/58/3929 |
| 22 | 14001 | SB I 5943 (dupl) | 16 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/5943dupl |
| 23 | 21866 | P.Oxy. XII 1464 | 27 June 250 | Oxyrhynchos | https://papyri.info/editions/p.oxy/12/1464 |
| 24 | 30379 | P.Oxy. XLI 2990 | 3rd century | Oxyrhynchos | https://papyri.info/editions/p.oxy/41/2990 |
| 25 | 13952 | SB I 4451 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4451 |
| 26 | 13953 | SB I 4452 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4452 |
| 27 | 13956 | SB I 4455 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4455 |
| 28 | 14005 | SB III 6827 | 21 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/3/6827 |
| 29 | 14006 | SB III 6828 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/3/6828 |
| 30 | 14104 | SB VI 9084 | 17 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/6/9084 |
| 31 | 15151 | Chrest.Wilck. 125 | 250 | Ptolemais Euergetis, Arsinoites | https://papyri.info/editions/chrest.wilck/125 |
| 32 | 20403 | P.Oxy. IV 658 | 14 June 250 | Oxyrhynchos | https://papyri.info/editions/p.oxy/4/658 |
| 33 | 44425 | P.Lips. II 152 | 16 June 250 | Euhemeria, Arsinoites | https://papyri.info/editions/p.lips/2/152 |
| 34 | 56431 | P.Ryl. I 12 | 14 June 250 | Ptolemais Euergetis, Arsinoites | https://papyri.info/editions/p.ryl/1/12 |
| 35 | 699682 | Tyche 30 no. 16 | ca. 4 June–14 July 250 | Theadelphia, Arsinoites | https://papyri.info/editions/tyche/30/16 |
| 36 | 11404 | P.Hamb. I 61a | 13 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.hamb/1/61a |
| 37 | 11405 | P.Hamb. I 61b | 21 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/p.hamb/1/61b |
| 38 | 13938 | SB I 4437 | 14 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4437 |
| 39 | 13939 | SB I 4438 | 15 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4438 |
| 40 | 13942 | SB I 4441 | 17 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4441 |
| 41 | 13943 | SB I 4442 | 19 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4442 |
| 42 | 13944 | SB I 4443 | 19 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4443 |
| 43 | 13947 | SB I 4446 | 23 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4446 |
| 44 | 13948 | SB I 4447 | 23 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4447 |
| 45 | 13950 | SB I 4449 | 23 June 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4449 |
| 46 | 13954 | SB I 4453 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4453 |
| 47 | 13955 | SB I 4454 | 250 | Theadelphia, Arsinoites | https://papyri.info/editions/sb/1/4454 |

# Example of a good report

This report meets every acceptance criterion. It answers the question directly and keeps two counts apart: what the database holds, and what the scholarly literature counts. It says how the corpus was searched and what that search can miss. It discards false positives and says why. Each reference can be checked.

---

## Question and approach

**Question:** How many libelli from the persecution of Christians under Decius are preserved?

**Interpretation:** A *libellus* here means a certificate of sacrifice. Under Decius's edict of late 249 or early 250, every inhabitant had to sacrifice to the gods in front of a local commission and receive a signed certificate. "Preserved" is read in two ways: (a) how many such certificates are in the papyrological database this assistant can search, and (b) how many the scholarly literature counts in total. The question does not name a region, but all known Decian libelli come from Egypt.

**Approach:** Candidate documents were found in two independent ways, by keyword metadata and by the Greek formula of the certificates. The two result sets were combined, and each candidate was checked for date, place and content. A third search looked for certificates that both ways had missed. The database total is then set against the counts published in the literature.

## Methods and sources

Corpus: the papyri.info data (DDbDP texts, HGV metadata, Trismegistos ids) as loaded into the assistant's PostgreSQL database. Tool: `query_sql`.

1. **Keyword search.** `keywords.keyword ILIKE 'libell%'`, joined to `papyri`, `orig_dates` and `orig_places`. Result: 29 documents.
   *Limitation:* in Latin, *libellus* also means any petition, so this search returns false positives. It also misses any certificate that HGV has not tagged as a libellus.
2. **Formula search.** In `transcriptions` (type `transcription`), with whitespace removed so that words split across lines still match, the text was searched for four elements of the certificate formula: the address to the commission (ἐπὶ τῶν θυσιῶν), the libation (stem σπεισ-, as in ἔσπεισα and ἐσπείσαμεν), the tasting of the offering (stem ἐγευσ-, as in ἐγευσάμην and ἐγευσάμεθα) and the sacrifice (ἔθυσα, ἐθύσαμεν, θύων, θύοντες). A document counted as a hit if at least two of the four elements were present. Result: 33 documents.
   *Limitation:* a fragment that preserves fewer than two elements is missed. So is a text whose spelling departs from the patterns used.
3. **Combination and review.** The two result sets were combined, and every candidate's date, place and title was checked.
   *Limitation:* the readings were not checked against photographs.
4. **Search for missed certificates.** Documents dated to overlap 249–251 whose title contains *libell*, *sacrific* or *Opfer*, whose keyword begins with `libell` or `Opfer`, or whose text contains at least one formula element, minus the documents already found. Result: 12 more certificates.
   *Limitation:* a certificate without a date in 249–251, and without a matching title, keyword or formula element, is still missed.

## Findings

### Finding 1: The database contains 47 records of Decian libelli, probably 46 distinct certificates.

**Claim:** 47 documents (by Trismegistos id) in the database are certificates of sacrifice from the Decian persecution. Two of them have the same text, so they are probably 46 distinct certificates.

**Evidence for:**
- The formula search finds 33 documents [1–19, 21–23, 25–35]. All of them are dated to 250 CE or, for P.Oxy. LVIII 3929 [21], to 25 June–24 July 250. They come from the Arsinoite and Oxyrhynchite nomes.
- The keyword search adds two documents that the formula search misses:
  - PSI VII 778 [20] is a fragment, too damaged for two formula elements to survive.
  - P.Oxy. XLI 2990 [24] has a "libellus" tag, but HGV dates it only to the 3rd century. Only the witnesses' signatures survive (εἶδον ὑμᾶς θύοντας καὶ γευομένους).
- The search for missed certificates adds 12 documents [36–47]. All are fragments from Theadelphia dated to 250, often preserving only the date with Decius's titulature. HGV tags them `Opfer` with `Bescheinigung` or `Bestätigung`, not `Libellus`, and their text preserves fewer than two formula elements.
- The firmly dated certificates run from 4 June 250 (P.Wisc. II 87 [6]) to 14 July 250 (SB I 4450 [16]). This matches what is known from other sources about how the edict was carried out.

**Evidence against / uncertainties:**
- P.Oxy. XLI 2990 [24] is dated only to the 3rd century. It belongs to the Decian group if its form is accepted as evidence, but its date does not show that on its own.
- PSI VII 778 [20] and the documents [36–47] are fragments. They are classed as libelli from their date, the editor's title and the HGV keywords, not from formula elements in their preserved text.
- SB I 4440dupl [12] and SB I 5943dupl [22] have distinct Trismegistos ids but the same text, the certificate of Aurelia Charis of Theadelphia of 16 June 250. They are probably one certificate.
- Chrest.Wilck. 125 [31] is the certificate of a pagan priestess. It is a Decian libellus, but it shows that the certificates were required of everyone, not only of suspected Christians. A reader who takes "libelli of the persecution of Christians" to mean "certificates issued to Christians" should note this point (see Alternatives).

**Reasoning:** Both searches agree on the core of the group. The documents found by one search alone, or by neither, each have a specific reason why they were missed: a fragmentary text, a vague date, or tagging only in German. Every included document falls within the known window of the edict, or, in one case, is compatible with it. The count of 47 records is therefore solid for this database, with [20], [24] and [36–47] as the least certain members and [12] and [22] probably one text.

### Finding 2: The keyword search alone gives a wrong count.

**Claim:** 10 of the 29 keyword hits are not Decian libelli, and the keyword search misses 28 certificates.

**Evidence:** The false positives are a petition from 138 CE (P.Oxy. III 484), a petition about landholding from about 345–352 (SB XVIII 13769), reports of proceedings for debt from the 5th century (P.Oxy. XVI 1876–1879), court proceedings from the 5th–6th century (CPR VII 24 r/v), a letter from the 6th century (P.Mich. XI 624) and a Latin liturgical book from 775–820 tagged *Libellus missae* (TM 67419). In the documentary texts *libellus* means "petition", which is the ordinary late-antique sense of the word. The missed certificates are tagged only in German, or not at all.

**Reasoning:** Their dates and contents rule out the false positives. A count based on the keyword search alone would therefore be wrong.

### Finding 3: The database total is close to the literature's total.

**Claim:** The database holds about as many Decian libelli as the literature counts. The database figure is nevertheless a lower bound.

**Evidence for:** Knipfing (1923) edited 41 libelli together. Later publications, for example P.Oxy. XLI 2990 (1972) [24], P.Oxy. LVIII 3929 (1991) [21] and Tyche 30 no. 16 [35], have raised the number. Recent surveys (e.g. Schubert 2016) count around 46. The database holds 46 distinct certificates (Finding 1).

**Evidence against / uncertainties:**
- The literature counts were not checked against the full lists in Knipfing and Schubert within this research.
- Some libelli may be in the database without a transcription, a keyword tag or a date in 249–251. None of the searches would find them.

**Reasoning:** The database draws on papyri.info, which does not include every published papyrus, so its count is a lower bound. That it matches the literature's figure suggests the database holds nearly all published certificates. Confirming this would require comparing the database against Schubert's list.

## Alternatives

- **"29 libelli"** (the keyword count): rejected. It includes 10 petitions, proceedings and other texts (Finding 2) and misses 28 certificates.
- **"35 libelli"** (keyword and formula searches combined): rejected. It misses 12 fragments tagged only in German [36–47].
- **"41 libelli"** (Knipfing): rejected as a current figure. It is the count of 1923 and does not include later publications.
- **Counting only certificates issued to Christians:** this cannot be done from the documents. The certificates do not say whether their holders were Christian, and at least one holder was a pagan priestess [31]. Whether any holder was a lapsed Christian (*libellaticus*) cannot be read off the papyri.

## Summary

The assistant's database holds **47** records of Decian certificates of sacrifice, which are probably **46** distinct certificates, since two records share one text [12, 22]. All come from Egypt, 43 from the Arsinoite nome (37 of them from Theadelphia) and 4 from the Oxyrhynchite nome. Their firm dates fall between 4 June and 14 July 250. This figure is certain for the core of 33 documents with formula and date. Fourteen documents are less certain: thirteen are fragments [20, 36–47] and one is dated only to the 3rd century [24]. Recent surveys count about 46, which matches the database. That figure comes from the literature and was not verified against the database.

## References

Links are to papyri.info. The current holding institution is recorded in the database only for [35].

| # | TM | Edition | Date | Place |
|---|----|---------|------|-------|
| 1 | 9033 | Chrest.Wilck. 124 | 26 June 250 | Alexandrou Nesos, Arsinoites |
| 2 | 11954 | P.Meyer 15 | 27 June 250 | Theadelphia, Arsinoites |
| 3 | 11955 | P.Meyer 16 | 250 | Theadelphia, Arsinoites |
| 4 | 11956 | P.Meyer 17 | 250 | Theadelphia, Arsinoites |
| 5 | 11977 | P.Mich. III 157 | 17 June 250 | Theadelphia, Arsinoites |
| 6 | 13730 | P.Wisc. II 87 | 4 June 250 | Narmuthis, Arsinoites |
| 7 | 11978 | P.Mich. III 158 | 21 June 250 | Theadelphia, Arsinoites |
| 8 | 12907 | P.Ryl. II 112A | 20 June 250 | Theadelphia, Arsinoites |
| 9 | 12908 | P.Ryl. II 112B | 250 | Theadelphia, Arsinoites |
| 10 | 12909 | P.Ryl. II 112C | 22 June 250 | Theadelphia, Arsinoites |
| 11 | 13780 | PSI V 453 | 14–23 June 250 | Theadelphia, Arsinoites |
| 12 | 13941 | SB I 4440 (dupl) | 16 June 250 | Theadelphia, Arsinoites |
| 13 | 13936 | SB I 4435 | 12 June 250 | Theadelphia, Arsinoites |
| 14 | 13937 | SB I 4436 | 14 June 250 | Theadelphia, Arsinoites |
| 15 | 13940 | SB I 4439 | 26 May–24 June 250 | Theadelphia, Arsinoites |
| 16 | 13951 | SB I 4450 | 14 July 250 | Theadelphia, Arsinoites |
| 17 | 13945 | SB I 4444 | 21 June 250 | Theadelphia, Arsinoites |
| 18 | 13946 | SB I 4445 | 22 June 250 | Theadelphia, Arsinoites |
| 19 | 13949 | SB I 4448 | 23 June 250 | Theadelphia, Arsinoites |
| 20 | 13792 | PSI VII 778 | 26 June 250 | Arsinoites |
| 21 | 17912 | P.Oxy. LVIII 3929 | 25 June–24 July 250 | Thosbis, Oxyrhynchites |
| 22 | 14001 | SB I 5943 (dupl) | 16 June 250 | Theadelphia, Arsinoites |
| 23 | 21866 | P.Oxy. XII 1464 | 27 June 250 | Oxyrhynchos |
| 24 | 30379 | P.Oxy. XLI 2990 | 3rd century | Oxyrhynchos |
| 25 | 13952 | SB I 4451 | 250 | Theadelphia, Arsinoites |
| 26 | 13953 | SB I 4452 | 250 | Theadelphia, Arsinoites |
| 27 | 13956 | SB I 4455 | 250 | Theadelphia, Arsinoites |
| 28 | 14005 | SB III 6827 | 21 June 250 | Theadelphia, Arsinoites |
| 29 | 14006 | SB III 6828 | 250 | Theadelphia, Arsinoites |
| 30 | 14104 | SB VI 9084 | 17 June 250 | Theadelphia, Arsinoites |
| 31 | 15151 | Chrest.Wilck. 125 | 250 | Ptolemais Euergetis, Arsinoites |
| 32 | 20403 | P.Oxy. IV 658 | 14 June 250 | Oxyrhynchos |
| 33 | 44425 | P.Lips. II 152 | 16 June 250 | Euhemeria, Arsinoites |
| 34 | 56431 | P.Ryl. I 12 | 14 June 250 | Ptolemais Euergetis, Arsinoites |
| 35 | 699682 | Tyche 30 no. 16 | ca. 4 June–14 July 250 | Theadelphia, Arsinoites; held at Decorah |
| 36 | 11404 | P.Hamb. I 61a | 13 June 250 | Theadelphia, Arsinoites |
| 37 | 11405 | P.Hamb. I 61b | 21 June 250 | Theadelphia, Arsinoites |
| 38 | 13938 | SB I 4437 | 14 June 250 | Theadelphia, Arsinoites |
| 39 | 13939 | SB I 4438 | 15 June 250 | Theadelphia, Arsinoites |
| 40 | 13942 | SB I 4441 | 17 June 250 | Theadelphia, Arsinoites |
| 41 | 13943 | SB I 4442 | 19 June 250 | Theadelphia, Arsinoites |
| 42 | 13944 | SB I 4443 | 19 June 250 | Theadelphia, Arsinoites |
| 43 | 13947 | SB I 4446 | 23 June 250 | Theadelphia, Arsinoites |
| 44 | 13948 | SB I 4447 | 23 June 250 | Theadelphia, Arsinoites |
| 45 | 13950 | SB I 4449 | 23 June 250 | Theadelphia, Arsinoites |
| 46 | 13954 | SB I 4453 | 250 | Theadelphia, Arsinoites |
| 47 | 13955 | SB I 4454 | 250 | Theadelphia, Arsinoites |

Literature: J. R. Knipfing, "The Libelli of the Decian Persecution", *Harvard Theological Review* 16 (1923) 345–390. P. Schubert, "On the Form and Content of the Certificates of Pagan Sacrifice", *Journal of Roman Studies* 106 (2016) 172–198.

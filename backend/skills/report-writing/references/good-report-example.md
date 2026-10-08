# Example of a good report

This report meets every acceptance criterion. It answers the question directly and keeps two counts apart: what the database holds, and what the scholarly literature counts. It says how the corpus was searched and what that search can miss. It discards false positives and says why. Each reference can be checked.

---

## Question and approach

**Question:** How many libelli from the persecution of Christians under Decius are preserved?

**Interpretation:** A *libellus* here means a certificate of sacrifice. Under Decius's edict of late 249 or early 250, every inhabitant had to sacrifice to the gods in front of a local commission and receive a signed certificate. "Preserved" is read in two ways: (a) how many such certificates are in the papyrological database this assistant can search, and (b) how many the scholarly literature counts in total. The question does not name a region, but all known Decian libelli come from Egypt.

**Approach:** Candidate documents were found in two independent ways, by keyword metadata and by the Greek formula of the certificates. The two result sets were combined, and each candidate was checked for date, place and content. The database total is then set against the counts published in the literature.

## Methods and sources

Corpus: the papyri.info data (DDbDP texts, HGV metadata, Trismegistos ids) as loaded into the assistant's PostgreSQL database. Tool: `query_sql`.

1. **Keyword search.** `keywords.keyword ILIKE 'libell%'`, joined to `papyri`, `orig_dates` and `orig_places`. Result: 28 documents.
   *Limitation:* in Latin, *libellus* also means any petition, so this search returns false positives. It also misses any certificate that HGV has not tagged as a libellus.
2. **Formula search.** In `transcriptions` (type `transcription`), with whitespace removed so that words split across lines still match, the text was searched for four elements of the certificate formula: the address to the commission (τοῖς ἐπὶ τῶν θυσιῶν ᾑρημένοις), the libation (ἔσπεισα), the tasting of the offering (ἐγευσάμην) and the sacrifice (θύων). A document counted as a hit if at least two of the four elements were present. Result: 32 documents.
   *Limitation:* a fragment that preserves fewer than two elements is missed. So is a text whose spelling departs from the patterns used.
3. **Combination and review.** The two result sets were combined, and every candidate's date, place and title was checked.
   *Limitation:* the readings were not checked against photographs. Duplicate records were checked only by Trismegistos id (see Finding 3).

## Findings

### Finding 1: The database contains 35 Decian libelli.

**Claim:** 35 distinct documents (by Trismegistos id) in the database are certificates of sacrifice from the Decian persecution.

**Evidence for:**
- The formula search finds 32 documents [1–19, 21, 22, 25–35]. All of them are dated to 250 CE or, for P.Oxy. LVIII 3929 [21], to 25 June–24 July 250. They come from the Arsinoite and Oxyrhynchite nomes.
- The keyword search adds three documents that the formula search misses:
  - PSI VII 778 [20] is a fragment, too damaged for two formula elements to survive.
  - P.Oxy. XII 1464 [23] has a "libellus" tag and is titled "Declaration of Pagan Sacrifice". Its address uses a different wording.
  - P.Oxy. XLI 2990 [24] has a "libellus" tag, but HGV dates it only to the 3rd century.
- The firmly dated certificates run from 4 June 250 (P.Wisc. II 87 [6]) to 14 July 250 (SB I 4450 [16]). This matches what is known from other sources about how the edict was carried out.

**Evidence against / uncertainties:**
- P.Oxy. XLI 2990 [24] is dated only to the 3rd century. It belongs to the Decian group if its form is accepted as evidence, but its date does not show that on its own.
- PSI VII 778 [20] is a fragment. It is classed as a libellus from the editor's title, not from formula elements in its preserved text.
- Chrest.Wilck. 125 [31] is the certificate of a pagan priestess. It is a Decian libellus, but it shows that the certificates were required of everyone, not only of suspected Christians. A reader who takes "libelli of the persecution of Christians" to mean "certificates issued to Christians" should note this point (see Alternatives).

**Reasoning:** Both searches agree on the core of the group. The documents found by keyword alone each have a specific reason why the formula search missed them. Every included document falls within the known window of the edict, or, in one case, is compatible with it. The count of 35 is therefore solid for this database, with [20] and [24] as the least certain members.

### Finding 2: The keyword search alone overcounts.

**Claim:** 9 of the 28 keyword hits are not Decian libelli.

**Evidence:** These are a petition from 138 CE (P.Oxy. III 484), a petition about landholding from about 345–352 (SB XVIII 13769), reports of proceedings for debt from the 5th century (P.Oxy. XVI 1876–1879), court proceedings from the 5th–6th century (CPR VII 24 r/v) and a letter from the 6th century (P.Mich. XI 624). In these documents *libellus* means "petition", which is the ordinary late-antique sense of the word.

**Reasoning:** Their dates and contents rule them out. A count based on the keyword search alone would therefore be wrong.

### Finding 3: The database total is lower than the literature's total.

**Claim:** The literature counts more Decian libelli than the database holds. The database figure is a lower bound.

**Evidence for:** Knipfing (1923) edited 41 libelli together. Later publications, for example P.Oxy. XLI 2990 (1972) [24], P.Oxy. LVIII 3929 (1991) [21] and Tyche 30 no. 16 [35], have raised the number. Recent surveys (e.g. Schubert 2016) count around 46.

**Evidence against / uncertainties:**
- The literature counts were not checked against the full lists in Knipfing and Schubert within this research.
- Two DDbDP files carry the suffix `dupl` (SB I 4440dupl [12], SB I 5943dupl [22]). They have distinct Trismegistos ids, so they were counted as separate texts. It was not confirmed that they do not reproduce a text already counted.
- Some libelli may be in the database without a transcription and without a keyword tag. Neither search would find them.

**Reasoning:** The database draws on papyri.info, which does not include every published papyrus. A gap of about ten between 35 and the literature's figure is therefore plausible. Finding out which texts are missing would require comparing the database against Schubert's list.

## Alternatives

- **"28 libelli"** (the keyword count): rejected. It includes 9 petitions and proceedings (Finding 2) and misses texts found only by the formula search.
- **"41 libelli"** (Knipfing): rejected as a current figure. It is the count of 1923 and does not include later publications.
- **Counting only certificates issued to Christians:** this cannot be done from the documents. The certificates do not say whether their holders were Christian, and at least one holder was a pagan priestess [31]. Whether any holder was a lapsed Christian (*libellaticus*) cannot be read off the papyri.

## Summary

The assistant's database holds **35** Decian certificates of sacrifice. All come from Egypt, 31 from the Arsinoite nome (25 of them from Theadelphia) and 4 from the Oxyrhynchite nome. Their firm dates fall between 4 June and 14 July 250. This figure is certain for the core of 33 documents. Two documents are less certain: one is a fragment [20] and one is dated only to the 3rd century [24]. The published total is higher, about 46 according to recent surveys. That figure comes from the literature and was not verified against the database.

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

Literature: J. R. Knipfing, "The Libelli of the Decian Persecution", *Harvard Theological Review* 16 (1923) 345–390. P. Schubert, "On the Form and Content of the Certificates of Pagan Sacrifice", *Journal of Roman Studies* 106 (2016) 172–198.

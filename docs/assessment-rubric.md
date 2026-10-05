# Assessment rubric

> Project-authored, derived from the official learning outcomes of QF ELECTRICIAN (DGT/1001, NSQF 4). The quoted
> QF references are verbatim; task design, weights and anchor wording are project design decisions.
> Source of truth: `data/assessment/electrician_tasks.json` and `rubric.json` (this table is generated from them).

## Scale

| Score | Meaning | Hindi | Guidance |
|---|---|---|---|
| 0 | Not demonstrated | नहीं दिखाया | Candidate did not attempt, or the outcome is absent/unsafe. |
| 1 | Requires substantial assistance | काफ़ी मदद चाहिए | Completed only with step-by-step help from the assessor. |
| 2 | Partially demonstrated | आंशिक रूप से | Some parts correct; a significant error or omission remains. |
| 3 | Competent with minor issues | सक्षम, छोटी कमियाँ | Meets the criterion; minor issue that does not affect safety or function. |
| 4 | Competent independently | पूरी तरह सक्षम | Meets the criterion fully and independently. |

## Rules

- **criterion anchors take precedence:** Where a criterion has its own anchors (data/assessment/electrician_tasks.json), score against those; the generic scale is the fallback.
- **evidence before score:** A final score may be recorded without uploaded evidence only if the assessor writes an observation note.
- **ai is advisory:** AI-suggested scores are stored separately (ai_suggested_score) and never used in calculations. Only assessor-confirmed final_score counts.
- **Safety-critical criteria** (marked ⚠ below) scored 0 or 1 block an *eligible* recommendation (project design rule, see methodology §5).
- **Governance:** once any score exists for a criterion, its weight and safety flag are locked in the admin editor; wording and anchors stay editable (audited).

## Official formative dimensions (QF §24)

| Dimension | Weightage in QF | Used in prototype |
|---|---|---|
| Safety consciousness | 15 % | yes |
| Workplace hygiene | 5 % | yes |
| Attendance/ Punctuality | 10 % | no — Not observable in a single RPL practical sitting |
| Ability to follow Manuals/ Written instructions | 5 % | yes |
| Application of Knowledge | 10 % | yes |
| Skills to handle tools / equipment/ Instruments/ Devices | 10 % | yes |
| Economical use of materials | 5 % | yes |
| Working Strategy | 10 % | yes |
| Quality in workmanship/ Performance | 15 % | yes |
| VIVA | 15 % | yes |

Each criterion is tagged with one dimension, so the competency profile can also be read along the QF's own dimensions.

## Thresholds

- **competency required pct = 60** — QF DGT/1001 §23: minimum pass percent for Trade Practical and Formative assessment is 60%. Used here as the prototype competency threshold per competency area.
- **lo coverage required = 0.7** — NCVET RPL Guidelines (Gazette 19 Jun 2024) §6.2(c): assessor ensures applicant has met more than 70% of all the declared learning outcomes for direct RPL assessments.
- **safety gate max score = 1** — Project design rule (not an official requirement): any safety-critical criterion scored 0 or 1 blocks an 'Eligible' recommendation. Rationale: QF §25 notes errors in these outcomes 'could cause fatal accidents'.

## Tasks and criteria

### T01 · Identify trade tools, wires and electrical components (weight 1.0, LO 1, 3)

From a tray of common tools, wires and accessories, name each item, say what it is used for, and check tools for damage before use.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C01.1** Names common trade tools and states their correct use | 1.0 | tools | LO1: Identify the trade tools; demonstrate their uses with safety, care & maintenance. |
| **C01.2** Identifies wire and cable types and reads their specification | 1.0 | knowledge | LO3: Identify types of wires, cables and verify their specifications. |
| ⚠ **C01.3** Inspects tools for damaged insulation before use and rejects unsafe tools | 1.0 | safety | LO1: Identify the trade tools; demonstrate their uses with safety, care & maintenance. |

<details><summary>Score anchors</summary>

- **C01.1** — 0: Cannot name tools · 1: Names fewer than half; needs prompting · 2: Names most but confuses uses of 2 or more · 3: Names all, one minor confusion of use · 4: Names all and explains use and care without prompting
- **C01.2** — 0: Cannot distinguish wire types · 1: Distinguishes only by colour; cannot read size · 2: Identifies type but misreads size/rating · 3: Correct type and size, hesitant on rating/application · 4: Correct type, size, rating and suitable application
- **C01.3** — 0: Uses a damaged tool · 1: Inspects only when told; misses the damaged tool · 2: Inspects but does not set damaged tool aside · 3: Finds and rejects damaged tool after a prompt · 4: Inspects unprompted and rejects the damaged tool

</details>

Required evidence: Tools and components laid out and labelled by the candidate (image, C01.1); Cable marking / wire gauge being read (image, C01.2)

Safety requirements: Damaged or un-insulated tools must be set aside, not used

### T02 · Safety preparation and supply isolation (weight 1.5, LO 5)

Prepare to work on a live installation: wear protective equipment, switch off and isolate the supply, and prove it is dead before touching conductors.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| ⚠ **C02.1** Selects and wears appropriate PPE for the task | 1.0 | safety | LO5: Comply with safety & IE rules when performing the wiring. |
| ⚠ **C02.2** Isolates the supply and proves dead before touching conductors | 2.0 | safety | LO5: Comply with safety & IE rules when performing the wiring. |
| **C02.3** Keeps work area clean, dry and tools organised | 0.5 | hygiene | QF §24 formative dimension: Workplace hygiene (5%) |

<details><summary>Score anchors</summary>

- **C02.1** — 0: No PPE · 1: PPE worn only after instruction, incomplete · 2: Some PPE worn unprompted, item missing · 3: Full PPE, worn correctly after a reminder on one item · 4: Full, correct PPE unprompted throughout
- **C02.2** — 0: Touches conductors without isolating · 1: Isolates only when told; no prove-dead test · 2: Isolates but tests only the circuit (tester not proven) · 3: Isolates and proves dead; omits tag or second check · 4: Isolates, tags, proves tester-circuit-tester before work
- **C02.3** — 0: Hazardous clutter/wet area · 1: Cluttered; tidies only when told · 2: Mostly tidy; offcuts left on floor · 3: Tidy with minor lapse · 4: Clean, dry, tools returned and offcuts cleared

</details>

Required evidence: Candidate wearing PPE at the work point (image, C02.1); Isolated MCB/main switch with tag (image, C02.2); Short clip of prove-dead test (optional) (video, C02.2)

Safety requirements: No work on conductors before prove-dead test; PPE on throughout

### T03 · Wire joints, crimping and soldering (weight 1.0, LO 2)

Make a straight twist joint and a rat-tail joint, terminate a cable lug with a crimping tool, and solder one joint safely.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C03.1** Makes straight twist and rat-tail joints that are tight and correctly formed | 1.5 | quality | LO2: Make simple straight twist and rat-tail joints in single strand conductors. |
| **C03.2** Terminates a cable lug using a crimping tool; termination passes pull test | 1.0 | tools | LO2: Prepare termination of cable lugs by using crimping tool. |
| ⚠ **C03.3** Observes precautions while jointing and soldering | 1.0 | safety | LO2: Observe safety/ precaution during joints & soldering. |

<details><summary>Score anchors</summary>

- **C03.1** — 0: Joint not attempted / falls apart · 1: Loose joint, needs re-doing with help · 2: One joint acceptable, one loose or nicked · 3: Both tight; minor unevenness of turns · 4: Both tight, even turns, no nicked copper
- **C03.2** — 0: Cannot use crimping tool · 1: Wrong die/lug size; needs guidance · 2: Crimped but strands outside barrel or fails pull test · 3: Passes pull test; minor strand protrusion · 4: Correct lug and die, clean crimp, passes pull test
- **C03.3** — 0: Unsafe handling of hot iron/blade · 1: Repeated unsafe acts corrected by assessor · 2: One unsafe act (e.g. iron left off stand) · 3: Safe throughout after one reminder · 4: Safe throughout unprompted

</details>

Required evidence: Close-up of finished joints (image, C03.1); Crimped lug (image, C03.2)

Safety requirements: Soldering iron on stand when not in use; Eye protection while cutting wire

### T04 · Wire a switch, socket and lamp circuit on a test board (weight 1.5, LO 1, 5)

Plan and wire a board with one switch-controlled lamp and one 6A socket in PVC channel, then test it.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C04.1** Plans the layout and estimates material correctly | 0.75 | materials | LO5: Estimate the cost of material for wiring in PVC channel for an office room having 2 lamps, 1 Fan, one 6A socket outlet and wire up. |
| ⚠ **C04.2** Connects correctly: switch in phase, neutral direct to load, socket earthed | 2.0 | quality | LO1: Make and wire up of a test board and test it. |
| **C04.3** Neat workmanship: secure terminations, no exposed copper, channel fixed straight | 1.0 | quality | LO1: Demonstrate fixing of surface mounting type of accessories. |
| **C04.4** Tests the circuit before and after energising | 1.0 | knowledge | LO1: Make and wire up of a test board and test it. |

<details><summary>Score anchors</summary>

- **C04.1** — 0: No plan · 1: Plan only with assistance; large omissions · 2: Plan with 2+ items missing or wrong quantity · 3: Plan complete, one quantity off · 4: Complete layout and accurate material list
- **C04.2** — 0: Circuit unsafe (switch in neutral or no earth) · 1: Wrong connections corrected only with step-by-step help · 2: Works but one non-safety error (e.g. polarity at lamp holder) · 3: All safety connections correct; minor termination issue · 4: All connections correct and verified by candidate
- **C04.3** — 0: Loose accessories, exposed copper · 1: Several loose terminations · 2: Functional but untidy; some copper exposed · 3: Neat with one minor defect · 4: Neat, straight, all terminations tight and covered
- **C04.4** — 0: Energises without any test · 1: Tests only when told · 2: Functional test only, no pre-energise check · 3: Pre- and post-checks with one omission · 4: Continuity/polarity check before, functional test after

</details>

Required evidence: Finished board, front (image, C04.3); Open switch/socket showing terminations (image, C04.2); Material list / estimate (photo of paper is fine) (document, C04.1)

Safety requirements: Switch must break the phase conductor; Socket earth terminal connected; Board energised only after assessor permission

### T05 · Measurement and continuity testing with a multimeter (weight 1.25, LO 8, 17)

Use a digital multimeter to check continuity of a cable, measure a resistance, and measure supply voltage safely; record the readings.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C05.1** Selects the correct function and range on the multimeter | 1.0 | tools | LO8: Measure the value of resistance, voltage and current using digital multimeter. |
| **C05.2** Performs continuity test and correctly interprets open/short result | 1.0 | knowledge | LO17: Test continuity and insulation of various AC motors. |
| ⚠ **C05.3** Measures live voltage safely (correct setting before probing, fingers behind guards) | 1.5 | safety | LO8: Measure the value of resistance, voltage and current using digital multimeter. |
| **C05.4** Records readings with correct units | 0.5 | manuals | QF §24 formative dimension: Ability to follow Manuals/ Written instructions (5%) |

<details><summary>Score anchors</summary>

- **C05.1** — 0: Cannot set meter · 1: Sets meter only with step-by-step help · 2: Correct for 1 of 3 measurements · 3: Correct for all after one self-correction · 4: Correct function and range first time for all
- **C05.2** — 0: Cannot perform test · 1: Performs test but cannot interpret · 2: Interprets one core correctly, misses open core · 3: All cores correct, hesitant explanation · 4: All cores correct with clear explanation of open/short
- **C05.3** — 0: Probes live terminal on resistance/current range · 1: Unsafe grip corrected by assessor · 2: Safe setting but poor probe handling · 3: Safe with one reminder · 4: Safe setting and handling throughout
- **C05.4** — 0: No record · 1: Record incomplete and unitless · 2: Readings recorded, units missing · 3: Complete with one unit error · 4: Complete and correct

</details>

Required evidence: Meter display during continuity test (image, C05.2); Reading sheet (image, C05.4)

Safety requirements: Meter set to voltage before probing live terminals; Fingers behind probe guards

### T06 · Locate and repair a fault in domestic wiring (weight 1.5, LO 5)

A fault has been placed in a domestic wiring board (e.g. open neutral or loose switch terminal). Find it systematically, repair it, and re-test.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C06.1** Follows a systematic diagnosis (symptom, supply to load, half-split) | 1.0 | strategy | LO5: Test, locate the fault and repair a domestic wiring installation. |
| **C06.2** Correctly locates the placed fault | 1.5 | knowledge | LO5: Test, locate the fault and repair a domestic wiring installation. |
| **C06.3** Repairs the fault and re-tests before handing back | 1.0 | quality | LO5: Test, locate the fault and repair a domestic wiring installation. |
| ⚠ **C06.4** Works with supply isolated while repairing | 1.5 | safety | LO5: Comply with safety & IE rules when performing the wiring. |

<details><summary>Score anchors</summary>

- **C06.1** — 0: Random replacement of parts · 1: Needs assessor to direct each step · 2: Some logic but skips sections · 3: Systematic with one redundant step · 4: Clear systematic sequence, explains reasoning
- **C06.2** — 0: Fault not found · 1: Found only with strong hints · 2: Found the area, not the exact point · 3: Found exact point after one wrong guess · 4: Found exact point directly
- **C06.3** — 0: Not repaired · 1: Repaired with help; not re-tested · 2: Repaired, functional test only · 3: Repaired and re-tested; minor finish issue · 4: Repaired neatly, re-tested, explains cause to customer
- **C06.4** — 0: Repairs live · 1: Isolates only after warning · 2: Isolates but does not prove dead · 3: Isolates and proves dead after reminder · 4: Isolates and proves dead unprompted

</details>

Required evidence: Fault location identified (before repair) (image, C06.2); Repaired point (image, C06.3)

Safety requirements: Repair only with supply isolated; Re-test before handing back

### T07 · Circuit protection: fuse, MCB and ELCB/RCCB (weight 1.0, LO 5, 27)

Choose the correct fuse/MCB rating for a given load, install an MCB in a distribution board, and check ELCB/RCCB operation.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C07.1** Selects correct fuse/MCB rating for the given load | 1.0 | knowledge | LO5: Identify the types of fuses their ratings and applications. |
| **C07.2** Installs MCB in the distribution board correctly | 1.0 | quality | LO5: Identify the parts of a relay, MCB & ELCB and check its operation. |
| ⚠ **C07.3** Checks ELCB/RCCB operation and explains earth-leakage protection | 1.0 | safety | LO27: Identify parts of circuit breaker and check its operation. |

<details><summary>Score anchors</summary>

- **C07.1** — 0: Cannot select · 1: Selects with heavy prompting · 2: Rating off by one step without reason · 3: Correct rating, calculation slightly wrong · 4: Correct calculation and rating with justification
- **C07.2** — 0: Not installed · 1: Installed with step-by-step help · 2: Installed; loose terminal or wrong busbar side · 3: Correct; minor finish issue · 4: Correct, tight, labelled
- **C07.3** — 0: Does not know purpose · 1: Knows purpose only when told · 2: Tests but explanation wrong · 3: Tests and explains with minor gap · 4: Tests, explains leakage protection and when to test

</details>

Required evidence: Installed MCB in board (image, C07.2); Rating calculation (document, C07.1)

Safety requirements: Board isolated while mounting MCB

### T08 · Read a wiring diagram and derive materials (weight 0.75, LO 12, 5)

Given a domestic wiring diagram (consumer main board with ICDP switch and distribution board), identify the symbols, trace the circuit and list the material required. Short viva.

| Criterion | Weight | Dimension | Official reference |
|---|---|---|---|
| **C08.1** Identifies standard electrical symbols in the diagram | 1.0 | knowledge | LO12: Read & interpret the information on drawings and apply in executing practical work. |
| **C08.2** Traces the circuit path and sequence of protective devices | 1.0 | strategy | LO5: Draw and wire up the consumers main board with ICDP switch and distribution fuse box. |
| **C08.3** Derives material requirement from the drawing | 1.0 | materials | LO12: Read &analyze the specification to ascertain the material requirement, tools and assembly/maintenance parameters. |
| **C08.4** Viva: explains how the circuit works and why protection is placed where it is | 1.0 | viva | QF §24 formative dimension: VIVA (15%) |

<details><summary>Score anchors</summary>

- **C08.1** — 0: None identified · 1: Fewer than half · 2: Most, confuses switchgear symbols · 3: All but one · 4: All symbols correct
- **C08.2** — 0: Cannot trace · 1: Traces with guidance · 2: Traces path, wrong device order · 3: Correct with hesitation · 4: Correct path and device sequence, explains why
- **C08.3** — 0: No list · 1: List with major omissions, guided · 2: List with 2+ omissions · 3: List complete, one quantity off · 4: Complete, correct list
- **C08.4** — 0: No answer · 1: Answers only with leading questions · 2: Partly correct · 3: Correct, minor gaps · 4: Correct and complete in own words

</details>

Required evidence: Annotated diagram / material list (document, C08.3)

Safety requirements: —


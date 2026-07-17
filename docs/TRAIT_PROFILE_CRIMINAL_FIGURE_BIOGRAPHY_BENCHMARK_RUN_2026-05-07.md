# Trait Criminal-Figure Biography Correctness Report

- Suite: `trait_criminal_figure_biography_correctness_aa_a`
- Cases: 21
- Cases passed: 21/21
- Clusters passed: 21/21
- Elapsed: 6258 ms
- Result: PASS

This benchmark checks whether chart-derived top traits align with documented criminal-case biographies. It is not a criminality detector and must not be used to infer guilt, risk, or diagnosis.

## Case Results

### PASS Ted Bundy (`ted_bundy`)

- Role target: serial murder and violent predation
- Birth source: https://arcadia-astrology.com/en/astrodb/bundy-ted (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Ted_Bundy
- Top traits: `destructiveness` 100.0, `cunning` 66.7, `ruthlessness` 54.5, `knavery_trickery_deceit` 69.2, `lying_falsehood` 69.2, `recklessness` 40.0, `rashness` 43.8, `government_authority` 38.1, `cowardice` 100.0, `intolerance` 100.0
- PASS `serial_predation_deception`: `destructiveness` score 100.0 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on serial murder, abduction, deceptive presentation, and violent predation.

### PASS Jeffrey Dahmer (`jeffrey_dahmer`)

- Role target: serial murder, violence, and extreme secrecy
- Birth source: https://arcadia-astrology.com/en/astrodb/dahmer-jeffrey (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Jeffrey_Dahmer
- Top traits: `cunning` 58.3, `severity` 46.2, `pugnacity` 32.7, `domination_capricorn` 66.7, `calculation` 65.0, `tyranny` 36.4, `reticence` 40.0, `government_authority` 76.2, `watchfulness` 75.0, `enterprise_initiative` 71.4
- PASS `serial_violence_concealment`: `domination_capricorn` score 66.7 rank 4; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on serial murder, concealment, domination of victims, and extreme violence.

### PASS John Wayne Gacy (`john_wayne_gacy`)

- Role target: serial murder and public-mask duplicity
- Birth source: https://arcadia-astrology.com/en/astrodb/gacy-john-wayne (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/John_Wayne_Gacy
- Top traits: `disruptiveness` 40.0, `calculation` 45.0, `knavery_trickery_deceit` 69.2, `lying_falsehood` 53.8, `reticence` 30.0, `government_authority` 38.1, `rashness` 37.5, `watchfulness` 31.2, `zealotry` 83.3, `neglect_of_duty` 80.0
- PASS `public_mask_serial_violence`: `knavery_trickery_deceit` score 69.2 rank 3; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography emphasizes civic/public masking alongside serial murder and deception.

### PASS Charles Manson (`charles_manson`)

- Role target: cult leadership, manipulation, and violence
- Birth source: https://arcadia-astrology.com/en/astrodb/manson-charles (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Charles_Manson
- Top traits: `cunning` 58.3, `severity` 46.2, `ruthlessness` 54.5, `wrath` 68.4, `calculation` 60.0, `tyranny` 63.6, `subtlety` 42.9, `reticence` 100.0, `government_authority` 66.7, `watchfulness` 56.2
- PASS `cult_control_violence`: `reticence` score 100.0 rank 8; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on cult control, manipulation, criminal command, and violent ideology.

### PASS David Berkowitz (`david_berkowitz`)

- Role target: serial shootings and destabilizing violence
- Birth source: https://arcadia-astrology.com/en/astrodb/berkowitz-david (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/David_Berkowitz
- Top traits: `severity` 46.2, `destructiveness` 45.5, `cunning` 41.7, `calculation` 50.0, `recklessness` 53.3, `subtlety` 42.9, `reticence` 30.0, `government_authority` 66.7, `watchfulness` 56.2, `zestlessness` 82.4
- PASS `serial_shooting_disruption`: `recklessness` score 53.3 rank 5; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on serial shootings, public fear, and destabilizing violence.

### PASS Mark David Chapman (`mark_david_chapman`)

- Role target: assassination and obsessive public violence
- Birth source: https://arcadia-astrology.com/en/astrodb/chapman-mark-david (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Mark_David_Chapman
- Top traits: `destructiveness` 45.5, `ruthlessness` 72.7, `tyranny` 54.5, `recklessness` 46.7, `lying_falsehood` 30.8, `enterprise_initiative` 71.4, `rashness` 37.5, `watchfulness` 37.5, `rebellion` 33.3, `intolerance` 58.3
- PASS `assassination_obsession`: `ruthlessness` score 72.7 rank 2; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on John Lennon's assassination and obsessive public violence.

### PASS Gary Gilmore (`gary_gilmore`)

- Role target: murder, defiance, and death-penalty notoriety
- Birth source: https://arcadia-astrology.com/en/astrodb/gilmore-gary (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Gary_Gilmore
- Top traits: `cunning` 83.3, `severity` 46.2, `ruthlessness` 100.0, `pugnacity` 36.7, `warlike` 36.7, `wrath` 36.8, `calculation` 30.0, `tyranny` 81.8, `lying_falsehood` 30.8, `subtlety` 42.9
- PASS `murder_defiance`: `ruthlessness` score 100.0 rank 3; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on murder convictions, defiance, and death-penalty notoriety.

### PASS John Hinckley Jr. (`john_hinckley_jr`)

- Role target: attempted assassination and obsessive public fixation
- Birth source: https://arcadia-astrology.com/en/astrodb/hinckley-john-jr (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/John_Hinckley_Jr.
- Top traits: `ruthlessness` 45.5, `calculation` 30.0, `recklessness` 46.7, `knavery_trickery_deceit` 46.2, `lying_falsehood` 30.8, `subtlety` 78.6, `enterprise_initiative` 42.9, `watchfulness` 37.5, `rebellion` 33.3, `intolerance` 58.3
- PASS `attempted_assassination_fixation`: `subtlety` score 78.6 rank 6; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on attempted assassination, fixation, and institutional confinement after a not-guilty-by-insanity verdict.

### PASS Squeaky Fromme (`squeaky_fromme`)

- Role target: cult allegiance and attempted assassination
- Birth source: https://arcadia-astrology.com/en/astrodb/fromme-squeaky (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Squeaky_Fromme
- Top traits: `destructiveness` 45.5, `calculation` 30.0, `reticence` 30.0, `enterprise_initiative` 42.9, `cowardice` 50.0, `neglect_of_duty` 50.0, `venturesomeness` 51.0, `restlessness` 100.0, `greed_covetousness` 41.2, `conservatism` 33.3
- PASS `cult_allegiance_attempted_assassination`: `restlessness` score 100.0 rank 8; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on Manson-family allegiance and attempted assassination of President Gerald Ford.

### PASS Robert Hansen (`robert_hansen`)

- Role target: serial murder and predatory violence
- Birth source: https://arcadia-astrology.com/en/astrodb/hansen-robert (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Robert_Hansen
- Top traits: `destructiveness` 45.5, `disruptiveness` 40.0, `lying_falsehood` 69.2, `knavery_trickery_deceit` 53.8, `recklessness` 46.7, `rebellion` 40.0, `rashness` 31.2, `neglect_of_duty` 60.0, `intolerance` 58.3, `vanity` 44.4
- PASS `predatory_serial_murder`: `lying_falsehood` score 69.2 rank 3; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on serial murder, abduction, deception, and predatory violence.

### PASS Clifford Olson (`clifford_olson`)

- Role target: serial murder and predatory violence
- Birth source: https://arcadia-astrology.com/en/astrodb/olson-clifford (Arcadia AstroDB citing Astro-Databank Rodden A)
- Biography sources: https://en.wikipedia.org/wiki/Clifford_Olson
- Top traits: `destructiveness` 45.5, `pugnacity` 36.7, `warlike` 36.7, `recklessness` 66.7, `knavery_trickery_deceit` 46.2, `lying_falsehood` 46.2, `self_assertion` 37.5, `enterprise_initiative` 71.4, `rashness` 68.8, `rebellion` 33.3
- PASS `serial_predatory_violence`: `violence` score 75.0 rank 11; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on serial child murders, deception, and predatory violence.

### PASS Nathan Leopold (`nathan_leopold`)

- Role target: planned murder and intellectualized transgression
- Birth source: https://arcadia-astrology.com/en/astrodb/leopold-nathan (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Leopold_and_Loeb
- Top traits: `severity` 76.9, `destructiveness` 45.5, `cunning` 41.7, `ruthlessness` 100.0, `pugnacity` 44.9, `warlike` 32.7, `calculation` 45.0, `wrath` 31.6, `knavery_trickery_deceit` 46.2, `lying_falsehood` 46.2
- PASS `planned_intellectualized_murder`: `ruthlessness` score 100.0 rank 4; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on the planned Leopold and Loeb murder and intellectualized transgression.

### PASS Reggie Kray (`reggie_kray`)

- Role target: organized crime leadership and violence
- Birth source: https://arcadia-astrology.com/en/astrodb/kray-reggie (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Kray_twins
- Top traits: `cunning` 58.3, `destructiveness` 45.5, `severity` 30.8, `wrath` 68.4, `calculation` 30.0, `reticence` 50.0, `enterprise_initiative` 42.9, `watchfulness` 31.2, `zestlessness` 70.6, `zealotry` 66.7
- PASS `gangland_control_violence`: `cunning` score 58.3 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on organized crime, gangland violence, and underworld leadership.

### PASS Ronnie Kray (`ronnie_kray`)

- Role target: organized crime leadership and violence
- Birth source: https://arcadia-astrology.com/en/astrodb/kray-ronnie (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Kray_twins
- Top traits: `cunning` 58.3, `destructiveness` 45.5, `severity` 30.8, `wrath` 68.4, `calculation` 30.0, `reticence` 50.0, `enterprise_initiative` 42.9, `watchfulness` 31.2, `zestlessness` 70.6, `zealotry` 66.7
- PASS `gangland_control_violence`: `cunning` score 58.3 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on organized crime, gangland violence, and underworld leadership.

### PASS Lucky Luciano (`lucky_luciano`)

- Role target: organized crime enterprise and syndicate leadership
- Birth source: https://arcadia-astrology.com/en/astrodb/luciano-lucky (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Lucky_Luciano
- Top traits: `destructiveness` 100.0, `cunning` 66.7, `severity` 46.2, `ruthlessness` 100.0, `disruptiveness` 40.0, `pugnacity` 36.7, `warlike` 36.7, `wrath` 63.2, `recklessness` 46.7, `knavery_trickery_deceit` 30.8
- PASS `organized_crime_enterprise`: `destructiveness` score 100.0 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on organized-crime syndicate formation, coercive enterprise, and underworld power.

### PASS Frank Coppola (`frank_coppola`)

- Role target: organized crime violence and underworld leadership
- Birth source: https://arcadia-astrology.com/en/astrodb/coppola-frank (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Frank_Coppola_(mobster)
- Top traits: `cunning` 58.3, `destructiveness` 45.5, `recklessness` 46.7, `enterprise_initiative` 35.7, `neglect_of_duty` 100.0, `zealotry` 50.0, `zestlessness` 47.1, `overconfidence` 42.9, `violence` 41.7, `prodigality` 38.5
- PASS `mafia_underworld_leadership`: `cunning` score 58.3 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on Mafia leadership, underworld enterprise, and criminal violence.

### PASS David Carpenter (`david_carpenter`)

- Role target: serial murder and predatory violence
- Birth source: https://arcadia-astrology.com/en/astrodb/carpenter-david (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/David_Carpenter
- Top traits: `severity` 61.5, `cunning` 33.3, `ruthlessness` 45.5, `pugnacity` 53.1, `warlike` 40.8, `wrath` 47.4, `calculation` 45.0, `knavery_trickery_deceit` 46.2, `lying_falsehood` 30.8, `reticence` 60.0
- PASS `serial_predatory_violence`: `watchfulness` score 75.0 rank 12; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on serial murder, predation, and repeated violent attacks.

### PASS Caryl Chessman (`caryl_chessman`)

- Role target: kidnapping, sexual assault, and legal notoriety
- Birth source: https://arcadia-astrology.com/en/astrodb/chessman-caryl (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Caryl_Chessman
- Top traits: `severity` 46.2, `destructiveness` 45.5, `ruthlessness` 72.7, `calculation` 60.0, `recklessness` 80.0, `reticence` 30.0, `watchfulness` 62.5, `government_authority` 38.1, `rashness` 31.2, `cowardice` 100.0
- PASS `kidnapping_legal_notoriety`: `recklessness` score 80.0 rank 5; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on kidnapping, sexual assault conviction, death-row writing, and legal notoriety.

### PASS Kenneth Kimes Jr. (`kenneth_kimes_jr`)

- Role target: fraud, murder, and criminal family enterprise
- Birth source: https://arcadia-astrology.com/en/astrodb/kimes-kenneth-jr (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Sante_Kimes
- Top traits: `destructiveness` 100.0, `cunning` 66.7, `pugnacity` 32.7, `warlike` 32.7, `calculation` 35.0, `recklessness` 100.0, `lying_falsehood` 53.8, `knavery_trickery_deceit` 38.5, `self_assertion` 33.3, `rashness` 68.8
- PASS `fraud_murder_family_enterprise`: `destructiveness` score 100.0 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on fraud schemes, murder, deception, and criminal activity with Sante Kimes.

### PASS Giovanni Brusca (`giovanni_brusca`)

- Role target: mafia violence, assassination, and command activity
- Birth source: https://arcadia-astrology.com/en/astrodb/brusca-giovanni (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Giovanni_Brusca
- Top traits: `severity` 46.2, `cunning` 41.7, `ruthlessness` 100.0, `calculation` 50.0, `wrath` 36.8, `tyranny` 81.8, `recklessness` 80.0, `lying_falsehood` 61.5, `knavery_trickery_deceit` 46.2, `subtlety` 64.3
- PASS `mafia_assassination_command`: `ruthlessness` score 100.0 rank 3; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on Mafia command violence, assassination activity, and organized-crime enforcement.

### PASS Salvatore Riina (`salvatore_riina`)

- Role target: mafia leadership, violence, and domination
- Birth source: https://arcadia-astrology.com/en/astrodb/riina-salvatore (Arcadia AstroDB citing Astro-Databank Rodden AA)
- Biography sources: https://en.wikipedia.org/wiki/Salvatore_Riina
- Top traits: `cunning` 83.3, `severity` 46.2, `ruthlessness` 72.7, `subtlety` 50.0, `reticence` 70.0, `leadership_executive` 31.2, `watchfulness` 31.2, `zestlessness` 82.4, `intolerance` 58.3, `perseverance` 61.5
- PASS `mafia_domination_leadership`: `cunning` score 83.3 rank 1; One expected trait must have score >= 30 and summary rank <= 12.
  Rationale: Biography centers on Cosa Nostra leadership, domination, violence, and underworld command.

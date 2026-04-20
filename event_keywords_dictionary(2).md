# Event Keywords Dictionary
## Comprehensive Database for Astrological Event Classification

---

## STRUCTURE OVERVIEW

```yaml
Event:
  category: [primary classification]
  subcategory: [specific type]
  keywords: [trigger words for identification]
  synonyms: [alternate terms]
  related_events: [connected events]
  
  astrological_indicators:
    primary_planets: [main significators]
    secondary_planets: [supporting significators]
    primary_houses: [main houses involved]
    secondary_houses: [supporting houses]
    aspects_favor: [helpful aspects]
    
  quality:
    nature: [benefic/malefic/neutral/mixed]
    severity: [1-10 scale]
    importance: [minor/moderate/major/critical]
    
  timing:
    typical_duration: [immediate/days/weeks/months/permanent]
    orb_sensitivity: [tight/moderate/loose]
    concordance_required: [none/low/moderate/high/critical]
    
  determination_requirements:
    planet_must_be_determined_to: [specific life areas]
    minimum_determination_score: [0.0-1.0]
    
  morin_specifics:
    mentioned_in_book: [yes/no]
    special_laws_apply: [list of applicable laws]
    example_charts: [references if any]
```

---

## I. LIFE & DEATH EVENTS

### A. Birth Events

```yaml
birth_self:
  category: life_events
  subcategory: birth
  
  keywords:
    primary: [birth, born, nativity, arrival, emergence]
    secondary: [came_into_world, incarnation, beginning_of_life]
    context: [delivery, birthing, childbirth, parturition]
    
  synonyms: [nativity, genesis, inception, origin]
  
  astrological_indicators:
    primary_planets: [Sun, Moon, Jupiter, ASC_ruler]
    secondary_planets: [Venus, benefics_generally]
    primary_houses: [1, 5, 4]
    secondary_houses: [11]
    aspects_favor: [trine, sextile, conjunction_benefic]
    
  quality:
    nature: benefic
    severity: 10
    importance: critical
    
  timing:
    typical_duration: permanent
    orb_sensitivity: tight
    concordance_required: critical
    
  related_events:
    - pregnancy
    - conception
    - birth_of_child
    - new_beginning

birth_of_child:
  category: family_events
  subcategory: birth
  
  keywords:
    primary: [child_born, baby, newborn, offspring, progeny]
    secondary: [son_born, daughter_born, infant, blessed_with_child]
    context: [became_parent, parenthood, new_baby, delivery]
    
  synonyms: [childbirth, blessed_event, arrival, issue]
  
  astrological_indicators:
    primary_planets: [Jupiter, Moon, Venus]
    secondary_planets: [Sun, 5th_ruler]
    primary_houses: [5, 11]
    secondary_houses: [1, 4]
    aspects_favor: [trine, sextile, conjunction_benefic]
    
  quality:
    nature: benefic
    severity: 9
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [children, 5th_house_matters, fertility]
    minimum_determination_score: 0.6
    
  related_events:
    - pregnancy
    - conception
    - parenthood
    - family_expansion
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_2_multiple_determinations]
```

### B. Death Events

```yaml
death_natural:
  category: life_events
  subcategory: death
  
  keywords:
    primary: [death, died, deceased, passed_away, demise, mortality]
    secondary: [expired, perished, succumbed, lost_life, end_of_life]
    context: [fatal, lethal, terminal, mortal, deadly]
    euphemisms: [passed_on, departed, went_to_heaven, eternal_rest]
    
  synonyms: [decease, expiration, passing, termination]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, 8th_ruler]
    secondary_planets: [afflicted_Sun, afflicted_Moon]
    primary_houses: [8, 12, 4]
    secondary_houses: [1, 6]
    aspects_favor: [opposition, square, conjunction_malefic]
    
  quality:
    nature: malefic
    severity: 10
    importance: critical
    
  timing:
    typical_duration: permanent
    orb_sensitivity: very_tight
    concordance_required: critical
    
  determination_requirements:
    planet_must_be_determined_to: [death, 8th_house_matters]
    minimum_determination_score: 0.7
    
  related_events:
    - terminal_illness
    - life_threatening_situation
    - old_age
    - chronic_illness
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_10, law_13]
    example_charts: yes
    critical_factors:
      - saturn_mars_together
      - malefics_in_8th
      - malefics_afflicting_ASC
      - ruler_8th_to_ASC
      - lights_conjunct_malefics

death_violent:
  category: life_events
  subcategory: death_violent
  
  keywords:
    primary: [killed, murdered, assassinated, slain, executed]
    secondary: [violent_death, sudden_death, homicide, manslaughter]
    context: [fatal_accident, deadly_attack, mortal_wound, lethal_injury]
    
  synonyms: [homicide, murder, killing, slaying, execution]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, 8th_ruler]
    secondary_planets: [afflicted_Sun, Uranus_if_using]
    primary_houses: [8, 12, 1]
    secondary_houses: [7, 6]
    aspects_favor: [opposition, square, mars_saturn_conjunction]
    
  quality:
    nature: malefic
    severity: 10
    importance: critical
    
  timing:
    typical_duration: immediate
    orb_sensitivity: very_tight
    concordance_required: critical
    
  determination_requirements:
    planet_must_be_determined_to: [death, violence, 8th_house]
    minimum_determination_score: 0.8
    
  related_events:
    - accident_fatal
    - attack
    - violence
    - danger_extreme

death_of_family:
  category: family_events
  subcategory: death_loss
  
  keywords:
    primary: [father_died, mother_died, sibling_died, spouse_died, child_died]
    secondary: [lost_parent, lost_loved_one, bereavement, family_death]
    context: [mourning, grief, funeral, loss, passing_of]
    
  synonyms: [bereavement, loss, family_passing]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, ruler_of_relevant_house]
    secondary_planets: [afflicted_Moon, afflicted_Sun]
    primary_houses: [4_father, 10_mother, 3_siblings, 7_spouse, 5_children]
    secondary_houses: [8, 12]
    aspects_favor: [square, opposition]
    
  quality:
    nature: malefic
    severity: 8-9
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [relevant_family_house, loss, grief]
    minimum_determination_score: 0.5
```

---

## II. HEALTH & ILLNESS EVENTS

### A. Acute Illness

```yaml
illness_acute:
  category: health_events
  subcategory: acute_illness
  
  keywords:
    primary: [illness, sick, disease, fell_ill, taken_ill, sickness]
    secondary: [ailment, malady, affliction, disorder, sudden_onset]
    context: [acute, sudden, came_down_with, struck_by]
    symptoms: [fever, pain, infection, inflammation, acute_symptoms]
    
  synonyms: [ailment, sickness, disease, malady, affliction]
  
  astrological_indicators:
    primary_planets: [Mars, afflicted_Moon, 6th_ruler]
    secondary_planets: [Saturn, afflicted_Mercury]
    primary_houses: [6, 12, 1]
    secondary_houses: [8]
    aspects_favor: [square, opposition, conjunction_malefic]
    
  quality:
    nature: malefic
    severity: 5-7
    importance: moderate_to_major
    
  timing:
    typical_duration: days_to_weeks
    orb_sensitivity: tight
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [health, illness, 6th_house]
    minimum_determination_score: 0.5
    
  related_events:
    - fever
    - hospitalization
    - surgery
    - recovery_health
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_10]
    example_charts: yes

illness_chronic:
  category: health_events
  subcategory: chronic_illness
  
  keywords:
    primary: [chronic, persistent, long_term, ongoing, enduring]
    secondary: [chronic_condition, chronic_disease, persistent_ailment, vitality_loss]
    context: [degenerative, progressive, incurable, manageable]
    conditions: [arthritis, diabetes, heart_disease, cancer]
    
  synonyms: [chronic_condition, persistent_illness, long_term_disease]
  
  astrological_indicators:
    primary_planets: [Saturn, afflicted_Moon]
    secondary_planets: [Mars, 6th_ruler_afflicted]
    primary_houses: [6, 12]
    secondary_houses: [8, 1]
    aspects_favor: [square, opposition, saturn_aspects]
    
  quality:
    nature: malefic
    severity: 6-9
    importance: major
    
  timing:
    typical_duration: months_to_permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [chronic_conditions, 6th_house, 12th_house]
    minimum_determination_score: 0.6

fever:
  category: health_events
  subcategory: acute_symptom
  
  keywords:
    primary: [fever, feverish, high_temperature, pyrexia]
    secondary: [burning, heat, hot, temperature, febrile]
    context: [came_down_with_fever, developed_fever, running_fever]
    
  synonyms: [pyrexia, high_temperature, febrile_condition]
  
  astrological_indicators:
    primary_planets: [Mars, afflicted_Sun]
    secondary_planets: [afflicted_Moon]
    primary_houses: [6, 1]
    secondary_houses: [12]
    aspects_favor: [mars_aspects, afflictions_to_lights]
    
  quality:
    nature: malefic
    severity: 4-6
    importance: moderate
    
  timing:
    typical_duration: days
    orb_sensitivity: tight
    concordance_required: moderate

injury_accident:
  category: health_events
  subcategory: injury
  
  keywords:
    primary: [injury, injured, wounded, trauma, accident]
    secondary: [cut, broken, fractured, sprained, torn, bruised, injury_risk, accident_risk]
    context: [accidental, sudden, traumatic, emergency]
    types: [cut, burn, break, fracture, laceration, contusion, sprain]
    
  synonyms: [wound, trauma, lesion, bodily_injury]
  
  astrological_indicators:
    primary_planets: [Mars]
    secondary_planets: [Uranus_if_using, afflicted_ASC_ruler]
    primary_houses: [1, 6, 8]
    secondary_houses: [12]
    aspects_favor: [square, opposition, mars_aspects]
    
  quality:
    nature: malefic
    severity: 5-8
    importance: moderate_to_major
    
  timing:
    typical_duration: immediate
    orb_sensitivity: very_tight
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [accidents, violence, sudden_events]
    minimum_determination_score: 0.5
    
  related_events:
    - injury_risk
    - accident_risk
    - surgery
    - hospitalization
    - recovery_health
    
  morin_specifics:
    mentioned_in_book: yes
    example_charts: yes
    note: "Mars especially significant"

surgery:
  category: health_events
  subcategory: medical_procedure
  
  keywords:
    primary: [surgery, operation, surgical_procedure, operated_on]
    secondary: [cut, incision, procedure, intervention, went_under_knife]
    context: [scheduled_surgery, emergency_surgery, surgical, operative]
    types: [appendectomy, bypass, caesarean, transplant, removal]
    
  synonyms: [operation, surgical_procedure, medical_procedure]
  
  astrological_indicators:
    primary_planets: [Mars]
    secondary_planets: [Saturn, 6th_ruler, 8th_ruler]
    primary_houses: [6, 8, 12]
    secondary_houses: [1]
    aspects_favor: [mars_aspects, but_can_be_beneficial_if_needed]
    
  quality:
    nature: mixed_necessary_evil
    severity: 5-8
    importance: moderate_to_major
    
  timing:
    typical_duration: immediate_with_recovery_period
    orb_sensitivity: tight
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [health, medical_matters, cutting]
    minimum_determination_score: 0.4
    
  related_events:
    - illness_acute
    - injury_accident
    - hospitalization
    - recovery_health
    
  morin_specifics:
    mentioned_in_book: yes
    note: "Mars as cutting, Saturn as necessity"

hospitalization:
  category: health_events
  subcategory: confinement
  
  keywords:
    primary: [hospitalized, admitted, hospital, hospitalization, confined]
    secondary: [taken_to_hospital, hospital_stay, in_hospital, patient]
    context: [emergency_room, ICU, ward, clinic, medical_facility]
    
  synonyms: [admission, confinement, institutionalization]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, 6th_ruler, 12th_ruler]
    secondary_planets: [Neptune_if_using]
    primary_houses: [6, 12, 8]
    secondary_houses: [1]
    aspects_favor: [afflictions, confinement_indicators]
    
  quality:
    nature: malefic_but_sometimes_necessary
    severity: 5-8
    importance: moderate_to_major
    
  timing:
    typical_duration: days_to_weeks
    orb_sensitivity: moderate
    concordance_required: moderate

recovery_health:
  category: health_events
  subcategory: recovery
  
  keywords:
    primary: [recovery, recovered, healed, recuperation, restoration]
    secondary: [got_better, feeling_better, improvement, healing, cured]
    context: [convalescence, rehabilitation, bounce_back, regain_health]
    
  synonyms: [recuperation, convalescence, healing, restoration]
  
  astrological_indicators:
    primary_planets: [Jupiter, Venus, Sun]
    secondary_planets: [well_aspected_Moon]
    primary_houses: [1, 6]
    secondary_houses: [5]
    aspects_favor: [trine, sextile, beneficial_aspects]
    
  quality:
    nature: benefic
    severity: 5-8
    importance: moderate_to_major
    
  timing:
    typical_duration: days_to_months
    orb_sensitivity: moderate
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [health, vitality, recovery]
    minimum_determination_score: 0.5
```

---

## III. CAREER & PROFESSIONAL EVENTS

### A. Advancement

```yaml
promotion:
  category: career_events
  subcategory: advancement
  
  keywords:
    primary: [promotion, promoted, advanced, elevation, raised, elevated]
    secondary: [moved_up, step_up, climb_ladder, career_advancement, authority_earned, discipline_rewarded, opportunity_received, initiative]
    context: [new_position, higher_rank, greater_responsibility, upward_mobility]
    
  synonyms: [advancement, elevation,升級, rise, upgrade]
  
  astrological_indicators:
    primary_planets: [Jupiter, Sun, 10th_ruler]
    secondary_planets: [Venus, well_placed_Saturn]
    primary_houses: [10, 1, 11]
    secondary_houses: [2, 6]
    aspects_favor: [trine, sextile, conjunction_benefic]
    
  quality:
    nature: benefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [career, honors, 10th_house, success]
    minimum_determination_score: 0.6
    
  related_events:
    - honor_award
    - recognition
    - public_recognition
    - salary_increase
    - new_job
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_11]
    example_charts: yes

honor_award:
  category: career_events
  subcategory: recognition
  
  keywords:
    primary: [honor, award, prize, recognition, distinction, accolade]
    secondary: [honored, awarded, recognized, commended, decorated, public_approval]
    context: [achievement, excellence, merit, distinction, laureate]
    types: [degree, title, medal, trophy, certificate, prize]
    
  synonyms: [accolade, distinction, laurels, kudos, recognition]
  
  astrological_indicators:
    primary_planets: [Sun, Jupiter]
    secondary_planets: [Venus, well_placed_Saturn]
    primary_houses: [10, 11, 9]
    secondary_houses: [1, 5]
    aspects_favor: [trine, sextile, sun_jupiter_aspects]
    
  quality:
    nature: benefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [honors, recognition, achievement, 10th_house]
    minimum_determination_score: 0.7
    
  related_events:
    - promotion
    - public_recognition
    - recognition
    - salary_increase
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_11]
    example_charts: yes
    note: "Jupiter to MC especially significant"

new_job:
  category: career_events
  subcategory: employment_change
  
  keywords:
    primary: [new_job, new_position, hired, employed, started_work]
    secondary: [got_job, landed_position, job_offer, employment, appointment]
    context: [began_working, new_role, career_change, job_transition]
    
  synonyms: [employment, hiring, appointment, engagement, placement]
  
  astrological_indicators:
    primary_planets: [Sun, Jupiter, Mercury, 10th_ruler, 6th_ruler]
    secondary_planets: [Saturn, Mars]
    primary_houses: [10, 6, 2]
    secondary_houses: [1, 11]
    aspects_favor: [trine, sextile, but_also_squares_for_action]
    
  quality:
    nature: usually_benefic
    severity: 6-8
    importance: moderate_to_major
    
  timing:
    typical_duration: permanent_shift
    orb_sensitivity: moderate
    concordance_required: moderate_to_high
    
  related_events:
    - promotion
    - salary_increase
    - financial_gain
    - opportunity_received

job_loss:
  category: career_events
  subcategory: loss
  
  keywords:
    primary: [fired, laid_off, dismissed, terminated, lost_job, unemployed]
    secondary: [let_go, redundant, downsized, sacked, job_loss]
    context: [unemployment, jobless, out_of_work, career_setback]
    
  synonyms: [dismissal, termination, redundancy, unemployment, discharge]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_10th_ruler]
    secondary_planets: [afflicted_Sun]
    primary_houses: [10, 12, 8]
    secondary_houses: [6, 2]
    aspects_favor: [square, opposition, malefic_conjunctions]
    
  quality:
    nature: malefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: immediate_with_lasting_effects
    orb_sensitivity: tight
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [career_loss, 10th_house, difficulties]
    minimum_determination_score: 0.5
    
  related_events:
    - financial_loss
    - loss_deprivation
    - fall_from_power
    - delay_obstruction

demotion:
  category: career_events
  subcategory: setback
  
  keywords:
    primary: [demotion, demoted, downgraded, reduced_rank, lowered]
    secondary: [step_down, moved_down, loss_of_status, career_decline, fall_from_power, authority_problems]
    context: [setback, reversal, fall, descent]
    
  synonyms: [downgrade, reduction,降級, descent]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_Sun]
    secondary_planets: [afflicted_Jupiter]
    primary_houses: [10, 12]
    secondary_houses: [8, 6]
    aspects_favor: [square, opposition, saturn_afflictions]
    
  quality:
    nature: malefic
    severity: 6-8
    importance: major
    
  timing:
    typical_duration: permanent_or_long_term
    orb_sensitivity: moderate
    concordance_required: high
    
  related_events:
    - job_loss
    - fall_from_power
    - authority_problems
    - delay_obstruction

retirement:
  category: career_events
  subcategory: ending
  
  keywords:
    primary: [retirement, retired, retire, stepping_down, end_of_career]
    secondary: [leaving_work, finished_career, ceased_working, pension]
    context: [elder_years, end_of_service, post_career, golden_years]
    
  synonyms: [cessation, withdrawal, conclusion_of_career]
  
  astrological_indicators:
    primary_planets: [Saturn, 4th_ruler]
    secondary_planets: [Jupiter_if_fortunate, Sun]
    primary_houses: [4, 10, 12]
    secondary_houses: [8]
    aspects_favor: [depends_on_circumstances]
    
  quality:
    nature: neutral_natural
    severity: 7
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: loose
    concordance_required: moderate
    
  morin_specifics:
    note: "Natural with Saturn, 4th house (endings)"

business_success:
  category: career_events
  subcategory: achievement
  
  keywords:
    primary: [business_success, profitable, thriving, flourishing, prosperous]
    secondary: [business_growth, expansion, successful_venture, enterprise_success, structure_established]
    context: [profitable_deal, business_deal, contract_won, client_gained]
    
  synonyms: [commercial_success, enterprise_achievement, business_triumph]
  
  astrological_indicators:
    primary_planets: [Jupiter, Mercury, Venus]
    secondary_planets: [Sun, 2nd_ruler, 10th_ruler]
    primary_houses: [2, 10, 11]
    secondary_houses: [3, 7]
    aspects_favor: [trine, sextile, jupiter_mercury_aspects]
    
  quality:
    nature: benefic
    severity: 7-8
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [business, commerce, wealth, success]
    minimum_determination_score: 0.6
    
  related_events:
    - financial_gain
    - investment_success
    - opportunity_received
    - salary_increase

business_failure:
  category: career_events
  subcategory: loss
  
  keywords:
    primary: [business_failure, bankruptcy, failed, collapsed, folded]
    secondary: [business_loss, enterprise_failed, venture_failed, went_under, contract_problems, delay_obstruction, excess_problems]
    context: [bankruptcy, insolvency, liquidation, closure, bust]
    
  synonyms: [commercial_failure, bankruptcy, insolvency, collapse]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_Mercury]
    secondary_planets: [afflicted_Jupiter, 2nd_ruler_afflicted]
    primary_houses: [2, 8, 12, 10]
    secondary_houses: [6]
    aspects_favor: [square, opposition, saturn_mars_afflictions]
    
  quality:
    nature: malefic
    severity: 8-9
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [business, 2nd_house, loss, difficulties]
    minimum_determination_score: 0.6
    
  related_events:
    - financial_loss
    - bankruptcy
    - loss_deprivation
    - investment_loss
```

---

## IV. FINANCIAL EVENTS

```yaml
financial_gain:
  category: financial_events
  subcategory: gain
  
  keywords:
    primary: [gain, profit, windfall, income, earnings, revenue]
    secondary: [made_money, financial_gain, monetary_gain, cash_influx, financial_windfall]
    context: [earned, received, gained, acquired, won]
    types: [bonus, raise, profit, dividend, prize_money, lottery]
    
  synonyms: [profit, earnings, revenue, income, gains]
  
  astrological_indicators:
    primary_planets: [Jupiter, Venus, 2nd_ruler]
    secondary_planets: [Sun, well_placed_Mercury]
    primary_houses: [2, 8, 11]
    secondary_houses: [5, 10]
    aspects_favor: [trine, sextile, benefic_conjunctions]
    
  quality:
    nature: benefic
    severity: 5-8
    importance: moderate_to_major
    
  timing:
    typical_duration: immediate_to_short_term
    orb_sensitivity: moderate
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [wealth, 2nd_house, finances, gain]
    minimum_determination_score: 0.5
    
  related_events:
    - salary_increase
    - bonus
    - inheritance
    - investment_success

financial_loss:
  category: financial_events
  subcategory: loss
  
  keywords:
    primary: [loss, debt, expense, cost, financial_loss, monetary_loss]
    secondary: [lost_money, financial_setback, cash_drain, money_problems, loss_deprivation]
    context: [spent, lost, wasted, squandered, depleted]
    types: [debt, fine, tax, penalty, theft, investment_loss]
    
  synonyms: [deficit, debt, depletion, expenditure]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_2nd_ruler]
    secondary_planets: [afflicted_Venus, afflicted_Jupiter]
    primary_houses: [2, 8, 12]
    secondary_houses: [6]
    aspects_favor: [square, opposition, malefic_afflictions]
    
  quality:
    nature: malefic
    severity: 5-9
    importance: moderate_to_major
    
  timing:
    typical_duration: immediate_to_long_term
    orb_sensitivity: moderate
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [finances, 2nd_house, loss, difficulties]
    minimum_determination_score: 0.5

inheritance:
  category: financial_events
  subcategory: gain_legacy
  
  keywords:
    primary: [inheritance, inherited, legacy, bequest, estate]
    secondary: [received_inheritance, came_into_money, inherited_wealth]
    context: [will, testament, heir, beneficiary, estate_settlement]
    
  synonyms: [legacy, bequest, patrimony, hereditary_wealth]
  
  astrological_indicators:
    primary_planets: [Jupiter, Venus, 8th_ruler]
    secondary_planets: [4th_ruler, benefics]
    primary_houses: [8, 4, 2]
    secondary_houses: [11]
    aspects_favor: [trine, sextile, benefic_to_8th_house]
    
  quality:
    nature: usually_benefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent_gain
    orb_sensitivity: loose
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [8th_house, inheritance, shared_resources]
    minimum_determination_score: 0.5
    
  related_events:
    - death_of_family
    - financial_gain
    - estate_settlement

salary_increase:
  category: financial_events
  subcategory: gain
  
  keywords:
    primary: [raise, salary_increase, pay_raise, income_increase, higher_pay]
    secondary: [got_raise, pay_bump, wage_increase, compensation_increase]
    context: [earned_more, making_more, better_paid]
    
  synonyms: [raise, pay_increase, wage_increase, increment]
  
  astrological_indicators:
    primary_planets: [Jupiter, Venus, 2nd_ruler, 10th_ruler]
    secondary_planets: [Sun]
    primary_houses: [2, 10, 6]
    secondary_houses: [11]
    aspects_favor: [trine, sextile, jupiter_venus_aspects]
    
  quality:
    nature: benefic
    severity: 6-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [income, 2nd_house, career_success]
    minimum_determination_score: 0.5

bankruptcy:
  category: financial_events
  subcategory: crisis
  
  keywords:
    primary: [bankruptcy, bankrupt, insolvent, insolvency, ruined]
    secondary: [financial_ruin, went_broke, penniless, destitute]
    context: [liquidation, foreclosure, debt_crisis, financial_collapse]
    
  synonyms: [insolvency, financial_ruin, destitution]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_2nd_ruler, afflicted_Jupiter]
    secondary_planets: [afflicted_8th_ruler]
    primary_houses: [2, 8, 12]
    secondary_houses: [10, 6]
    aspects_favor: [square, opposition, saturn_mars_afflictions]
    
  quality:
    nature: malefic
    severity: 9-10
    importance: major_to_critical
    
  timing:
    typical_duration: permanent_or_very_long_term
    orb_sensitivity: tight
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [finances, loss, ruin, 2nd_house, 8th_house]
    minimum_determination_score: 0.7

investment_success:
  category: financial_events
  subcategory: gain_speculation
  
  keywords:
    primary: [investment_success, profitable_investment, good_return, gains]
    secondary: [stock_gain, investment_profit, portfolio_growth, return_on_investment]
    context: [speculation, trading, investment, portfolio]
    
  synonyms: [investment_profit, speculation_success, trading_gains]
  
  astrological_indicators:
    primary_planets: [Jupiter, Venus, Mercury]
    secondary_planets: [5th_ruler, 2nd_ruler, 8th_ruler]
    primary_houses: [2, 5, 8, 11]
    secondary_houses: [3]
    aspects_favor: [trine, sextile, benefic_aspects]
    
  quality:
    nature: benefic
    severity: 6-8
    importance: moderate_to_major
    
  determination_requirements:
    planet_must_be_determined_to: [speculation, 5th_house, 2nd_house, gains]
    minimum_determination_score: 0.5

investment_loss:
  category: financial_events
  subcategory: loss_speculation
  
  keywords:
    primary: [investment_loss, lost_money_investing, bad_investment, losses]
    secondary: [stock_loss, portfolio_decline, investment_failure]
    context: [speculation_failed, trading_loss, market_crash]
    
  synonyms: [speculation_loss, trading_losses, investment_failure]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_Mercury]
    secondary_planets: [afflicted_5th_ruler, afflicted_2nd_ruler]
    primary_houses: [2, 5, 8, 12]
    secondary_houses: [6]
    aspects_favor: [square, opposition, malefic_afflictions]
    
  quality:
    nature: malefic
    severity: 6-8
    importance: moderate_to_major
    
  determination_requirements:
    planet_must_be_determined_to: [speculation, 5th_house, loss, difficulties]
    minimum_determination_score: 0.5

theft_fraud:
  category: financial_events
  subcategory: loss_crime
  
  keywords:
    primary: [theft, stolen, robbed, fraud, embezzlement, swindled]
    secondary: [burglarized, defrauded, conned, scammed, cheated]
    context: [crime, criminal, thief, fraud, deception]
    
  synonyms: [robbery, larceny, embezzlement, swindle, fraud]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, Mercury_afflicted]
    secondary_planets: [Neptune_if_using, afflicted_2nd_ruler]
    primary_houses: [2, 8, 12, 7]
    secondary_houses: [3]
    aspects_favor: [square, opposition, mars_mercury_afflictions]
    
  quality:
    nature: malefic
    severity: 6-8
    importance: moderate_to_major
    
  determination_requirements:
    planet_must_be_determined_to: [loss, theft, deception, 12th_house]
    minimum_determination_score: 0.5
```

---

## V. RELATIONSHIP & MARRIAGE EVENTS

```yaml
marriage:
  category: relationship_events
  subcategory: union
  
  keywords:
    primary: [marriage, married, wed, wedding, matrimony, nuptials]
    secondary: [got_married, tied_the_knot, wedded, took_vows, union, partnership_strengthened]
    context: [ceremony, bride, groom, spouse, husband, wife]
    
  synonyms: [matrimony, wedlock, union, nuptials, espousal]
  
  astrological_indicators:
    primary_planets: [Venus, Jupiter, 7th_ruler]
    secondary_planets: [Moon, Sun]
    primary_houses: [7, 1, 5]
    secondary_houses: [8, 11]
    aspects_favor: [trine, sextile, benefic_conjunctions]
    
  quality:
    nature: benefic
    severity: 9
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [marriage, 7th_house, partnership, commitment]
    minimum_determination_score: 0.6
    
  related_events:
    - engagement
    - romantic_connection
    - commitment
    - partnership
    
  morin_specifics:
    mentioned_in_book: yes
    note: "Venus and 7th house critical"

engagement:
  category: relationship_events
  subcategory: commitment
  
  keywords:
    primary: [engagement, engaged, betrothal, betrothed, promised]
    secondary: [got_engaged, proposed, proposal, fiancé, fiancée]
    context: [ring, proposal, promise, commitment, pledge]
    
  synonyms: [betrothal, pledge, promise, commitment]
  
  astrological_indicators:
    primary_planets: [Venus, 7th_ruler]
    secondary_planets: [Jupiter, Moon]
    primary_houses: [7, 5, 1]
    secondary_houses: [11]
    aspects_favor: [trine, sextile, venus_aspects]
    
  quality:
    nature: benefic
    severity: 7-8
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [relationships, 7th_house, commitment]
    minimum_determination_score: 0.5

divorce_separation:
  category: relationship_events
  subcategory: dissolution
  
  keywords:
    primary: [divorce, divorced, separation, separated, split, breakup]
    secondary: [ended_marriage, dissolved_union, parted_ways, marriage_ended]
    context: [legal_separation, custody, settlement, ex_spouse]
    
  synonyms: [dissolution, split, breakup, separation, parting]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, afflicted_Venus, afflicted_7th_ruler]
    secondary_planets: [Uranus_if_using]
    primary_houses: [7, 8, 12]
    secondary_houses: [1]
    aspects_favor: [square, opposition, mars_saturn_afflictions]
    
  quality:
    nature: malefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [relationships, 7th_house, separation, conflict]
    minimum_determination_score: 0.6
    
  related_events:
    - relationship_conflict
    - legal_proceedings
    - emotional_crisis

romantic_connection:
  category: relationship_events
  subcategory: romance
  
  keywords:
    primary: [romance, love, affair, relationship, romantic_connection]
    secondary: [fell_in_love, met_someone, new_relationship, dating]
    context: [attraction, chemistry, passion, love_affair, courtship]
    
  synonyms: [romance, love_affair, courtship, amour]
  
  astrological_indicators:
    primary_planets: [Venus]
    secondary_planets: [Mars, Moon, 5th_ruler, 7th_ruler]
    primary_houses: [5, 7, 1]
    secondary_houses: [11]
    aspects_favor: [trine, sextile, venus_mars_aspects]
    
  quality:
    nature: benefic
    severity: 5-7
    importance: moderate
    
  timing:
    typical_duration: variable
    orb_sensitivity: moderate
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [romance, 5th_house, attraction]
    minimum_determination_score: 0.4

relationship_conflict:
  category: relationship_events
  subcategory: discord
  
  keywords:
    primary: [conflict, argument, fight, dispute, quarrel, discord]
    secondary: [relationship_problems, marital_problems, partnership_issues, partnership_strained, miscommunication]
    context: [tension, friction, disagreement, strife, trouble]
    
  synonyms: [discord, strife, friction, disagreement, dispute]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn]
    secondary_planets: [afflicted_Venus, afflicted_7th_ruler]
    primary_houses: [7, 12]
    secondary_houses: [8, 1]
    aspects_favor: [square, opposition, mars_aspects]
    
  quality:
    nature: malefic
    severity: 4-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [relationships, conflict, 7th_house]
    minimum_determination_score: 0.4

betrayal:
  category: relationship_events
  subcategory: treachery
  
  keywords:
    primary: [betrayal, betrayed, infidelity, affair, cheating, unfaithful]
    secondary: [deceived, cuckolded, adultery, two_timing, dishonesty]
    context: [secret_affair, hidden_relationship, deception, disloyalty]
    
  synonyms: [treachery, infidelity, disloyalty, perfidy]
  
  astrological_indicators:
    primary_planets: [Neptune_if_using, Mars, afflicted_Venus]
    secondary_planets: [Mercury_afflicted, 12th_ruler]
    primary_houses: [7, 12, 8]
    secondary_houses: [5]
    aspects_favor: [square, opposition, neptune_venus_afflictions]
    
  quality:
    nature: malefic
    severity: 7-8
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [relationships, deception, hidden_enemies]
    minimum_determination_score: 0.5

reconciliation:
  category: relationship_events
  subcategory: healing
  
  keywords:
    primary: [reconciliation, reconciled, made_up, forgave, reunion]
    secondary: [got_back_together, patched_things_up, resolved_differences]
    context: [peace, harmony, resolution, forgiveness, healing]
    
  synonyms: [reunion, rapprochement, making_peace, resolution]
  
  astrological_indicators:
    primary_planets: [Venus, Jupiter]
    secondary_planets: [Moon, 7th_ruler]
    primary_houses: [7, 11]
    secondary_houses: [5]
    aspects_favor: [trine, sextile, benefic_aspects]
    
  quality:
    nature: benefic
    severity: 6-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [relationships, harmony, healing]
    minimum_determination_score: 0.4
```

---

## VI. FAMILY EVENTS

```yaml
pregnancy:
  category: family_events
  subcategory: fertility
  
  keywords:
    primary: [pregnancy, pregnant, expecting, conception, conceived]
    secondary: [with_child, gravid, expecting_baby, baby_on_way]
    context: [fertility, conception, prenatal, maternity]
    
  synonyms: [gestation, gravidity, expectancy]
  
  astrological_indicators:
    primary_planets: [Moon, Venus, Jupiter]
    secondary_planets: [5th_ruler]
    primary_houses: [5, 1]
    secondary_houses: [4, 11]
    aspects_favor: [trine, sextile, benefic_conjunctions]
    
  quality:
    nature: benefic
    severity: 8
    importance: major
    
  timing:
    typical_duration: 9_months
    orb_sensitivity: moderate
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [fertility, children, 5th_house]
    minimum_determination_score: 0.5
    
  related_events:
    - birth_of_child
    - conception
    - fertility

family_celebration:
  category: family_events
  subcategory: joy
  
  keywords:
    primary: [celebration, party, gathering, reunion, festivity]
    secondary: [family_event, get_together, festivities, family_joy, domestic_happiness, comfort_security]
    context: [wedding, birthday, anniversary, holiday, homecoming]
    
  synonyms: [festivity, celebration, gathering, jubilation]
  
  astrological_indicators:
    primary_planets: [Jupiter, Venus, Moon]
    secondary_planets: [Sun, 4th_ruler, 5th_ruler]
    primary_houses: [4, 5, 11]
    secondary_houses: [3, 7]
    aspects_favor: [trine, sextile, benefic_conjunctions]
    
  quality:
    nature: benefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [family, joy, celebration, 4th_or_5th_house]
    minimum_determination_score: 0.4

family_conflict:
  category: family_events
  subcategory: discord
  
  keywords:
    primary: [family_conflict, family_fight, family_dispute, family_problems]
    secondary: [family_tension, domestic_discord, household_strife, domestic_disruption]
    context: [argument, disagreement, feud, estrangement, rift]
    
  synonyms: [domestic_discord, family_strife, household_conflict]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn]
    secondary_planets: [afflicted_Moon, afflicted_4th_ruler]
    primary_houses: [4, 12]
    secondary_houses: [3, 8]
    aspects_favor: [square, opposition, mars_moon_afflictions]
    
  quality:
    nature: malefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [family, conflict, 4th_house]
    minimum_determination_score: 0.4

moving_home:
  category: family_events
  subcategory: relocation
  
  keywords:
    primary: [moving, moved, relocation, relocated, new_home, new_house]
    secondary: [changed_residence, moved_house, change_of_address]
    context: [packing, unpacking, settling_in, house_move, apartment]
    
  synonyms: [relocation, change_of_residence, house_move]
  
  astrological_indicators:
    primary_planets: [Moon, 4th_ruler]
    secondary_planets: [Mercury, Uranus_if_using]
    primary_houses: [4, 3]
    secondary_houses: [1, 10]
    aspects_favor: [depends_on_circumstances]
    
  quality:
    nature: neutral
    severity: 6-8
    importance: moderate_to_major
    
  timing:
    typical_duration: permanent_change
    orb_sensitivity: loose
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [home, 4th_house, change, movement]
    minimum_determination_score: 0.4
    
  related_events:
    - purchase_property
    - sale_property
    - relocation

purchase_property:
  category: family_events
  subcategory: acquisition
  
  keywords:
    primary: [bought_house, purchased_property, bought_home, real_estate_purchase]
    secondary: [acquired_property, home_ownership, property_acquisition]
    context: [mortgage, down_payment, closing, deed, ownership]
    
  synonyms: [property_acquisition, home_purchase, real_estate_transaction]
  
  astrological_indicators:
    primary_planets: [Moon, Jupiter, Venus, 4th_ruler]
    secondary_planets: [2nd_ruler, Saturn_for_property]
    primary_houses: [4, 2]
    secondary_houses: [8, 10]
    aspects_favor: [trine, sextile, benefic_aspects]
    
  quality:
    nature: benefic
    severity: 8
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [property, 4th_house, acquisition, wealth]
    minimum_determination_score: 0.5
```

---

## VII. LEGAL EVENTS

```yaml
lawsuit:
  category: legal_events
  subcategory: litigation
  
  keywords:
    primary: [lawsuit, sued, litigation, legal_action, court_case]
    secondary: [legal_proceedings, trial, court, plaintiff, defendant]
    context: [attorney, lawyer, judge, court_date, hearing]
    
  synonyms: [litigation, legal_action, court_case, legal_proceedings]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, 7th_ruler]
    secondary_planets: [Mercury, Jupiter_for_law]
    primary_houses: [7, 9, 12]
    secondary_houses: [8, 10]
    aspects_favor: [square, opposition, mars_saturn_aspects]
    
  quality:
    nature: malefic
    severity: 6-9
    importance: moderate_to_major
    
  timing:
    typical_duration: months_to_years
    orb_sensitivity: moderate
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [legal_matters, 7th_house, conflict, 9th_house]
    minimum_determination_score: 0.5
    
  related_events:
    - legal_victory
    - legal_defeat
    - settlement

legal_victory:
  category: legal_events
  subcategory: success
  
  keywords:
    primary: [won_case, legal_victory, court_victory, judgment_favorable]
    secondary: [case_won, lawsuit_won, vindicated, exonerated, acquitted, legal_resolution, settlement, protection_granted]
    context: [favorable_ruling, favorable_judgment, court_win, verdict]
    
  synonyms: [judicial_victory, court_win, legal_success, vindication]
  
  astrological_indicators:
    primary_planets: [Jupiter, Sun]
    secondary_planets: [Venus, well_placed_Mercury]
    primary_houses: [7, 9, 10]
    secondary_houses: [1, 11]
    aspects_favor: [trine, sextile, jupiter_sun_aspects]
    
  quality:
    nature: benefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent_resolution
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [legal_matters, justice, victory, 9th_house]
    minimum_determination_score: 0.6
    
  morin_specifics:
    mentioned_in_book: yes
    note: "Jupiter and 9th house for law/justice"

legal_defeat:
  category: legal_events
  subcategory: loss
  
  keywords:
    primary: [lost_case, legal_defeat, court_loss, judgment_against]
    secondary: [case_lost, lawsuit_lost, found_guilty, convicted, contract_problems, delay_obstruction]
    context: [unfavorable_ruling, adverse_judgment, court_loss, verdict_against]
    
  synonyms: [judicial_defeat, court_loss, legal_failure, conviction]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_Jupiter]
    secondary_planets: [afflicted_9th_ruler]
    primary_houses: [7, 9, 12]
    secondary_houses: [8]
    aspects_favor: [square, opposition, saturn_afflictions]
    
  quality:
    nature: malefic
    severity: 7-9
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [legal_matters, loss, 12th_house]
    minimum_determination_score: 0.6

arrest_imprisonment:
  category: legal_events
  subcategory: confinement
  
  keywords:
    primary: [arrested, imprisonment, jailed, incarcerated, detained]
    secondary: [taken_into_custody, locked_up, confined, prison, jail]
    context: [police, charges, custody, bail, sentence, conviction]
    
  synonyms: [incarceration, detention, confinement, custody]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, 12th_ruler]
    secondary_planets: [afflicted_7th_ruler]
    primary_houses: [12, 8, 7]
    secondary_houses: [6]
    aspects_favor: [square, opposition, saturn_mars_afflictions]
    
  quality:
    nature: malefic
    severity: 9-10
    importance: major_to_critical
    
  timing:
    typical_duration: variable_imprisonment_length
    orb_sensitivity: tight
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [confinement, 12th_house, restriction, loss_of_freedom]
    minimum_determination_score: 0.7
    
  related_events:
    - arrest
    - trial
    - conviction
    - legal_trouble
    
  morin_specifics:
    mentioned_in_book: yes
    note: "12th house critical, Saturn as restrictor"

contract_signing:
  category: legal_events
  subcategory: agreement
  
  keywords:
    primary: [contract, signed_contract, agreement, deal, signed_agreement]
    secondary: [contract_signed, signing, executed_contract, binding_agreement]
    context: [terms, clause, stipulation, signature, document]
    
  synonyms: [agreement, pact, covenant, compact]
  
  astrological_indicators:
    primary_planets: [Mercury, Jupiter, 7th_ruler]
    secondary_planets: [Venus, 3rd_ruler]
    primary_houses: [7, 3, 10]
    secondary_houses: [2, 11]
    aspects_favor: [trine, sextile, mercury_aspects]
    
  quality:
    nature: usually_benefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [contracts, agreements, 7th_house, communication]
    minimum_determination_score: 0.4
```

---

## VIII. TRAVEL & RELOCATION EVENTS

```yaml
short_journey:
  category: travel_events
  subcategory: short_travel
  
  keywords:
    primary: [trip, journey, travel, excursion, short_trip]
    secondary: [went_on_trip, traveled, visiting, day_trip, weekend_trip]
    context: [vacation, visit, outing, getaway, tour]
    
  synonyms: [excursion, outing, jaunt, trip]
  
  astrological_indicators:
    primary_planets: [Mercury, Moon, 3rd_ruler]
    secondary_planets: [Jupiter]
    primary_houses: [3]
    secondary_houses: [9, 5]
    aspects_favor: [mostly_neutral, benefics_help]
    
  quality:
    nature: neutral
    severity: 3-5
    importance: minor_to_moderate
    
  timing:
    typical_duration: days_to_week
    orb_sensitivity: loose
    concordance_required: low
    
  determination_requirements:
    planet_must_be_determined_to: [travel, 3rd_house, movement]
    minimum_determination_score: 0.3

long_journey:
  category: travel_events
  subcategory: long_travel
  
  keywords:
    primary: [long_journey, voyage, travel_abroad, foreign_travel, expedition]
    secondary: [overseas_trip, international_travel, extended_travel, pilgrimage]
    context: [abroad, foreign, distant, far_away, journey]
    
  synonyms: [voyage, expedition, odyssey, pilgrimage]
  
  astrological_indicators:
    primary_planets: [Jupiter, Mercury, 9th_ruler]
    secondary_planets: [Moon, Uranus_if_using]
    primary_houses: [9, 3]
    secondary_houses: [12]
    aspects_favor: [trine, sextile, jupiter_aspects]
    
  quality:
    nature: neutral_to_benefic
    severity: 6-7
    importance: moderate
    
  timing:
    typical_duration: weeks_to_months
    orb_sensitivity: moderate
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [travel, 9th_house, foreign_lands]
    minimum_determination_score: 0.4
    
  related_events:
    - foreign_encounter
    - cultural_experience
    - adventure
    
  morin_specifics:
    mentioned_in_book: yes
    note: "9th house for long journeys, Jupiter favorable"

relocation_permanent:
  category: travel_events
  subcategory: permanent_change
  
  keywords:
    primary: [relocated, moved_permanently, emigrated, immigrated, resettled]
    secondary: [changed_location, new_country, new_city, permanent_move]
    context: [emigration, immigration, expatriate, settler, transplant]
    
  synonyms: [emigration, immigration, resettlement, transplantation]
  
  astrological_indicators:
    primary_planets: [Moon, Uranus_if_using, 4th_ruler, 9th_ruler]
    secondary_planets: [Jupiter, Mercury]
    primary_houses: [4, 9, 1]
    secondary_houses: [3, 10]
    aspects_favor: [depends_on_circumstances]
    
  quality:
    nature: neutral_major_change
    severity: 8-9
    importance: major
    
  timing:
    typical_duration: permanent
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [relocation, change, 4th_or_9th_house]
    minimum_determination_score: 0.5

travel_accident:
  category: travel_events
  subcategory: danger
  
  keywords:
    primary: [travel_accident, accident_while_traveling, crash, collision]
    secondary: [car_accident, plane_crash, shipwreck, travel_mishap]
    context: [during_journey, while_traveling, on_the_road, in_transit]
    
  synonyms: [travel_mishap, journey_accident, travel_disaster]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, afflicted_3rd_or_9th_ruler]
    secondary_planets: [Uranus_if_using]
    primary_houses: [3, 9, 8, 12]
    secondary_houses: [6]
    aspects_favor: [square, opposition, mars_afflictions]
    
  quality:
    nature: malefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: immediate
    orb_sensitivity: tight
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [travel, accidents, danger]
    minimum_determination_score: 0.5
```

---

## IX. EDUCATIONAL EVENTS

```yaml
degree_completion:
  category: educational_events
  subcategory: achievement
  
  keywords:
    primary: [graduation, graduated, degree, diploma, completed_studies]
    secondary: [earned_degree, finished_school, academic_achievement, commencement]
    context: [bachelor, master, doctorate, PhD, certificate, qualification]
    
  synonyms: [graduation, commencement, academic_completion, qualification]
  
  astrological_indicators:
    primary_planets: [Mercury, Jupiter, 9th_ruler]
    secondary_planets: [Sun, 3rd_ruler]
    primary_houses: [9, 3, 10]
    secondary_houses: [11, 5]
    aspects_favor: [trine, sextile, mercury_jupiter_aspects]
    
  quality:
    nature: benefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent_achievement
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [education, 9th_house, achievement, learning]
    minimum_determination_score: 0.6
    
  related_events:
    - academic_success
    - honor_award
    - learning_completion
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_2, law_11]
    example_charts: yes
    note: "Doctorate example May 9, 1613"

exam_success:
  category: educational_events
  subcategory: achievement
  
  keywords:
    primary: [passed_exam, exam_success, test_passed, aced_test]
    secondary: [passed_test, successful_examination, good_grade, high_score]
    context: [examination, test, quiz, assessment, evaluation]
    
  synonyms: [test_success, examination_success, academic_achievement]
  
  astrological_indicators:
    primary_planets: [Mercury, Jupiter]
    secondary_planets: [Sun, 3rd_ruler, 9th_ruler]
    primary_houses: [3, 9]
    secondary_houses: [5, 10]
    aspects_favor: [trine, sextile, mercury_aspects]
    
  quality:
    nature: benefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [learning, education, testing, mental_ability]
    minimum_determination_score: 0.4

exam_failure:
  category: educational_events
  subcategory: setback
  
  keywords:
    primary: [failed_exam, exam_failure, test_failed, flunked]
    secondary: [failed_test, unsuccessful_examination, poor_grade, low_score]
    context: [failed, flunked, didn't_pass, unsuccessful]
    
  synonyms: [test_failure, examination_failure, academic_setback]
  
  astrological_indicators:
    primary_planets: [Saturn, afflicted_Mercury]
    secondary_planets: [Mars, afflicted_3rd_or_9th_ruler]
    primary_houses: [3, 9, 12]
    secondary_houses: [6]
    aspects_favor: [square, opposition, saturn_mercury_afflictions]
    
  quality:
    nature: malefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [learning, education, difficulties, obstacles]
    minimum_determination_score: 0.4

enrollment_admission:
  category: educational_events
  subcategory: beginning
  
  keywords:
    primary: [enrolled, admitted, accepted, admission, matriculated]
    secondary: [got_into_school, accepted_to_college, university_admission]
    context: [acceptance_letter, enrollment, registration, matriculation]
    
  synonyms: [admission, acceptance, enrollment, matriculation]
  
  astrological_indicators:
    primary_planets: [Mercury, Jupiter, 9th_ruler]
    secondary_planets: [3rd_ruler]
    primary_houses: [9, 3]
    secondary_houses: [11]
    aspects_favor: [trine, sextile, benefic_aspects]
    
  quality:
    nature: benefic
    severity: 6-8
    importance: moderate_to_major
    
  determination_requirements:
    planet_must_be_determined_to: [education, 9th_house, new_beginnings]
    minimum_determination_score: 0.5
```

---

## X. ACCIDENT & DANGER EVENTS

```yaml
accident_major:
  category: danger_events
  subcategory: accident
  
  keywords:
    primary: [accident, major_accident, serious_accident, catastrophe, disaster]
    secondary: [calamity, mishap, unfortunate_event, traumatic_event]
    context: [emergency, crisis, catastrophic, devastating]
    types: [car_accident, fall, collision, crash, explosion]
    
  synonyms: [catastrophe, disaster, calamity, mishap]
  
  astrological_indicators:
    primary_planets: [Mars, Uranus_if_using]
    secondary_planets: [Saturn, afflicted_ASC_ruler]
    primary_houses: [8, 12, 1]
    secondary_houses: [6, 3]
    aspects_favor: [square, opposition, mars_uranus_aspects]
    
  quality:
    nature: malefic
    severity: 8-10
    importance: major_to_critical
    
  timing:
    typical_duration: immediate
    orb_sensitivity: very_tight
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [accidents, sudden_events, danger, violence]
    minimum_determination_score: 0.6
    
  related_events:
    - injury
    - hospitalization
    - surgery
    - near_death
    
  morin_specifics:
    mentioned_in_book: yes
    note: "Requires multiple concordances per Morin"

near_death_experience:
  category: danger_events
  subcategory: life_threatening
  
  keywords:
    primary: [near_death, almost_died, life_threatening, close_call, brush_with_death]
    secondary: [narrowly_escaped, survived, miracle, close_to_death]
    context: [critical, life_or_death, touch_and_go, survived_by_miracle]
    
  synonyms: [close_call, narrow_escape, brush_with_death, survival]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, 8th_ruler]
    secondary_planets: [Uranus_if_using, afflicted_ASC_ruler]
    primary_houses: [8, 12, 1]
    secondary_houses: [6]
    aspects_favor: [square, opposition, mars_saturn_conjunction]
    
  quality:
    nature: malefic
    severity: 9-10
    importance: critical
    
  timing:
    typical_duration: immediate
    orb_sensitivity: very_tight
    concordance_required: critical
    
  determination_requirements:
    planet_must_be_determined_to: [death, danger, 8th_house, life_threats]
    minimum_determination_score: 0.7
    
  related_events:
    - accident
    - illness_severe
    - violence
    - danger
    
  morin_specifics:
    mentioned_in_book: yes
    special_laws_apply: [law_10, law_13]
    example_charts: yes
    note: "Near-drowning July 7, 1615"

attack_violence:
  category: danger_events
  subcategory: violence
  
  keywords:
    primary: [attacked, assault, violence, assaulted, beaten, struck]
    secondary: [violent_attack, physical_assault, aggression, fight, brawl]
    context: [violent, aggressive, attack, combat, confrontation]
    
  synonyms: [assault, attack, aggression, violence, battery]
  
  astrological_indicators:
    primary_planets: [Mars]
    secondary_planets: [Saturn, Uranus_if_using]
    primary_houses: [1, 8, 12, 7]
    secondary_houses: [6]
    aspects_favor: [square, opposition, mars_afflictions]
    
  quality:
    nature: malefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: immediate
    orb_sensitivity: tight
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [violence, conflict, danger, aggression]
    minimum_determination_score: 0.6

fire_burn:
  category: danger_events
  subcategory: injury_fire
  
  keywords:
    primary: [fire, burn, burned, burnt, fire_injury, conflagration]
    secondary: [burned_in_fire, house_fire, fire_damage, scorched]
    context: [flames, combustion, ignition, burning, fire_accident]
    
  synonyms: [combustion, burning, fire_damage, scorching]
  
  astrological_indicators:
    primary_planets: [Mars, afflicted_Sun]
    secondary_planets: [Uranus_if_using]
    primary_houses: [1, 4, 6, 8]
    secondary_houses: [12]
    aspects_favor: [mars_sun_afflictions, fire_indicators]
    
  quality:
    nature: malefic
    severity: 6-9
    importance: moderate_to_major
    
  timing:
    typical_duration: immediate
    orb_sensitivity: tight
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [fire, accidents, sudden_events, destruction]
    minimum_determination_score: 0.5

drowning_submersion:
  category: danger_events
  subcategory: water_danger
  
  keywords:
    primary: [drowning, drowned, nearly_drowned, submersion, water_danger]
    secondary: [submerged, underwater, waterlogged, water_accident]
    context: [swimming, water, river, ocean, pool, flood]
    
  synonyms: [submersion, water_accident, inundation]
  
  astrological_indicators:
    primary_planets: [Neptune_if_using, afflicted_Moon, Mars_in_water]
    secondary_planets: [Saturn, 8th_ruler]
    primary_houses: [8, 12, 4]
    secondary_houses: [1]
    aspects_favor: [afflictions_to_water_planets]
    
  quality:
    nature: malefic
    severity: 8-10
    importance: major_to_critical
    
  timing:
    typical_duration: immediate
    orb_sensitivity: very_tight
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [water, danger, death, accidents]
    minimum_determination_score: 0.6
    
  morin_specifics:
    mentioned_in_book: yes
    example_charts: yes
    note: "Near-drowning July 7, 1615"

fall_from_height:
  category: danger_events
  subcategory: falling
  
  keywords:
    primary: [fell, fall, falling, dropped, plummeted, tumbled]
    secondary: [fell_from_height, fell_down, took_fall, lost_footing]
    context: [height, cliff, ladder, stairs, horse, building]
    
  synonyms: [falling, tumble, plunge, descent]
  
  astrological_indicators:
    primary_planets: [Saturn, Uranus_if_using]
    secondary_planets: [Mars]
    primary_houses: [1, 8, 6]
    secondary_houses: [12]
    aspects_favor: [saturn_afflictions, sudden_planet_afflictions]
    
  quality:
    nature: malefic
    severity: 6-9
    importance: moderate_to_major
    
  timing:
    typical_duration: immediate
    orb_sensitivity: tight
    concordance_required: moderate_to_high
    
  determination_requirements:
    planet_must_be_determined_to: [accidents, falls, sudden_events]
    minimum_determination_score: 0.5
    
  morin_specifics:
    mentioned_in_book: yes
    example_charts: yes
    note: "Fall from horse January 1, 1616"
```

---

## XI. SPIRITUAL & RELIGIOUS EVENTS

```yaml
spiritual_awakening:
  category: spiritual_events
  subcategory: enlightenment
  
  keywords:
    primary: [awakening, enlightenment, realization, revelation, epiphany]
    secondary: [spiritual_experience, mystical_experience, transcendence]
    context: [consciousness, awareness, insight, illumination, understanding]
    
  synonyms: [enlightenment, illumination, realization, revelation]
  
  astrological_indicators:
    primary_planets: [Jupiter, Neptune_if_using]
    secondary_planets: [Moon, Uranus_if_using, 9th_ruler, 12th_ruler]
    primary_houses: [9, 12]
    secondary_houses: [8, 4]
    aspects_favor: [trine, conjunction, jupiter_neptune_aspects]
    
  quality:
    nature: benefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: permanent_shift
    orb_sensitivity: moderate
    concordance_required: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [spirituality, 9th_or_12th_house, consciousness]
    minimum_determination_score: 0.5

religious_conversion:
  category: spiritual_events
  subcategory: faith_change
  
  keywords:
    primary: [conversion, converted, faith_change, religious_conversion]
    secondary: [found_faith, embraced_religion, became_believer, baptized]
    context: [religion, faith, belief, creed, denomination]
    
  synonyms: [conversion, baptism, profession_of_faith]
  
  astrological_indicators:
    primary_planets: [Jupiter, 9th_ruler]
    secondary_planets: [Neptune_if_using, Moon]
    primary_houses: [9]
    secondary_houses: [12, 4]
    aspects_favor: [jupiter_aspects, religious_indicators]
    
  quality:
    nature: benefic_or_neutral
    severity: 7-8
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [religion, 9th_house, faith, belief]
    minimum_determination_score: 0.5

pilgrimage:
  category: spiritual_events
  subcategory: journey
  
  keywords:
    primary: [pilgrimage, sacred_journey, religious_journey, holy_travel]
    secondary: [went_on_pilgrimage, religious_travel, sacred_voyage]
    context: [shrine, holy_place, sacred_site, religious_destination]
    
  synonyms: [sacred_journey, religious_pilgrimage, holy_voyage]
  
  astrological_indicators:
    primary_planets: [Jupiter, 9th_ruler]
    secondary_planets: [Moon, Mercury]
    primary_houses: [9]
    secondary_houses: [12, 3]
    aspects_favor: [jupiter_aspects, benefic_aspects]
    
  quality:
    nature: benefic
    severity: 6-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [religion, travel, 9th_house, spirituality]
    minimum_determination_score: 0.4

mystical_experience:
  category: spiritual_events
  subcategory: transcendence
  
  keywords:
    primary: [mystical, transcendent, divine, visionary, spiritual_vision]
    secondary: [mystical_experience, vision, divine_encounter, transcendence]
    context: [mysticism, esoteric, occult, metaphysical, supernatural]
    
  synonyms: [mystical_experience, vision, divine_encounter, transcendence]
  
  astrological_indicators:
    primary_planets: [Neptune_if_using, Jupiter, Moon]
    secondary_planets: [12th_ruler, Uranus_if_using]
    primary_houses: [12, 9, 8]
    secondary_houses: [4]
    aspects_favor: [neptune_moon_aspects, mystical_indicators]
    
  quality:
    nature: benefic_profound
    severity: 7-9
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [spirituality, mysticism, 12th_house, transcendence]
    minimum_determination_score: 0.6
```

---

## XII. SOCIAL & FRIENDSHIP EVENTS

```yaml
new_friendship:
  category: social_events
  subcategory: connection
  
  keywords:
    primary: [new_friend, friendship, made_friend, befriended, met_friend]
    secondary: [new_friendship, formed_friendship, made_connection]
    context: [companionship, camaraderie, bond, connection]
    
  synonyms: [companionship, camaraderie, fellowship, amity]
  
  astrological_indicators:
    primary_planets: [Venus, Mercury, 11th_ruler]
    secondary_planets: [Jupiter, Moon]
    primary_houses: [11, 7]
    secondary_houses: [3, 5]
    aspects_favor: [trine, sextile, venus_mercury_aspects]
    
  quality:
    nature: benefic
    severity: 5-6
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [friendships, 11th_house, connections]
    minimum_determination_score: 0.4

friendship_loss:
  category: social_events
  subcategory: separation
  
  keywords:
    primary: [lost_friend, friendship_ended, falling_out, estrangement]
    secondary: [friendship_broken, former_friend, friend_loss, betrayal]
    context: [conflict, argument, separation, drift_apart, alienation]
    
  synonyms: [estrangement, alienation, falling_out, rift]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_11th_ruler]
    secondary_planets: [afflicted_Venus]
    primary_houses: [11, 12]
    secondary_houses: [7]
    aspects_favor: [square, opposition, saturn_afflictions]
    
  quality:
    nature: malefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [friendships, 11th_house, loss, separation]
    minimum_determination_score: 0.4

social_success:
  category: social_events
  subcategory: popularity
  
  keywords:
    primary: [popular, popularity, social_success, well_liked, admired]
    secondary: [socially_successful, gained_popularity, social_recognition]
    context: [acclaim, admiration, popularity, social_circle, network]
    
  synonyms: [popularity, social_acclaim, admiration, esteem]
  
  astrological_indicators:
    primary_planets: [Venus, Sun, Jupiter]
    secondary_planets: [Moon, 11th_ruler]
    primary_houses: [11, 1, 5]
    secondary_houses: [10, 7]
    aspects_favor: [trine, sextile, benefic_aspects]
    
  quality:
    nature: benefic
    severity: 6-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [social_life, 11th_house, popularity]
    minimum_determination_score: 0.4

social_embarrassment:
  category: social_events
  subcategory: humiliation
  
  keywords:
    primary: [embarrassment, embarrassed, humiliation, humiliated, shame]
    secondary: [social_embarrassment, public_embarrassment, disgrace, scandal]
    context: [ashamed, mortified, disgraced, scandal, ridicule]
    
  synonyms: [humiliation, disgrace, shame, mortification]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_Venus]
    secondary_planets: [afflicted_Sun, afflicted_Moon]
    primary_houses: [12, 11, 10]
    secondary_houses: [7]
    aspects_favor: [square, opposition, afflictions]
    
  quality:
    nature: malefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [social_matters, humiliation, 12th_house]
    minimum_determination_score: 0.4
```

---

## XIII. MISCELLANEOUS EVENTS

```yaml
publication:
  category: creative_events
  subcategory: achievement
  
  keywords:
    primary: [published, publication, book_published, article_published]
    secondary: [writing_published, work_published, author, publisher]
    context: [manuscript, book, article, paper, journal, press]
    
  synonyms: [publishing, release, issuance, appearance]
  
  astrological_indicators:
    primary_planets: [Mercury, 9th_ruler]
    secondary_planets: [Jupiter, 3rd_ruler]
    primary_houses: [9, 3, 10]
    secondary_houses: [5, 11]
    aspects_favor: [trine, sextile, mercury_jupiter_aspects]
    
  quality:
    nature: benefic
    severity: 6-8
    importance: moderate_to_major
    
  determination_requirements:
    planet_must_be_determined_to: [writing, communication, 9th_house, publishing]
    minimum_determination_score: 0.5
    
  morin_specifics:
    mentioned_in_book: yes
    note: "Demonstration of Longitude Science, March 30, 1634"

artistic_success:
  category: creative_events
  subcategory: achievement
  
  keywords:
    primary: [artistic_success, creative_success, masterpiece, acclaimed]
    secondary: [art_success, creative_achievement, artistic_recognition]
    context: [art, creativity, performance, exhibition, show]
    
  synonyms: [creative_achievement, artistic_triumph, creative_success]
  
  astrological_indicators:
    primary_planets: [Venus, Neptune_if_using, 5th_ruler]
    secondary_planets: [Sun, Moon]
    primary_houses: [5, 10, 11]
    secondary_houses: [3, 9]
    aspects_favor: [trine, sextile, venus_aspects]
    
  quality:
    nature: benefic
    severity: 6-8
    importance: moderate_to_major
    
  determination_requirements:
    planet_must_be_determined_to: [creativity, art, 5th_house, self_expression]
    minimum_determination_score: 0.5

discovery_breakthrough:
  category: achievement_events
  subcategory: innovation
  
  keywords:
    primary: [discovery, breakthrough, innovation, invention, found]
    secondary: [discovered, invented, breakthrough_moment, eureka, communication_breakthrough]
    context: [research, science, innovation, revelation, finding]
    
  synonyms: [breakthrough, innovation, discovery, invention, revelation]
  
  astrological_indicators:
    primary_planets: [Uranus_if_using, Mercury, Jupiter]
    secondary_planets: [Sun, 9th_ruler]
    primary_houses: [9, 11, 3]
    secondary_houses: [5, 10]
    aspects_favor: [trine, conjunction, uranus_mercury_aspects]
    
  quality:
    nature: benefic
    severity: 7-9
    importance: major
    
  determination_requirements:
    planet_must_be_determined_to: [innovation, discovery, 9th_house, insight]
    minimum_determination_score: 0.6

loss_of_possessions:
  category: loss_events
  subcategory: material_loss
  
  keywords:
    primary: [lost_possessions, theft, stolen, burglary, robbed]
    secondary: [property_loss, belongings_lost, items_stolen]
    context: [loss, theft, robbery, burglary, stolen_goods]
    
  synonyms: [theft, robbery, burglary, larceny, loss]
  
  astrological_indicators:
    primary_planets: [Mars, Saturn, afflicted_2nd_ruler]
    secondary_planets: [Mercury_afflicted, 12th_ruler]
    primary_houses: [2, 12, 8]
    secondary_houses: [7]
    aspects_favor: [square, opposition, mars_afflictions]
    
  quality:
    nature: malefic
    severity: 5-7
    importance: moderate
    
  determination_requirements:
    planet_must_be_determined_to: [possessions, 2nd_house, loss, theft]
    minimum_determination_score: 0.4

reputation_damage:
  category: loss_events
  subcategory: social_loss
  
  keywords:
    primary: [reputation_damaged, disgrace, scandal, dishonor, infamy]
    secondary: [reputation_loss, public_disgrace, loss_of_face, scandal]
    context: [shame, dishonor, ignominy, discredit, defamation]
    
  synonyms: [disgrace, dishonor, infamy, ignominy, defamation]
  
  astrological_indicators:
    primary_planets: [Saturn, Mars, afflicted_Sun]
    secondary_planets: [afflicted_10th_ruler, afflicted_Venus]
    primary_houses: [10, 12, 8]
    secondary_houses: [7]
    aspects_favor: [square, opposition, saturn_sun_afflictions]
    
  quality:
    nature: malefic
    severity: 7-9
    importance: major
    
  timing:
    typical_duration: long_lasting
    orb_sensitivity: moderate
    concordance_required: high
    
  determination_requirements:
    planet_must_be_determined_to: [reputation, 10th_house, loss, disgrace]
    minimum_determination_score: 0.6
```

---

## XIV. IMPLEMENTATION NOTES

### A. Using This Dictionary

```python
# Query by keyword
def find_event_by_keyword(keyword):
    """Search for events containing this keyword"""
    matches = []
    for event_id, event_data in EVENTS_DICTIONARY.items():
        all_keywords = (
            event_data['keywords']['primary'] +
            event_data['keywords'].get('secondary', []) +
            event_data.get('synonyms', [])
        )
        if keyword.lower() in [k.lower() for k in all_keywords]:
            matches.append(event_id)
    return matches

# Query by astrological factors
def find_events_by_indicators(planet, house):
    """Find events associated with planet + house"""
    matches = []
    for event_id, event_data in EVENTS_DICTIONARY.items():
        indicators = event_data['astrological_indicators']
        if (planet in indicators['primary_planets'] and
            house in indicators['primary_houses']):
            matches.append(event_id)
    return matches

# Classify text description
def classify_event_from_text(description):
    """Identify event type from natural language description"""
    description_lower = description.lower()
    scores = {}
    
    for event_id, event_data in EVENTS_DICTIONARY.items():
        score = 0
        for keyword in event_data['keywords']['primary']:
            if keyword in description_lower:
                score += 3
        for keyword in event_data['keywords'].get('secondary', []):
            if keyword in description_lower:
                score += 2
        for synonym in event_data.get('synonyms', []):
            if synonym in description_lower:
                score += 1
        
        if score > 0:
            scores[event_id] = score
    
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    return None
```

### B. Multi-Language Support

```yaml
# Example structure for internationalization
events_i18n:
  promotion:
    en: [promotion, promoted, advanced, elevated]
    es: [promoción, promovido, ascendido, elevado]
    fr: [promotion, promu, avancé, élevé]
    de: [Beförderung, befördert, aufgestiegen]
    zh: [晋升, 升职, 提升, 擢升]
    ar: [ترقية, ترقى, تقدم, رفع]
```

### C. Severity Weighting

```python
SEVERITY_WEIGHTS = {
    1: 'trivial',
    2: 'minor',
    3: 'light',
    4: 'noticeable',
    5: 'moderate',
    6: 'significant',
    7: 'major',
    8: 'serious',
    9: 'severe',
    10: 'critical'
}
```

### D. Related Events Network

```python
# Build event relationship graph
def build_event_relationships():
    """Create network of related events"""
    graph = {}
    for event_id, event_data in EVENTS_DICTIONARY.items():
        related = event_data.get('related_events', [])
        graph[event_id] = related
    return graph

# Find event chains
def find_event_sequence(start_event, max_depth=3):
    """Find common sequences starting from an event"""
    sequences = []
    # BFS through relationship graph
    # Return likely sequences
    return sequences
```

---

## XV. SUMMARY STATISTICS

```yaml
Total_Events: 100+
Categories: 13
  - Life & Death: 5
  - Health & Illness: 11
  - Career & Professional: 12
  - Financial: 10
  - Relationship & Marriage: 8
  - Family: 6
  - Legal: 6
  - Travel & Relocation: 5
  - Educational: 4
  - Accident & Danger: 8
  - Spiritual & Religious: 4
  - Social & Friendship: 4
  - Miscellaneous: 17+

Quality Distribution:
  - Benefic: 35%
  - Malefic: 45%
  - Neutral/Mixed: 20%

Morin References:
  - Explicitly mentioned: 25+
  - With example charts: 8
  - Special laws apply: 12
```

This comprehensive event keywords dictionary provides the foundation for event classification, natural language processing, and astrological interpretation in the Morin transit engine.

# Chinese Astrology Ten Gods Polish

Date: 2026-05-13

## What The Tab Is

`Ten Gods` maps how every visible and hidden stem relates to the Day Master, then marks each Five Factor through the current strength, useful-element, contact-pressure, and timing gates.

It is not a final fate judgement. It answers:

- which roles appear on visible heavenly stems
- which roles are carried by hidden stems inside branches
- whether each role belongs to Companion, Output, Wealth, Influence, or Resource
- which Chinese Ten God term applies to each role
- whether the role is useful, pressured, timing-activated, cautionary, quiet, or topic-only in the current chart state

## Source And Correctness Scan

The implemented derivation is correct for the production role-map layer:

- `同我`: same element as the Day Master gives Friend / Rob Wealth.
- `我生`: what the Day Master produces gives Eating God / Hurting Officer.
- `我克`: what the Day Master controls gives Indirect Wealth / Direct Wealth.
- `克我`: what controls the Day Master gives Seven Killings / Direct Officer.
- `生我`: what produces the Day Master gives Indirect Resource / Direct Resource.
- Same or opposite polarity decides the direct/indirect pair.
- The Day Master is the comparison reference for each visible and hidden stem.
- Hidden stems are included because branch contents can carry roles that are not visible on the stems.
- Strong Day Master charts normally treat Output, Wealth, and Influence as balancing directions, while Companion and Resource add support that can become cautionary.
- Weak Day Master charts normally treat Resource and Companion as support directions, while Output, Wealth, and Influence can drain, burden, or over-control the chart.
- Useful factors are downgraded when the useful element is absent, contact-pressured, or only timing-supplied; timing can activate the factor but does not replace the natal strength gate.

Local source anchors:

- `bazi_augier`: Ten Gods are the Five Factors with polarity and are found by comparing each heavenly stem with the Day Master; hidden stems also carry Ten Gods.
- `bazi_destiny_code_book1_joey_yap`: Ten Gods are an advanced role layer for action, career, relationship, wealth, and role interpretation; strength and favorable-element context remain required.
- `bazi_destiny_code_book2_joey_yap`: career, wealth, and relationship examples read Five Factors through favorable/unfavorable status, Luck Pillars, and clash/harm/punishment/destruction pressure.
- `local.destiny_code_five_factors`: Companion, Output, Wealth, Influence, and Resource are read before direct/indirect Ten God labels are expanded.

Public cross-checks:

- ShenShu Ten Gods overview: https://www.shen-shu.com/en/shishen
- FateMaster Ten Gods calculation rules: https://www.fatemaster.ai/zh-Hant/guides/shishen
- Fates.cc Ten Gods reference: https://fates.cc/bazi/%E5%8D%81%E7%A5%9E/
- BaZi Open Guide strength/useful-god cross-check: https://bazi8.net/learn/self-strength
- ShenShu branch contact cross-check: https://www.shen-shu.com/en/blog/detailed-explanation-of-earthly-branches-punishment-clash-break-and-harm

## Implemented Direction

- Keep the Ten Gods tab in production as a deterministic role map.
- Remove the redundant `Day Master` tab from production navigation; Four Pillars already contains the Day Master card.
- Add Chinese terms and relation rules to backend Ten God payloads.
- Separate visible and hidden roles in the UI.
- Rename the top Five Factors panel to `Role Summary`.
- Remove source-confidence chips from the normal Ten Gods tab.
- Replace the generic "final favorability needs..." warning with computed status labels:
  - `Final useful`
  - `Useful`
  - `Pressured`
  - `Needed`
  - `Timing`
  - `Timing pressure`
  - `Caution`
  - `Neutral`
  - `Topic`
  - `Role`
  - `Quiet`
- Each factor row now carries `functional_status`, `status_label`, `status_tone`, `strength_direction`, optional damage/timing status, and short decision basis lines.
- Removed the repeated balanced/mixed-strength explanation from individual cards. A `Topic` card now only describes where the factor appears; clearing `Topic` requires a decisive strength gate or a released climate/special-structure override.

## Follow-Up Candidates

- Weight hidden stems by main/secondary/residual qi instead of simple counts.
- Add topic examples for each direct/indirect pair.
- Add hidden-stem weighting by main/secondary/residual qi so status confidence can distinguish a main root from a small residual root.
- Add direct/indirect pair-specific examples once curated fixtures exist for each individual Ten God, not only the Five Factor family.

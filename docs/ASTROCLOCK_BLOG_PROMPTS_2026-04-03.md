# AstroClock Blog Prompts

Date: 2026-04-03

## Purpose

Prepare two SEO-oriented writing prompts for an AI writing agent that does **not** have access to the Vox Stella codebase, internal docs, or product workflow.

The two target posts are:

1. `Birth Chart Compatibility vs Zodiac Compatibility: What’s the Difference?`
2. `Kylie Jenner + Timothee Chalamet: What Vox Stella's Synastry Reading Suggests`

## Research Notes

### General SEO Direction

Priority search-intent phrases for these two posts:

1. `birth chart compatibility`
2. `zodiac compatibility`
3. `synastry`
4. `synastry chart`
5. `astrology compatibility`
6. `relationship astrology`
7. `celebrity synastry`
8. `Kylie Jenner Timothee Chalamet synastry`
9. `Kylie Jenner Timothee Chalamet compatibility`
10. `birth chart compatibility vs zodiac compatibility`

### Kylie Jenner + Timothee Chalamet Birth-Data Quality

Public birth data is strong enough for an engine-led **content** case study.

1. `Kylie Jenner`
   - public timed data used: `1997-08-10 17:25 PDT`
   - place: `Los Angeles, California, USA`
   - source quality: `Rodden Rating AA`
   - source note: Astro-Databank currently reflects an AA-rated time and notes that an earlier public `17:31` entry was superseded
2. `Timothee Chalamet`
   - public timed data used: `1995-12-27 21:16 EST`
   - place: `Manhattan, New York, USA`
   - source quality: `Rodden Rating AA`
   - source note: Astro-Databank currently reflects AA-rated timed data

Editorial conclusion:

1. This pair is materially stronger than mixed-confidence celebrity cases.
2. It is suitable for a public-facing engine-led synastry article.
3. It is still a content case study, not scientific proof or private certainty.

## Current Relationship Context For The Kylie/Timothee Post

Useful public framing as of April 3, 2026:

1. Kylie Jenner and Timothee Chalamet have been publicly linked since 2023.
2. They remain relatively private compared with many celebrity couples.
3. ELLE's January 21, 2026 timeline reports that Chalamet publicly thanked Jenner in major award speeches and described her as his partner of three years.

Use this only as public-timeline context, not as proof that astrology explains the relationship.

## Engine Snapshot: Kylie Jenner + Timothee Chalamet

These outputs come from the local Vox Stella synastry engine using the AA-rated timed public data above and balanced options with modern planets and nodes enabled.

### Category Scores

1. `overall: 45`
2. `resonance: 20`
3. `communication: 10`
4. `attraction: 93`
5. `compatibility: 46`
6. `attachment: 89`
7. `growth: 82`
8. `friction: 94`
9. `burden: 83`

### Summary Lines

1. `Strongest support: Venus Trine Mars.`
2. `Main compensation factor: Natal lack activated.`
3. `Main pressure: Saturn Square Mars.`
4. `Mutual reception adds extra binding force beneath the visible contacts.`

### Strongest Supportive Signals

1. `Venus Trine Mars`
2. `Mutual reception`
3. `Unilateral reception`
4. `North Node Trine Mars`
5. `Natal lack activated`

### Strongest Challenging Signals

1. `Saturn Square Mars`
2. `Saturn Square Mars`
3. `Sun Quincunx Saturn`
4. `Venus Opposition Saturn`
5. `Directional overlay imbalance`

### Plain-Language Interpretation

This is not an easy or low-friction chart. It is a high-chemistry, high-pressure chart. The engine reads the pair as strongly magnetic and strongly binding, but not naturally smooth.

The most important pattern is the combination of:

1. `attraction: 93`
2. `attachment: 89`
3. `friction: 94`
4. `burden: 83`

That combination suggests:

1. very strong pull
2. high romantic or physical magnetism
3. real staying power or structural glue
4. meaningful pressure, difficulty, or emotional weight

Best blog framing:

1. this pair reads more like `magnetic and intense` than `easy and harmonious`
2. the chart suggests `chemistry plus strain`, not `light compatibility`
3. the reading is strong for an article about why high attraction is not the same as easy compatibility

## Prompt 1

```text
Write a polished, SEO-focused blog post for the Vox Stella website.

Important constraints:
- You do NOT have access to the app code, internal files, internal docs, or workflow.
- Do NOT invent implementation details, engineering claims, algorithms, APIs, or technical architecture.
- Use only the product/context details provided below.
- The article should feel authoritative, readable, modern, and useful.
- The goal is to attract organic search traffic from people interested in synastry, birth chart compatibility, zodiac compatibility, and relationship astrology.
- The article should be strong for SEO but must not feel spammy or stuffed with keywords.

Product context you can rely on:
- Vox Stella is an astrology desktop app.
- One of its features is Synastry.
- Synastry compares two astrological charts in a relationship context.
- The feature presents results visually using score-style categories and supporting astrological indicators instead of only giving a vague compatibility percentage.
- The output is structured around relationship dimensions such as:
  - Emotional resonance
  - Communication
  - Attraction / chemistry
  - Compatibility / ease
  - Attachment / staying power
  - Growth / life impact
  - Friction
  - Burden

This blog post topic is:
Birth Chart Compatibility vs Zodiac Compatibility: What’s the Difference?

Core article goal:
- Explain the difference between sun-sign compatibility and full-chart compatibility in plain language.
- Help readers understand why synastry is a deeper and more useful tool than generic zodiac matching.
- Position Vox Stella’s Synastry feature as a practical way to visualize relationship astrology without sounding like a hard sell.

Key points the article should cover:
- Zodiac compatibility usually refers to sun-sign matching only.
- Birth chart compatibility compares much more than the sun sign.
- A synastry chart can show differences between chemistry, ease, communication, emotional resonance, attachment, friction, and long-term weight.
- Two people can have strong attraction without having easy compatibility.
- Two people can have strong attachment without having effortless communication.
- This is why full-chart comparison is more useful than generic “best zodiac matches” content.

SEO requirements:
- Naturally incorporate keywords such as:
  - birth chart compatibility
  - zodiac compatibility
  - astrology compatibility
  - synastry
  - synastry chart
  - relationship astrology
  - compare natal charts
  - horoscope compatibility
  - astrology app
  - astrology software
- Use keywords naturally, not mechanically.
- The article should target informational search intent first, with subtle product-discovery value second.

Output format:
Please provide the following in order:

1. 5 SEO title options
- At least 2 should directly target “birth chart compatibility”
- At least 2 should directly target “zodiac compatibility”

2. Recommended URL slug

3. Meta title
- Around 60 characters max

4. Meta description
- Around 155 characters max

5. Primary keyword
6. Secondary keywords
7. Long-tail keywords

8. Article outline
- H1
- H2s
- H3s where useful

9. Full blog post
Requirements:
- 1,300 to 1,900 words
- Strong opening paragraph
- Clear explanation of zodiac compatibility vs birth chart compatibility
- Explain synastry in plain language
- Include one practical section that explains why structured categories like attraction, communication, friction, and attachment are more useful than generic matching
- Include a subtle Vox Stella mention without sounding like a product release note
- No fake technical details
- No mystical exaggeration
- No claims of scientific proof

10. On-page FAQ
- 5 questions and answers
- Focus on search intent around birth chart compatibility, synastry, and zodiac compatibility

11. Suggested CTA section
- short and product-appropriate

12. Suggested internal links
- 3 to 5 related article ideas for an astrology software site

Style guidance:
- Confident but not sensational
- Search-friendly but not cheap
- Modern and insightful
- Avoid clichés and filler
- Avoid sounding like a press release
```

## Prompt 2

```text
Write a polished, SEO-focused blog post for the Vox Stella website.

Important constraints:
- You do NOT have access to the app code, internal files, internal docs, or workflow.
- Do NOT invent implementation details, engineering claims, algorithms, APIs, or technical architecture.
- Use only the product/context details provided below.
- The article should feel authoritative, readable, modern, and useful.
- The goal is to attract organic search traffic from people interested in synastry, celebrity synastry, relationship astrology, and astrology compatibility.
- The article should be strong for SEO but must not feel spammy or stuffed with keywords.

Product context you can rely on:
- Vox Stella is an astrology desktop app.
- One of its features is Synastry.
- Synastry compares two astrological charts in a relationship context.
- The feature presents results visually using score-style categories and supporting astrological indicators instead of only giving a vague compatibility percentage.
- The output is structured around relationship dimensions such as:
  - Emotional resonance
  - Communication
  - Attraction / chemistry
  - Compatibility / ease
  - Attachment / staying power
  - Growth / life impact
  - Friction
  - Burden

This article topic is:
Kylie Jenner + Timothee Chalamet: What Vox Stella’s Synastry Reading Suggests

Very important:
- This article must be written as an illustrative celebrity synastry case study.
- Do NOT say the chart proves anything.
- Do NOT overclaim certainty.
- Do NOT present astrology as science.
- Frame the article as “what the synastry reading suggests” or “how the chart reads.”
- Include a caution that public celebrity birth data, while unusually strong here, still does not reveal private truth with certainty.

Verified birth-data-quality context:
- Kylie Jenner public timed data used: 1997-08-10 17:25 PDT, Los Angeles, California, USA
- Timothee Chalamet public timed data used: 1995-12-27 21:16 EST, Manhattan, New York, USA
- Both are treated here as AA-grade timed public data from Astro-Databank
- That makes this case stronger than many celebrity astrology examples, but it should still be framed as an illustrative reading

Public relationship context you may use:
- Kylie Jenner and Timothee Chalamet have been publicly linked since 2023
- They have kept the relationship relatively private
- In early 2026, Timothee publicly referred to Kylie as his partner in major award-season speeches

You must use this Vox Stella synastry output:

Category scores:
- overall: 45
- resonance: 20
- communication: 10
- attraction: 93
- compatibility: 46
- attachment: 89
- growth: 82
- friction: 94
- burden: 83

Summary lines:
- Strongest support: Venus Trine Mars
- Main compensation factor: Natal lack activated
- Main pressure: Saturn Square Mars
- Mutual reception adds extra binding force beneath the visible contacts

Strongest supportive signals:
- Venus Trine Mars
- Mutual reception
- Unilateral reception
- North Node Trine Mars
- Natal lack activated

Strongest challenging signals:
- Saturn Square Mars
- Sun Quincunx Saturn
- Venus Opposition Saturn
- Directional overlay imbalance

Interpretation guidance:
- This is not an easy or low-friction relationship chart
- It reads as highly magnetic and highly pressurized
- Attraction is extremely strong
- Attachment is also very strong
- Compatibility is much lower than attraction
- Communication is notably weak
- Friction and burden are both very high
- The best summary is: chemistry plus strain, magnetism plus weight
- This is a good example of why attraction is not the same thing as ease

Core narrative angle for the article:
- The chart does not read as light, effortless, or especially simple
- It reads as compelling, sticky, and intense
- The article should help readers understand the difference between:
  - attraction and compatibility
  - attachment and ease
  - chemistry and long-term smoothness

SEO requirements:
- Naturally incorporate keywords such as:
  - Kylie Jenner Timothee Chalamet synastry
  - Kylie Jenner Timothee Chalamet compatibility
  - celebrity synastry
  - synastry chart
  - astrology compatibility
  - relationship astrology
  - birth chart compatibility
  - celebrity astrology couple analysis
  - astrology app
  - astrology software
- Use keywords naturally, not mechanically.

Output format:
Please provide the following in order:

1. 5 SEO title options
- At least 2 should directly target “Kylie Jenner Timothee Chalamet synastry”
- At least 1 should target “celebrity synastry”

2. Recommended URL slug

3. Meta title
- Around 60 characters max

4. Meta description
- Around 155 characters max

5. Primary keyword
6. Secondary keywords
7. Long-tail keywords

8. Article outline
- H1
- H2s
- H3s where useful

9. Full blog post
Requirements:
- 1,300 to 1,900 words
- Strong opening paragraph
- Briefly explain what synastry is
- Explain why this pairing is interesting astrologically
- Use the category scores and top signals in readable prose
- Make the distinction between attraction and compatibility very clear
- Include one section that gently connects the reading back to why a structured synastry tool like Vox Stella is useful
- No fake technical details
- No mystical exaggeration
- No claims of scientific proof

10. On-page FAQ
- 5 questions and answers
- Focus on search intent around celebrity synastry, compatibility, and chart comparison

11. Suggested CTA section
- short and product-appropriate

12. Suggested internal links
- 3 to 5 related article ideas for an astrology software site

One sentence to include or closely paraphrase in the article:
“This is best read as an illustrative synastry case study based on strong public birth data, not as a definitive statement of private relationship truth.”

Style guidance:
- Confident but not sensational
- Search-friendly but not cheap
- Modern and insightful
- Avoid clichés and filler
- Avoid sounding like a press release
```

## Sources Used

1. [SEOPital astrology SEO keywords](https://www.seopital.co/blog/the-best-astrology-seo-keywords)
2. [The SEO Labs astrology keyword list](https://www.theseolabs.com/keywords-lists/astrology/)
3. [Astro.com Kylie Jenner search snippet with AA note](https://www.astro.com/adbvip/adbvip_08_10.htm?lang=n&nho2=2&nhor=3va%3DArisde.cgiilink1ract%3Dxx2f6367692f6177642e6367693f6c616e673d6e2676613d4172697364652e636769696c696e6b31266e686f323d32)
4. [Astro.com Timothee Chalamet search snippet with Rodden Rating AA](https://www.astro.com/adbvip/adbvip_12_27.htm?lang=r&nho2=47)
5. [ELLE Kylie Jenner and Timothee Chalamet timeline, Jan. 21, 2026](https://www.elle.com/culture/celebrities/a43746386/kylie-jenner-timothee-chalamet-relationship-timeline/)

# Novel Flood Holdout Event Notes

Status date: 2026-04-19

Purpose:

- Anchor predictive hindcast cases that are not cited in the local astrology source corpus.
- Preserve verification material for historical flood events used as out-of-source holdouts.

## Hindman / Eastern Kentucky Flooding, July 2022

Primary verification sources:

- National Weather Service Jackson, KY
  - `https://www.weather.gov/jkl/July2022Flooding`
- National Weather Service Service Assessment
  - `https://www.weather.gov/media/publications/assessments/July_2022_Significant_River_Flash_Flood_SE_KY.pdf`

Verification summary:

- NWS Jackson documents historic flooding across eastern Kentucky from July 26 through July 30, 2022.
- The event page describes training thunderstorms over several days and shows devastating flooding across Breathitt County.
- The storm report section on the page shows inundation in Jackson on July 29, 2022.
- Hindman and nearby communities in Knott and Breathitt Counties were among the signature flood impact zones during the late July event.

Benchmark framing:

- Holdout location: Hindman, Kentucky, USA
- Benchmark window: 2022-07-25 through 2022-07-31
- Target window: 2022-07-28 through 2022-07-29
- Reason for target window:
  - concentrates the most destructive flood phase after repeated training convection and before the event decays

## Montpelier / Great Vermont Flood, July 2023

Primary verification sources:

- National Weather Service Service Assessment
  - `https://www.weather.gov/media/publications/assessments/NE%20Flash%20Flood%20and%20River%20Flooding%20AAR%20-%20July%202023%20-%20Final_revision1%20-%202_3_2025.pdf`
- National Weather Service Burlington Hazard Safety Campaigns
  - `https://www.weather.gov/btv/safetycampaigns`

Verification summary:

- The NWS service assessment states that intense rainfall on July 9-10, 2023 caused rapid river rises across Vermont.
- The assessment notes that the Winooski and Lamoille reached major flood stage and that Interstate 89 near Montpelier flooded.
- The Burlington office safety page preserves the Great Vermont Flood of July 2023 as a recent significant flooding event.

Benchmark framing:

- Holdout location: Montpelier, Vermont, USA
- Benchmark window: 2023-07-08 through 2023-07-14
- Target window: 2023-07-10 through 2023-07-11
- Reason for target window:
  - captures the major flood rise and peak-impact interval around Montpelier during the statewide flood disaster

## Corpus Status

- These holdout events are intended as predictive hindcast generalization checks.
- They are not drawn from the local source-alignment weather doctrine set and should stay marked as `novel_holdout` in the predictive hindcast dataset.

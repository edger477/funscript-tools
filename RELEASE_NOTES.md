## What's New in v2.4.8

### Bug Fixes

1. **alpha-prostate overwrite guard** — `alpha-prostate` now respects the "overwrite existing files" setting. Previously it was always regenerated and overwritten on every processing run regardless of the setting.

2. **OFS chapter timestamp parsing** — fractional-second fields shorter than 3 digits (e.g. `.5` from third-party funscripts) are now zero-padded before parsing, so `00:00:01.5` correctly becomes 1500 ms instead of 1005 ms. Prevents wrong sort order when merging existing chapters.

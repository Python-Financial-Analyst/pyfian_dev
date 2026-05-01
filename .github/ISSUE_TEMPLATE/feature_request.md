---
name: Feature request
about: Suggest a new feature or improvement
title: "[FEAT] "
labels: enhancement
assignees: ''
---

## Is your feature request related to a problem?

A clear and concise description of what the problem is.
Example: *I want to price callable bonds but pyfian only supports bullet structures.*

## Proposed solution

Describe the solution you would like. If you have a design in mind, sketch the
public API you expect:

```python
from pyfian.fixed_income import CallableBond
bond = CallableBond(issue_dt="2024-01-01", maturity="2034-01-01", cpn=5.0, ...)
```

## Alternatives considered

Any alternative approaches you have evaluated.

## Additional context

Links to papers, Bloomberg documentation, or other libraries that implement
the feature are very helpful.

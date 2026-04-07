# Functional Specification Template

> Fill this template for each feature/change. This captures WHAT the feature does from the user's perspective.
> Refer to `rules.md` for classification into Functional / Regression / Negative.

---

## 1. Feature Summary

| Field              | Value                                    |
|--------------------|------------------------------------------|
| Feature Name       |                                          |
| Component          |                                          |
| Spec ID / Jira     |                                          |
| Author             |                                          |
| Change Type        | New / Modified / Bug Fix / Upgrade       |
| Target Release     |                                          |

**User Story:** As a ___(role)___, I want to ___(action)___, so that ___(benefit)___.

---

## 2. Functional Requirements

List each requirement. Each one drives test case generation.

| Req ID | Requirement Description                                | Priority  |
|--------|--------------------------------------------------------|-----------|
| FR-01  |                                                        | Must      |
| FR-02  |                                                        | Must      |
| FR-03  |                                                        | Should    |

> **Test generation rule:** Each "Must" requirement → at least 1 Functional + 1 Negative test case.
> Each "Should" requirement → at least 1 Functional test case.

---

## 3. User Workflows

Describe the step-by-step user workflow for each use case. These map directly to Functional test case steps.

### Workflow 1: (name)

| Step | User Action                          | Expected System Response              |
|------|--------------------------------------|---------------------------------------|
| 1    |                                      |                                       |
| 2    |                                      |                                       |
| 3    |                                      |                                       |

> **Test generation rule:** Each workflow → 1 Functional test case. Steps map to test steps.

### Workflow 2: (name)

| Step | User Action                          | Expected System Response              |
|------|--------------------------------------|---------------------------------------|
| 1    |                                      |                                       |
| 2    |                                      |                                       |

---

## 4. Input / Output Specification

### 4.1 Inputs (user-provided)

| Input              | Type    | Required | Valid Values / Range         | Example         |
|--------------------|---------|----------|------------------------------|-----------------|
|                    |         |          |                              |                 |

> **Test generation rule:** Each required input → 1 Negative test case (missing), 1 Negative test case (invalid value).

### 4.2 Outputs (system-produced)

| Output             | Format  | When Produced                          | Example         |
|--------------------|---------|----------------------------------------|-----------------|
|                    |         |                                        |                 |

---

## 5. Error Scenarios

What can go wrong from the user's perspective?

| Scenario                         | Error Message / Behavior                 |
|----------------------------------|------------------------------------------|
|                                  |                                          |

> **Test generation rule:** Each row → 1 Negative test case.

---

## 6. Pre/Post Conditions

### Preconditions (what must be true before using this feature)

- [ ] Condition 1
- [ ] Condition 2

### Postconditions (what must be true after successful use)

- [ ] Condition 1
- [ ] Condition 2

> **Test generation rule:** Each precondition violation → 1 Negative test case.

---

## 7. Impact on Existing Features

| Existing Feature              | Expected Impact                          |
|-------------------------------|------------------------------------------|
|                               | No impact / Changed behavior / Removed   |

> **Test generation rule:** "No impact" → 1 Regression test case per feature listed. "Changed" → 1 Regression + 1 Functional.

---

## 8. Acceptance Criteria

These are the pass/fail criteria. Each one maps to a test case.

- [ ] AC-01:
- [ ] AC-02:
- [ ] AC-03:

> **Test generation rule:** Each acceptance criterion → 1 Functional test case.

---

## 9. Test Case Generation Summary

After filling this spec, count the test cases to generate:

| Source Section               | Functional | Regression | Negative |
|------------------------------|:----------:|:----------:|:--------:|
| Sec 2 - Requirements         |            |            |          |
| Sec 3 - Workflows            |            |            |          |
| Sec 4 - Inputs               |            |            |          |
| Sec 5 - Error Scenarios      |            |            |          |
| Sec 6 - Precondition Violations |         |            |          |
| Sec 7 - Existing Feature Impact |         |            |          |
| Sec 8 - Acceptance Criteria  |            |            |          |
| **Total**                    |            |            |          |

Then generate all test cases into `template.yaml` and run:
```bash
python qtest.py add-tc --dry-run     # validate & preview
python qtest.py add-tc               # push to qTest
```

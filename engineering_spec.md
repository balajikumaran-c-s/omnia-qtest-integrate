# Engineering Specification Template

> Fill this template for each feature/change. This drives test case generation.
> Refer to `rules.md` for classification into Functional / Regression / Negative.

---

## 1. Feature Overview

| Field              | Value                                    |
|--------------------|------------------------------------------|
| Feature Name       |                                          |
| Component          |                                          |
| Spec ID / Jira     |                                          |
| Author             |                                          |
| Change Type        | New / Modified / Bug Fix / Upgrade       |

**Summary:** (one-line description of what this feature does)

---

## 2. Technical Design

### 2.1 Architecture

- **Affected modules:**
- **New files/scripts:**
- **Modified files/scripts:**
- **Dependencies added/changed:**

### 2.2 Implementation Details

Describe HOW the feature is implemented technically:

- Data flow:
- API endpoints (new/changed):
- CLI commands (new/changed):
- Configuration parameters (new/changed):
- Database/state changes:

### 2.3 Interfaces

| Interface     | Type        | Input              | Output             |
|---------------|-------------|--------------------|--------------------|
|               | API / CLI / Config |               |                    |

---

## 3. Input Validation

List all inputs this feature accepts and their constraints:

| Input Parameter    | Type    | Required | Valid Range / Values        | Default  |
|--------------------|---------|----------|-----------------------------|----------|
|                    |         |          |                             |          |

> **Test generation rule:** Each row generates 1 Functional (valid input) + 1 Negative (invalid input) test case.

---

## 4. Error Handling

List all error conditions and how they are handled:

| Error Condition                  | Expected Behavior                        | Recovery   |
|----------------------------------|------------------------------------------|------------|
|                                  |                                          |            |

> **Test generation rule:** Each row generates 1 Negative test case.

---

## 5. Dependencies

| Dependency         | Version   | What Happens If Unavailable              |
|--------------------|-----------|------------------------------------------|
|                    |           |                                          |

> **Test generation rule:** Each "unavailable" scenario generates 1 Negative test case.

---

## 6. Backward Compatibility

| Existing Feature              | Impact (None / Changed / Broken)  | Notes      |
|-------------------------------|-----------------------------------|------------|
|                               |                                   |            |

> **Test generation rule:** Each "None" impact row generates 1 Regression test case (verify it still works). Each "Changed" row generates 1 Functional + 1 Regression test case.

---

## 7. Configuration Changes

| Parameter          | Old Value | New Value | File               |
|--------------------|-----------|-----------|--------------------|
|                    |           |           |                    |

> **Test generation rule:** Each row generates 1 Functional (new value works) + 1 Negative (invalid value handled) + 1 Regression (old behavior preserved if applicable).

---

## 8. Test Case Generation Checklist

After filling this spec, use the tables above to generate test cases:

- [ ] Section 3 (Inputs) → Functional + Negative test cases
- [ ] Section 4 (Errors) → Negative test cases
- [ ] Section 5 (Dependencies) → Negative test cases
- [ ] Section 6 (Backward Compat) → Regression test cases
- [ ] Section 7 (Config Changes) → Functional + Negative + Regression test cases
- [ ] Happy path end-to-end → At least 1 Functional test case
- [ ] All generated test cases written to `template.yaml`

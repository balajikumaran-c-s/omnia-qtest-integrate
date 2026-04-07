# Test Case Preparation Rules

This document defines the rules for generating test cases from engineering and functional specifications. Every test case must be classified as one of three types: **Functional**, **Regression**, or **Negative**.

---

## 1. Test Case Type Definitions

### Functional
> Does the feature work as designed?

A test case is **Functional** when it validates that a NEW or CHANGED feature behaves exactly as described in the specification under NORMAL operating conditions.

**Generate a Functional test case when:**
- A new feature is introduced (first-time implementation)
- A new API endpoint, CLI command, or configuration option is added
- A new workflow or user journey is defined in the spec
- The spec describes a "shall" / "must" / "should" requirement
- The spec defines input → output behavior for valid inputs
- The spec describes integration between two or more components
- The spec defines a new state transition or lifecycle event
- The spec introduces a new role, permission, or access control rule

**Naming convention:** `<component>_<action>_<expected_behavior>`
```
Example: omnia_slurm_add_compute_node_x86
Example: omnia_local_repo_create_with_pulp_backend
Example: omnia_k8s_service_cluster_ha_failover
```

**Template pattern:**
```yaml
- name: "omnia_<component>_<action>_<expected>"
  description: "Validate that <component> <does what> as per <spec section>"
  precondition: "<what must be set up before this test>"
  status: "Design"
  type: "Functional"
  steps:
    - description: "<perform the action described in spec>"
      expected: "<expected outcome from spec>"
    - description: "<verify the result>"
      expected: "<state/output matches spec>"
```

---

### Regression
> Does existing functionality still work after the change?

A test case is **Regression** when it validates that EXISTING functionality that was working BEFORE the change continues to work AFTER the change.

**Generate a Regression test case when:**
- An existing feature is modified, refactored, or optimized
- A dependency is upgraded (e.g., Slurm version, K8s version, OS version)
- Infrastructure changes are made (e.g., new network config, storage backend swap)
- A bug fix is applied that touches shared code paths
- A configuration default value is changed
- A library, package, or base image is updated
- Code is moved, renamed, or restructured without intended behavior change
- The spec says "maintain backward compatibility" or "no impact to existing"

**Naming convention:** `<component>_<existing_feature>_after_<change>`
```
Example: omnia_slurm_job_submission_after_k8s_upgrade
Example: omnia_nfs_mounts_persist_after_oim_update
Example: omnia_ldap_auth_works_after_ansible_upgrade
```

**Template pattern:**
```yaml
- name: "omnia_<existing_feature>_after_<change>"
  description: "Verify that <existing feature> still works after <change>"
  precondition: "<existing feature was working before the change>"
  status: "Design"
  type: "Regression"
  steps:
    - description: "<perform the existing workflow that was working before>"
      expected: "<same result as before the change>"
    - description: "<verify no side effects from the change>"
      expected: "<system state unchanged for unrelated components>"
```

---

### Negative
> Does the system handle failures, bad inputs, and edge cases gracefully?

A test case is **Negative** when it validates that the system handles INVALID inputs, ERROR conditions, BOUNDARY cases, and FAILURE scenarios without crashing, corrupting data, or leaving the system in a broken state.

**Generate a Negative test case when:**
- The spec mentions error handling, validation, or rejection of input
- A required field can be left empty or given an invalid value
- A service, node, or dependency can be unavailable during an operation
- A network partition, timeout, or connection failure can occur
- A resource limit can be exceeded (disk full, memory, max nodes)
- A user can attempt an action without proper permissions
- A concurrent or duplicate operation can happen (race condition)
- The spec describes "if X fails, then Y should happen"
- An operation can be interrupted mid-way (reboot, kill, cancel)
- A configuration file can have wrong syntax, missing fields, or invalid values

**Naming convention:** `<component>_<action>_<failure_condition>`
```
Example: omnia_slurm_add_node_with_controller_down
Example: omnia_local_repo_create_with_invalid_url
Example: omnia_provision_with_duplicate_hostname
```

**Template pattern:**
```yaml
- name: "omnia_<component>_<action>_<failure_condition>"
  description: "Verify that <component> handles <failure condition> gracefully"
  precondition: "<setup the failure condition>"
  status: "Design"
  type: "Negative"
  steps:
    - description: "<trigger the failure condition>"
      expected: "<clear error message or graceful handling>"
    - description: "<verify system is not left in broken state>"
      expected: "<system recoverable, no data corruption>"
```

---

## 2. Decision Flowchart

Use this to classify each requirement from the spec:

```
Is this a NEW feature or NEW behavior?
  ├── YES → Is the test checking VALID/NORMAL usage?
  │           ├── YES → FUNCTIONAL
  │           └── NO  → Is it checking error/invalid/edge case?
  │                       └── YES → NEGATIVE
  └── NO  → Is EXISTING functionality being retested after a change?
              ├── YES → REGRESSION
              └── NO  → Is it checking error/invalid/edge case on existing feature?
                          └── YES → NEGATIVE
```

---

## 3. Rules for Step Writing

1. **Each step must be independently verifiable** - one action, one check
2. **Step description** - write what to DO (command, action, click)
3. **Step expected** (optional) - write what to SEE (output, state, message)
4. **Keep steps atomic** - don't combine "do A and B and verify C"
5. **First step** - always setup/precondition verification
6. **Last step** - always verify final state or cleanup
7. **Error steps (Negative)** - always check error message AND system recovery

---

## 4. Required Fields per Test Case

| Field         | Required | Notes                                              |
|---------------|----------|----------------------------------------------------|
| name          | YES      | snake_case, prefix with component                  |
| description   | YES      | one line explaining what is validated               |
| precondition  | YES      | what must be true before running                   |
| status        | YES      | always "Design" for new test cases                 |
| type          | YES      | Functional / Regression / Negative                 |
| steps         | YES      | at least 1 step                                    |
| steps.description | YES  | what to do                                         |
| steps.expected | NO      | what to expect (optional but recommended)          |

---

## 5. Coverage Rules

For each feature/requirement in the spec, generate AT MINIMUM:

| Spec Type                    | Functional | Regression | Negative |
|------------------------------|:----------:|:----------:|:--------:|
| New feature                  | 1+         | -          | 1+       |
| Modified feature             | 1+         | 1+         | 1+       |
| Bug fix                      | -          | 1+         | 1+       |
| Dependency upgrade           | -          | 2+         | 1+       |
| Configuration change         | 1+         | 1+         | 1+       |
| API endpoint (new)           | 1+         | -          | 2+       |
| API endpoint (changed)       | 1+         | 1+         | 2+       |

---

## 6. Example: Generating from a Spec

**Spec requirement:** "Add support for adding compute nodes to an existing Slurm cluster via pxe_mapping file"

**Functional test cases:**
```yaml
- name: "omnia_slurm_add_single_compute_node_x86"
  type: "Functional"
  # Tests: can we add one x86 node?

- name: "omnia_slurm_add_multiple_compute_nodes_bulk"
  type: "Functional"
  # Tests: can we add many nodes at once?

- name: "omnia_slurm_add_gpu_compute_node"
  type: "Functional"
  # Tests: can we add a GPU node?
```

**Regression test cases:**
```yaml
- name: "omnia_slurm_existing_jobs_after_node_addition"
  type: "Regression"
  # Tests: do running jobs survive the node addition?

- name: "omnia_slurm_old_nodes_not_impacted_after_adding_new"
  type: "Regression"
  # Tests: are existing nodes still working?
```

**Negative test cases:**
```yaml
- name: "omnia_slurm_add_node_with_controller_not_running"
  type: "Negative"
  # Tests: what happens if controller is down?

- name: "omnia_slurm_add_duplicate_node_entry_in_pxe_mapping"
  type: "Negative"
  # Tests: what happens with duplicate entries?

- name: "omnia_slurm_add_node_with_nfs_server_unavailable"
  type: "Negative"
  # Tests: what happens if NFS is down during add?
```

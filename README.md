# qtest_integrate

CLI tool to connect to **qTest Manager** via REST API, browse test design folders, and push test cases from YAML templates.

---

## How it works

```
 You write test cases          The tool validates             Test cases appear
 in template.yaml       --->   and pushes via API     --->   in qTest Manager
                                                              (Test Design tab)

 You run qtest ls        --->   API fetches modules    --->   Folder tree printed
                                                              to your terminal
```

---

## Installation

```bash
cd qtest_integrate
./setup_qtest_env.sh
```

**What setup_qtest_env.sh does:**
1. Creates a Python virtual environment (`.venv/`) inside the project
2. Installs all dependencies (requests, click, PyYAML)
3. Registers `qtest` as a system command (works from any directory)
4. Enables **tab completion** (`qtest` + TAB shows commands, `ls` + TAB shows `-al`, etc.)

After setup, the `qtest` command works immediately. No need to activate any venv manually.

---

## Next steps after installation

### Step 1: Edit config.yaml

Open `config.yaml` and fill in your qTest details:

```yaml
qtest:
  # Your qTest instance URL
  base_url: "https://qtest.gtie.dell.com"

  # Bearer token from qTest
  # Go to: qTest -> Profile (top-right) -> API & SDK -> Generate Token
  api_token: "a4ddcddf-eba1-49e5-ba61-d64622c78185"

  # Project ID - from the qTest URL
  # Example: https://qtest.gtie.dell.com/p/183/portal/... -> project_id: 183
  project_id: 183

  # Default folder path for 'qtest ls' (optional, leave empty for root)
  default_path: ""

  # Parent ID for 'qtest add-tc' - where test cases will be created
  # From the qTest URL: ...#id=1273930&tab=testdesign -> parent_id: 1273930
  parent_id: 1273930

# Allowed values for template validation
# You can add or remove values to match your qTest project settings
allowed:
  status:
    - design
    - new
    - ready
    - approved
    - draft
    - in review

  type:
    - manual
    - automation
    - performance
    - functional
    - regression
    - negative
    - scenario
```

**Where to find each value:**

| Field | How to find it |
|---|---|
| `base_url` | Your qTest URL, e.g. `https://qtest.company.com` |
| `api_token` | qTest -> click your profile (top-right) -> API & SDK -> Generate Token |
| `project_id` | From URL: `https://qtest.company.com/p/`**183**`/portal/...` |
| `parent_id` | Open a folder in Test Design, look at URL: `...#id=`**1273930**`&tab=testdesign` |

### Step 2: Test the connection

```bash
qtest ls
```

You should see a tree of test design folders.

### Step 3: Write test cases in template.yaml

See the [Template format](#template-format) section below.

### Step 4: Push to qTest

```bash
qtest add-tc --dry-run    # preview first
qtest add-tc              # push to qTest
```

---

## Commands

### `qtest ls` - List test design folders

```bash
qtest ls                                    # top-level folders
qtest ls "Omnia-2.X"                        # sub-tree under Omnia-2.X
qtest ls "Omnia-2.X/Slurm Cluster"         # go deeper using /
qtest ls -al "Omnia-2.X/Slurm Cluster"     # folders + test case titles
```

**Output:**
```
Project 183 / Omnia-2.X/Slurm Cluster

├── [F] add-delete node
├── [F] Apptainer
├── [F] Passwordless SSH
├── [F] Slurm Head and Compute
└── [F] Slurm with GPU Support Custom Repo

5 folders
```

**With `-al` (like `ls -al` in Linux):**
```
├── [F] Passwordless SSH
│   ├── [TC] TC-5890: omnia_passwordless_ssh_from_slurm_node_2_to_slurm_node_1_IP
│   ├── [TC] TC-5889: omnia_passwordless_ssh_from_slurm_node_1_to_slurm_node_2_IP
│   └── [TC] TC-5888: omnia_passwordless_ssh_from_slurm_node_2_to_slurm_control_node_IP
```

`[F]` = Folder, `[TC]` = Test Case

### `qtest add-tc` - Add test cases

```bash
qtest add-tc                                # push template.yaml to parent_id in config
qtest add-tc -t my_tests.yaml              # use a different template file
qtest add-tc --parent-id 1273930            # override parent ID from config
qtest add-tc --dry-run                      # validate and preview, don't push
```

**What happens:**
1. **Validates** the template - checks YAML syntax, required fields, allowed values
2. **Pushes** each test case to qTest via REST API under the configured `parent_id`

**Output:**
```
Step 1: Validating template: template.yaml

Validation passed: 3 test case(s) in template.yaml

Step 2: Pushing test cases

  Parent ID : 1273930
  Project   : 183
  Count     : 3
------------------------------------------------------------
  [1] OK: TC-6659 - omnia_verify_slurm_cluster_health_after_reboot
  [2] OK: TC-6660 - omnia_verify_nfs_mount_persistence_across_reboot
  [3] OK: TC-6661 - omnia_slurm_job_submission_as_ldap_user
------------------------------------------------------------

Completed successfully! 3 test case(s) added.
```

### `qtest show-config` - Show configuration

```bash
qtest show-config
```

Shows your current config with the API token masked.

---

## Template format

### Example template.yaml

```yaml
test_cases:

  - name: "omnia_verify_slurm_cluster_health_after_reboot"
    description: "Validate that all Slurm services recover correctly after a full cluster reboot"
    precondition: "Slurm cluster is deployed and all nodes are in idle state"
    status: "Design"
    type: "Functional"
    steps:
      - description: "Reboot all compute nodes simultaneously"
        expected: "All nodes reboot without errors"
      - description: "Wait for nodes to come back online and run sinfo"
        expected: "All nodes show idle state within 5 minutes"
      - description: "Submit a test job: srun -N2 hostname"
        expected: "Job completes successfully"

  - name: "omnia_slurm_add_node_with_controller_down"
    description: "Verify that adding a node fails gracefully when the Slurm controller is down"
    precondition: "Slurm cluster is deployed, controller service is stopped"
    status: "Design"
    type: "Negative"
    steps:
      - description: "Stop the slurmctld service on the controller node"
      - description: "Attempt to add a new compute node"
        expected: "Clear error message indicating controller is unreachable"
      - description: "Restart slurmctld and verify cluster recovers"
        expected: "All existing nodes return to idle state"
```

### Field reference

| Field | Required | Description |
|---|:---:|---|
| `name` | **Yes** | Test case title. Use snake_case, prefix with component name. |
| `description` | **Yes** | One-line summary of what this test validates. |
| `precondition` | **Yes** | What must be true before running this test. Setup requirements, cluster state, etc. |
| `status` | **Yes** | Test case status. Must be one of the values listed in `allowed.status` in config.yaml. |
| `type` | **Yes** | Test case type. Must be one of the values listed in `allowed.type` in config.yaml. |
| `steps` | **Yes** | List of test steps. At least 1 step required. |
| `steps[].description` | **Yes** | What to do in this step. The action to perform. |
| `steps[].expected` | **No** | Expected result. Optional - skip it for setup steps or when the result is obvious. |

### Allowed values for `status`

| Value | When to use |
|---|---|
| `design` | New test case, still being written (default) |
| `new` | Just created, not yet reviewed |
| `ready` | Reviewed and ready for execution |
| `approved` | Formally approved by lead/manager |
| `draft` | Work in progress, incomplete |
| `in review` | Under review by the team |

### Allowed values for `type`

| Value | When to use |
|---|---|
| `manual` | Manually executed test case |
| `automation` | Automated test case |
| `functional` | Validates a feature works as designed (happy path) |
| `regression` | Validates existing features still work after a change |
| `negative` | Validates error handling, invalid inputs, failure scenarios |
| `performance` | Load, stress, or performance testing |
| `scenario` | End-to-end scenario covering multiple features |

You can modify these allowed values in the `allowed:` section of `config.yaml`.

### Validation

The tool validates the template **before** pushing anything. It catches:

- YAML syntax errors with exact line and column number
- Missing required fields (name, description, precondition, status, type, steps)
- Invalid `status` or `type` values not in the allowed list
- Steps with bad indentation or missing description
- Empty or non-string field values

If validation fails, **nothing is pushed** and you get a clear error report:

```
Validation FAILED for: template.yaml

  [1] test_cases[1]: 'name' is required and must be a non-empty string.
  [2] test_cases[2] (my_test): Invalid status 'Foo'. Allowed: design, new, ready, ...
  [3] test_cases[3].steps[2]: 'description' is required for each step.

3 error(s) found. Fix the template and try again.
```

---

## Project structure

```
qtest_integrate/
├── setup_qtest_env.sh      # Run this to install (./setup_qtest_env.sh)
├── setup.py                # Python package config
├── requirements.txt        # Python dependencies
├── config.yaml             # Your qTest connection settings
├── template.yaml           # Your test cases to push
├── README.md               # This file
├── .gitignore
├── qtest_cli/              # CLI source code
│   ├── __init__.py
│   └── main.py
├── rules.md                # Test case writing rules (Functional/Regression/Negative)
├── engineering_spec.md     # Engineering spec template
└── functional_spec.md      # Functional spec template
```

---

## Reference docs

| File | What it contains |
|---|---|
| `rules.md` | Rules for classifying test cases as Functional, Regression, or Negative |
| `engineering_spec.md` | Template to document engineering specifications |
| `functional_spec.md` | Template to document functional specifications |

These help you write test cases systematically: fill the spec, follow the rules, write the YAML, push to qTest.

---

## Uninstall

```bash
rm /usr/local/bin/qtest
rm -rf qtest_integrate/.venv
pip uninstall qtest-cli
```

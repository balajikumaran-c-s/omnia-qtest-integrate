# omnia-qtest-integrate

CLI tool to connect to **qTest Manager** via REST API. Browse test design folders and push test cases from YAML templates.

---

## Installation

### Linux / macOS

```bash
git clone git@github.com:balajikumaran-c-s/omnia-qtest-integrate.git
cd omnia-qtest-integrate
./setup_qtest_env.sh
```

This will:
1. Create a Python virtual environment (`.venv/`)
2. Install all dependencies
3. Register `qtest` as a system command (works without activating venv)
4. Enable tab completion (`qtest` + TAB shows `ls`, `add-tc`, `download`, etc.)

### Windows

```cmd
git clone git@github.com:balajikumaran-c-s/omnia-qtest-integrate.git
cd omnia-qtest-integrate
setup_qtest_env.bat
```

After setup on Windows:
```cmd
.venv\Scripts\activate.bat
qtest --help
```

---

## Setup

Edit `config.yaml` with your qTest instance details:

```yaml
qtest:
  base_url: "https://your-company.qtestnet.com"
  api_token: "YOUR_BEARER_TOKEN_HERE"
  project_id: 123
  default_path: ""
  parent_id: 456789

allowed:
  status:
    - design
  type:
    - functional
    - regression
    - negative
```

**How to get each value:**

| Field | Where to find it |
|---|---|
| `base_url` | Your qTest URL. Example: `https://qtest.gtie.dell.com` |
| `api_token` | Log in to qTest -> click your name (top-right) -> **API & SDK** -> **Generate Token** |
| `project_id` | Look at the qTest URL: `https://qtest.gtie.dell.com/p/`**183**`/portal/...` -> the number after `/p/` |
| `parent_id` | Open a folder in **Test Design** tab, look at URL: `...#id=`**1273930**`&tab=testdesign` -> the number after `id=` |
| `default_path` | Optional. If set, `qtest ls` starts from this path instead of root. Example: `"Omnia-2.X"` |

Verify the connection:

```bash
qtest ls
```

If everything is correct, you'll see a tree of test design folders.

---

## Commands

### `qtest ls` - Browse test design folders

```bash
# List top-level folders
qtest ls

# List sub-folders under a path (use / to go deeper)
qtest ls "Omnia-2.X"
qtest ls "Omnia-2.X/Slurm Cluster"
qtest ls "Omnia-2.X/Slurm Cluster/add-delete node"

# List folders AND test case titles (like ls -al in Linux)
qtest ls -al "Omnia-2.X/Slurm Cluster"
```

**Example output:**

```
Project 183 / Omnia-2.X/Slurm Cluster

├── [F] add-delete node
├── [F] Apptainer
├── [F] Passwordless SSH
├── [F] Slurm Head and Compute
└── [F] Slurm with GPU Support Custom Repo

5 folders
```

With `-al`:

```
├── [F] Passwordless SSH
│   ├── [TC] TC-5890: omnia_passwordless_ssh_node2_to_node1_IP
│   ├── [TC] TC-5889: omnia_passwordless_ssh_node1_to_node2_IP
│   └── [TC] TC-5888: omnia_passwordless_ssh_node2_to_control_IP
```

`[F]` = Folder, `[TC]` = Test Case

---

### `qtest add-tc` - Add test cases to qTest

```bash
# Preview what will be added (no changes made)
qtest add-tc --dry-run

# Push test cases from template.yaml to qTest
qtest add-tc

# Use a different template file
qtest add-tc -t my_tests.yaml

# Override parent ID from config
qtest add-tc --parent-id 456789
```

**What happens when you run `qtest add-tc`:**

1. **Step 1** - Validates template.yaml (checks YAML syntax, required fields, allowed values)
2. **Step 2** - Pushes each test case to qTest via REST API

**Example output:**

```
Step 1: Validating template: template.yaml

Validation passed: 3 test case(s) in template.yaml

Step 2: Pushing test cases

  Parent ID : 456789
  Project   : 123
  Count     : 3
------------------------------------------------------------
  [1] OK: TC-6659 - omnia_verify_slurm_cluster_health
  [2] OK: TC-6660 - omnia_verify_nfs_mount_persistence
  [3] OK: TC-6661 - omnia_slurm_job_submission_ldap_user
------------------------------------------------------------

Completed successfully! 3 test case(s) added.
```

---

### `qtest show-config` - Show current configuration

```bash
qtest show-config
```

Shows your config with API token masked.

---

## Template format

Write test cases in `template.yaml`:

```yaml
test_cases:
  - name: "omnia_verify_slurm_cluster_health_after_reboot"
    description: "Validate that all Slurm services recover after a full cluster reboot"
    precondition: "Slurm cluster is deployed and all nodes are in idle state"
    status: "Design"
    type: "Functional"
    steps:
      - description: "Reboot all compute nodes simultaneously"
        expected: "All nodes reboot without errors"
      - description: "Run sinfo to check node states"
        expected: "All nodes show idle state within 5 minutes"
      - description: "Submit a test job: srun -N2 hostname"
        expected: "Job completes successfully"
```

### Fields

| Field | Required | Description |
|---|:---:|---|
| `name` | **Yes** | Test case title. Use snake_case. |
| `description` | **Yes** | What this test validates. |
| `precondition` | **Yes** | What must be true before running (cluster state, setup, etc). |
| `status` | **Yes** | Must be one of the allowed values (see below). |
| `type` | **Yes** | Must be one of the allowed values (see below). |
| `steps` | **Yes** | At least 1 step required. |
| `steps[].description` | **Yes** | What action to perform in this step. |
| `steps[].expected` | **No** | Expected result. Optional - skip for setup steps. |

### Allowed values for `status`

| Value | When to use |
|---|---|
| `design` | All new test cases use this status |

### Allowed values for `type`

| Value | When to use |
|---|---|
| `functional` | Validates a feature works correctly (happy path) |
| `regression` | Validates existing features still work after a change |
| `negative` | Validates error handling, invalid inputs, failure scenarios |

You can modify these lists in the `allowed:` section of `config.yaml`.

---

## Validation

The tool validates the template **before** pushing anything. It catches:

- **YAML syntax errors** with exact line and column number
- **Missing required fields** (name, description, precondition, status, type, steps)
- **Invalid status/type** not in the allowed list from config.yaml
- **Bad indentation** in steps
- **Empty fields**

If validation fails, nothing gets pushed:

```
Validation FAILED for: template.yaml

  [1] test_cases[1]: 'name' is required and must be a non-empty string.
  [2] test_cases[2] (my_test): Invalid status 'Foo'. Allowed: design, new, ready, ...
  [3] test_cases[3].steps[2]: 'description' is required for each step.

3 error(s) found. Fix the template and try again.
```

---

## Error handling

| Error | Message |
|---|---|
| qTest server unreachable | `Error: Cannot connect to qTest. Check your base_url in config.yaml.` |
| Invalid API token | `Error: Authentication failed. Check your api_token in config.yaml.` |
| No access to project | `Error: Access denied. Verify project permissions for this token.` |
| Wrong project ID | `Error: Not found (404). Check your project_id in config.yaml.` |
| Config file missing | `Error: Config not found: config.yaml` |
| Required config field empty | `Error: 'api_token' not set in config.yaml` |
| Folder not found | `Error: 'FolderName' not found under (root).` + shows available folders |
| Template file missing | `Validation FAILED: File not found: template.yaml` |
| Template has bad YAML | `Invalid YAML syntax at line 4, column 6: ...` |

---

## Project structure

```
omnia-qtest-integrate/
├── setup_qtest_env.sh      # Setup script (Linux/macOS)
├── setup_qtest_env.bat     # Setup script (Windows)
├── setup.py                # Python package config
├── requirements.txt        # Dependencies
├── config.yaml             # Your qTest connection settings
├── template.yaml           # Test cases to push
├── README.md
├── .gitignore
└── qtest_cli/
    ├── __init__.py
    └── main.py             # CLI implementation
```

---

## Uninstall

**Linux/macOS:**
```bash
rm /usr/local/bin/qtest
rm -rf .venv
```

**Windows:**
```cmd
rmdir /s /q .venv
```

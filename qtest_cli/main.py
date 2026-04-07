#!/usr/bin/env python3
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
qtest_cli - CLI tool for listing test design folders and adding test cases.

After installation, use the ``qtest`` command::

    qtest ls
    qtest ls "Omnia-2.X"
    qtest ls -al "Omnia-2.X/Slurm Cluster"
    qtest add-tc
    qtest add-tc -t my_tests.yaml --dry-run
    qtest show-config
"""

import sys
import os

import click
import yaml
import requests


# Paths resolved from the project directory (parent of qtest_cli/)
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(_PROJECT_DIR, "config.yaml")
DEFAULT_TEMPLATE = os.path.join(_PROJECT_DIR, "template.yaml")

# Tree-drawing characters
TREE_TEE = "├── "
TREE_LAST = "└── "
TREE_PIPE = "│   "
TREE_BLANK = "    "

# qTest field IDs - update these for your project
FIELD_STATUS = 36712
FIELD_TYPE = 36713

STATUS_MAP = {
    "design": 58491, "new": 201, "ready": 58495,
    "approved": 58529, "draft": 58505, "in review": 58492,
}
TYPE_MAP = {
    "manual": 701, "automation": 702, "performance": 703,
    "functional": 58566, "regression": 58567,
    "negative": 58568, "scenario": 704,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(path):
    """Load and validate qTest configuration from a YAML file."""
    if not os.path.isfile(path):
        click.echo(f"Error: Config not found: {path}", err=True)
        click.echo(
            "Copy config.yaml.example to config.yaml "
            "and fill in your values.", err=True
        )
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as cfg_file:
        raw = yaml.safe_load(cfg_file)
    cfg = raw.get("qtest", {})
    for key in ["base_url", "api_token", "project_id"]:
        val = cfg.get(key)
        if not val or str(val).startswith("YOUR_"):
            click.echo(f"Error: '{key}' not set in {path}", err=True)
            sys.exit(1)
    allowed = raw.get("allowed", {})
    default_statuses = list(STATUS_MAP.keys())
    default_types = list(TYPE_MAP.keys())
    cfg["allowed_statuses"] = [
        s.lower().strip()
        for s in allowed.get("status", default_statuses)
    ]
    cfg["allowed_types"] = [
        t.lower().strip()
        for t in allowed.get("type", default_types)
    ]
    return cfg


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def qtest_api(session, base_url, project_id, method, endpoint,
              params=None, json_data=None):
    """Send a request to the qTest REST API."""
    url = (
        f"{base_url.rstrip('/')}/api/v3"
        f"/projects/{project_id}{endpoint}"
    )
    try:
        resp = getattr(session, method)(
            url, params=params, json=json_data, timeout=60
        )
    except requests.exceptions.ConnectionError:
        click.echo(
            "Error: Cannot connect to qTest. "
            "Check your base_url in config.yaml.",
            err=True
        )
        sys.exit(1)
    except requests.exceptions.Timeout:
        click.echo(
            "Error: Request timed out. "
            "qTest server may be slow or unreachable.",
            err=True
        )
        sys.exit(1)

    if resp.status_code == 401:
        click.echo(
            "Error: Authentication failed. "
            "Check your api_token in config.yaml.",
            err=True
        )
        sys.exit(1)
    if resp.status_code == 403:
        click.echo(
            "Error: Access denied. "
            "Verify project permissions for this token.",
            err=True
        )
        sys.exit(1)
    if resp.status_code == 404:
        click.echo(
            f"Error: Not found (404). "
            f"Check your project_id in config.yaml. "
            f"URL: {url}",
            err=True
        )
        sys.exit(1)
    return resp


def _get_test_cases(session, base_url, project_id, module_id):
    """Fetch test cases for a module."""
    resp = qtest_api(
        session, base_url, project_id, "get", "/test-cases",
        params={"parentId": module_id, "page": 1, "size": 100}
    )
    return resp.json() if resp.status_code == 200 else []


# ---------------------------------------------------------------------------
# Tree printing
# ---------------------------------------------------------------------------
def _print_tc_line(prefix, connector, test_case):
    """Print a single test case line in the tree."""
    tc_pid = test_case.get("pid", "?")
    tc_name = test_case.get("name", "?")
    click.echo(f"{prefix}{connector}[TC] {tc_pid}: {tc_name}")


def _print_folder_children(session, base_url, pid, children,
                           prefix, show_tc, counts):
    """Print child folders and their test cases."""
    for j, child in enumerate(children):
        is_last = j == len(children) - 1
        connector = TREE_LAST if is_last else TREE_TEE
        click.echo(
            f"{prefix}{connector}[F] {child.get('name', '?')}"
        )
        counts["folders"] += 1
        sub = child.get("children", [])
        sub_ext = TREE_BLANK if is_last else TREE_PIPE
        if sub:
            print_folder_tree(
                session, base_url, pid, sub,
                prefix + sub_ext, show_tc, counts
            )
        if show_tc:
            sub_tcs = _get_test_cases(
                session, base_url, pid, child["id"]
            )
            for k, tc in enumerate(sub_tcs):
                tc_last = k == len(sub_tcs) - 1 and not sub
                tc_conn = TREE_LAST if tc_last else TREE_TEE
                _print_tc_line(prefix + sub_ext, tc_conn, tc)
                counts["tcs"] += 1


def print_folder_tree(session, base_url, pid, modules,
                      prefix="", show_tc=False, counts=None):
    """Recursively print folder tree with optional test cases."""
    if counts is None:
        counts = {"folders": 0, "tcs": 0}
    for i, mod in enumerate(modules):
        is_last = i == len(modules) - 1
        connector = TREE_LAST if is_last else TREE_TEE
        click.echo(
            f"{prefix}{connector}[F] {mod.get('name', '?')}"
        )
        counts["folders"] += 1
        ext = TREE_BLANK if is_last else TREE_PIPE
        children = mod.get("children", [])

        if show_tc:
            tcs = _get_test_cases(
                session, base_url, pid, mod["id"]
            )
            if children:
                _print_folder_children(
                    session, base_url, pid, children,
                    prefix + ext, show_tc, counts
                )
            for j, tc in enumerate(tcs):
                tc_last = j == len(tcs) - 1
                tc_conn = TREE_LAST if tc_last else TREE_TEE
                _print_tc_line(prefix + ext, tc_conn, tc)
                counts["tcs"] += 1
        elif children:
            print_folder_tree(
                session, base_url, pid, children,
                prefix + ext, False, counts
            )
    return counts


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
def resolve_path(session, base_url, project_id, path_parts):
    """Walk the folder hierarchy using path segments."""
    resp = qtest_api(
        session, base_url, project_id, "get", "/modules"
    )
    resp.raise_for_status()
    data = resp.json()
    current = data if isinstance(data, list) else [data]
    names = []

    for i, seg in enumerate(path_parts):
        seg_lower = seg.lower().strip()
        matched = next(
            (m for m in current
             if m.get("name", "").lower().strip() == seg_lower),
            None
        )
        if not matched:
            where = "/".join(names) if names else "(root)"
            click.echo(
                f"Error: '{seg}' not found under {where}.",
                err=True
            )
            click.echo("\nAvailable:")
            for mod in current:
                click.echo(f"  - {mod.get('name', '?')}")
            sys.exit(1)
        names.append(matched.get("name", seg))
        detail_resp = qtest_api(
            session, base_url, project_id, "get",
            f"/modules/{matched['id']}",
            params={"expand": "descendants"}
        )
        detail_resp.raise_for_status()
        detail = detail_resp.json()
        if i == len(path_parts) - 1:
            return detail, "/".join(names)
        current = detail.get("children", [])
        if not current:
            mod_name = matched.get("name")
            click.echo(
                f"Error: '{mod_name}' has no sub-folders.",
                err=True
            )
            sys.exit(1)
    return None, "/".join(names)


# ---------------------------------------------------------------------------
# Template validation
# ---------------------------------------------------------------------------
def _validate_yaml_syntax(template_path):
    """Parse YAML and return (data, error_msg)."""
    with open(template_path, "r", encoding="utf-8") as tpl_file:
        raw = tpl_file.read()
    try:
        data = yaml.safe_load(raw)
        return data, None
    except yaml.YAMLError as exc:
        msg = "Invalid YAML syntax"
        if hasattr(exc, "problem_mark"):
            mark = exc.problem_mark
            msg += (
                f" at line {mark.line + 1}, "
                f"column {mark.column + 1}"
            )
        if hasattr(exc, "problem"):
            msg += f": {exc.problem}"
        return None, msg


ALLOWED_TC_FIELDS = {
    "name", "description", "precondition",
    "status", "type", "steps",
}
ALLOWED_STEP_FIELDS = {"description", "expected"}


def _validate_tc_fields(tc, idx, valid_statuses, valid_types):
    """Validate fields of a single test case. Returns list of errors."""
    errors = []
    prefix = f"test_cases[{idx}]"

    if not isinstance(tc, dict):
        errors.append(
            f"{prefix}: Must be a mapping (key: value), "
            "check indentation."
        )
        return errors

    # Check for unknown fields
    unknown = set(tc.keys()) - ALLOWED_TC_FIELDS
    if unknown:
        errors.append(
            f"{prefix}: Unknown field(s): {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_TC_FIELDS))}"
        )

    name = tc.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        errors.append(
            f"{prefix}: 'name' is required and "
            "must be a non-empty string."
        )
    display = (name or "(unnamed)").strip()[:50]

    # description - required, string
    desc = tc.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        errors.append(
            f"{prefix} ({display}): 'description' is required."
        )

    # precondition - required, string or list of strings
    precond = tc.get("precondition")
    if precond is None:
        errors.append(
            f"{prefix} ({display}): 'precondition' is required."
        )
    elif isinstance(precond, list):
        for pi, item in enumerate(precond, 1):
            if not isinstance(item, str) or not item.strip():
                errors.append(
                    f"{prefix} ({display}): "
                    f"precondition[{pi}] must be a non-empty string."
                )
        if len(precond) == 0:
            errors.append(
                f"{prefix} ({display}): "
                "'precondition' list must not be empty."
            )
    elif not isinstance(precond, str) or not precond.strip():
        errors.append(
            f"{prefix} ({display}): 'precondition' is required."
        )

    status = tc.get("status")
    if not status or not isinstance(status, str) or not status.strip():
        errors.append(
            f"{prefix} ({display}): 'status' is required."
        )
    elif status.lower().strip() not in valid_statuses:
        allowed = ", ".join(valid_statuses)
        errors.append(
            f"{prefix} ({display}): Invalid status "
            f"'{status}'. Allowed: {allowed}"
        )

    tc_type = tc.get("type")
    if not tc_type or not isinstance(tc_type, str) or not tc_type.strip():
        errors.append(
            f"{prefix} ({display}): 'type' is required."
        )
    elif tc_type.lower().strip() not in valid_types:
        allowed = ", ".join(valid_types)
        errors.append(
            f"{prefix} ({display}): Invalid type "
            f"'{tc_type}'. Allowed: {allowed}"
        )

    errors.extend(_validate_steps(tc.get("steps"), prefix, display))
    return errors


def _validate_steps(steps, prefix, display):
    """Validate the steps list. Returns list of errors."""
    errors = []
    if not isinstance(steps, list) or len(steps) == 0:
        errors.append(
            f"{prefix} ({display}): 'steps' is required "
            "and must have at least 1 step."
        )
        return errors
    for si, step in enumerate(steps, 1):
        step_prefix = f"{prefix}.steps[{si}]"
        if not isinstance(step, dict):
            errors.append(
                f"{step_prefix}: Must be a mapping, "
                "check indentation."
            )
            continue
        # Check for unknown fields in step
        unknown = set(step.keys()) - ALLOWED_STEP_FIELDS
        if unknown:
            errors.append(
                f"{step_prefix}: Unknown field(s): "
                f"{', '.join(sorted(unknown))}. "
                f"Allowed: {', '.join(sorted(ALLOWED_STEP_FIELDS))}"
            )
        step_desc = step.get("description")
        if not step_desc or not isinstance(step_desc, str):
            errors.append(
                f"{step_prefix}: 'description' is required "
                "for each step."
            )
        # expected is optional - no validation needed
    return errors


def validate_template(template_path,
                      allowed_statuses=None,
                      allowed_types=None):
    """Validate a test case template YAML. Returns (test_cases, errors)."""
    valid_statuses = allowed_statuses or list(STATUS_MAP.keys())
    valid_types = allowed_types or list(TYPE_MAP.keys())

    if not os.path.isfile(template_path):
        return [], [f"File not found: {template_path}"]

    data, syntax_err = _validate_yaml_syntax(template_path)
    if syntax_err:
        return [], [syntax_err]

    if not isinstance(data, dict):
        return [], [
            "Template must be a YAML mapping "
            "with a 'test_cases' key."
        ]
    tcs = data.get("test_cases")
    if not isinstance(tcs, list) or len(tcs) == 0:
        return [], ["'test_cases' must be a non-empty list."]

    errors = []
    for idx, tc in enumerate(tcs, 1):
        errors.extend(
            _validate_tc_fields(tc, idx, valid_statuses, valid_types)
        )
    return tcs, errors


def print_validation_result(errors, template_path, tc_count):
    """Print validation report. Returns True if valid."""
    if errors:
        click.echo(
            f"Validation FAILED for: {template_path}\n",
            err=True
        )
        for i, err in enumerate(errors, 1):
            click.echo(f"  [{i}] {err}", err=True)
        click.echo(
            f"\n{len(errors)} error(s) found. "
            "Fix the template and try again.",
            err=True
        )
        return False
    click.echo(
        f"Validation passed: {tc_count} test case(s) "
        f"in {template_path}"
    )
    return True


# ---------------------------------------------------------------------------
# Test case creation
# ---------------------------------------------------------------------------
def _format_precondition(precond):
    """Format precondition as numbered HTML list if it's a list."""
    if isinstance(precond, list):
        items = [
            f"{i}. {item.strip()}"
            for i, item in enumerate(precond, 1)
            if isinstance(item, str) and item.strip()
        ]
        return "<p>" + "<br/>".join(items) + "</p>"
    if isinstance(precond, str) and precond.strip():
        return f"<p>{precond.strip()}</p>"
    return ""


def build_payload(tc_def):
    """Convert a template test case into a qTest API payload."""
    name = tc_def.get("name", "").strip()
    if not name:
        return None, "No name"
    status_key = tc_def.get("status", "Design").lower().strip()
    type_key = tc_def.get("type", "Manual").lower().strip()
    status_val = STATUS_MAP.get(status_key, STATUS_MAP["design"])
    type_val = TYPE_MAP.get(type_key, TYPE_MAP["manual"])
    payload = {
        "name": name,
        "properties": [
            {"field_id": FIELD_STATUS, "field_value": status_val},
            {"field_id": FIELD_TYPE, "field_value": type_val},
        ],
    }
    if tc_def.get("description"):
        payload["description"] = f"<p>{tc_def['description']}</p>"
    precond = tc_def.get("precondition")
    if precond:
        payload["precondition"] = _format_precondition(precond)
    steps = tc_def.get("steps", [])
    if steps:
        test_steps = []
        for i, step in enumerate(steps, 1):
            step_data = {
                "description": (
                    f"<p>{step.get('description', '')}</p>"
                ),
                "order": i,
            }
            expected = step.get("expected")
            if expected and isinstance(expected, str) and expected.strip():
                step_data["expected"] = f"<p>{expected}</p>"
            test_steps.append(step_data)
        payload["test_steps"] = test_steps
    return payload, None


def push_test_case(session, base_url, project_id,
                   parent_id, payload):
    """Create a test case and move it to the correct parent."""
    resp = qtest_api(
        session, base_url, project_id,
        "post", "/test-cases", json_data=payload
    )
    if resp.status_code != 200:
        return None, (
            f"Create failed ({resp.status_code}): "
            f"{resp.text}"
        )
    tc_data = resp.json()
    move = qtest_api(
        session, base_url, project_id, "put",
        f"/test-cases/{tc_data['id']}",
        json_data={"parent_id": parent_id}
    )
    if move.status_code != 200:
        return tc_data, (
            f"Created but move failed ({move.status_code})"
        )
    return move.json(), None


def update_test_case(session, base_url, project_id,
                     tc_id, payload):
    """Update an existing test case by ID."""
    resp = qtest_api(
        session, base_url, project_id, "put",
        f"/test-cases/{tc_id}", json_data=payload
    )
    if resp.status_code != 200:
        return None, (
            f"Update failed ({resp.status_code}): "
            f"{resp.text}"
        )
    return resp.json(), None


def _fetch_existing_tcs(session, base_url, project_id,
                        parent_id):
    """Fetch all existing test cases under parent_id. Returns name->tc map."""
    existing = {}
    page = 1
    while True:
        resp = qtest_api(
            session, base_url, project_id, "get",
            "/test-cases",
            params={
                "parentId": parent_id,
                "page": page, "size": 100
            }
        )
        if resp.status_code != 200:
            break
        batch = resp.json()
        if not batch:
            break
        for tc_item in batch:
            name = tc_item.get("name", "").strip()
            if name:
                existing[name.lower()] = tc_item
        if len(batch) < 100:
            break
        page += 1
    return existing


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
class AliasGroup(click.Group):
    """Click group with command aliases."""
    ALIASES = {"ls": "list", "list-td": "list"}

    def get_command(self, ctx, cmd_name):
        """Resolve command aliases."""
        resolved = self.ALIASES.get(cmd_name, cmd_name)
        return super().get_command(ctx, resolved)


@click.group(cls=AliasGroup)
@click.option(
    "--config", "-c", default=DEFAULT_CONFIG,
    help="Path to config.yaml."
)
@click.pass_context
def cli(ctx, config):
    """
    qtest - CLI tool for qTest Manager integration.

    \b
    Browse test design folders and push test cases
    from YAML templates.

    \b
    Commands:
      list (ls)     List test design folders as a tree
      add-tc        Add test cases from a YAML template
      download      Download test cases from a folder as YAML
      show-config   Show current configuration
    """
    ctx.ensure_object(dict)
    ctx.obj["cfg_path"] = config


def _create_session(cfg):
    """Create a requests session with qTest auth headers."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {cfg['api_token']}",
        "Content-Type": "application/json",
    })
    return session


def _list_root(session, base_url, pid, show_all):
    """List top-level folders."""
    click.echo(f"Project {pid} / (root)\n")
    resp = qtest_api(session, base_url, pid, "get", "/modules")
    resp.raise_for_status()
    data = resp.json()
    modules = data if isinstance(data, list) else [data]
    if show_all:
        for mod in modules:
            detail = qtest_api(
                session, base_url, pid, "get",
                f"/modules/{mod['id']}",
                params={"expand": "descendants"}
            )
            mod["children"] = detail.json().get("children", [])
        counts = print_folder_tree(
            session, base_url, pid, modules, show_tc=True
        )
        click.echo(
            f"\n{counts['folders']} folders, "
            f"{counts['tcs']} test cases"
        )
    else:
        counts = print_folder_tree(
            session, base_url, pid, modules
        )
        click.echo(f"\n{counts['folders']} folders")


def _list_path(session, base_url, pid, resolved, show_all):
    """List folders at a specific path."""
    parts = [p.strip() for p in resolved.split("/") if p.strip()]
    detail, display = resolve_path(session, base_url, pid, parts)
    click.echo(f"Project {pid} / {display}\n")
    children = detail.get("children", [])
    if show_all:
        counts = {"folders": 0, "tcs": 0}
        if children:
            counts = print_folder_tree(
                session, base_url, pid, children, show_tc=True
            )
        direct = _get_test_cases(
            session, base_url, pid, detail["id"]
        )
        for tc_item in direct:
            _print_tc_line("", TREE_TEE, tc_item)
            counts["tcs"] += 1
        click.echo(
            f"\n{counts['folders']} folders, "
            f"{counts['tcs']} test cases"
        )
    else:
        if not children:
            click.echo("(no sub-folders)")
            return
        counts = print_folder_tree(
            session, base_url, pid, children
        )
        click.echo(f"\n{counts['folders']} folders")


@cli.command("list")
@click.argument("path", nargs=-1)
@click.option(
    "-al", "show_all", is_flag=True,
    default=False, help="Include test case titles."
)
@click.pass_context
def cmd_list(ctx, path, show_all):
    """
    List test design folders as a tree.

    \b
    Examples:
      qtest ls
      qtest ls "Omnia-2.X"
      qtest ls Omnia-2.X
      qtest ls "Omnia-2.X/Slurm Cluster"
      qtest ls Omnia-2.X/Service K8S Cluster
      qtest ls -al "Omnia-2.X/Slurm Cluster"
    """
    cfg = load_config(ctx.obj["cfg_path"])
    session = _create_session(cfg)
    base_url = cfg["base_url"]
    pid = cfg["project_id"]
    default_path = (cfg.get("default_path") or "").strip().strip("/")
    # Join multiple args: "Omnia-2.X/Service" "K8S" "Cluster" -> "Omnia-2.X/Service K8S Cluster"
    raw_path = " ".join(path) if path else ""
    resolved = (raw_path or default_path or "").strip().strip("/")

    if not resolved:
        _list_root(session, base_url, pid, show_all)
    else:
        _list_path(session, base_url, pid, resolved, show_all)


def _run_add_tc(session, base_url, project_id,
                pid, tcs, dry_run, force_new):
    """Execute the add-tc push/preview loop."""
    # Fetch existing test cases for duplicate check
    existing = {}
    if not force_new and not dry_run:
        click.echo(
            "Step 2: Checking existing test cases "
            "in target folder...\n"
        )
        existing = _fetch_existing_tcs(
            session, base_url, project_id, pid
        )
        click.echo(
            f"  Found {len(existing)} existing test case(s)\n"
        )
        step = "Step 3"
    else:
        step = "Step 2"

    action = "Preview" if dry_run else "Pushing"
    click.echo(f"{step}: {action} test cases\n")
    click.echo(f"  Parent ID : {pid}")
    click.echo(f"  Project   : {project_id}")
    click.echo(f"  Count     : {len(tcs)}")
    if force_new:
        click.echo("  Mode      : Force new (skip duplicate check)")
    if dry_run:
        click.echo("\n  [DRY RUN] No changes will be made.\n")
    click.echo("-" * 60)

    created, updated, failed = 0, 0, 0
    for i, tc_def in enumerate(tcs, 1):
        name = tc_def.get("name", "(unnamed)")
        if dry_run:
            steps = len(tc_def.get("steps", []))
            status = tc_def.get("status", "Design")
            tc_type = tc_def.get("type", "Manual")
            match = existing.get(name.lower()) if not force_new else None
            tag = "UPDATE" if match else "NEW"
            click.echo(f"  [{i}] [{tag}] {name}")
            click.echo(
                f"      Status: {status} | "
                f"Type: {tc_type} | Steps: {steps}"
            )
            if tag == "UPDATE":
                updated += 1
            else:
                created += 1
            continue

        payload, err = build_payload(tc_def)
        if err:
            click.echo(f"  [{i}] SKIP: {name} - {err}")
            failed += 1
            continue

        # Check if test case already exists
        match = existing.get(name.lower()) if not force_new else None

        if match:
            tc_id = match.get("id")
            tc_pid = match.get("pid", "?")
            result, err = update_test_case(
                session, base_url, project_id,
                tc_id, payload
            )
            if err:
                click.echo(
                    f"  [{i}] FAIL (update): "
                    f"{name} - {err}"
                )
                failed += 1
            else:
                click.echo(
                    f"  [{i}] UPDATED: {tc_pid} - {name}"
                )
                updated += 1
        else:
            result, err = push_test_case(
                session, base_url, project_id, pid, payload
            )
            if err:
                click.echo(
                    f"  [{i}] FAIL (create): "
                    f"{name} - {err}"
                )
                failed += 1
            else:
                tc_pid = result.get("pid", "?")
                click.echo(
                    f"  [{i}] CREATED: {tc_pid} - {name}"
                )
                created += 1

    click.echo("-" * 60)
    _print_add_tc_summary(
        created, updated, failed, dry_run,
        base_url, project_id, pid
    )


def _print_add_tc_summary(created, updated, failed,
                          dry_run, base_url, project_id, pid):
    """Print the final summary after add-tc."""
    if dry_run:
        click.echo(
            f"\n{created} to create, "
            f"{updated} to update."
        )
    elif failed == 0:
        click.echo(
            f"\nCompleted successfully! "
            f"{created} created, {updated} updated."
        )
        click.echo("\nVerify with:")
        click.echo(
            "  qtest ls -al  "
            "(if parent_id is under your default_path)"
        )
        click.echo("\nOr check in qTest UI:")
        click.echo(
            f"  {base_url}/p/{project_id}"
            f"/portal/project#id={pid}&tab=testdesign"
        )
    else:
        click.echo(
            f"\n{created} created, {updated} updated, "
            f"{failed} failed."
        )


@cli.command("add-tc")
@click.option(
    "-t", "--template", default=DEFAULT_TEMPLATE,
    show_default=True, help="Template YAML file."
)
@click.option(
    "-p", "--parent-id", default=None, type=int,
    help="Parent ID (overrides config)."
)
@click.option(
    "-d", "--dry-run", is_flag=True, default=False,
    help="Preview only, no changes."
)
@click.option(
    "--force-new", is_flag=True, default=False,
    help="Always create new test cases (skip duplicate check)."
)
@click.pass_context
def cmd_add_tc(ctx, template, parent_id, dry_run, force_new):
    """
    Add test cases from a YAML template to qTest.

    \b
    By default, if a test case with the same name already
    exists in the target folder, it will be UPDATED instead
    of creating a duplicate. Use --force-new to always create.

    \b
    Examples:
      qtest add-tc
      qtest add-tc -t my_tests.yaml
      qtest add-tc --parent-id 456789
      qtest add-tc --dry-run
      qtest add-tc --force-new
    """
    cfg = load_config(ctx.obj["cfg_path"])
    pid = parent_id or cfg.get("parent_id")
    if not pid:
        click.echo(
            "Error: No parent_id. Set it in config.yaml "
            "or use --parent-id.", err=True
        )
        sys.exit(1)

    click.echo(f"Step 1: Validating template: {template}\n")
    tcs, errors = validate_template(
        template,
        cfg.get("allowed_statuses"),
        cfg.get("allowed_types")
    )
    if not print_validation_result(
        errors, template, len(tcs) if tcs else 0
    ):
        sys.exit(1)
    click.echo("")

    session = _create_session(cfg)
    _run_add_tc(
        session, cfg["base_url"], cfg["project_id"],
        pid, tcs, dry_run, force_new
    )


@cli.command("show-config")
@click.pass_context
def cmd_show_config(ctx):
    """Show current configuration (token masked)."""
    cfg = load_config(ctx.obj["cfg_path"])
    token = cfg["api_token"]
    if len(token) > 8:
        masked = token[:4] + "****" + token[-4:]
    else:
        masked = "****"
    click.echo(f"  Base URL    : {cfg['base_url']}")
    click.echo(f"  Project ID  : {cfg['project_id']}")
    click.echo(f"  API Token   : {masked}")
    default_path = cfg.get("default_path") or "(none)"
    parent_id = cfg.get("parent_id") or "(none)"
    click.echo(f"  Default Path: {default_path}")
    click.echo(f"  Parent ID   : {parent_id}")


# ---------------------------------------------------------------------------
# Download test cases
# ---------------------------------------------------------------------------
def _strip_html(text):
    """Remove HTML tags from a string."""
    if not text:
        return ""
    import re  # pylint: disable=import-outside-toplevel
    clean = re.sub(r'<[^>]+>', '', str(text))
    return clean.strip()


def _fetch_tc_steps(session, base_url, project_id, tc_data):
    """Fetch test steps for a test case."""
    version_id = tc_data.get("test_case_version_id")
    tc_id = tc_data.get("id")
    if not version_id:
        return []
    resp = qtest_api(
        session, base_url, project_id, "get",
        f"/test-cases/{tc_id}/versions/{version_id}/test-steps"
    )
    if resp.status_code != 200:
        return []
    return resp.json() if isinstance(resp.json(), list) else []


def _tc_to_yaml_dict(tc_data, steps_data):
    """Convert a qTest test case + steps to a template-format dict."""
    # Extract status and type from properties
    status = "design"
    tc_type = "manual"
    for prop in tc_data.get("properties", []):
        if prop.get("field_id") == FIELD_STATUS:
            val_name = prop.get("field_value_name", "")
            if val_name:
                status = val_name.lower()
        elif prop.get("field_id") == FIELD_TYPE:
            val_name = prop.get("field_value_name", "")
            if val_name:
                tc_type = val_name.lower()

    precondition = _strip_html(
        tc_data.get("precondition", "")
    )

    tc_dict = {
        "name": tc_data.get("name", ""),
        "description": _strip_html(
            tc_data.get("description", "")
        ),
        "precondition": precondition if precondition else "N/A",
        "status": status,
        "type": tc_type,
        "steps": [],
    }

    for step in sorted(steps_data, key=lambda s: s.get("order", 0)):
        step_dict = {
            "description": _strip_html(
                step.get("description", "")
            ),
        }
        expected = _strip_html(step.get("expected", ""))
        if expected:
            step_dict["expected"] = expected
        tc_dict["steps"].append(step_dict)

    return tc_dict


def _fetch_module_tcs(session, base_url, project_id, module_id):
    """Fetch all test cases from a single module (paginated)."""
    page = 1
    result = []
    while True:
        resp = qtest_api(
            session, base_url, project_id, "get",
            "/test-cases",
            params={
                "parentId": module_id,
                "page": page, "size": 100
            }
        )
        if resp.status_code != 200:
            break
        batch = resp.json()
        if not batch:
            break
        result.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return result


def _collect_module_ids(detail):
    """Recursively collect all module IDs from a folder tree."""
    ids = [detail.get("id")]
    for child in detail.get("children", []):
        ids.extend(_collect_module_ids(child))
    return ids


def _download_folder(session, base_url, project_id,
                     detail, output_file):
    """Download all test cases recursively from a module tree."""
    # Collect all module IDs (this folder + all sub-folders)
    module_ids = _collect_module_ids(detail)
    click.echo(
        f"Scanning {len(module_ids)} folder(s) "
        "for test cases..."
    )

    all_tcs = []
    for mid in module_ids:
        tcs = _fetch_module_tcs(
            session, base_url, project_id, mid
        )
        all_tcs.extend(tcs)

    if not all_tcs:
        click.echo("No test cases found.")
        return

    click.echo(
        f"Found {len(all_tcs)} test case(s). "
        "Fetching details and steps...\n"
    )
    yaml_tcs = []
    for tc_summary in all_tcs:
        tc_id = tc_summary["id"]
        detail_resp = qtest_api(
            session, base_url, project_id, "get",
            f"/test-cases/{tc_id}"
        )
        if detail_resp.status_code != 200:
            continue
        tc_full = detail_resp.json()
        steps = _fetch_tc_steps(
            session, base_url, project_id, tc_full
        )
        yaml_tcs.append(_tc_to_yaml_dict(tc_full, steps))
        click.echo(
            f"  [{len(yaml_tcs)}] "
            f"{tc_summary.get('pid', '?')}: "
            f"{tc_summary.get('name', '?')}"
        )

    output = {"test_cases": yaml_tcs}
    with open(output_file, "w", encoding="utf-8") as out:
        yaml.dump(
            output, out, default_flow_style=False,
            allow_unicode=True, sort_keys=False
        )
    click.echo(
        f"\nDownloaded {len(yaml_tcs)} test case(s) "
        f"to {output_file}"
    )


@cli.command("download")
@click.argument("path", nargs=-1, required=True)
@click.option(
    "-o", "--output", default=None,
    help="Output YAML file (default: <folder_name>.yaml)."
)
@click.pass_context
def cmd_download(ctx, path, output):
    """
    Download test cases from a folder as YAML.

    \b
    Exports test cases in the same format as template.yaml
    so you can view, edit, or re-upload them.

    \b
    Examples:
      qtest download "Omnia-2.X/Slurm Cluster/add-delete node"
      qtest download Omnia-2.X/Slurm Cluster/Passwordless SSH
      qtest download "Omnia-2.X/Slurm Cluster/Passwordless SSH" -o ssh_tests.yaml
    """
    cfg = load_config(ctx.obj["cfg_path"])
    session = _create_session(cfg)
    base_url = cfg["base_url"]
    pid = cfg["project_id"]

    raw_path = " ".join(path) if path else ""
    parts = [p.strip() for p in raw_path.split("/") if p.strip()]
    detail, display = resolve_path(
        session, base_url, pid, parts
    )
    folder_name = parts[-1] if parts else "test_cases"

    if not output:
        safe_name = folder_name.replace(" ", "_").lower()
        output = f"{safe_name}.yaml"

    click.echo(f"Downloading from: {display}\n")
    _download_folder(
        session, base_url, pid, detail, output
    )


def main():
    """Entry point for the CLI."""
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()

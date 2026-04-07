#!/usr/bin/env python3
"""
qtest_cli - qTest CLI tool for listing test design folders and adding test cases.

After installation, use the `qtest` command:

    qtest ls                                       # top-level folders
    qtest ls "Omnia-2.X"                           # folder tree
    qtest ls -al "Omnia-2.X/Slurm Cluster"        # folders + test cases
    qtest add-tc                                   # add from template.yaml
    qtest add-tc -t my_tests.yaml --dry-run        # preview
    qtest show-config                              # show config
"""

import sys
import os

import click
import yaml
import requests


# Default file paths - resolved from the project directory (where qtest_cli lives)
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(_PROJECT_DIR, "config.yaml")
DEFAULT_TEMPLATE = os.path.join(_PROJECT_DIR, "template.yaml")

# Tree characters
T = "├── "
L = "└── "
P = "│   "
B = "    "

# qTest field IDs - update these for your project
FIELD_STATUS = 36712
FIELD_TYPE = 36713

STATUS_MAP = {
    "design": 58491, "new": 201, "ready": 58495,
    "approved": 58529, "draft": 58505, "in review": 58492,
}
TYPE_MAP = {
    "manual": 701, "automation": 702, "performance": 703,
    "functional": 58566, "regression": 58567, "negative": 58568, "scenario": 704,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(path):
    """Load and validate qTest configuration from a YAML file."""
    if not os.path.isfile(path):
        click.echo(f"Error: Config not found: {path}", err=True)
        click.echo("Copy config.yaml.example to config.yaml and fill in your values.", err=True)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = raw.get("qtest", {})
    for k in ["base_url", "api_token", "project_id"]:
        v = cfg.get(k)
        if not v or str(v).startswith("YOUR_"):
            click.echo(f"Error: '{k}' not set in {path}", err=True)
            sys.exit(1)
    allowed = raw.get("allowed", {})
    cfg["allowed_statuses"] = [s.lower().strip() for s in allowed.get("status", list(STATUS_MAP.keys()))]
    cfg["allowed_types"] = [t.lower().strip() for t in allowed.get("type", list(TYPE_MAP.keys()))]
    return cfg


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def api(session, base_url, project_id, method, endpoint, params=None, json_data=None):
    """Send a request to qTest REST API."""
    url = f"{base_url.rstrip('/')}/api/v3/projects/{project_id}{endpoint}"
    resp = getattr(session, method)(url, params=params, json=json_data, timeout=60)
    if resp.status_code == 401:
        click.echo("Error: Authentication failed. Check your API token.", err=True)
        sys.exit(1)
    if resp.status_code == 403:
        click.echo("Error: Access denied. Verify project permissions.", err=True)
        sys.exit(1)
    return resp


# ---------------------------------------------------------------------------
# Tree printing
# ---------------------------------------------------------------------------
def print_folder_tree(session, base_url, pid, modules, prefix="", show_tc=False, counts=None):
    """Recursively print folder tree with optional test cases."""
    if counts is None:
        counts = {"folders": 0, "tcs": 0}
    for i, mod in enumerate(modules):
        last = i == len(modules) - 1
        click.echo(f"{prefix}{L if last else T}[F] {mod.get('name', '?')}")
        counts["folders"] += 1

        ext = B if last else P
        children = mod.get("children", [])

        if show_tc:
            tcs = _get_test_cases(session, base_url, pid, mod["id"])
            items = [("f", c) for c in children] + [("t", t) for t in tcs]
            for j, (kind, item) in enumerate(items):
                ilast = j == len(items) - 1
                if kind == "f":
                    click.echo(f"{prefix}{ext}{L if ilast else T}[F] {item.get('name', '?')}")
                    counts["folders"] += 1
                    sub = item.get("children", [])
                    sub_ext = B if ilast else P
                    if sub:
                        print_folder_tree(session, base_url, pid, sub, prefix + ext + sub_ext, show_tc, counts)
                    sub_tcs = _get_test_cases(session, base_url, pid, item["id"])
                    for k, tc in enumerate(sub_tcs):
                        tlast = k == len(sub_tcs) - 1 and not sub
                        click.echo(f"{prefix}{ext}{sub_ext}{L if tlast else T}[TC] {tc.get('pid','?')}: {tc.get('name','?')}")
                        counts["tcs"] += 1
                else:
                    click.echo(f"{prefix}{ext}{L if ilast else T}[TC] {item.get('pid','?')}: {item.get('name','?')}")
                    counts["tcs"] += 1
        elif children:
            print_folder_tree(session, base_url, pid, children, prefix + ext, False, counts)
    return counts


def _get_test_cases(session, base_url, project_id, module_id):
    """Fetch test cases for a module."""
    resp = api(session, base_url, project_id, "get", "/test-cases",
               params={"parentId": module_id, "page": 1, "size": 100})
    return resp.json() if resp.status_code == 200 else []


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
def resolve_path(session, base_url, project_id, path_parts):
    """Walk the folder hierarchy using path segments."""
    resp = api(session, base_url, project_id, "get", "/modules")
    resp.raise_for_status()
    current = resp.json() if isinstance(resp.json(), list) else [resp.json()]
    names = []

    for i, seg in enumerate(path_parts):
        seg_lower = seg.lower().strip()
        matched = next((m for m in current if m.get("name", "").lower().strip() == seg_lower), None)
        if not matched:
            where = "/".join(names) if names else "(root)"
            click.echo(f"Error: '{seg}' not found under {where}.", err=True)
            click.echo("\nAvailable:")
            for m in current:
                click.echo(f"  - {m.get('name', '?')}")
            sys.exit(1)
        names.append(matched.get("name", seg))
        detail_resp = api(session, base_url, project_id, "get",
                          f"/modules/{matched['id']}", params={"expand": "descendants"})
        detail_resp.raise_for_status()
        detail = detail_resp.json()
        if i == len(path_parts) - 1:
            return detail, "/".join(names)
        current = detail.get("children", [])
        if not current:
            click.echo(f"Error: '{matched.get('name')}' has no sub-folders.", err=True)
            sys.exit(1)
    return None, "/".join(names)


# ---------------------------------------------------------------------------
# Template validation
# ---------------------------------------------------------------------------
def validate_template(template_path, allowed_statuses=None, allowed_types=None):
    """Validate a test case template YAML. Returns (test_cases, errors)."""
    valid_statuses = allowed_statuses or list(STATUS_MAP.keys())
    valid_types = allowed_types or list(TYPE_MAP.keys())
    errors = []

    if not os.path.isfile(template_path):
        return [], [f"File not found: {template_path}"]

    with open(template_path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        msg = "Invalid YAML syntax"
        if hasattr(exc, "problem_mark"):
            mark = exc.problem_mark
            msg += f" at line {mark.line + 1}, column {mark.column + 1}"
        if hasattr(exc, "problem"):
            msg += f": {exc.problem}"
        return [], [msg]

    if not isinstance(data, dict):
        return [], ["Template must be a YAML mapping with a 'test_cases' key."]
    tcs = data.get("test_cases")
    if not isinstance(tcs, list) or len(tcs) == 0:
        return [], ["'test_cases' must be a non-empty list."]

    for idx, tc in enumerate(tcs, 1):
        prefix = f"test_cases[{idx}]"
        if not isinstance(tc, dict):
            errors.append(f"{prefix}: Must be a mapping (key: value), check indentation.")
            continue

        name = tc.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}: 'name' is required and must be a non-empty string.")
        display = (name or "(unnamed)").strip()[:50]

        for field in ["description", "precondition"]:
            val = tc.get(field)
            if not val or not isinstance(val, str) or not val.strip():
                errors.append(f"{prefix} ({display}): '{field}' is required.")

        status = tc.get("status")
        if not status or not isinstance(status, str) or not status.strip():
            errors.append(f"{prefix} ({display}): 'status' is required.")
        elif status.lower().strip() not in valid_statuses:
            errors.append(f"{prefix} ({display}): Invalid status '{status}'. Allowed: {', '.join(valid_statuses)}")

        tc_type = tc.get("type")
        if not tc_type or not isinstance(tc_type, str) or not tc_type.strip():
            errors.append(f"{prefix} ({display}): 'type' is required.")
        elif tc_type.lower().strip() not in valid_types:
            errors.append(f"{prefix} ({display}): Invalid type '{tc_type}'. Allowed: {', '.join(valid_types)}")

        steps = tc.get("steps")
        if not isinstance(steps, list) or len(steps) == 0:
            errors.append(f"{prefix} ({display}): 'steps' is required and must have at least 1 step.")
        else:
            for si, step in enumerate(steps, 1):
                step_prefix = f"{prefix}.steps[{si}]"
                if not isinstance(step, dict):
                    errors.append(f"{step_prefix}: Must be a mapping, check indentation.")
                    continue
                if not step.get("description") or not isinstance(step.get("description"), str):
                    errors.append(f"{step_prefix}: 'description' is required for each step.")

    return tcs, errors


def print_validation_result(errors, template_path, tc_count):
    """Print validation report. Returns True if valid."""
    if errors:
        click.echo(f"Validation FAILED for: {template_path}\n", err=True)
        for i, err in enumerate(errors, 1):
            click.echo(f"  [{i}] {err}", err=True)
        click.echo(f"\n{len(errors)} error(s) found. Fix the template and try again.", err=True)
        return False
    click.echo(f"Validation passed: {tc_count} test case(s) in {template_path}")
    return True


# ---------------------------------------------------------------------------
# Test case creation
# ---------------------------------------------------------------------------
def build_payload(tc):
    """Convert a template test case into a qTest API payload."""
    name = tc.get("name", "").strip()
    if not name:
        return None, "No name"
    status_val = STATUS_MAP.get(tc.get("status", "Design").lower().strip(), STATUS_MAP["design"])
    type_val = TYPE_MAP.get(tc.get("type", "Manual").lower().strip(), TYPE_MAP["manual"])
    payload = {
        "name": name,
        "properties": [
            {"field_id": FIELD_STATUS, "field_value": status_val},
            {"field_id": FIELD_TYPE, "field_value": type_val},
        ],
    }
    if tc.get("description"):
        payload["description"] = f"<p>{tc['description']}</p>"
    if tc.get("precondition"):
        payload["precondition"] = f"<p>{tc['precondition']}</p>"
    steps = tc.get("steps", [])
    if steps:
        payload["test_steps"] = [
            {"description": f"<p>{s.get('description','')}</p>",
             "expected": f"<p>{s.get('expected','')}</p>", "order": i}
            for i, s in enumerate(steps, 1)
        ]
    return payload, None


def push_test_case(session, base_url, project_id, parent_id, payload):
    """Create a test case and move it to the correct parent module."""
    resp = api(session, base_url, project_id, "post", "/test-cases", json_data=payload)
    if resp.status_code != 200:
        return None, f"Create failed ({resp.status_code}): {resp.text}"
    tc = resp.json()
    move = api(session, base_url, project_id, "put",
               f"/test-cases/{tc['id']}", json_data={"parent_id": parent_id})
    if move.status_code != 200:
        return tc, f"Created but move failed ({move.status_code})"
    return move.json(), None


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------
class AliasGroup(click.Group):
    """Click group with command aliases."""
    ALIASES = {"ls": "list", "list-td": "list"}

    def get_command(self, ctx, name):
        return super().get_command(ctx, self.ALIASES.get(name, name))


@click.group(cls=AliasGroup)
@click.option("--config", "-c", default=DEFAULT_CONFIG, help="Path to config.yaml.")
@click.pass_context
def cli(ctx, config):
    """
    qtest - CLI tool for qTest Manager integration.

    \b
    Browse test design folders and push test cases from YAML templates.

    \b
    Commands:
      list (ls)     List test design folders as a tree
      add-tc        Add test cases from a YAML template
      show-config   Show current configuration
    """
    ctx.ensure_object(dict)
    ctx.obj["cfg_path"] = config


@cli.command("list")
@click.argument("path", required=False, default=None)
@click.option("-al", "show_all", is_flag=True, default=False, help="Include test case titles.")
@click.pass_context
def cmd_list(ctx, path, show_all):
    """
    List test design folders as a tree.

    \b
    Examples:
      qtest ls                                 # top-level folders
      qtest ls "Omnia-2.X"                     # sub-tree
      qtest ls "Omnia-2.X/Slurm Cluster"      # deeper
      qtest ls -al "Omnia-2.X/Slurm Cluster"  # folders + test cases
    """
    cfg = load_config(ctx.obj["cfg_path"])
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {cfg['api_token']}", "Content-Type": "application/json"})
    base, pid = cfg["base_url"], cfg["project_id"]
    default_path = (cfg.get("default_path") or "").strip().strip("/")
    resolved = (path or default_path or "").strip().strip("/")

    try:
        if not resolved:
            click.echo(f"Project {pid} / (root)\n")
            resp = api(s, base, pid, "get", "/modules")
            resp.raise_for_status()
            modules = resp.json() if isinstance(resp.json(), list) else [resp.json()]
            if show_all:
                for m in modules:
                    d = api(s, base, pid, "get", f"/modules/{m['id']}", params={"expand": "descendants"})
                    m["children"] = d.json().get("children", [])
                c = print_folder_tree(s, base, pid, modules, show_tc=True)
                click.echo(f"\n{c['folders']} folders, {c['tcs']} test cases")
            else:
                c = print_folder_tree(s, base, pid, modules)
                click.echo(f"\n{c['folders']} folders")
        else:
            parts = [p.strip() for p in resolved.split("/") if p.strip()]
            detail, display = resolve_path(s, base, pid, parts)
            click.echo(f"Project {pid} / {display}\n")
            children = detail.get("children", [])
            if show_all:
                c = {"folders": 0, "tcs": 0}
                if children:
                    c = print_folder_tree(s, base, pid, children, show_tc=True)
                direct = _get_test_cases(s, base, pid, detail["id"])
                for tc in direct:
                    click.echo(f"{T}[TC] {tc.get('pid','?')}: {tc.get('name','?')}")
                    c["tcs"] += 1
                click.echo(f"\n{c['folders']} folders, {c['tcs']} test cases")
            else:
                if not children:
                    click.echo("(no sub-folders)")
                    return
                c = print_folder_tree(s, base, pid, children)
                click.echo(f"\n{c['folders']} folders")
    except requests.exceptions.ConnectionError:
        click.echo("Error: Cannot connect to qTest. Check base_url.", err=True)
        sys.exit(1)


@cli.command("add-tc")
@click.option("-t", "--template", default=DEFAULT_TEMPLATE, show_default=True, help="Template YAML file.")
@click.option("-p", "--parent-id", default=None, type=int, help="Parent ID (overrides config).")
@click.option("-d", "--dry-run", is_flag=True, default=False, help="Preview only, no changes.")
@click.pass_context
def cmd_add_tc(ctx, template, parent_id, dry_run):
    """
    Add test cases from a YAML template to qTest.

    \b
    Validates the template first, then pushes test cases.

    \b
    Examples:
      qtest add-tc                              # uses template.yaml + config parent_id
      qtest add-tc -t my_tests.yaml             # custom template
      qtest add-tc --parent-id 456789          # override parent
      qtest add-tc --dry-run                    # preview only
    """
    cfg = load_config(ctx.obj["cfg_path"])
    pid = parent_id or cfg.get("parent_id")
    if not pid:
        click.echo("Error: No parent_id. Set it in config.yaml or use --parent-id.", err=True)
        sys.exit(1)

    click.echo(f"Step 1: Validating template: {template}\n")
    tcs, errors = validate_template(template, cfg.get("allowed_statuses"), cfg.get("allowed_types"))
    if not print_validation_result(errors, template, len(tcs) if tcs else 0):
        sys.exit(1)

    click.echo("")

    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {cfg['api_token']}", "Content-Type": "application/json"})
    base, project = cfg["base_url"], cfg["project_id"]

    click.echo(f"Step 2: {'Preview' if dry_run else 'Pushing'} test cases\n")
    click.echo(f"  Parent ID : {pid}")
    click.echo(f"  Project   : {project}")
    click.echo(f"  Count     : {len(tcs)}")
    if dry_run:
        click.echo("\n  [DRY RUN] No changes will be made.\n")
    click.echo("-" * 60)

    ok_count, fail_count = 0, 0

    for i, tc in enumerate(tcs, 1):
        name = tc.get("name", "(unnamed)")
        if dry_run:
            steps = len(tc.get("steps", []))
            click.echo(f"  [{i}] {name}")
            click.echo(f"      Status: {tc.get('status','Design')} | Type: {tc.get('type','Manual')} | Steps: {steps}")
            ok_count += 1
            continue

        payload, err = build_payload(tc)
        if err:
            click.echo(f"  [{i}] SKIP: {name} - {err}")
            fail_count += 1
            continue

        result, err = push_test_case(s, base, project, pid, payload)
        if err:
            click.echo(f"  [{i}] FAIL: {name} - {err}")
            fail_count += 1
        else:
            tc_pid = result.get("pid", "?")
            click.echo(f"  [{i}] OK: {tc_pid} - {name}")
            ok_count += 1

    click.echo("-" * 60)

    if dry_run:
        click.echo(f"\n{ok_count} test case(s) would be created.")
    elif fail_count == 0:
        click.echo(f"\nCompleted successfully! {ok_count} test case(s) added.")
        click.echo(f"\nVerify with:")
        click.echo(f"  qtest ls -al  (if parent_id is under your default_path)")
        click.echo(f"\nOr check in qTest UI:")
        click.echo(f"  {base}/p/{project}/portal/project#id={pid}&tab=testdesign")
    else:
        click.echo(f"\n{ok_count} succeeded, {fail_count} failed.")


@cli.command("show-config")
@click.pass_context
def cmd_show_config(ctx):
    """Show current configuration (token masked)."""
    cfg = load_config(ctx.obj["cfg_path"])
    token = cfg["api_token"]
    masked = token[:4] + "****" + token[-4:] if len(token) > 8 else "****"
    click.echo(f"  Base URL    : {cfg['base_url']}")
    click.echo(f"  Project ID  : {cfg['project_id']}")
    click.echo(f"  API Token   : {masked}")
    click.echo(f"  Default Path: {cfg.get('default_path') or '(none)'}")
    click.echo(f"  Parent ID   : {cfg.get('parent_id') or '(none)'}")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()

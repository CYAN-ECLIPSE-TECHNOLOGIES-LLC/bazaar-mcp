# OWNER-HANDS — eclipse-bazaar PyPI launch

Everything in this file is done **by the owner, in the owner's
browser**, in one sitting. The build is ready-to-publish; per the
name-squat protocol (gate S6) there is **no public mention of the
PyPI name before this session** — registration day is ship day, and
the first upload is the real Phase-1 artifact, never a placeholder.

> **Stop rule (gate §8.5):** no step below creates or hands over an
> API token. If any screen asks for a token, stop — the design has
> failed; tell the agent.

## 1. PyPI account (one-time, ~10 min)

1. Register at <https://pypi.org/account/register/> under the owner's
   identity/email. Password goes in the owner's password manager.
2. Enable **2FA** (TOTP or security key) — mandatory for uploads.
3. Recommended same sitting: repeat both steps on
   <https://test.pypi.org/account/register/> for rehearsal uploads.

## 2. Trusted Publisher for `eclipse-bazaar` (pending publisher)

On <https://pypi.org/manage/account/publishing/> → "Add a new pending
publisher" → **GitHub** tab. Enter these strings **exactly**:

| Field | Value |
|---|---|
| PyPI Project Name | `eclipse-bazaar` |
| GitHub Repository Owner | `CYAN-ECLIPSE-TECHNOLOGIES-LLC` |
| GitHub Repository Name | `bazaar-mcp` |
| GitHub Workflow Name | `publish-pypi.yml` |
| Environment Name | `pypi` |

(Optional rehearsal twin: same five values on
<https://test.pypi.org/manage/account/publishing/>.)

## 3. Ship day (owner triggers; agent prepares)

Release checklist — one run, both doors (gate A3):

1. Agent bumps `version` in `server.json` and runs
   `python tools/sync_package_data.py` (stamps VERSION, catalog,
   verdict snapshot, corpus) and the full test suite.
2. Agent commits; owner reviews; tag `v<version>` is pushed.
3. GitHub Actions `publish-pypi.yml` then, unattended:
   tests (version/data drift pins included) → builds wheel+sdist →
   `twine check` → publishes to PyPI via Trusted Publishing with
   PEP 740 attestations → re-publishes `server.json` to the Official
   MCP Registry. (Stamped data is committed in step 2 — CI builds
   from it as-is and the suite fails on staleness.)
4. Agent verifies: `pip index`/project page shows the version, and
   the Registry resolves `version=latest` to the same version.

## Fallback names (gate A4/K3 — only if registration rejects)

In order: `eclipse-bazaar-mcp`, then `cetech-eclipse-bazaar`. If all
three fail, the PyPI door pauses (the OCI door continues) — no
improvised name without an owner ruling.

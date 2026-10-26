# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""MCP client config discovery + identity extraction for `bazaar check`.

Privacy law (gate S3) is structural here, not a promise:
  * redact_config() runs on the parsed document before anything else
    touches it. Every `env` mapping is replaced by a key *count*;
    header mappings likewise; secret-named keys are dropped to a
    placeholder; `docker run -e KEY=value` args keep only the key.
  * extract_identity() only ever sees the redacted copy and returns a
    small identity dict (kind, name, pin) — raw args, env, and URLs'
    query strings never leave this module.
  * URL userinfo (user[:password]@) is stripped at extraction, on both
    the entry-URL path and the package-spec path: credentials are
    ABSENT from every identity, never masked — a masked value still
    proves a credential was present and reveals its shape (gate S3,
    card PY-D2).
  * Nothing in this module executes a configured server, opens a
    socket, or reads a tool description (gate C2 fence).
"""
import json
import os
import re
from pathlib import Path

SECRET_KEY_NAMES = {"authorization", "api_key", "apikey", "api-key",
                    "token", "access_token", "secret", "password",
                    "passwd", "client_secret"}
SCRIPT_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts"}
VALUE_FLAGS = {"-e", "--env", "-v", "--volume", "--mount", "-p", "--publish",
               "--name", "--network", "--hostname", "-w", "--workdir",
               "--entrypoint", "--user", "-u", "--pull", "--platform",
               "--env-file", "--from", "--with", "--python", "--package",
               "-p", "--index-url", "--extra-index-url"}


# ------------------------------------------------------------- discovery
def default_config_paths():
    """Known MCP client config locations that exist on this machine.
    The CLI prints this list before reading any of them."""
    home = Path.home()
    candidates = [
        home / "Library/Application Support/Claude/claude_desktop_config.json",
        home / ".config/Claude/claude_desktop_config.json",
        home / ".claude.json",
        home / ".cursor/mcp.json",
        home / ".codeium/windsurf/mcp_config.json",
        home / ".config/Code/User/mcp.json",
        Path.cwd() / ".mcp.json",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.insert(0, Path(appdata) / "Claude/claude_desktop_config.json")
    seen, out = set(), []
    for p in candidates:
        rp = str(p)
        if rp not in seen and p.exists():
            seen.add(rp)
            out.append(p)
    return out


# ------------------------------------------------------------- redaction
def _redact_envish(value):
    return "<redacted>"


def redact_config(node, _prev=None):
    """Deep-copy a parsed config with every secret carrier neutralised.
    Runs before extraction; the original is discarded by the caller."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            lk = str(k).lower()
            if lk == "env" and isinstance(v, dict):
                out[k] = {"<redacted-env-key-count>": len(v)}
            elif lk == "headers" and isinstance(v, dict):
                out[k] = {"<redacted-header-key-count>": len(v)}
            elif lk in SECRET_KEY_NAMES:
                out[k] = _redact_envish(v)
            else:
                out[k] = redact_config(v)
        return out
    if isinstance(node, list):
        out = []
        for i, item in enumerate(node):
            prev = node[i - 1] if i > 0 else None
            if (isinstance(item, str) and prev in ("-e", "--env")
                    and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", item)):
                out.append(item.split("=", 1)[0] + "=<redacted>")
            else:
                out.append(redact_config(item))
        return out
    return node


def server_entries(doc):
    """Yield (config_name, entry_dict) from a parsed client config.
    Supports the `mcpServers` shape (Claude Desktop/Code, Cursor,
    Windsurf, project .mcp.json) and the `servers` shape (VS Code)."""
    if not isinstance(doc, dict):
        return
    for key in ("mcpServers", "servers"):
        block = doc.get(key)
        if isinstance(block, dict):
            for name, entry in block.items():
                if isinstance(entry, dict):
                    yield str(name), entry


# ------------------------------------------------------------- identity
def _strip_url_userinfo(text):
    """Drop userinfo (user[:password]@) from the authority of a
    URL-shaped string. Credentials are removed outright, never masked
    (gate S3 / PY-D2): a masked value still proves a credential was
    present and leaks its shape. Non-URL strings pass through."""
    if "://" not in text:
        return text
    scheme, rest = text.split("://", 1)
    end = len(rest)
    for ch in "/?#":
        i = rest.find(ch)
        if i != -1:
            end = min(end, i)
    authority, tail = rest[:end], rest[end:]
    if "@" in authority:
        authority = authority.rsplit("@", 1)[-1]
    return scheme + "://" + authority + tail


def _parse_spec(spec):
    """Package spec -> (name, pin). Handles name@1.2, name==1.2,
    @scope/name@1.2, github:owner/repo. pin 'latest'/'*' -> None."""
    spec = spec.strip().strip('"').strip("'")
    if not spec:
        return None, None
    spec = _strip_url_userinfo(spec)
    if spec.startswith("github:"):
        return spec.split("/", 1)[-1].lower(), None
    name, pin = spec, None
    for sep in ("==", ">="):
        if sep in spec:
            name, pin = spec.split(sep, 1)
            break
    else:
        if spec.startswith("@"):
            rest = spec[1:]
            if "/" in rest:
                scope_name, _, tail = rest.partition("/")
                if "@" in tail:
                    nm, _, pn = tail.partition("@")
                    name, pin = "@" + scope_name + "/" + nm, pn
                else:
                    name = spec
        elif "@" in spec:
            name, _, pin = spec.partition("@")
    if pin in ("", "latest", "*"):
        pin = None
    return name.lower(), pin


def _first_positional(args):
    """First non-flag arg, skipping values of known value-flags and any
    -e payloads (already redacted to KEY=<redacted>)."""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return args[i + 1] if i + 1 < len(args) else None
        if a in VALUE_FLAGS:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return None


def _package_from_runner_args(args):
    """npx/uvx-style args -> parsed spec of the package being run."""
    if "--from" in args:
        spec = args[args.index("--from") + 1] if args.index("--from") + 1 < len(args) else None
        return _parse_spec(spec) if spec else (None, None)
    if "--package" in args or "-p" in args:
        idx = args.index("--package") if "--package" in args else args.index("-p")
        spec = args[idx + 1] if idx + 1 < len(args) else None
        return _parse_spec(spec) if spec else (None, None)
    pos = _first_positional(args)
    return _parse_spec(pos) if pos else (None, None)


def _docker_image(args):
    if "run" not in args:
        return None, None
    rest = args[args.index("run") + 1:]
    img = _first_positional(rest)
    if not img:
        return None, None
    pin = None
    name = img
    if "@" in img:
        name, _, pin = img.partition("@")
    else:
        last = img.rsplit("/", 1)[-1]
        if ":" in last:
            name = img[: img.rfind(":")]
            pin = last.split(":", 1)[1]
            if pin == "latest":
                pin = None
    return name.lower(), pin


def _local_identity(arg):
    p = Path(arg)
    if p.suffix.lower() in SCRIPT_SUFFIXES:
        parent = p.parent.name
        return (parent or p.stem).lower()
    return (p.name or p.stem).lower()


def extract_identity(entry):
    """Redacted config entry -> {"kind","name","pin"} or None.
    None means no identity could be extracted; the caller classifies
    the entry UNRESOLVABLE with `unresolvable_reason(entry)`."""
    url = entry.get("url") or entry.get("httpUrl") or entry.get("serverUrl")
    if isinstance(url, str) and url.strip():
        from urllib.parse import urlparse
        u = urlparse(_strip_url_userinfo(url.strip()))
        if u.netloc:
            host = u.hostname or ""
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            try:
                port = u.port
            except ValueError:
                port = None
            netloc = host + (f":{port}" if port else "")
            name = (netloc + u.path).rstrip("/").lower()
        else:
            # Schemeless authority form (user:pass@host/path): the
            # first segment is the authority — strip userinfo there too.
            first, sep, rest = u.path.partition("/")
            if "@" in first:
                first = first.rsplit("@", 1)[-1]
            name = (first + sep + rest).rstrip("/").lower()
        return {"kind": "remote", "name": name, "pin": None}
    command = entry.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    base = Path(command.strip()).name.lower()
    if base.endswith(".exe"):
        base = base[:-4]
    args = [a for a in (entry.get("args") or []) if isinstance(a, str)]
    if base in ("npx", "npm", "pnpm", "bunx", "yarn"):
        work = args[1:] if (base == "yarn" and args[:1] == ["dlx"]) else args
        if base == "npm" and work[:1] == ["exec"]:
            work = work[1:]
        name, pin = _package_from_runner_args(work)
        return {"kind": "package", "name": name, "pin": pin} if name else None
    if base == "uvx":
        name, pin = _package_from_runner_args(args)
        return {"kind": "package", "name": name, "pin": pin} if name else None
    if base == "uv":
        work = args
        if work[:2] == ["tool", "run"]:
            work = work[2:]
        elif work[:1] == ["run"]:
            work = work[1:]
            if work and work[0].endswith(".py"):
                return {"kind": "local", "name": _local_identity(work[0]), "pin": None}
        name, pin = _package_from_runner_args(work)
        return {"kind": "package", "name": name, "pin": pin} if name else None
    if base in ("docker", "podman"):
        name, pin = _docker_image(args)
        return {"kind": "image", "name": name, "pin": pin} if name else None
    if base in ("python", "python3", "py"):
        if "-m" in args:
            mod = args[args.index("-m") + 1] if args.index("-m") + 1 < len(args) else None
            return {"kind": "python-module", "name": mod.lower(), "pin": None} if mod else None
        if "-c" in args:
            return None
        target = _first_positional(args)
        return {"kind": "local", "name": _local_identity(target), "pin": None} if target else None
    if base == "node":
        target = _first_positional(args)
        return {"kind": "local", "name": _local_identity(target), "pin": None} if target else None
    if base in ("sh", "bash", "zsh", "cmd", "powershell", "pwsh", "env"):
        return None
    return {"kind": "command", "name": base, "pin": None}


def unresolvable_reason(entry):
    if not isinstance(entry, dict):
        return "entry is not an object"
    if not entry.get("command") and not (entry.get("url") or entry.get("httpUrl")):
        return "no command or url to extract an identity from"
    cmd = entry.get("command")
    if isinstance(cmd, str):
        base = Path(cmd.strip()).name.lower()
        if base in ("sh", "bash", "zsh", "cmd", "powershell", "pwsh", "env"):
            return f"shell wrapper command ({base}) — the wrapped target is not visible in the config"
        if base in ("python", "python3", "py") and "-c" in (entry.get("args") or []):
            return "inline interpreter code (-c) — no package or path identity"
    return "no package, image, path, or URL identity could be extracted"


def load_config_entries(path):
    """(entries, error) — entries are (name, redacted_entry) pairs."""
    try:
        doc = json.loads(Path(path).read_text())
    except Exception as e:
        return [], f"unparseable config ({type(e).__name__})"
    redacted = redact_config(doc)
    return list(server_entries(redacted)), None

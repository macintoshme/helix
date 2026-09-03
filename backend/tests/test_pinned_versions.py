"""Guard that the installed environment matches `backend/requirements.txt`.

This is the concrete check behind the M-6 version bumps: it fails if any pinned
package is missing or present at a different version (e.g. an unapplied bump or a
silent downgrade). The expected versions are parsed from requirements.txt, so a
Dependabot bump keeps this test in sync automatically.
"""
import importlib.metadata as md
import pathlib
import re

_REQ = pathlib.Path(__file__).resolve().parent.parent / "requirements.txt"
_PIN_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._\-]*)(\[[^\]]*\])?==([\w.\+!-]+)\s*(#.*)?$"
)


def _pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in _REQ.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = _PIN_RE.match(line)
        if m:
            pins[m.group(1).lower()] = m.group(3)
    return pins


def test_requirements_have_pins():
    assert len(_pins()) >= 8


def test_installed_versions_match_pins():
    mismatches = []
    for name, want in _pins().items():
        try:
            have = md.version(name)
        except md.PackageNotFoundError:
            mismatches.append(f"{name}: pinned {want} but not installed")
            continue
        if have != want:
            mismatches.append(f"{name}: pinned {want} but {have} installed")
    assert not mismatches, "; ".join(mismatches)

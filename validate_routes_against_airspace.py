#!/usr/bin/env python3
"""Validate routes from latest_routes.json against Airspace.xml from vatSys/australia-dataset."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

DEFAULT_BRANCH = "master"
DEFAULT_ROUTES_FILE = Path(__file__).with_name("latest_routes.json")
DEFAULT_CACHE_DIR = Path(__file__).with_name(".cache")
SPECIAL_TOKENS = {
    "DCT",
    "VIA",
    "SID",
    "STAR",
    "RWY",
    "DEP",
    "ARR",
    "RAD",
    "RNP",
    "RNAV",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
}


def prompt_branch(default: str) -> str:
    try:
        raw = input(f"Which australia-dataset branch should I validate against? [{default}]: ").strip()
    except EOFError:
        raw = ""
    return raw or default


def download_airspace_xml(branch: str, output_path: Path) -> Path:
    url = f"https://raw.githubusercontent.com/vatSys/australia-dataset/{branch}/Airspace.xml"
    try:
        with urlopen(Request(url, headers={"User-Agent": "vatpac-routes-validator"})) as response:
            data = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"Unable to download Airspace.xml for branch '{branch}': HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to reach GitHub for branch '{branch}': {exc.reason}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return output_path


def load_airspace_identifiers(xml_path: Path) -> set[str]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    identifiers: set[str] = set()

    for element in root.iter():
        for value in element.attrib.values():
            if isinstance(value, str) and value.strip():
                identifiers.update(token.upper() for token in re.findall(r"[A-Za-z0-9]+", value))
        if element.text and element.text.strip():
            identifiers.update(token.upper() for token in re.findall(r"[A-Za-z0-9]+", element.text))

    # Also include the tag names so the validator can compare procedure shapes if needed.
    identifiers.update(str(element.tag).upper() for element in root.iter())
    return identifiers


def extract_route_tokens(route: str) -> list[str]:
    tokens = [token.upper() for token in re.findall(r"[A-Za-z0-9]+", route)]
    return [token for token in tokens if token not in SPECIAL_TOKENS]


def load_routes(routes_file: Path) -> list[dict]:
    with routes_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            return payload["data"]
        if isinstance(payload.get("routes"), list):
            return payload["routes"]
    raise ValueError(f"Unsupported routes payload in {routes_file}")


def get_route_line_numbers(routes_file: Path) -> list[int | None]:
    text = routes_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    pattern = re.compile(r'"route"\s*:\s*"(?P<value>[^"]*)"')

    line_numbers: list[int | None] = []
    for line_number, line in enumerate(lines, start=1):
        match = pattern.search(line)
        if match:
            line_numbers.append(line_number)
    return line_numbers


def validate_routes(routes: Iterable[dict], identifiers: set[str], route_line_numbers: list[int | None] | None = None) -> tuple[list[dict], list[str]]:
    issues: list[dict] = []
    missing_tokens: list[str] = []

    for index, route_entry in enumerate(routes):
        route_text = str(route_entry.get("route", "")).strip()
        if not route_text:
            continue

        tokens = extract_route_tokens(route_text)
        missing = [token for token in tokens if token not in identifiers]
        if missing:
            line_number = None
            if route_line_numbers is not None and index < len(route_line_numbers):
                line_number = route_line_numbers[index]

            issues.append(
                {
                    "dept": route_entry.get("dept", ""),
                    "dest": route_entry.get("dest", ""),
                    "route": route_text,
                    "missing": missing,
                    "line": line_number,
                }
            )
            missing_tokens.extend(missing)

    return issues, missing_tokens


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate route tokens against Airspace.xml from vatSys/australia-dataset")
    parser.add_argument("--branch", help="Branch name to use from vatSys/australia-dataset")
    parser.add_argument("--routes-file", type=Path, default=DEFAULT_ROUTES_FILE, help="Path to the JSON file with routes")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Directory to cache downloaded Airspace.xml")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    branch = args.branch or prompt_branch(DEFAULT_BRANCH)
    routes_file = args.routes_file.resolve()
    cache_dir = args.cache_dir.resolve()
    airspace_path = cache_dir / f"Airspace-{branch}.xml"

    if not routes_file.exists():
        print(f"Routes file not found: {routes_file}", file=sys.stderr)
        return 2

    try:
        if not airspace_path.exists():
            print(f"Downloading Airspace.xml from branch '{branch}'...")
            download_airspace_xml(branch, airspace_path)
        else:
            print(f"Using cached Airspace.xml: {airspace_path}")

        identifiers = load_airspace_identifiers(airspace_path)
        routes = load_routes(routes_file)
        route_line_numbers = get_route_line_numbers(routes_file)
        issues, missing_tokens = validate_routes(routes, identifiers, route_line_numbers)

        total_routes = len(routes)
        invalid_routes = len(issues)
        print(f"Validated {total_routes} routes against branch '{branch}'.")
        print(f"Routes with missing tokens: {invalid_routes}")
        print(f"Missing token count: {len(missing_tokens)}")

        if issues:
            print("\nExamples of missing tokens:")
            for issue in issues[:20]:
                line_text = f" [line {issue['line']}]" if issue.get('line') is not None else ""
                print(f"- {issue['dept']}->{issue['dest']}{line_text}: {issue['route']}")
                print(f"  missing: {', '.join(issue['missing'])}")

            print("\nTop missing tokens:")
            from collections import Counter

            counter = Counter(missing_tokens)
            for token, count in counter.most_common(20):
                print(f"- {token}: {count}")
        else:
            print("All route tokens were found in Airspace.xml.")

        return 0
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

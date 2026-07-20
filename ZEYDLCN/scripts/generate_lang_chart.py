#!/usr/bin/env python3
"""Generate assets/top-langs.svg from GitHub language stats (private repos included when the token allows)."""
import json
import math
import os
import sys
import urllib.error
import urllib.request

USERNAME = "ZEYDLCN"
LANGS_COUNT = 8
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "assets", "top-langs.svg")

COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Dart": "#00B4AB",
    "C#": "#178600", "HTML": "#e34c26", "CSS": "#663399", "Swift": "#F05138",
    "C++": "#f34b7d", "C": "#555555", "Java": "#b07219", "Python": "#3572A5",
    "Kotlin": "#A97BFF", "Ruby": "#701516", "CMake": "#DA3434",
    "Shell": "#89e051", "Dockerfile": "#384d54", "Objective-C": "#438eff",
    "Go": "#00ADD8", "Rust": "#dea584", "PHP": "#4F5D95",
}
FALLBACK_COLOR = "#8b949e"

BG, TITLE_COLOR, TEXT_COLOR = "#0d1117", "#A855F7", "#c9d1d9"


def api_get(path, token):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch_repos(token):
    # /user/repos sees private repos with a PAT; the Actions GITHUB_TOKEN
    # cannot use /user endpoints, so fall back to public repos only.
    for base in (f"/user/repos?affiliation=owner&per_page=100&page=",
                 f"/users/{USERNAME}/repos?type=owner&per_page=100&page="):
        try:
            repos, page = [], 1
            while True:
                batch = api_get(base + str(page), token)
                repos.extend(batch)
                if len(batch) < 100:
                    return repos
                page += 1
        except urllib.error.HTTPError as e:
            print(f"warning: {base} failed ({e.code}), trying fallback", file=sys.stderr)
    sys.exit("error: could not list repositories")


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    totals = {}
    for repo in fetch_repos(token):
        if repo["fork"]:
            continue
        for lang, size in api_get(f"/repos/{repo['full_name']}/languages", token).items():
            totals[lang] = totals.get(lang, 0) + size

    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LANGS_COUNT]
    total = sum(size for _, size in top)
    langs = [(name, size / total * 100, COLORS.get(name, FALLBACK_COLOR)) for name, size in top]

    width, height = 360, 100 + len(langs) * 22
    cx, cy, r = 275, height / 2 + 18, 52
    circumference = 2 * math.pi * r

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-label="Most used languages">',
        f'<rect width="{width}" height="{height}" rx="4.5" fill="{BG}"/>',
        f'<text x="25" y="38" font-family="\'Segoe UI\', Ubuntu, Sans-Serif" font-size="18" font-weight="600" fill="{TITLE_COLOR}">Most Used Languages</text>',
    ]

    offset = 0.0
    for _, pct, color in langs:
        seg = pct / 100 * circumference
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{color}" stroke-width="14" '
            f'stroke-dasharray="{seg:.2f} {circumference - seg:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += seg

    y = 72
    for name, pct, color in langs:
        parts.append(f'<circle cx="31" cy="{y - 4}" r="5" fill="{color}"/>')
        parts.append(
            f'<text x="44" y="{y}" font-family="\'Segoe UI\', Ubuntu, Sans-Serif" font-size="12" fill="{TEXT_COLOR}">'
            f'{name} {pct:.2f}%</text>'
        )
        y += 22

    parts.append("</svg>")

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        f.write("\n".join(parts) + "\n")
    print(f"wrote {os.path.normpath(OUTPUT)}: " + ", ".join(f"{n} {p:.1f}%" for n, p, _ in langs))


if __name__ == "__main__":
    main()

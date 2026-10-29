#!/usr/bin/env python3
"""Generate assets/top-langs-{dark,light}.svg from GitHub language stats.

Languages that describe markup, styling, notebooks or build config rather than hand-written
code are ignored (see IGNORED_LANGUAGES): one exported notebook or a bundled site can
otherwise outweigh an entire backend. Add more with IGNORE_LANGUAGES="Foo,Bar".

Private repositories are included only when GH_TOKEN is a personal access token that can list
them; the Actions GITHUB_TOKEN sees public repositories only. Per-repo details are logged for
public repositories only, because Actions logs of a public repo are public.
"""
import html
import json
import math
import os
import sys
import urllib.error
import urllib.request

USERNAME = "ZEYDLCN"
LANGS_COUNT = 6
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

IGNORED_LANGUAGES = {
    "HTML", "CSS", "SCSS", "Sass", "Less", "Jupyter Notebook",
    "Jinja", "Handlebars", "EJS", "Mustache", "Liquid", "XSLT",
    "Dockerfile", "Makefile", "CMake", "Batchfile", "TeX", "Roff",
} | {n.strip() for n in os.environ.get("IGNORE_LANGUAGES", "").split(",") if n.strip()}

COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "C#": "#178600", "Java": "#b07219", "C++": "#f34b7d", "C": "#555555",
    "Kotlin": "#A97BFF", "Dart": "#00B4AB", "Swift": "#F05138", "Ruby": "#701516",
    "Shell": "#89e051", "Go": "#00ADD8", "Rust": "#dea584", "PHP": "#4F5D95",
    "Vue": "#41b883", "Svelte": "#ff3e00", "PLpgSQL": "#336790", "Objective-C": "#438eff",
}
FALLBACK_COLOR = "#8b949e"
OTHER_COLOR = "#6e7681"

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", title="#e6edf3", text="#c9d1d9",
                 muted="#8b949e", track="#21262d", accent="#A855F7"),
    "light": dict(bg="#ffffff", border="#d0d7de", title="#1f2328", text="#1f2328",
                  muted="#59636e", track="#eaeef2", accent="#7C3AED"),
}

FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
WIDTH, PAD = 495, 24


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


def collect(token):
    """Return ({language: bytes} without ignored languages, repo count, private repo count)."""
    totals, repo_count, private_count = {}, 0, 0
    for repo in fetch_repos(token):
        if repo["fork"]:
            continue
        repo_count += 1
        private = repo.get("private", False)
        private_count += private
        langs = api_get(f"/repos/{repo['full_name']}/languages", token)
        if not private:
            top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:3]
            print(f"  {repo['name']}: " + ", ".join(
                f"{n}{' (ignored)' if n in IGNORED_LANGUAGES else ''} {s:,}" for n, s in top))
        for lang, size in langs.items():
            if lang not in IGNORED_LANGUAGES:
                totals[lang] = totals.get(lang, 0) + size
    return totals, repo_count, private_count


def summarize(totals):
    """Top LANGS_COUNT languages as (name, percent, color), the rest folded into 'Other'."""
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(size for _, size in ranked)
    langs = [(n, s / total * 100, COLORS.get(n, FALLBACK_COLOR)) for n, s in ranked[:LANGS_COUNT]]
    rest = sum(s for _, s in ranked[LANGS_COUNT:])
    if rest:
        langs.append(("Other", rest / total * 100, OTHER_COLOR))
    return langs


def render(langs, theme):
    t = THEMES[theme]
    bar_x, bar_w, bar_y, bar_h = PAD, WIDTH - 2 * PAD, 74, 10
    rows = math.ceil(len(langs) / 2)
    legend_y = bar_y + bar_h + 34
    height = legend_y + rows * 24 + 10
    col_w = (WIDTH - 2 * PAD) / 2
    label = "Most used languages: " + ", ".join(f"{n} {p:.1f}%" for n, p, _ in langs)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" fill="none" role="img" aria-label="{html.escape(label)}">',
        f"<style>text{{font-family:{FONT}}}</style>",
        '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".32"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
        f'<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}"/></clipPath>',
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="6" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<rect x="{PAD}" y="22" width="4" height="18" rx="2" fill="{t["accent"]}"/>',
        f'<text x="{PAD + 14}" y="36" font-size="16" font-weight="600" fill="{t["title"]}">Top Languages</text>',
        f'<text x="{PAD}" y="58" font-size="11" fill="{t["muted"]}">By code volume · notebooks, markup and stylesheets excluded</text>',
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}" fill="{t["track"]}"/>',
        '<g clip-path="url(#bar)">',
    ]

    x = float(bar_x)
    for _, pct, color in langs:
        w = pct / 100 * bar_w
        parts.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{w + 0.5:.2f}" height="{bar_h}" fill="{color}"/>')
        x += w
    parts.append(
        f'<rect x="{bar_x - 90}" y="{bar_y}" width="90" height="{bar_h}" fill="url(#shine)">'
        f'<animateTransform attributeName="transform" type="translate" values="0,0;{bar_w + 90},0;{bar_w + 90},0" '
        'keyTimes="0;.45;1" dur="5s" repeatCount="indefinite"/></rect>'
    )
    parts.append("</g>")

    for i, (name, pct, color) in enumerate(langs):
        col, row = divmod(i, rows)
        lx = PAD + col * col_w
        y = legend_y + row * 24
        parts.append(f'<circle cx="{lx + 5:.1f}" cy="{y - 4}" r="5" fill="{color}"/>')
        parts.append(f'<text x="{lx + 18:.1f}" y="{y}" font-size="12.5" fill="{t["text"]}">{html.escape(name)}</text>')
        parts.append(f'<text x="{lx + col_w - 16:.1f}" y="{y}" font-size="12.5" text-anchor="end" fill="{t["muted"]}">{pct:.1f}%</text>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    totals, repo_count, private_count = collect(token)
    if not totals:
        sys.exit("error: no language data left after ignoring " + ", ".join(sorted(IGNORED_LANGUAGES)))

    langs = summarize(totals)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    for theme in THEMES:
        path = os.path.normpath(os.path.join(ASSETS_DIR, f"top-langs-{theme}.svg"))
        with open(path, "w") as f:
            f.write(render(langs, theme))
        print(f"wrote {path}")
    print(f"{repo_count} repos ({private_count} private): " + ", ".join(f"{n} {p:.1f}%" for n, p, _ in langs))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Automatically syncs Nusss0's public GitHub repositories into the README.md table
between <!-- REPOS-START --> and <!-- REPOS-END -->.
- Preserves existing custom badge labels/colors/overviews already in README.md.
- Automatically appends any newly created or forked public repository using its
  GitHub description (or first descriptive paragraph from its README.md).
"""
import json
import os
import re
import urllib.request

USERNAME = "Nusss0"
README_PATH = "README.md"


def github_get(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "Nusss0-Readme-Auto-Updater")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_repo_label(repo_name: str) -> str:
    # Strip common coursework prefixes like Tubes_IF2211_ or Tucil_IF2211_
    cleaned = re.sub(r"^(?:Tubes|Tucil)[-_][A-Z]{2}\d{4}[-_]", "", repo_name)
    # Split camelCase (e.g. EldenRing -> Elden Ring, ArionCompiler -> Arion Compiler)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = cleaned.replace("_", " ").replace("-", " ").strip()
    return cleaned if cleaned else repo_name


def fetch_readme_summary(repo_name: str) -> str:
    url = f"https://raw.githubusercontent.com/{USERNAME}/{repo_name}/main/README.md"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Nusss0-Readme-Auto-Updater"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith(("#", "!", "<", "|", "-", "`", ">", "[!")):
                continue
            # Clean markdown formatting
            s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
            s = re.sub(r"[*_`]", "", s).strip()
            if len(s) >= 20:
                return (s[:117] + "...") if len(s) > 120 else s
    except Exception:
        pass
    return ""


def main():
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    pattern = re.compile(r"(<!-- REPOS-START -->)(.*?)(<!-- REPOS-END -->)", re.S)
    match = pattern.search(readme)
    if not match:
        print("Markers <!-- REPOS-START --> / <!-- REPOS-END --> not found.")
        return

    existing_block = match.group(2)

    # Parse existing rows so custom names, overviews, and ordering are preserved
    row_regex = re.compile(
        r"^\|\s*\[.*?\]\(https://github\.com/"
        + re.escape(USERNAME)
        + r"/([^)\s/]+)\)\s*\|\s*(.*?)\s*\|$",
        re.M,
    )
    existing_rows = {}
    existing_order = []
    for m in row_regex.finditer(existing_block):
        rname = m.group(1)
        existing_rows[rname] = m.group(0)
        existing_order.append(rname)

    repos = github_get(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=created&direction=desc"
    )
    EXCLUDED = {USERNAME.lower(), "offsecvault", "dotfiles"}
    public_repos = {
        r["name"]: r
        for r in repos
        if not r.get("private") and r["name"].lower() not in EXCLUDED
    }

    # Find new repos not yet in the table
    new_repo_names = [name for name in public_repos if name not in existing_rows]

    # Build final rows: put newly created project repos at the top,
    # and keep all existing project repos that still exist on GitHub
    new_rows_rendered = []
    for name in new_repo_names:
        r = public_repos[name]
        label = clean_repo_label(name)

        desc = (r.get("description") or "").strip()
        if not desc:
            desc = fetch_readme_summary(name)
        if not desc:
            lang = r.get("language")
            desc = f"{label} project repository" + (f" ({lang})" if lang else "")

        link = f"[**{label}**](https://github.com/{USERNAME}/{name})"
        new_rows_rendered.append((name, f"| {link} | {desc} |"))

    kept_existing = [
        (name, existing_rows[name]) for name in existing_order
    ]

    combined = new_rows_rendered + kept_existing

    lines = [
        "",
        '<div align="center">',
        "",
        "| Repository | Overview |",
        "| :--- | :--- |",
    ]
    for _, row_str in combined:
        lines.append(row_str)
    lines.extend(["", "</div>", ""])

    new_block = "\n".join(lines)
    updated_readme = readme[: match.start(2)] + new_block + readme[match.end(2) :]

    if updated_readme != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated_readme)
        print(f"Updated README.md ({len(new_rows_rendered)} new repos added).")
    else:
        print("README.md is already up to date.")


if __name__ == "__main__":
    main()

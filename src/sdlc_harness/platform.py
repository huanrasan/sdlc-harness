"""Verify approval receipts against the VCS platform (GitHub or GitLab) in CI.

A receipt is accepted only when the platform confirms that:
  1. the named approver currently approves the pull/merge request;
  2. the approval covers the exact artifact content hashed in the receipt;
  3. the approver holds the receipt's role (roster member, or member of the roster's platform team);
  4. with separation of duties, the approver did not author the pull request or commits touching the artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import authority, receipts
from .core import HarnessError, Report, git, load_config, paths


class Http:
    def __init__(self, token: str, auth_header: str):
        self.token, self.auth_header = token, auth_header

    def get(self, url: str) -> tuple[object, dict]:
        req = urllib.request.Request(url, headers={self.auth_header: self.token, "Accept": "application/json",
                                                   "User-Agent": "sdlc-harness"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode()), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None, {}
            raise HarnessError(f"platform API {exc.code} for {url}") from exc

    def get_all(self, url: str) -> list:
        items, sep = [], "&" if "?" in url else "?"
        url = f"{url}{sep}per_page=100"
        while url:
            data, headers = self.get(url)
            items += data or []
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", headers.get("link", "")))
            url = nxt.group(1) if nxt else ""
        return items


def _blob_sha256(root: Path, commit: str, path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if proc.returncode != 0:
        return None
    return hashlib.sha256(proc.stdout.replace(b"\r\n", b"\n")).hexdigest()


def _changed_change_dirs(root: Path, cfg: dict, base: str) -> list[Path]:
    prefix = paths(cfg)["changes"].rstrip("/") + "/"
    names = git(root, "diff", "--name-only", f"{base}...HEAD").splitlines()
    ids = sorted({n[len(prefix):].split("/")[0] for n in names if n.startswith(prefix)})
    return [root / prefix / i for i in ids if (root / prefix / i / receipts.APPROVALS_FILE).exists()]


class GitHub:
    """Uses the PR reviews API: each review records the commit it was submitted on."""

    def __init__(self, http: Http, api: str, repo: str, number: int):
        self.http, self.base = http, f"{api.rstrip('/')}/repos/{repo}"
        self.api, self.number, self.org = api.rstrip("/"), number, repo.split("/")[0]

    def pr_author(self) -> str:
        pr, _ = self.http.get(f"{self.base}/pulls/{self.number}")
        return pr["user"]["login"]

    def approvals(self) -> dict[str, str]:
        """login -> commit sha of the reviewer's latest decisive review, only if it is APPROVED."""
        latest: dict[str, dict] = {}
        for r in self.http.get_all(f"{self.base}/pulls/{self.number}/reviews"):
            if r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
                latest[r["user"]["login"]] = r
        return {u: r["commit_id"] for u, r in latest.items() if r["state"] == "APPROVED"}

    def commit_authors(self) -> dict[str, str]:
        return {c["sha"]: (c.get("author") or {}).get("login", "")
                for c in self.http.get_all(f"{self.base}/pulls/{self.number}/commits")}

    def in_team(self, team: str, user: str) -> bool:
        org, slug = team.lstrip("@").split("/", 1)
        data, _ = self.http.get(f"{self.api}/orgs/{org}/teams/{slug}/memberships/{user}")
        return bool(data) and data.get("state") == "active"


class GitLab:
    """GitLab approvals carry no commit; the project must reset approvals when commits are pushed."""

    def __init__(self, http: Http, api: str, project: str, iid: int, root: Path):
        self.http, self.api, self.root = http, api.rstrip("/"), root
        self.base = f"{self.api}/projects/{urllib.parse.quote(project, safe='')}"
        self.iid = iid

    def pr_author(self) -> str:
        mr, _ = self.http.get(f"{self.base}/merge_requests/{self.iid}")
        return mr["author"]["username"]

    def approvals(self) -> dict[str, str]:
        settings, _ = self.http.get(f"{self.base}/approvals")
        if not settings or not settings.get("reset_approvals_on_push"):
            raise HarnessError("GitLab project must enable 'Remove all approvals when commits are added'")
        data, _ = self.http.get(f"{self.base}/merge_requests/{self.iid}/approvals")
        head = git(self.root, "rev-parse", "HEAD")
        return {a["user"]["username"]: head for a in (data or {}).get("approved_by", [])}

    def commit_authors(self) -> dict[str, str]:
        # GitLab commits expose author email, not username; map through the users API.
        out = {}
        for c in self.http.get_all(f"{self.base}/merge_requests/{self.iid}/commits"):
            users, _ = self.http.get(f"{self.api}/users?search={urllib.parse.quote(c.get('author_email', ''))}")
            out[c["id"]] = users[0]["username"] if users else ""
        return out

    def in_team(self, team: str, user: str) -> bool:
        users, _ = self.http.get(f"{self.api}/users?username={urllib.parse.quote(user)}")
        if not users:
            return False
        group = urllib.parse.quote(team.lstrip("@"), safe="")
        data, _ = self.http.get(f"{self.api}/groups/{group}/members/all/{users[0]['id']}")
        return bool(data)


def verify(root: Path, client, base: str) -> Report:
    cfg = load_config(root)
    report = Report()
    sod = authority.settings(cfg)["separation_of_duties"]
    approvals = client.approvals()
    pr_author = client.pr_author()
    authors = client.commit_authors() if sod else {}
    for change_dir in _changed_change_dirs(root, cfg, base):
        rel_receipt = (change_dir / receipts.APPROVALS_FILE).relative_to(root).as_posix()
        before = tomllib.loads(git(root, "show", f"{base}:{rel_receipt}", check=False) or "")
        already = {(e["artifact"], e["approver"], e["sha256"]) for e in before.get("approval", [])}
        for e in receipts.load(change_dir):
            if (e["artifact"], e["approver"], e["sha256"]) in already:
                continue  # verified when it was merged
            who, artifact, label = e["approver"], e["artifact"], f"{e['artifact']} ({e['approver']})"
            commit = approvals.get(who)
            if commit is None:
                report.error(f"{label}: no current approval from '{who}' on the pull/merge request")
                continue
            if git(root, "cat-file", "-t", commit, check=False) != "commit":
                report.error(f"{label}: approved commit {commit[:12]} not in history (force-push?); re-approve")
                continue
            if _blob_sha256(root, commit, artifact) != e["sha256"]:
                report.error(f"{label}: platform approval was given on different content than the receipt")
                continue
            if e["sha256"] not in git(root, "show", f"{commit}:{rel_receipt}", check=False):
                report.error(f"{label}: receipt was added after the approval; approve again")
                continue
            members = authority.roles(cfg).get(e["role"], [])
            direct = who in (m.lstrip("@") for m in members if not authority.is_team(m))
            if not direct and not any(client.in_team(m, who) for m in members if authority.is_team(m)):
                report.error(f"{label}: not a member of role '{e['role']}' on the platform")
                continue
            if sod:
                touched = git(root, "log", "--format=%H", f"{base}..HEAD", "--", artifact).splitlines()
                if who == pr_author or who in {authors.get(sha, "") for sha in touched}:
                    report.error(f"{label}: separation of duties - approver authored the change")
                    continue
    return report


def client_from_env(root: Path, platform: str, number: int | None):
    if platform == "github":
        token = os.environ.get("GITHUB_TOKEN") or raise_missing("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY") or raise_missing("GITHUB_REPOSITORY")
        if number is None:
            event = json.loads(Path(os.environ.get("GITHUB_EVENT_PATH", "")).read_text())
            number = (event.get("pull_request") or {}).get("number")
        if not number:
            raise HarnessError("pull request number not found (pass --pr)")
        return GitHub(Http(f"Bearer {token}", "Authorization"), os.environ.get("GITHUB_API_URL", "https://api.github.com"),
                      repo, int(number))
    token = os.environ.get("GITLAB_TOKEN") or raise_missing("GITLAB_TOKEN")
    project = os.environ.get("CI_PROJECT_ID") or raise_missing("CI_PROJECT_ID")
    number = number or os.environ.get("CI_MERGE_REQUEST_IID") or raise_missing("CI_MERGE_REQUEST_IID")
    return GitLab(Http(token, "PRIVATE-TOKEN"), os.environ.get("CI_API_V4_URL", "https://gitlab.com/api/v4"),
                  project, int(number), root)


def raise_missing(var: str):
    raise HarnessError(f"environment variable {var} is required")

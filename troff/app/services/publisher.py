from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from ..models import BlogPost, Platform, SocialPost
from .generator import BLOG_URL_PLACEHOLDER


@dataclass
class PublishResult:
    external_id: str
    canonical_url: str = ""
    landing_pr_url: str = ""
    landing_pr_number: int | None = None
    landing_branch: str = ""
    landing_commit_sha: str = ""
    landing_state: str = "none"


class PublishError(RuntimeError):
    def __init__(self, message: str, *, code: str = "publish_error", http_status: int | None = None, provider_response: str = ""):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.provider_response = provider_response[:900]


def _to_iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(value: str, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _slug_to_export_name(slug: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]", slug) if p]
    if not parts:
        return "generatedPost"
    first = parts[0].lower()
    rest = "".join(p.capitalize() for p in parts[1:])
    return f"{first}{rest}Post"


def _link_mark(href: str) -> dict:
    return {
        "type": "link",
        "attrs": {
            "href": href,
            "target": "_blank",
            "rel": "noopener noreferrer nofollow",
            "class": "text-primary underline underline-offset-4 hover:text-primary/80",
        },
    }


def _text_node(text: str, marks: list[dict] | None = None) -> dict:
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def _inline_nodes(text: str) -> list[dict]:
    nodes: list[dict] = []
    buffer: list[str] = []
    italic_active = False
    idx = 0

    def flush_buffer() -> None:
        if not buffer:
            return
        marks = [{"type": "italic"}] if italic_active else None
        nodes.append(_text_node("".join(buffer), marks))
        buffer.clear()

    while idx < len(text):
        char = text[idx]
        if char == "\\" and idx + 1 < len(text):
            buffer.append(text[idx + 1])
            idx += 2
            continue
        if char in {"*", "_"}:
            flush_buffer()
            italic_active = not italic_active
            idx += 1
            continue
        if char == "[":
            middle = text.find("](", idx)
            if middle != -1:
                end = text.find(")", middle + 2)
                if end != -1:
                    flush_buffer()
                    label = text[idx + 1 : middle]
                    href = text[middle + 2 : end]
                    marks: list[dict] = []
                    if italic_active:
                        marks.append({"type": "italic"})
                    marks.append(_link_mark(href))
                    nodes.append(_text_node(label, marks))
                    idx = end + 1
                    continue
        buffer.append(char)
        idx += 1

    flush_buffer()
    return nodes


def _paragraph_node(text: str = "") -> dict:
    node = {
        "type": "paragraph",
        "attrs": {"textAlign": None},
    }
    if text:
        node["content"] = _inline_nodes(text)
    return node


def markdown_to_tiptap(markdown: str) -> dict:
    lines = markdown.splitlines()
    content: list[dict] = []
    list_type: str | None = None
    list_items: list[dict] = []

    def flush_list() -> None:
        nonlocal list_items, list_type
        if not list_items or not list_type:
            list_items = []
            list_type = None
            return
        if list_type == "ordered":
            content.append({"type": "orderedList", "attrs": {"start": 1}, "content": list_items})
        else:
            content.append({"type": "bulletList", "content": list_items})
        list_items = []
        list_type = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_list()
            content.append(_paragraph_node())
            continue

        if stripped.startswith("- ") or re.match(r"^\d+\.\s+", stripped):
            next_list_type = "ordered" if re.match(r"^\d+\.\s+", stripped) else "bullet"
            text_value = re.sub(r"^\d+\.\s+", "", stripped) if next_list_type == "ordered" else stripped[2:].strip()
            if list_type and list_type != next_list_type:
                flush_list()
            list_type = next_list_type
            list_items.append(
                {
                    "type": "listItem",
                    "content": [
                        _paragraph_node(text_value),
                    ],
                }
            )
            continue

        flush_list()

        heading_level = 0
        if stripped.startswith("### "):
            heading_level = 3
            stripped = stripped[4:].strip()
        elif stripped.startswith("## "):
            heading_level = 2
            stripped = stripped[3:].strip()
        elif stripped.startswith("# "):
            heading_level = 1
            stripped = stripped[2:].strip()

        if heading_level:
            content.append(
                {
                    "type": "heading",
                    "attrs": {"textAlign": None, "level": heading_level},
                    "content": _inline_nodes(stripped),
                }
            )
        else:
            content.append(_paragraph_node(stripped))

    flush_list()

    if not content:
        content.append(_paragraph_node())

    return {"type": "doc", "content": content}


def _run_git(repo_path: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    process = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and process.returncode != 0:
        raise PublishError(
            f"Git command failed: {' '.join(args)}: {process.stderr.strip() or process.stdout.strip()}",
            code="landing_git_failed",
            provider_response=(process.stderr or process.stdout),
        )
    return process


def _ensure_clean_repo(repo_path: Path) -> None:
    status = _run_git(repo_path, ["status", "--porcelain"], check=False)
    dirty = (status.stdout or "").strip()
    if dirty:
        raise PublishError(
            "Landing repo has uncommitted changes. Commit or stash them before publishing.",
            code="landing_repo_dirty",
            provider_response=dirty,
        )


def _current_ref(repo_path: Path) -> str:
    branch = _run_git(repo_path, ["branch", "--show-current"]).stdout.strip()
    if branch:
        return branch
    return _run_git(repo_path, ["rev-parse", "HEAD"]).stdout.strip()


def _restore_ref(repo_path: Path, ref: str) -> None:
    if ref:
        _run_git(repo_path, ["checkout", ref])


def _write_landing_post(blog: BlogPost, publish_iso: str) -> tuple[Path, Path, str]:
    repo_root = Path(os.getenv("LANDING_REPO_PATH", "").strip())
    if not repo_root:
        raise PublishError("LANDING_REPO_PATH is not configured.", code="landing_path_missing")

    posts_dir = repo_root / "src/core/domains/blog/data/posts"
    data_path = repo_root / "src/core/domains/blog/data/data.ts"
    if not posts_dir.exists() or not data_path.exists():
        raise PublishError("LANDING_REPO_PATH does not contain expected blog files.", code="landing_path_invalid")

    tiptap_obj = markdown_to_tiptap(blog.markdown)
    blog.tiptap_json = json.dumps(tiptap_obj)
    categories = _safe_json(blog.categories_json, [{"primary": "Marketing"}])
    faq = _safe_json(blog.faq_json, [])

    export_name = _slug_to_export_name(blog.slug)
    post_payload = {
        "id": str(uuid.uuid4()),
        "slug": blog.slug,
        "title": blog.title,
        "description": blog.meta_description,
        "author": blog.author,
        "categories": categories,
        "content": tiptap_obj,
        "faq": faq,
    }

    post_path = posts_dir / f"{blog.slug}.ts"
    post_code = (
        'import { BlogPostData } from "../types";\n\n'
        f"export const {export_name}: BlogPostData = "
        + json.dumps(post_payload, indent=2)
        + ";\n"
    )
    post_path.write_text(post_code, encoding="utf-8")

    data_text = data_path.read_text(encoding="utf-8")
    import_line = f'import {{ {export_name} }} from "./posts/{blog.slug}";'
    if import_line not in data_text:
        marker = "export type"
        idx = data_text.find(marker)
        if idx == -1:
            raise PublishError("Unable to update landing data.ts imports.", code="landing_data_parse_failed")
        data_text = data_text[:idx] + import_line + "\n" + data_text[idx:]

    if f"...{export_name}," not in data_text:
        entry = (
            "  {\n"
            f"    ...{export_name},\n"
            f"    publishDate: \"{publish_iso}\",\n"
            "  },\n"
        )
        array_marker = "export const blogPostsData: BlogPostDataWithDate[] = ["
        start = data_text.find(array_marker)
        if start == -1:
            raise PublishError("Unable to update landing data.ts post list.", code="landing_data_parse_failed")
        insert_at = data_text.find("\n", start)
        data_text = data_text[: insert_at + 1] + entry + data_text[insert_at + 1 :]

    data_path.write_text(data_text, encoding="utf-8")
    return post_path, data_path, export_name


def _create_landing_pr(blog: BlogPost) -> PublishResult:
    publish_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    repo_root = Path(os.getenv("LANDING_REPO_PATH", "").strip())
    if not repo_root:
        raise PublishError("LANDING_REPO_PATH is not configured.", code="landing_path_missing")

    _ensure_clean_repo(repo_root)
    original_ref = _current_ref(repo_root)

    prefix = os.getenv("PR_BRANCH_PREFIX", "codex/troff-blog").strip() or "codex/troff-blog"
    branch = f"{prefix}-{blog.id}-{blog.slug}"[:120]

    result: PublishResult | None = None
    publish_error: PublishError | None = None
    try:
        _run_git(repo_root, ["checkout", "-B", branch])
        post_path, data_path, _ = _write_landing_post(blog, publish_iso)
        _run_git(repo_root, ["add", str(post_path), str(data_path)])

        commit_message = f"Add generated blog post: {blog.slug}"
        commit_process = _run_git(repo_root, ["commit", "-m", commit_message], check=False)
        if commit_process.returncode != 0:
            if "nothing to commit" not in (commit_process.stdout + commit_process.stderr).lower():
                raise PublishError(
                    "Failed to commit landing blog changes.",
                    code="landing_commit_failed",
                    provider_response=commit_process.stderr or commit_process.stdout,
                )

        push_process = _run_git(repo_root, ["push", "-u", "origin", branch], check=False)
        if push_process.returncode != 0:
            raise PublishError(
                "Failed to push landing branch to origin.",
                code="landing_push_failed",
                provider_response=push_process.stderr or push_process.stdout,
            )

        sha = _run_git(repo_root, ["rev-parse", "HEAD"]).stdout.strip()

        token = os.getenv("GITHUB_TOKEN", "").strip()
        owner = os.getenv("GITHUB_OWNER", "").strip()
        repo = os.getenv("GITHUB_REPO", "").strip()
        canonical_base = os.getenv("LANDING_BASE_URL", "https://www.billwithbomi.com").rstrip("/")
        canonical_url = f"{canonical_base}/blog/{blog.slug}"

        if not token or not owner or not repo:
            result = PublishResult(
                external_id=sha or branch,
                canonical_url=canonical_url,
                landing_branch=branch,
                landing_commit_sha=sha,
                landing_state="pending_pr",
            )
            return result

        payload = {
            "title": f"Publish blog: {blog.title}",
            "head": branch,
            "base": "main",
            "body": "Auto-generated by Troff.",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            json=payload,
            headers=headers,
            timeout=30,
        )

        if response.status_code >= 300:
            if response.status_code == 422:
                existing = requests.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls",
                    params={"state": "open", "head": f"{owner}:{branch}"},
                    headers=headers,
                    timeout=30,
                )
                if existing.status_code < 300:
                    items = existing.json()
                    if items:
                        item = items[0]
                        result = PublishResult(
                            external_id=str(item.get("number") or branch),
                            canonical_url=canonical_url,
                            landing_pr_url=item.get("html_url", ""),
                            landing_pr_number=item.get("number"),
                            landing_branch=branch,
                            landing_commit_sha=sha,
                            landing_state="open",
                        )
                        return result
            raise PublishError(
                f"GitHub PR creation failed with HTTP {response.status_code}.",
                code="landing_pr_failed",
                http_status=response.status_code,
                provider_response=response.text,
            )

        data = response.json()
        result = PublishResult(
            external_id=str(data.get("number") or branch),
            canonical_url=canonical_url,
            landing_pr_url=data.get("html_url", ""),
            landing_pr_number=data.get("number"),
            landing_branch=branch,
            landing_commit_sha=sha,
            landing_state="open",
        )
        return result
    except PublishError as err:
        publish_error = err
        raise
    finally:
        try:
            _restore_ref(repo_root, original_ref)
        except PublishError as restore_err:
            if publish_error is None:
                raise PublishError(
                    "Landing publish succeeded but the original landing branch could not be restored.",
                    code="landing_restore_failed",
                    provider_response=restore_err.provider_response or str(restore_err),
                ) from restore_err


def _render_social_body(post: SocialPost) -> str:
    body = (post.body or "").strip()
    canonical_url = ((post.blog_post.canonical_url if post.blog_post else "") or "").strip()
    if canonical_url:
        body = body.replace(BLOG_URL_PLACEHOLDER, canonical_url)
        if canonical_url not in body and post.platform in {Platform.linkedin, Platform.reddit, Platform.facebook}:
            body = f"{body}\n\nFull post: {canonical_url}".strip()
    return body.replace(BLOG_URL_PLACEHOLDER, "").strip()


def _publish_blog_to_outbox(blog: BlogPost) -> PublishResult:
    out_dir = Path(os.getenv("BLOG_OUTBOX_DIR", "/data/outbox/blog"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{blog.slug}.md"
    safe_title = blog.title.replace('"', '\\"')
    safe_description = blog.meta_description.replace('"', '\\"')
    path.write_text(
        "\n".join(
            [
                "---",
                f'title: "{safe_title}"',
                f'description: "{safe_description}"',
                f"published_at: {datetime.utcnow().isoformat()}Z",
                "---",
                "",
                blog.markdown,
            ]
        ),
        encoding="utf-8",
    )
    canonical_base = os.getenv("LANDING_BASE_URL", "https://www.billwithbomi.com").rstrip("/")
    return PublishResult(
        external_id=str(path),
        canonical_url=f"{canonical_base}/blog/{blog.slug}",
        landing_state="outbox",
    )


def publish_blog(blog: BlogPost) -> PublishResult:
    if os.getenv("LANDING_REPO_PATH", "").strip():
        return _create_landing_pr(blog)
    return _publish_blog_to_outbox(blog)


def _postiz_integration_id(platform: Platform) -> str:
    env_map = {
        Platform.linkedin: "POSTIZ_INTEGRATION_LINKEDIN",
        Platform.facebook: "POSTIZ_INTEGRATION_FACEBOOK",
        Platform.instagram: "POSTIZ_INTEGRATION_INSTAGRAM",
        Platform.tiktok: "POSTIZ_INTEGRATION_TIKTOK",
        Platform.reddit: "POSTIZ_INTEGRATION_REDDIT",
    }
    key = env_map.get(platform)
    if not key:
        return ""
    return os.getenv(key, "").strip()


def _postiz_settings(platform: Platform) -> dict:
    if platform == Platform.instagram:
        return {"__type": "instagram", "post_type": "POST"}
    if platform == Platform.tiktok:
        return {"__type": "tiktok"}
    if platform == Platform.reddit:
        return {"__type": "reddit", "post_type": "self"}
    return {"__type": platform.value}


def _postiz_api_base_url() -> str:
    raw = os.getenv("POSTIZ_API_URL", "https://api.postiz.com").strip().rstrip("/")
    if not raw:
        raw = "https://api.postiz.com"
    if raw.endswith("/public/v1"):
        return raw
    if raw.endswith("/public"):
        return f"{raw}/v1"
    return f"{raw}/public/v1"


def _publish_social_postiz(post: SocialPost) -> str:
    api_url = _postiz_api_base_url()
    api_key = os.getenv("POSTIZ_API_KEY", "").strip()
    if not api_key:
        raise PublishError("POSTIZ_API_KEY is not set.", code="postiz_api_key_missing")

    integration_id = _postiz_integration_id(post.platform)
    if not integration_id:
        raise PublishError(f"Missing Postiz integration id for {post.platform.value}.", code="postiz_integration_missing")

    images = []
    if post.asset_url.strip():
        images.append({"path": post.asset_url.strip()})

    if post.platform in {Platform.instagram, Platform.tiktok} and not images:
        raise PublishError(f"{post.platform.value} requires asset_url.", code="asset_required")

    payload = {
        "type": "now",
        "date": _to_iso_now(),
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": integration_id},
                "value": [{"content": _render_social_body(post), "image": images}],
                "settings": _postiz_settings(post.platform),
            }
        ],
    }

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    response = requests.post(f"{api_url}/posts", json=payload, headers=headers, timeout=30)
    if response.status_code >= 300:
        raise PublishError(
            f"Postiz publish failed for {post.platform.value}.",
            code="postiz_publish_failed",
            http_status=response.status_code,
            provider_response=response.text,
        )

    data = response.json()
    return str(data.get("id") or data.get("postId") or f"postiz-{post.id}")

def publish_social(post: SocialPost) -> str:
    return _publish_social_postiz(post)


def github_pr_merged(pr_number: int) -> bool:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    owner = os.getenv("GITHUB_OWNER", "").strip()
    repo = os.getenv("GITHUB_REPO", "").strip()
    if not token or not owner or not repo:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}", headers=headers, timeout=20)
    if response.status_code >= 300:
        return False
    data = response.json()
    return bool(data.get("merged"))


def url_is_live(url: str) -> bool:
    if not url:
        return False
    try:
        response = requests.get(url, timeout=15)
        return response.status_code < 400
    except Exception:
        return False

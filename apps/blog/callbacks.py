# apps/blog/callbacks.py
import json
import os
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest

from apps.blog.models import Category, Comment, Post

User = get_user_model()

TOP_AUTHORS_LIMIT = 5
PERCENTAGE_MULTIPLIER = 100


def environment_callback(request: HttpRequest) -> list[str]:
    """Return environment badge [label, color] based on BLOG_ENV_ID."""
    env_id = getattr(settings, "BLOG_ENV_ID", os.getenv("BLOG_ENV_ID", "local")).lower()
    if env_id in ("prod", "production"):
        return ["Production", "danger"]  # red
    return ["Local", "warning"]  # orange


def drafts_badge_callback(request: HttpRequest) -> int | str:
    """Return number of draft posts for the sidebar badge."""
    count = Post.objects.filter(status="draft").count()
    return count if count > 0 else ""


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Populate admin dashboard context with database statistics."""
    total_users = User.objects.count()
    total_comments = Comment.objects.count()

    post_counts = Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status="published")),
        drafts=Count("id", filter=Q(status="draft")),
    )
    total_posts: int = post_counts["total"] or 0
    published_posts: int = post_counts["published"] or 0
    draft_posts: int = post_counts["drafts"] or 0

    published_pct = (
        round((published_posts / total_posts) * PERCENTAGE_MULTIPLIER, 1)
        if total_posts > 0
        else 0.0
    )
    draft_pct = (
        round((draft_posts / total_posts) * PERCENTAGE_MULTIPLIER, 1)
        if total_posts > 0
        else 0.0
    )

    # Bar chart: number of posts per category (1 query)
    categories_qs = Category.objects.annotate(posts_count=Count("posts")).order_by(
        "-posts_count", "name"
    )
    chart_labels = [cat.name for cat in categories_qs]
    chart_values = [cat.posts_count for cat in categories_qs]

    posts_per_category_chart = json.dumps(
        {
            "labels": chart_labels,
            "datasets": [
                {
                    "label": "Posts",
                    "data": chart_values,
                    "backgroundColor": "rgb(16, 185, 129)",
                    "borderRadius": 6,
                }
            ],
        }
    )

    # Table: top 5 authors by number of posts (1 query)
    top_authors_qs = (
        User.objects.annotate(posts_count=Count("posts"))
        .order_by("-posts_count", "email")[:TOP_AUTHORS_LIMIT]
    )
    top_authors_table = {
        "headers": ["Author", "Email", "Posts"],
        "rows": [
            [
                f"{author.first_name} {author.last_name}".strip() or author.email,
                author.email,
                author.posts_count,
            ]
            for author in top_authors_qs
        ],
    }

    context.update(
        {
            "kpi_cards": [
                {
                    "title": "Total Users",
                    "metric": total_users,
                    "icon": "person",
                },
                {
                    "title": "Published Posts",
                    "metric": published_posts,
                    "icon": "check_circle",
                },
                {
                    "title": "Draft Posts",
                    "metric": draft_posts,
                    "icon": "edit_note",
                },
                {
                    "title": "Total Comments",
                    "metric": total_comments,
                    "icon": "chat",
                },
            ],
            "posts_per_category_chart": posts_per_category_chart,
            "top_authors_table": top_authors_table,
            "progress_bars": [
                {
                    "title": "Published posts",
                    "description": f"{published_posts} of {total_posts} posts",
                    "value": published_pct,
                },
                {
                    "title": "Draft posts",
                    "description": f"{draft_posts} of {total_posts} posts",
                    "value": draft_pct,
                },
            ],
        }
    )
    return context
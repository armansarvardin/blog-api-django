# apps/blog/admin.py
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

COMMENT_BODY_PREVIEW_LENGTH = 60
COMMENTS_INLINE_PER_PAGE = 10


# =====================================================================
# 1. GROUP ADMIN (Re-register with Unfold)
# =====================================================================
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# =====================================================================
# 2. USER FORMS & ADMIN (Custom User without username)
# =====================================================================
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


# На случай если User уже зарегистрирован где-то ещё:
if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ("email",)
    list_display = (
        "user_header",
        "is_active_label",
        "is_staff_label",
        "posts_count",
    )
    list_filter = (
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    )
    list_filter_submit = True
    search_fields = ("email", "first_name", "last_name")
    actions = ["activate_users", "deactivate_users"]

    fieldsets = (
        (
            _("Personal info"),
            {
                "fields": ("email", "password", "first_name", "last_name"),
                "classes": ["tab"],
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ["tab"],
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login", "date_joined"),
                "classes": ["tab"],
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description=_("User"), header=True)
    def user_header(self, obj: Any) -> list[str]:
        full_name = f"{obj.first_name} {obj.last_name}".strip() or obj.email
        initials = (
            f"{obj.first_name[:1]}{obj.last_name[:1]}".upper()
            or obj.email[:2].upper()
        )
        return [full_name, obj.email, initials]

    @display(
        description=_("Active"),
        label={
            "Active": "success",
            "Inactive": "danger",
        },
    )
    def is_active_label(self, obj: Any) -> str:
        return "Active" if obj.is_active else "Inactive"

    @display(
        description=_("Staff"),
        label={
            "Staff": "info",
            "Regular": "secondary",
        },
    )
    def is_staff_label(self, obj: Any) -> str:
        return "Staff" if obj.is_staff else "Regular"

    @display(description=_("Posts"), ordering="_posts_count")
    def posts_count(self, obj: Any) -> int:
        return getattr(obj, "_posts_count", 0)

    @admin.action(description=_("Activate selected users"))
    def activate_users(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _(f"{updated} users were successfully activated."),
            messages.SUCCESS,
        )

    @admin.action(description=_("Deactivate selected users"))
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _(f"{updated} users were successfully deactivated."),
            messages.SUCCESS,
        )


# =====================================================================
# 3. CATEGORY & TAG ADMINS
# =====================================================================
class CategoryPostsTableSection(TableSection):
    verbose_name = _("Category Posts")
    height = 300
    related_name = "posts"  # имя обратной связи Category -> Post
    fields = ["title", "author", "status", "created_at"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_sections = [CategoryPostsTableSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .annotate(_posts_count=Count("posts"))
            .prefetch_related("posts__author")
        )

    @display(description=_("Posts"), ordering="_posts_count")
    def posts_count(self, obj: Category) -> int:
        return getattr(obj, "_posts_count", 0)


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description=_("Posts"), ordering="_posts_count")
    def posts_count(self, obj: Tag) -> int:
        return getattr(obj, "_posts_count", 0)


# =====================================================================
# 4. COMMENT ADMIN
# =====================================================================
@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post_title", "author", "short_body", "created_at")
    list_select_related = ("post", "author")
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")

    @display(description=_("Post"), ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description=_("Comment"))
    def short_body(self, obj: Comment) -> str:
        return Truncator(obj.body).chars(COMMENT_BODY_PREVIEW_LENGTH)


# =====================================================================
# 5. POST ADMIN (Main Showcase)
# =====================================================================
class CommentInline(TabularInline):
    model = Comment
    extra = 0
    tab = True
    per_page = COMMENTS_INLINE_PER_PAGE
    autocomplete_fields = ("author",)
    readonly_fields = ("created_at",)
    fields = ("author", "body", "created_at")


class PostCommentsTableSection(TableSection):
    verbose_name = _("Comments")
    height = 300
    related_name = "comments"  # имя обратной связи Post -> Comment
    fields = ["author", "body", "created_at"]


@admin.register(Post)
class PostAdmin(ModelAdmin):
    warn_unsaved_form = True
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CommentInline]
    list_sections = [PostCommentsTableSection]

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
    }

    list_display = (
        "post_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count",
        "created_at",
    )
    list_select_related = ("author", "category")

    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("title", "body", "author__email")

    fieldsets = (
        (
            _("Content"),
            {
                "fields": ("title", "slug", "body"),
                "classes": ["tab"],
            },
        ),
        (
            _("Classification"),
            {
                "fields": ("category", "tags", "status"),
                "classes": ["tab"],
            },
        ),
        (
            _("Meta"),
            {
                "fields": ("author", "created_at", "updated_at"),
                "classes": ["tab"],
            },
        ),
    )

    actions = ["publish_selected", "move_to_drafts"]
    actions_row = ["toggle_publish_row"]
    actions_list = ["publish_all_drafts"]
    actions_detail = ["open_post_comments"]
    actions_submit_line = ["save_and_publish"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related("tags", "comments__author")
            .annotate(_comments_count=Count("comments", distinct=True))
        )

    # --- Columns (@display) ---

    @display(description=_("Post"), header=True, ordering="title")
    def post_header(self, obj: Post) -> list[str]:
        author_name = (
            f"{obj.author.first_name} {obj.author.last_name}".strip()
            or obj.author.email
        )
        return [obj.title, author_name]

    @display(
        description=_("Status"),
        ordering="status",
        label={
            "published": "success",
            "draft": "warning",
        },
    )
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description=_("Tags"), dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict[str, Any]:
        # Используем .all(), чтобы задействовать prefetch_related("tags") без N+1
        tags = list(obj.tags.all())
        return {
            "title": f"{len(tags)} tags",
            "items": [{"title": tag.name} for tag in tags],
        }

    @display(description=_("Comments"), ordering="_comments_count")
    def comments_count(self, obj: Post) -> int:
        return getattr(obj, "_comments_count", 0)

    # --- 1. Bulk Actions (with checkboxes) ---

    @admin.action(description=_("Publish selected"))
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = queryset.update(status="published")
        self.message_user(
            request,
            _(f"{updated} posts were published."),
            messages.SUCCESS,
        )

    @admin.action(description=_("Move to drafts"))
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = queryset.update(status="draft")
        self.message_user(
            request,
            _(f"{updated} posts were moved to drafts."),
            messages.SUCCESS,
        )

    # --- 2. Row Action (in every row) ---

    @action(description=_("Publish / unpublish"), url_path="toggle-publish-row")
    def toggle_publish_row(self, request: HttpRequest, object_id: int) -> HttpResponseRedirect:
        post = get_object_or_404(Post, pk=object_id)
        post.status = "draft" if post.status == "published" else "published"
        post.save(update_fields=["status"])
        self.message_user(
            request,
            _(f'Post "{post.title}" status changed to {post.status}.'),
            messages.SUCCESS,
        )
        return redirect(reverse("admin:blog_post_changelist"))

    # --- 3. List Action (above the list) ---

    @action(description=_("Publish all drafts"), url_path="publish-all-drafts")
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponseRedirect:
        updated = Post.objects.filter(status="draft").update(status="published")
        self.message_user(
            request,
            _(f"Published {updated} draft posts."),
            messages.SUCCESS,
        )
        return redirect(reverse("admin:blog_post_changelist"))

    # --- 4. Detail Action (on the post edit page) ---

    @action(description=_("Open this post's comments"), url_path="open-comments")
    def open_post_comments(self, request: HttpRequest, object_id: int) -> HttpResponseRedirect:
        comments_url = reverse("admin:blog_comment_changelist")
        return redirect(f"{comments_url}?post__id__exact={object_id}")

    # --- 5. Submit Line Action (next to the Save button) ---

    @action(description=_("Save & publish"))
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = "published"
        obj.save(update_fields=["status"])
        self.message_user(
            request,
            _(f'Post "{obj.title}" was saved and published.'),
            messages.SUCCESS,
        )
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.blog.models import Category, Comment, Post, Tag


class SeedCommandTests(TestCase):
    def seed(self, **options: int | bool) -> None:
        call_command("seed", stdout=StringIO(), **options)

    def test_creates_requested_data(self) -> None:
        self.seed(users=3, posts=4, comments=5)

        self.assertEqual(get_user_model().objects.count(), 3)
        self.assertEqual(Post.objects.count(), 4)
        self.assertEqual(Comment.objects.count(), 5)
        self.assertEqual(Category.objects.count(), 8)
        self.assertEqual(Tag.objects.count(), 20)
        self.assertTrue(get_user_model().objects.first().check_password("password123"))
        self.assertFalse(Comment.objects.exclude(post__status=Post.Status.PUBLISHED).exists())

    def test_reuses_existing_users_categories_and_tags(self) -> None:
        self.seed(users=1, posts=0, comments=0)
        with patch("apps.blog.commands.seed.random.random", return_value=0.5), patch(
            "apps.blog.commands.seed.random.randint", return_value=3
        ):
            self.seed(users=0, posts=1, comments=1)

        post = Post.objects.get()
        self.assertIsNotNone(post.category)
        self.assertEqual(post.tags.count(), 3)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Comment.objects.count(), 1)

    def test_comments_work_when_all_generated_posts_are_drafts(self) -> None:
        with patch("apps.blog.commands.seed.random.random", return_value=0.9):
            self.seed(users=1, posts=1, comments=1)

        self.assertEqual(Comment.objects.get().post.status, Post.Status.PUBLISHED)

    def test_failed_clear_rolls_back_existing_data(self) -> None:
        self.seed(users=1, posts=1, comments=0)
        user_id = get_user_model().objects.get().pk
        post_id = Post.objects.get().pk

        with self.assertRaises(CommandError):
            self.seed(clear=True, users=0, posts=1, comments=0)

        self.assertTrue(get_user_model().objects.filter(pk=user_id).exists())
        self.assertTrue(Post.objects.filter(pk=post_id).exists())

    def test_rejects_negative_counts(self) -> None:
        with self.assertRaises(CommandError):
            self.seed(users=-1, posts=0, comments=0)
        self.assertEqual(get_user_model().objects.count(), 0)

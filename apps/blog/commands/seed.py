import random
import time
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandParser, CommandError
from django.db import transaction
from django.utils.text import slugify
from faker.proxy import Faker

from apps.blog.models import Comment, Post, Tag, Category

User = get_user_model()

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

SEED_PASSWORD = "password123"

CATEGORY_NAMES: list[str] = [
    "Python",
    "Django",
    "DevOps",
    "Databases",
    "Frontend",
    "Architecture",
    "Testing",
    "Security",
]

TAG_NAMES: list[str] = [
"python",
    "django",
    "rest-api",
    "postgresql",
    "docker",
    "kubernetes",
    "ci-cd",
    "pytest",
    "celery",
    "redis",
    "asyncio",
    "typescript",
    "react",
    "linux",
    "git",
    "nginx",
    "aws",
    "GraphQL",
    "microservices",
    "performance",
]

class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding the database",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        start_time = time.perf_counter()

        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear = options["clear"]

        if users_count < 0 or posts_count < 0 or comments_count < 0:
            raise CommandError("User, post, and comment counts must be non-negative")

        fake = Faker()

        with transaction.atomic():
            if clear:
                self._clear_data()

            created_users = self._create_users(fake, users_count)
            all_users = list(User.objects.all())
            if (posts_count > 0 or comments_count > 0) and not all_users:
                raise CommandError("At least one user is required to create posts or comments")
            created_categories = self._created_categories()
            all_categories = list(Category.objects.all())

            created_tags = self._create_tags()
            all_tags = list(Tag.objects.all())

            created_posts = self._create_posts(
                fake=fake,
                count=posts_count,
                users=all_users,
                categories=all_categories,
                tags=all_tags,
            )
            published_posts = list(Post.objects.filter(status="published"))
            if comments_count > 0 and not published_posts and created_posts:
                post = created_posts[0]
                post.status = Post.Status.PUBLISHED
                post.save(update_fields=["status"])
                published_posts = [post]
            if comments_count > 0 and not published_posts:
                raise CommandError("At least one published post is required to create comments")

            created_comments = self._create_comments(
                fake=fake,
                count=comments_count,
                users=all_users,
                published_posts=published_posts,
            )

        elapsed = time.perf_counter() - start_time

        self.stdout.write(f"Users: {len(created_users)} created")
        self.stdout.write(f"Categories: {len(created_categories)} created")
        self.stdout.write(f"Tags: {len(created_tags)} created")
        self.stdout.write(f"Posts: {len(created_posts)} created")
        self.stdout.write(f"Comments: {len(created_comments)} created")
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))


    def _clear_data(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.all().delete()

    def _create_users(self, fake: Faker, count: int) -> list[Any]:
        if count == 0:
            return []
        hashed_password = make_password(SEED_PASSWORD)
        used_emails: set[str] = set(User.objects.values_list("email", flat=True))
        used_usernames: set[str] = set(
            User.objects.values_list("username", flat=True)
            if hasattr(User, "username")
            else []
        )
        users_to_create = []
        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            base_local = slugify(f"{first_name} {last_name}") or "user"
            domain = fake.free_email_domain()

            email = f"{base_local}@{domain}"
            counter = 2
            while email in used_emails:
                email = f"{base_local}{counter}@{domain}"
                counter += 1
            used_emails.add(email)

            is_active = random.random() >= 0.15
            is_staff = random.random() < 0.10

            user_kwargs: dict[str, Any] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_active": is_active,
                "is_staff": is_staff,
            }

            if hasattr(User, "username") and User.USERNAME_FIELD != "email":
                username = base_local
                u_counter = 2
                while username in used_usernames:
                    username = f"{base_local}{u_counter}"
                    u_counter += 1
                used_usernames.add(username)
                user_kwargs["username"] = username
            users_to_create.append(User(**user_kwargs))
        return User.objects.bulk_create(users_to_create)

    def _created_categories(self) -> list[Category]:
        existing_slugs: set[str] = set(Category.objects.values_list("slug", flat=True))
        existing_names: set[str] = set(Category.objects.values_list("name", flat=True))

        to_create: list[Category] = []
        for name in CATEGORY_NAMES:
            slug = slugify(name)
            if slug in existing_slugs or name in existing_names:
                continue
            existing_slugs.add(slug)
            existing_names.add(name)
            to_create.append(Category(name=name, slug=slug))
        return Category.objects.bulk_create(to_create)

    def _create_tags(self) -> list[Tag]:
        existing_slugs: set[str] = set(Tag.objects.values_list("slug", flat=True))
        existing_names: set[str] = set(Tag.objects.values_list("name", flat=True))

        to_create: list[Tag] = []
        for name in TAG_NAMES:
            slug = slugify(name)
            if slug in existing_slugs or name in existing_names:
                continue
            existing_slugs.add(slug)
            existing_names.add(name)
            to_create.append(Tag(name=name, slug=slug))
        return Tag.objects.bulk_create(to_create)

    def _create_posts(
            self,
            fake: Faker,
            count: int,
            users: list[Any],
            categories: list[Category],
            tags: list[Tag],
    ) -> list[Post]:
        if count == 0:
            return []
        used_slugs: set[str] = set(Post.objects.values_list("slug", flat=True))
        posts_to_create: list[Post] = []

        for _ in range(count):
            title = fake.sentence(nb_words=6).rstrip(".")
            base_slug = slugify(title) or "post"
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)
            status = "published" if random.random() < 0.7 else "draft"

            category = (
                None
                if (not categories or random.random() < 0.10)
                else random.choice(categories)
            )

            body = "\n\n".join(fake.paragraphs(nb=random.randint(3, 6)))

            posts_to_create.append(
                Post(
                    author=random.choice(users),
                    title=title,
                    slug=slug,
                    status=status,
                    body=body,
                    category=category,
                )
            )
        created_posts = Post.objects.bulk_create(posts_to_create)

        if tags:
            max_tags = min(5, len(tags))
            for post in created_posts:
                chosen_tags = random.sample(tags, k=random.randint(0, max_tags))
                post.tags.set(chosen_tags)
        return created_posts

    def _create_comments(
            self,
            fake: Faker,
            count: int,
            users: list[Any],
            published_posts: list[Post],
    ) -> list[Comment]:
        if count == 0:
            return []

        comments_to_create: list[Comment] = [
            Comment(
                post=random.choice(published_posts),
                author=random.choice(users),
                body=" ".join(fake.sentence() for _ in range(random.randint(1, 3))),
            )
            for _ in range(count)
        ]
        return Comment.objects.bulk_create(comments_to_create)

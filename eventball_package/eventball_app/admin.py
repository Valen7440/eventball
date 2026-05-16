from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.forms import Textarea
from django.utils.safestring import mark_safe

from .models import EventBall

if TYPE_CHECKING:
    from django.db.models import Field
    from django.http import HttpRequest


@admin.register(EventBall)
class EventBallAdmin(admin.ModelAdmin):
    autocomplete_fields = ("ball", "regime")
    readonly_fields = ("collection_image", "spawn_image")
    save_on_top = True
    fieldsets = [
        (None, {"fields": ("name", "ball", "start_date", "end_date", "emoji_id", "catch_phrase", "regime")}),
        (
            "Assets",
            {
                "description": "You must have permission from the copyright holder to use the files you're uploading!",
                "fields": ["spawn_image", "wild_card", "collection_image", "collection_card", "credits"],
            },
        ),
        (
            "Ability",
            {"description": "The ability of the eventball", "fields": ["capacity_name", "capacity_description"]},
        ),
    ]

    list_display = ["name", "ball_name", "start_date", "end_date", "emoji", "pk"]

    search_fields = ("name", "capacity_name", "capacity_description", "credits")
    search_help_text = "Search for eventball name, or ability name/content or credits "

    @admin.display(description="Name of this ball")
    def ball_name(self, obj: EventBall):
        return obj.ball.country

    @admin.display(description="Emoji")
    def emoji(self, obj: EventBall):
        return mark_safe(
            f'<img src="https://cdn.discordapp.com/emojis/{obj.emoji_id}.png?size=40" '
            f'title="ID: {obj.emoji_id}" />'
        )

    def formfield_for_dbfield(
        self, db_field: "Field[Any, Any]", request: "HttpRequest | None", **kwargs: Any
    ) -> "Field[Any, Any] | None":
        if db_field.name in ("capacity_description", "catch_phrase"):
            kwargs["widget"] = Textarea()
        return super().formfield_for_dbfield(db_field, request, **kwargs)  # type: ignore

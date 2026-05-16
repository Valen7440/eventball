from typing import TYPE_CHECKING
from django.contrib import admin
from django.db import models

from bd_models.models import Ball, Regime, image_display

if TYPE_CHECKING:
    from django.utils.safestring import SafeText

class EventBall(models.Model):
    name = models.CharField(max_length=64, unique=True)
    ball = models.ForeignKey(Ball, on_delete=models.CASCADE, related_name="eventballs")
    start_date = models.DateTimeField(
        help_text="Start time of the eventball. When active, all countryballs of this type become eventballs."
    )
    end_date = models.DateTimeField(help_text="End time of the eventball.")
    catch_phrase = models.CharField(
        max_length=128, blank=True, null=True, help_text="Sentence sent in bonus when someone catches a eventball"
    )
    capacity_name = models.CharField(max_length=64, help_text="Name of the eventball's capacity", null=True, blank=True)
    capacity_description = models.CharField(
        max_length=256, help_text="Description of the countryball's capacity", null=True, blank=True
    )
    wild_card = models.ImageField(
        max_length=200, help_text="An optional wild card for this eventball.", null=True, blank=True
    )
    collection_card = models.ImageField(
        max_length=200, help_text="An optional collection card for this eventball.", null=True, blank=True
    )
    credits = models.CharField(max_length=64, help_text="Author of the collection artwork", null=True, blank=True)
    regime = models.ForeignKey(
        Regime,
        help_text="An optional regime for this eventball.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    emoji_id = models.BigIntegerField(default=0, help_text="Emoji ID of this eventball.", blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True, blank=True)

    @admin.display(description="Current collection card")
    def collection_image(self) -> "SafeText":
        return image_display(str(self.collection_card))

    @admin.display(description="Current spawn asset")
    def spawn_image(self) -> "SafeText":
        return image_display(str(self.wild_card))

    def __str__(self) -> str:
        return self.name

    class Meta:
        managed = True
        db_table = "eventball"


from django.contrib import admin
from django.db import models
from django.utils.safestring import SafeText

from bd_models.models import Ball, BallInstance, Player, Regime, balls, image_display, regimes


class EventBall(models.Model):
    name = models.CharField(max_length=64, unique=True)
    ball = models.ForeignKey(Ball, on_delete=models.CASCADE, related_name="eventballs")
    ball_id: int
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
        "bd_models.Regime",
        help_text="An optional regime for this eventball.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    regime_id: int | None

    @admin.display(description="Current collection card")
    def collection_image(self) -> SafeText:
        return image_display(str(self.collection_card))

    @admin.display(description="Current spawn asset")
    def spawn_image(self) -> SafeText:
        return image_display(str(self.wild_card))

    @property
    def cached_ball(self) -> Ball:
        return balls.get(self.ball_id, self.ball)

    @property
    def cached_regime(self) -> Regime | None:
        return regimes.get(self.regime_id) or self.regime if self.regime_id else None

    def __str__(self) -> str:
        return self.name

    class Meta:
        managed = True
        db_table = "eventball"
        verbose_name_plural = "eventballs"


class EventBallInstance(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    player_id: int
    event_ball = models.ForeignKey(EventBall, on_delete=models.CASCADE)
    event_ball_id: int
    ball_instance = models.OneToOneField(
        BallInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name="eventball"
    )
    ball_instance_id: int | None

    class Meta:
        managed = True
        db_table = "eventballinstance"

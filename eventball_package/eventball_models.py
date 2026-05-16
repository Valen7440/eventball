from __future__ import annotations

from tortoise import models, fields

from ballsdex.core.models import Ball, Regime, balls, regimes

eventballs: dict[int, EventBall] = {}

class EventBall(models.Model):
    name = fields.CharField(max_length=64, unique=True)
    ball: fields.ForeignKeyRelation[Ball] = fields.ForeignKeyField(
        "models.Ball", on_delete=fields.CASCADE, related_name="eventballs"
    )
    ball_id: int
    start_date = fields.DatetimeField(
        description="Start time of the eventball. When active, all countryballs of this type become eventballs."
    )
    end_date = fields.DatetimeField(description="End time of the eventball.")
    catch_phrase = fields.CharField(
        max_length=128,
        blank=True,
        null=True,
        description="Sentence sent in bonus when someone catches a eventball"
    )
    capacity_name = fields.CharField(
        max_length=64, description="Name of the eventball's capacity", null=True, blank=True
    )
    capacity_description = fields.CharField(
        max_length=256, description="Description of the countryball's capacity", null=True, blank=True
    )
    wild_card = fields.CharField(
        max_length=200, description="An optional wild card for this eventball.", null=True, blank=True
    )
    collection_card = fields.CharField(
        max_length=200, description="An optional collection card for this eventball.", null=True, blank=True
    )
    credits = fields.CharField(max_length=64, description="Author of the collection artwork", null=True, blank=True)
    regime: fields.ForeignKeyNullableRelation[Regime] = fields.ForeignKeyField(
        "models.Regime",
        description="An optional regime for this eventball.",
        on_delete=fields.SET_NULL,
        null=True,
        blank=True,
    )
    regime_id: int | None
    emoji_id = fields.BigIntField(default=0, description="Emoji ID of this eventball.", blank=False)
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    @property
    def cached_ball(self):
        return balls.get(self.ball_id, self.ball)

    @property
    def cached_regime(self):
        return regimes.get(self.regime_id, self.regime) if self.regime_id else None

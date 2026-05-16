from discord import app_commands

from ballsdex.core.utils.transformers import TTLModelTransformer

from .models import EventBall


class EventBallTransformer(TTLModelTransformer[EventBall]):
    name = "eventball"
    model = EventBall


EventBallTransform = app_commands.Transform[EventBall, EventBallTransformer]

import textwrap
from PIL import Image, ImageDraw, ImageOps
from typing import TYPE_CHECKING, Any

from ballsdex.core.eventball_models import eventballs
from ballsdex.core.image_generator.image_gen import (
    get_credit_color,
    CORNERS,
    artwork_size,
    title_font,
    stats_font,
    credits_font,
    capacity_name_font,
    capacity_description_font,
    credits_color_cache,
)
from ballsdex.settings import settings

if TYPE_CHECKING:
    from ballsdex.core.models import BallInstance


def draw_card(
    ball_instance: "BallInstance",
    media_path: str = "./admin_panel/media/",
) -> tuple[Image.Image, dict[str, Any]]:
    ball = ball_instance.countryball

    if (
        isinstance(ball_instance.extra_data, dict)
        and "eventball_id" in ball_instance.extra_data
    ):
        eventball = eventballs.get(
            ball_instance.extra_data["eventball_id"], None
        )
    else:
        eventball = None

    ball_health = (237, 115, 101, 255)
    ball_credits = (
        eventball.credits
        if eventball and eventball.credits
        else ball.credits
    )

    special_credits = ""
    card_name = ball.cached_regime.name

    if special_image := ball_instance.special_card:
        card_name = getattr(ball_instance.specialcard, "name", card_name)
        image = Image.open(media_path + special_image)

        if (
            ball_instance.specialcard
            and ball_instance.specialcard.credits
        ):
            special_credits += (
                f" • Special Author: "
                f"{ball_instance.specialcard.credits}"
            )
    else:
        background = (
            media_path + eventball.cached_regime.background
            if eventball and eventball.cached_regime
            else media_path + ball.cached_regime.background
        )

        image = Image.open(background)

    image = image.convert("RGBA")

    icon = (
        Image.open(media_path + ball.cached_economy.icon).convert("RGBA")
        if ball.cached_economy
        else None
    )

    draw = ImageDraw.Draw(image)

    draw.text(
        (50, 20),
        ball.short_name or ball.country,
        font=title_font,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )

    capacity_name = (
        eventball.capacity_name
        if eventball and eventball.capacity_name
        else ball.capacity_name
    )

    cap_name = textwrap.wrap(
        f"Ability: {capacity_name}",
        width=26,
    )

    for i, line in enumerate(cap_name):
        draw.text(
            (100, 1050 + 100 * i),
            line,
            font=capacity_name_font,
            fill=(230, 230, 230, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )

    capacity_description = (
        eventball.capacity_description
        if eventball and eventball.capacity_description
        else ball.capacity_description
    )

    capacity_description_lines = (
        wrapped_line
        for newline in capacity_description.splitlines()
        for wrapped_line in textwrap.wrap(newline, 32)
    )

    for i, line in enumerate(capacity_description_lines):
        draw.text(
            (60, 1100 + 100 * len(cap_name) + 80 * i),
            line,
            font=capacity_description_font,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )

    draw.text(
        (320, 1670),
        str(ball_instance.health),
        font=stats_font,
        fill=ball_health,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
    )

    draw.text(
        (1120, 1670),
        str(ball_instance.attack),
        font=stats_font,
        fill=(252, 194, 76, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra",
    )

    if settings.show_rarity:
        draw.text(
            (1200, 50),
            str(ball.rarity),
            font=stats_font,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )

    if card_name in credits_color_cache:
        credits_color = credits_color_cache[card_name]
    else:
        credits_color = get_credit_color(
            image,
            (
                0,
                int(image.height * 0.8),
                image.width,
                image.height,
            ),
        )

        credits_color_cache[card_name] = credits_color

    draw.text(
        (30, 1870),
        # Modifying the line below is breaking the licence as you are removing credits
        # If you don't want to receive a DMCA, just don't
        (
            f"Created by El Laggron{special_credits}\n"
            f"Artwork author: {ball_credits}"
        ),
        font=credits_font,
        fill=credits_color,
        stroke_width=0,
        stroke_fill=(255, 255, 255, 255),
    )

    if eventball and eventball.collection_card:
        artwork = Image.open(
            media_path + eventball.collection_card
        ).convert("RGBA")
    else:
        artwork = Image.open(
            media_path + ball.collection_card
        ).convert("RGBA")

    image.paste(ImageOps.fit(artwork, artwork_size), CORNERS[0])  # type: ignore

    if icon:
        icon = ImageOps.fit(icon, (192, 192))
        image.paste(icon, (1200, 30), mask=icon)
        icon.close()

    artwork.close()

    return image, {"format": "WEBP"}
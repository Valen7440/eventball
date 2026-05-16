import logging
import math
import string
import random
from datetime import datetime, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Any, AsyncIterator

import discord
from discord import app_commands
from discord.ext import commands
from tortoise.exceptions import DoesNotExist

from ballsdex.core.metrics import caught_balls
from ballsdex.core.eventball_models import EventBall, eventballs
from ballsdex.core.models import Ball, BallInstance, Player, Special, Trade, TradeObject
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.core.utils.sorting import FilteringChoices, filter_balls
from ballsdex.core.utils.transformers import BallEnabledTransform, SpecialEnabledTransform
from ballsdex.core.utils.utils import inventory_privacy, is_staff
from ballsdex.packages.balls.countryballs_paginator import CountryballsSelector
from ballsdex.packages.countryballs.countryball import BallSpawnView
from ballsdex.settings import settings
from tortoise.timezone import get_default_timezone, now as tortoise_now

from .card import draw_card

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.frames")

def generate_random_name():
    source = string.ascii_uppercase + string.ascii_lowercase + string.ascii_letters
    return "".join(random.choices(source, k=15))

async def load_cache():
    eventballs.clear()
    for eventball in await EventBall.all():
        eventballs[eventball.pk] = eventball

    log.info(f"Cached {len(eventballs)} eventballs.")

class EventBallCog(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.originals: dict[str, Any] = {}
        self._patch()

    events = app_commands.Group(name="events", description="...")

    @events.command()
    async def completion(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        user: discord.User | None = None,
        countryball: BallEnabledTransform | None = None,
        special: SpecialEnabledTransform | None = None,
        filter: FilteringChoices | None = None,
    ):
        """
        Show your current completion of eventballs.

        Parameters
        ----------
        user: discord.User
            The user whose eventball completion you want to view, if not yours.
        countryball: Ball
            The ball you want to see the eventball completion of
        special: Special
            The special you want to see the eventball completion of
        filter: FilteringChoices
            Filter the list by a specific filter.
        """
        user_obj = user or interaction.user
        await interaction.response.defer(thinking=True)
        ball_txt = countryball.country if countryball else ""
        special_txt = special if special else ""
        combined_parts = [str(x) for x in [special_txt, ball_txt] if x]
        combined = " ".join(combined_parts)
        if user is not None:
            try:
                player = await Player.get(discord_id=user_obj.id)
            except DoesNotExist:
                await interaction.followup.send(
                    f"{user_obj.name} doesn't have any "
                    f"{combined} eventballs yet."
                )
                return
            if user.id in self.bot.blacklist and not is_staff(interaction):
                await interaction.followup.send(
                    "You cannot view the completion of a blacklisted user.", ephemeral=True
                )
                return

            interaction_player, _ = await Player.get_or_create(discord_id=interaction.user.id)

            blocked = await player.is_blocked(interaction_player)
            if blocked and not is_staff(interaction):
                await interaction.followup.send(
                    "You cannot view the eventball completion of a user that has blocked you.",
                    ephemeral=True,
                )
                return

            if await inventory_privacy(self.bot, interaction, player, user_obj) is False:
                return
        now = tortoise_now()
        # Filter disabled balls, they do not count towards progression
        # Only ID and emoji is interesting for us
        bot_countryballs = {
            x: y
            for x, y in eventballs.items()
            if (y.start_date or datetime.min.replace(tzinfo=get_default_timezone()))
            <= now
            <= (y.end_date or datetime.max.replace(tzinfo=get_default_timezone()))
        }

        # Set of ball IDs owned by the player
        filters = {"player__discord_id": user_obj.id, "ball__enabled": True, "extra_data__not": {}}
        if countryball:
            filters["ball"] = countryball
            bot_countryballs = {
                x: y
                for x, y in eventballs.items()
                if (
                    (y.start_date or datetime.min.replace(tzinfo=get_default_timezone()))
                    <= now
                    <= (y.end_date or datetime.max.replace(tzinfo=get_default_timezone()))
                ) and y.cached_ball.pk == countryball.pk
            }
        if special:
            filters["special"] = special
            bot_countryballs = {
                x: y
                for x, y in bot_countryballs.items()
                if special.end_date is None or y.created_at < special.end_date
            }
        if filter:
            query = filter_balls(filter, BallInstance.filter(**filters))
        else:
            query = BallInstance.filter(**filters)

        if not bot_countryballs:
            await interaction.followup.send(
                f"There are no {combined} eventballs"
                " registered on this bot yet.",
                ephemeral=True,
            )
            return

        owned_countryballs: set[int] = {
            extra_data["eventball_id"]
            for (extra_data,) in await query.distinct().values_list("extra_data")
            if isinstance(extra_data, dict) and "eventball_id" in extra_data
        }

        entries: list[tuple[str, str]] = []

        def fill_fields(title: str, emoji_ids: set[int]):
            # check if we need to add "(continued)" to the field name
            first_field_added = False
            buffer = ""

            for emoji_id in emoji_ids:
                emoji = self.bot.get_emoji(emoji_id)
                if not emoji:
                    continue
                text = f"{emoji} "

                if len(buffer) + len(text) > 1024:
                    # hitting embed limits, adding an intermediate field
                    if first_field_added:
                        entries.append(("\u200b", buffer))
                    else:
                        entries.append((f"__**{title}**__", buffer))
                        first_field_added = True
                    buffer = ""
                buffer += text

            if buffer:  # add what's remaining
                if first_field_added:
                    entries.append(("\u200b", buffer))
                else:
                    entries.append((f"__**{title}**__", buffer))

        if owned_countryballs:
            # Getting the list of emoji IDs from the IDs of the owned countryballs
            fill_fields(
                "Owned eventballs",
                set(bot_countryballs[x].emoji_id for x in owned_countryballs),
            )
        else:
            entries.append(("__**Owned eventballs**__", "Nothing yet."))

        if missing := set(y.emoji_id for x, y in bot_countryballs.items() if x not in owned_countryballs):
            fill_fields("Missing eventballs", missing)
        else:
            entries.append(
                (
                    "__**:tada: No missing eventballs, "
                    "congratulations! :tada:**__",
                    "\u200b",
                )
            )  # force empty field value

        source = FieldPageSource(entries, per_page=5, inline=False, clear_description=False)
        special_str = f" ({special.name})" if special else ""
        ball_str = f" {countryball.country}" if countryball else ""
        original_catcher_string = " " + filter.value.replace("_", " ") + " " if filter else ""
        source.embed.description = (
            f"{settings.bot_name}{original_catcher_string}{ball_str}{special_str} eventballs progression: "
            f"**{round(len(owned_countryballs) / len(bot_countryballs) * 100, 1)}%**"
        )
        source.embed.colour = discord.Colour.blurple()
        source.embed.set_author(name=user_obj.display_name, icon_url=user_obj.display_avatar.url)

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @commands.group()
    async def eventball(self, ctx: commands.Context["BallsDexBot"]):
        """
        Admin eventball commands.
        """
        pass


    @eventball.command()
    @commands.is_owner()
    async def reloadcache(self, ctx: commands.Context["BallsDexBot"]):
        """
        Reload the cache of the eventballs.
        """
        await load_cache()
        await ctx.message.add_reaction("✅")

    async def cog_unload(self):
        if "spawn" in self.originals:
            BallSpawnView.spawn = self.originals["spawn"]
        if "catch_ball" in self.originals:
            BallSpawnView.catch_ball = self.originals["catch_ball"]
        if "get_catch_message" in self.originals:
            BallSpawnView.get_catch_message = self.originals["get_catch_message"]
        if "set_options" in self.originals:
            CountryballsSelector.set_options = self.originals["set_options"]
        if "instance_draw_card" in self.originals:
            BallInstance.draw_card = self.originals["instance_draw_card"]
        if "instance_to_string" in self.originals:
            BallInstance.to_string = self.originals["instance_to_string"]

    def _patch(self):
        # BallSpawnView
        async def spawn(self: BallSpawnView, channel: discord.TextChannel):
            now = tortoise_now()
            eventball = await EventBall.filter(start_date__lte=now, end_date__gte=now).order_by("-start_date").first()
            self.eventball = eventball # type: ignore
            if eventball:
                extension = eventball.wild_card.split(".")[-1]
                file_location = "./admin_panel/media/" + eventball.wild_card
                file_name = f"nt_{generate_random_name()}.{extension}"
            else:
                extension = self.model.wild_card.split(".")[-1]
                file_location = "./admin_panel/media/" + self.model.wild_card
                file_name = f"nt_{generate_random_name()}.{extension}"
            try:
                permissions = channel.permissions_for(channel.guild.me)
                if permissions.attach_files and permissions.send_messages:
                    spawn_message = random.choice(settings.spawn_messages).format(
                        collectible=settings.collectible_name,
                        ball=self.name,
                        collectibles=settings.plural_collectible_name,
                        emoji=self.bot.get_emoji(self.model.emoji_id),
                    )

                    self.message = await channel.send(
                        spawn_message,
                        view=self,
                        file=discord.File(file_location, filename=file_name),
                    )
                    return True
                else:
                    log.warning("Missing permission to spawn ball in channel %s.", channel)
            except discord.Forbidden:
                log.warning(f"Missing permission to spawn ball in channel {channel}.")
            except discord.HTTPException:
                log.error("Failed to spawn ball", exc_info=True)
            return False

        async def catch_ball(
            self: BallSpawnView,
            user: discord.User | discord.Member,
            *,
            player: Player | None,
            guild: discord.Guild | None,
        ) -> tuple[BallInstance, bool]:
            if self.caught:
                raise RuntimeError("This ball was already caught!")
            self.caught = True
            self.catch_button.disabled = True
            caught_time = tortoise_now()
            player = player or (await Player.get_or_create(discord_id=user.id))[0]
            is_new = not await BallInstance.filter(player=player, ball=self.model).exists()

            if self.ballinstance:
                # if specified, do not create a countryball but switch owner
                # it's important to register this as a trade to avoid bypass
                trade = await Trade.create(player1=self.ballinstance.player, player2=player)
                await TradeObject.create(
                    trade=trade, player=self.ballinstance.player, ballinstance=self.ballinstance
                )
                self.ballinstance.trade_player = self.ballinstance.player
                self.ballinstance.player = player
                self.ballinstance.locked = None  # type: ignore
                await self.ballinstance.save(update_fields=("player_id", "trade_player_id", "locked"))
                return self.ballinstance, is_new

            # stat may vary by +/- 20% of base stat
            bonus_attack = (
                self.atk_bonus
                if self.atk_bonus is not None
                else random.randint(-settings.max_attack_bonus, settings.max_attack_bonus)
            )
            bonus_health = (
                self.hp_bonus
                if self.hp_bonus is not None
                else random.randint(-settings.max_health_bonus, settings.max_health_bonus)
            )

            # check if we can spawn cards with a special background
            special: Special | None = self.special

            if not special:
                special = self.get_random_special()

            ball = await BallInstance.create(
                ball=self.model,
                player=player,
                special=special,
                attack_bonus=bonus_attack,
                health_bonus=bonus_health,
                server_id=guild.id if guild else None,
                spawned_time=self.message.created_at,
                catch_date=caught_time,
            )
            eventball = getattr(self, "eventball", None)
            if eventball:
                ball.extra_data = {"eventball_id": eventball.pk}
                await ball.save(update_fields=("extra_data",))

            # logging and stats
            log.log(
                logging.INFO if user.id in self.bot.catch_log else logging.DEBUG,
                f"{user} caught {settings.collectible_name} {self.model}, {special=}",
            )
            if isinstance(user, discord.Member) and user.guild.member_count:
                caught_balls.labels(
                    country=self.name,
                    special=special,
                    # observe the size of the server, rounded to the nearest power of 10
                    guild_size=10 ** math.ceil(math.log(max(user.guild.member_count - 1, 1), 10)),
                    spawn_algo=self.algo,
                ).inc()

            return ball, is_new

        def get_catch_message(self: BallSpawnView, ball: BallInstance, new_ball: bool, mention: str) -> str:
            text = ""
            if ball.specialcard and ball.specialcard.catch_phrase:
                text += f"*{ball.specialcard.catch_phrase}*\n"
            eventball = getattr(self, "eventball", None)
            if eventball and eventball.catch_phrase:
                text += f"*{eventball.catch_phrase}*"
            if new_ball:
                text += (
                    f"This is a **new {settings.collectible_name}** "
                    "that has been added to your completion!"
                )
            if self.ballinstance:
                text += f"This {settings.collectible_name} was dropped by <@{self.og_id}>\n"

            caught_message = (
                random.choice(settings.caught_messages).format(
                    user=mention,
                    collectible=settings.collectible_name,
                    ball=self.name,
                    collectibles=settings.plural_collectible_name,
                    emoji=self.bot.get_emoji(self.model.emoji_id),
                )
                + " "
            )

            return (
                caught_message
                + f"`(#{ball.pk:0X}, {ball.attack_bonus:+}%/{ball.health_bonus:+}%)`\n\n{text}"
            )

        self.originals["spawn"] = BallSpawnView.spawn
        self.originals["catch_ball"] = BallSpawnView.catch_ball
        self.originals["get_catch_message"] = BallSpawnView.get_catch_message
        BallSpawnView.spawn = spawn
        BallSpawnView.catch_ball = catch_ball
        BallSpawnView.get_catch_message = get_catch_message

        # CountryballsSelector
        async def set_options(self: CountryballsSelector, balls: AsyncIterator[BallInstance]):
            options: list[discord.SelectOption] = []
            async for ball in balls:
                emoji = self.bot.get_emoji(int(ball.countryball.emoji_id))
                favorite = f"{settings.favorited_collectible_emoji} " if ball.favorite else ""
                special = ball.special_emoji(self.bot, True)
                eventball_emoji = "🖼️" if ball.extra_data.get("eventball_id", None) else ""
                options.append(
                    discord.SelectOption(
                        label=f"{favorite}{special}{eventball_emoji}#{ball.pk:0X} {ball.countryball.country}",
                        description=(
                            f"ATK: {ball.attack}({ball.attack_bonus:+d}%) "
                            f"• HP: {ball.health}({ball.health_bonus:+d}%) • "
                            f"{ball.catch_date.strftime('%Y/%m/%d | %H:%M')}"
                        ),
                        emoji=emoji,
                        value=f"{ball.pk}",
                    )
                )
            self.select_ball_menu.options = options
        
        self.originals["set_options"] = CountryballsSelector.set_options
        CountryballsSelector.set_options = set_options

        # ballinstance
        def instance_draw_card(self: BallInstance):
            image, kwargs = draw_card(self)
            buffer = BytesIO()
            image.save(buffer, **kwargs)
            buffer.seek(0)
            image.close()
            return buffer

        def instance_to_string(self: BallInstance, bot: discord.Client | None = None, is_trade: bool = False) -> str:
            emotes = ""
            if not is_trade and self.locked and self.locked > tortoise_now() - timedelta(minutes=30):
                emotes += "🔒"
            if self.favorite and not is_trade:
                emotes += settings.favorited_collectible_emoji
            if isinstance(self.extra_data, dict) and self.extra_data.get("eventball_id", False):
                emotes += "🖼️"
            if emotes:
                emotes += " "
            if self.specialcard:
                emotes += self.special_emoji(bot)
            country = (
                self.countryball.country
                if isinstance(self.countryball, Ball)
                else f"<Ball {self.ball_id}>"
            )
            return f"{emotes}#{self.pk:0X} {country}"
    
        self.originals["instance_draw_card"] = BallInstance.draw_card
        self.originals["instance_to_string"] = BallInstance.to_string
        BallInstance.draw_card = instance_draw_card
        BallInstance.to_string = instance_to_string

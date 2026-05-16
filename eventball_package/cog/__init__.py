from typing import TYPE_CHECKING

from .cog import EventBallCog, load_cache

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    await load_cache()
    await bot.add_cog(EventBallCog(bot))
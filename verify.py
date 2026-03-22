import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class VerifyView(discord.ui.View):
    def __init__(self, target: discord.Member, requester: discord.Member):
        super().__init__(timeout=60)
        self.target = target
        self.requester = requester
        self.responded = False

    async def on_timeout(self):
        if not self.responded:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(
                    embed=discord.Embed(
                        title="⏱️  Verification Expired",
                        description=f"{self.target.mention} did not respond in time. The verification request has expired.",
                        color=0x747F8D
                    ),
                    view=self
                )
            except Exception:
                pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ This verification is not for you.", ephemeral=True
            )
            return
        self.responded = True
        for item in self.children:
            item.disabled = True

        verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
        role_added = False
        if verified_role:
            try:
                await self.target.add_roles(verified_role, reason="Verification accepted")
                role_added = True
            except discord.Forbidden:
                pass

        embed = discord.Embed(
            title="✅  Verified — Welcome to the Team",
            description=(
                f"{self.target.mention} made the right call.\n\n"
                "You're in. Time to get that bag. 💰"
            ),
            color=0x57F287
        )
        if role_added:
            embed.add_field(name="Role Granted", value=f"`Verified` has been added to your profile.", inline=False)
        embed.set_footer(text="Trading Core  •  Smart choices lead to bigger bags.")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ This verification is not for you.", ephemeral=True
            )
            return
        self.responded = True
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="❌  Verification Declined",
            description=(
                f"{self.target.mention} chose to decline.\n\n"
                "That's on you. The opportunity doesn't wait. 🤷"
            ),
            color=0xED4245
        )
        embed.set_footer(text="Trading Core  •  You can always change your mind later.")
        await interaction.response.edit_message(embed=embed, view=self)


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Send a verification request to a user")
    @app_commands.describe(user="The user to send the verification to")
    async def verify(self, interaction: discord.Interaction, user: discord.Member):
        if user.bot:
            await interaction.response.send_message("❌ You can't verify a bot.", ephemeral=True)
            return
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't verify yourself.", ephemeral=True)
            return

        embed = discord.Embed(
            title="👁️  Hi — If You're Seeing This, You Know Why.",
            description=(
                f"**{user.mention}**, this is your moment.\n\n"
                "You probably already know what this is about. "
                "The choice in front of you is simple, but the outcome isn't.\n\n"
                "**Accept** — join us, operate with the team, and start earning **5x, 10x** more than you had before. "
                "Real moves. Real results.\n\n"
                "**Decline** — and stay exactly where you are. No hard feelings. Stay broke.\n\n"
                "Think carefully. Choose wisely. The clock's ticking. ⏱️"
            ),
            color=0x5865F2
        )
        embed.set_footer(
            text=f"Sent by {interaction.user.display_name}  •  You have 60 seconds to decide.",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        view = VerifyView(target=user, requester=interaction.user)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Verify(bot))

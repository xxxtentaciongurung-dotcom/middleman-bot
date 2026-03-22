import discord
from discord.ext import commands
from discord import app_commands

MIDDLEMAN_ROLE_NAME = "Middleman"

def is_middleman(member: discord.Member) -> bool:
    return any(r.name == MIDDLEMAN_ROLE_NAME for r in member.roles)


class TradeInfoModal(discord.ui.Modal, title="📦  Submit Your Trade Info"):
    what_giving = discord.ui.TextInput(
        label="What are you GIVING?",
        placeholder="e.g. $50 PayPal, Fortnite Account Level 200, 1000 Robux...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    what_receiving = discord.ui.TextInput(
        label="What are you RECEIVING?",
        placeholder="e.g. $50 PayPal, Fortnite Account Level 200, 1000 Robux...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    proof = discord.ui.TextInput(
        label="Proof (link or describe)",
        placeholder="Screenshot link, description of proof you can provide...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300
    )

    def __init__(self, user1: discord.Member, user2: discord.Member, collector: dict, channel: discord.TextChannel):
        super().__init__()
        self.user1 = user1
        self.user2 = user2
        self.collector = collector
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        self.collector[interaction.user.id] = {
            "giving": self.what_giving.value,
            "receiving": self.what_receiving.value,
            "proof": self.proof.value or "Not provided",
        }
        await interaction.response.send_message(
            "✅ Trade info submitted. Waiting for the other party...",
            ephemeral=True
        )

        if self.user1.id in self.collector and self.user2.id in self.collector:
            d1 = self.collector[self.user1.id]
            d2 = self.collector[self.user2.id]

            embed = discord.Embed(
                title="📋  Trade Info — Both Parties Submitted",
                color=0x57F287
            )
            embed.add_field(
                name=f"◈  {self.user1.display_name}",
                value=(
                    f"> **Giving:** {d1['giving']}\n"
                    f"> **Receiving:** {d1['receiving']}\n"
                    f"> **Proof:** {d1['proof']}"
                ),
                inline=False
            )
            embed.add_field(
                name=f"◈  {self.user2.display_name}",
                value=(
                    f"> **Giving:** {d2['giving']}\n"
                    f"> **Receiving:** {d2['receiving']}\n"
                    f"> **Proof:** {d2['proof']}"
                ),
                inline=False
            )
            embed.add_field(
                name="🔍  Next Step",
                value=(
                    "> The Middleman will now review this information.\n"
                    "> Use `/confirmation` when both parties are ready to lock the trade in."
                ),
                inline=False
            )
            embed.set_footer(text="Trading Core  •  Reviewed by Middleman")
            await self.channel.send(embed=embed)


class TradeInfoView(discord.ui.View):
    def __init__(self, user1: discord.Member, user2: discord.Member, channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.user1 = user1
        self.user2 = user2
        self.channel = channel
        self.collector: dict = {}

    @discord.ui.button(label="Submit My Trade Info", style=discord.ButtonStyle.primary, emoji="📝")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.user1.id, self.user2.id):
            await interaction.response.send_message(
                "❌ You are not part of this trade.", ephemeral=True
            )
            return
        if interaction.user.id in self.collector:
            await interaction.response.send_message(
                "✅ You've already submitted your trade info.", ephemeral=True
            )
            return
        modal = TradeInfoModal(self.user1, self.user2, self.collector, self.channel)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


class ConfirmationView(discord.ui.View):
    def __init__(self, user1: discord.Member, user2: discord.Member):
        super().__init__(timeout=300)
        self.user1 = user1
        self.user2 = user2
        self.confirmed: set = set()

    @discord.ui.button(label="Confirm Trade", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.user1.id, self.user2.id):
            await interaction.response.send_message(
                "❌ You are not part of this trade.", ephemeral=True
            )
            return
        if interaction.user.id in self.confirmed:
            await interaction.response.send_message(
                "✅ You've already confirmed.", ephemeral=True
            )
            return

        self.confirmed.add(interaction.user.id)

        if self.user1.id in self.confirmed and self.user2.id in self.confirmed:
            for item in self.children:
                item.disabled = True
            embed = discord.Embed(
                title="✅  Trade Locked In — Both Parties Confirmed",
                description=(
                    f"{self.user1.mention} and {self.user2.mention} have both confirmed.\n\n"
                    "**This trade is now final and cannot be reversed.** "
                    "The Middleman will proceed to close the session.\n\n"
                    "Remember to pay the **5% service fee** before the ticket is closed."
                ),
                color=0x57F287
            )
            embed.set_footer(text="Trading Core  •  Both parties confirmed. No going back now.")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            other = self.user1 if interaction.user.id == self.user2.id else self.user2
            await interaction.response.send_message(
                f"✅ **{interaction.user.display_name}** confirmed. Waiting on {other.mention}...",
            )


class Trade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tradeinfo", description="Collect trade information from both parties via form")
    @app_commands.describe(
        user1="First party in the trade",
        user2="Second party in the trade"
    )
    async def tradeinfo(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        if not is_middleman(interaction.user):
            await interaction.response.send_message(
                "❌ Only **Middlemen** can use this command.", ephemeral=True
            )
            return
        if user1.id == user2.id:
            await interaction.response.send_message("❌ Both parties must be different users.", ephemeral=True)
            return
        if user1.bot or user2.bot:
            await interaction.response.send_message("❌ Bots cannot be trade parties.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📦  Trade Information Collection",
            description=(
                f"{user1.mention} and {user2.mention} — both of you must click the button below "
                "and fill out the form with your trade details.\n\n"
                "**Be honest and thorough.** The Middleman reviews everything before the trade proceeds."
            ),
            color=0x5865F2
        )
        embed.add_field(name="◈  Party 1", value=user1.mention, inline=True)
        embed.add_field(name="◈  Party 2", value=user2.mention, inline=True)
        embed.add_field(
            name="⚠️  Reminder",
            value="> Do not proceed with the trade until **both** parties have submitted their info.",
            inline=False
        )
        embed.set_footer(
            text=f"Session managed by {interaction.user.display_name}  •  Trading Core MM",
            icon_url=interaction.user.display_avatar.url
        )

        view = TradeInfoView(user1=user1, user2=user2, channel=interaction.channel)
        await interaction.response.send_message(
            content=f"{user1.mention} {user2.mention}",
            embed=embed,
            view=view
        )
        view.message = await interaction.original_response()

    @app_commands.command(name="confirmation", description="Send trade confirmation buttons for both parties")
    @app_commands.describe(
        user1="First party in the trade",
        user2="Second party in the trade"
    )
    async def confirmation(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        if not is_middleman(interaction.user):
            await interaction.response.send_message(
                "❌ Only **Middlemen** can use this command.", ephemeral=True
            )
            return
        if user1.id == user2.id:
            await interaction.response.send_message("❌ Both parties must be different users.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️  Final Trade Confirmation",
            description=(
                f"Both {user1.mention} and {user2.mention} must confirm below.\n\n"
                "By clicking **Confirm Trade**, you acknowledge:\n"
                "> 🔹 You have reviewed and agreed to the trade terms\n"
                "> 🔹 You are satisfied with what you're giving and receiving\n"
                "> 🔹 This trade is **final and cannot be reversed**\n"
                "> 🔹 You agree to the **5% service fee** for this session\n\n"
                "**Think before you click. There is no undo.**"
            ),
            color=0xFEE75C
        )
        embed.set_footer(
            text=f"Confirmation requested by {interaction.user.display_name}  •  Trading Core MM",
            icon_url=interaction.user.display_avatar.url
        )

        view = ConfirmationView(user1=user1, user2=user2)
        await interaction.response.send_message(
            content=f"{user1.mention} {user2.mention}",
            embed=embed,
            view=view
        )


async def setup(bot):
    await bot.add_cog(Trade(bot))

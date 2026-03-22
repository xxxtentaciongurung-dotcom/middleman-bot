import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal

# ─── Role Hierarchy ────────────────────────────────────────────────────────────
# Co-owner           → can give: Middleman
# Operation Lead     → can give: Middleman, Head Middleman
# Chief Lead         → can give: Middleman, Head Middleman, Middleman Manager
# Team Lead          → can give: Middleman, Head Middleman, Middleman Manager, Mod
# President          → can give: Middleman, Head Middleman, Middleman Manager, Mod, Head Mod, Lead Cord

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Co-owner": ["Middleman"],
    "Operation Lead": ["Middleman", "Head Middleman"],
    "Chief Lead": ["Middleman", "Head Middleman", "Middleman Manager"],
    "Team Lead": ["Middleman", "Head Middleman", "Middleman Manager", "Mod"],
    "President": ["Middleman", "Head Middleman", "Middleman Manager", "Mod", "Head Mod", "Lead Cord"],
}

BAN_PERMISSION_ROLE = "Ban Perms"


def get_user_rank(member: discord.Member) -> tuple[str | None, list[str]]:
    """Returns the highest matching rank name and its assignable roles."""
    priority = ["President", "Chief Lead", "Team Lead", "Operation Lead", "Co-owner"]
    for rank in priority:
        if any(r.name == rank for r in member.roles):
            return rank, ROLE_PERMISSIONS[rank]
    return None, []


def has_ban_perms(member: discord.Member) -> bool:
    return any(r.name == BAN_PERMISSION_ROLE for r in member.roles) or member.guild_permissions.ban_members


class BanGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="manage", description="Management commands for staff")

    @app_commands.command(name="ban", description="Ban or unban a member from the server")
    @app_commands.describe(
        target="The user to ban or unban",
        action="Whether to ban or unban the user",
        reason="Reason for the action"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        action: Literal["ban", "unban"],
        reason: str = "No reason provided"
    ):
        if not has_ban_perms(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have the **Ban Perms** role required to use this command.", ephemeral=True
            )
            return

        if action == "ban":
            if target.id == interaction.user.id:
                await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True)
                return
            if target.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ You cannot ban someone with an equal or higher role than you.", ephemeral=True
                )
                return

            try:
                try:
                    dm_embed = discord.Embed(
                        title="🔨  You've Been Banned",
                        description=(
                            f"You have been banned from **{interaction.guild.name}**.\n\n"
                            f"**Reason:** {reason}\n\n"
                            "If you believe this was a mistake, contact a staff member."
                        ),
                        color=0xED4245
                    )
                    await target.send(embed=dm_embed)
                except Exception:
                    pass

                await target.ban(reason=f"{reason} | Action by {interaction.user}")
                embed = discord.Embed(
                    title="🔨  Member Banned",
                    color=0xED4245
                )
                embed.add_field(name="◈  User", value=f"{target.mention} (`{target.id}`)", inline=True)
                embed.add_field(name="◈  Banned By", value=interaction.user.mention, inline=True)
                embed.add_field(name="◈  Reason", value=f"> {reason}", inline=False)
                embed.set_thumbnail(url=target.display_avatar.url)
                embed.set_footer(text="Trading Core Moderation")
                await interaction.response.send_message(embed=embed)

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ I don't have permission to ban this user.", ephemeral=True
                )

        elif action == "unban":
            try:
                ban_entry = None
                async for entry in interaction.guild.bans():
                    if entry.user.id == target.id:
                        ban_entry = entry
                        break

                if not ban_entry:
                    await interaction.response.send_message(
                        f"❌ {target.mention} is not currently banned.", ephemeral=True
                    )
                    return

                await interaction.guild.unban(target, reason=f"{reason} | Unbanned by {interaction.user}")
                embed = discord.Embed(
                    title="✅  Member Unbanned",
                    color=0x57F287
                )
                embed.add_field(name="◈  User", value=f"{target.mention} (`{target.id}`)", inline=True)
                embed.add_field(name="◈  Unbanned By", value=interaction.user.mention, inline=True)
                embed.add_field(name="◈  Reason", value=f"> {reason}", inline=False)
                embed.set_footer(text="Trading Core Moderation")
                await interaction.response.send_message(embed=embed)

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ I don't have permission to unban this user.", ephemeral=True
                )

    @app_commands.command(name="roles", description="Promote or demote a member's staff role")
    @app_commands.describe(
        target="The user to promote or demote",
        action="Whether to promote or demote",
        role="The role to add or remove",
        reason="Reason for the role change"
    )
    async def roles(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        action: Literal["promote", "demote"],
        role: str,
        reason: str = "No reason provided"
    ):
        executor_rank, assignable = get_user_rank(interaction.user)
        if not executor_rank:
            await interaction.response.send_message(
                "❌ You don't have a staff rank that allows role management.", ephemeral=True
            )
            return

        assignable_lower = [r.lower() for r in assignable]
        if role.lower() not in assignable_lower:
            allowed = ", ".join(f"`{r}`" for r in assignable)
            await interaction.response.send_message(
                f"❌ As **{executor_rank}**, you can only manage these roles: {allowed}",
                ephemeral=True
            )
            return

        matched_role_name = assignable[[r.lower() for r in assignable].index(role.lower())]
        guild_role = discord.utils.get(interaction.guild.roles, name=matched_role_name)

        if not guild_role:
            await interaction.response.send_message(
                f"❌ The role `{matched_role_name}` doesn't exist in this server yet. "
                "Have an admin create it first.",
                ephemeral=True
            )
            return

        try:
            if action == "promote":
                if guild_role in target.roles:
                    await interaction.response.send_message(
                        f"❌ {target.mention} already has the `{matched_role_name}` role.", ephemeral=True
                    )
                    return
                await target.add_roles(guild_role, reason=f"{reason} | By {interaction.user}")
                color = 0x57F287
                action_text = "Promoted"
                verb = "given"

            else:
                if guild_role not in target.roles:
                    await interaction.response.send_message(
                        f"❌ {target.mention} doesn't have the `{matched_role_name}` role.", ephemeral=True
                    )
                    return
                await target.remove_roles(guild_role, reason=f"{reason} | By {interaction.user}")
                color = 0xED4245
                action_text = "Demoted"
                verb = "removed"

            embed = discord.Embed(
                title=f"{'📈' if action == 'promote' else '📉'}  Member {action_text}",
                color=color
            )
            embed.add_field(name="◈  User", value=target.mention, inline=True)
            embed.add_field(name="◈  By", value=f"{interaction.user.mention} ({executor_rank})", inline=True)
            embed.add_field(name="◈  Role", value=f"`{matched_role_name}` {verb}", inline=False)
            embed.add_field(name="◈  Reason", value=f"> {reason}", inline=False)
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text="Trading Core Staff Management")
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to modify this user's roles.", ephemeral=True
            )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manage_group = BanGroup()
        self.bot.tree.add_command(self.manage_group)


async def setup(bot):
    await bot.add_cog(Moderation(bot))

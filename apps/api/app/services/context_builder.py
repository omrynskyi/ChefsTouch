from __future__ import annotations

from apps.api.app.models import SessionContext


def build_context(ctx: SessionContext) -> str:
    parts = []
    if ctx.active_recipe:
        parts.append("Recipe: {title}".format(title=ctx.active_recipe.title))
        if ctx.current_step is not None:
            total = len(ctx.active_recipe.steps)
            parts.append("Step {current} of {total}".format(current=ctx.current_step + 1, total=total))
    return ". ".join(parts) if parts else ""


def humanize_action(action: str, ctx: SessionContext) -> str:
    if action == "next_step":
        if ctx.active_recipe and ctx.current_step is not None:
            next_n = ctx.current_step + 2
            total = len(ctx.active_recipe.steps)
            return "Go to step {step} of {total} in {title}".format(
                step=next_n,
                total=total,
                title=ctx.active_recipe.title,
            )
        return "Advance to the next cooking step"

    if action.startswith("select_"):
        name = action[len("select_"):].replace("_", " ").title()
        return 'User selected recipe: "{name}"'.format(name=name)

    return action

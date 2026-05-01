from __future__ import annotations

from typing import Any, Dict, List


async def analyze_frames(frames: List[str], context: str, llm: Any = None) -> Dict[str, Any]:
    return {
        "frames_seen": len(frames),
        "context": context,
        "observation": "No analysis available yet.",
        "assessment": "unknown",
        "suggested_action": None,
    }

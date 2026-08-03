"""Per-match highlight colours shared by the document viewer and sidebar."""

_MATCH_PALETTE = (
    "#FDE047",  # yellow
    "#86EFAC",  # green
    "#93C5FD",  # blue
    "#F9A8D4",  # pink
    "#C4B5FD",  # violet
    "#FDBA74",  # orange
    "#5EEAD4",  # teal
    "#FCA5A5",  # red
)


def get_match_color(match_id: int) -> str:
    if match_id <= 0:
        return "#CBD5E1"
    return _MATCH_PALETTE[(match_id - 1) % len(_MATCH_PALETTE)]


def get_match_bg(match_id: int, alpha: str = "66") -> str:
    color = get_match_color(match_id)
    return f"#{alpha}{color[1:]}"


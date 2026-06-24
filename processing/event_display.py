"""Shared event display naming for UI and chapter export."""


def format_event_display_name(event_name: str) -> str:
    """Format event key as a human-readable label (matches Custom Event Builder)."""
    if event_name.startswith('mcb_'):
        name = event_name.replace('mcb_', '').replace('_', ' ').title()
        return f"MCB - {name}"
    if event_name.startswith('clutch_'):
        name = event_name.replace('clutch_', '').replace('_', ' ').title()
        return f"Clutch - {name}"
    name = event_name.replace('_', ' ').title()
    return f"General - {name}"

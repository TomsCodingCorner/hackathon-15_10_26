"""Sessiedata zonder Streamlit-import: caller bewaart dit in Session State."""

from .controller import TurnResult

GREETING = "Hallo, ik ben je AI-minoradviseur. Welke opleiding volg je en wat vind je interessant? Deel geen onnodige persoonsgegevens."


def new_conversation(epoch: int = 0) -> dict:
    return {"epoch": epoch, "history": [], "messages": [], "events": set()}


def append_turn(conversation: dict, turn: TurnResult, event_id: str) -> bool:
    """Idempotent voor dezelfde UI-input, ook na een Streamlit-rerun."""
    if event_id in conversation["events"]:
        return False
    conversation["events"].add(event_id)
    if turn.message:
        conversation["history"].append({"role": "user", "content": turn.message})
        conversation["messages"].append({"role": "user", "content": turn.message})
    conversation["history"].append({"role": "assistant", "content": turn.result["response"]})
    conversation["messages"].append({"role": "assistant", "content": turn.result["response"],
                                      "cards": turn.cards, "audio": turn.audio})
    return True

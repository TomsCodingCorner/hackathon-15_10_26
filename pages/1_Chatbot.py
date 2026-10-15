"""Chat-UI: alleen invoer, sessiebeheer en weergave."""

import hashlib
import uuid

import streamlit as st

from core.controller import run_turn
from core.diagnostics import record_turn
from core.session import GREETING, append_turn, new_conversation
from core.ui import render_cards, settings_and_status

st.title("MinorAdviseur AI")
st.write("Verken welke minor bij jouw opleiding en interesses past. Je praat met AI; controleer adviezen bij de aanbieder of een studieadviseur.")
st.caption("Tekst, gesprekscontext en geselecteerde minorbeschrijvingen gaan naar Google Gemini. Spraakherkenning en spraakuitvoer blijven lokaal. Deel geen onnodige persoonsgegevens.")
settings, minors = settings_and_status()

if "conversation" not in st.session_state:
    st.session_state.conversation = new_conversation()
conversation = st.session_state.conversation
if st.button("Nieuw gesprek"):
    st.session_state.conversation = new_conversation(conversation["epoch"] + 1)
    st.session_state.pop("last_turn", None)
    st.rerun()

with st.chat_message("assistant"):
    st.write(GREETING)
for entry in conversation["messages"]:
    with st.chat_message(entry["role"]):
        if entry.get("transcribed"):
            st.caption("Herkende Nederlandse tekst uit jouw opname")
        st.write(entry["content"])
        render_cards(entry.get("cards", []))
        if entry.get("audio"):
            st.audio(entry["audio"], format="audio/wav")

speak = st.checkbox("AI-antwoorden ook als Nederlandse spraak genereren", value=True)
audio = st.audio_input("Neem je bericht op en stop om te verzenden (maximaal 60 seconden)", sample_rate=16000,
                       key=f"chat_audio_{conversation['epoch']}")
send_audio = st.button("Verwerk opname", disabled=audio is None)
text = st.chat_input("Typ je bericht als alternatief")

if text or (send_audio and audio is not None):
    recorded = audio.getvalue() if send_audio and audio is not None else None
    event_id = "audio:" + hashlib.sha256(recorded).hexdigest() if recorded is not None else "text:" + uuid.uuid4().hex
    if event_id not in conversation["events"]:
        with st.spinner("Bericht verwerken met Gemini…"):
            turn = run_turn(text or "", conversation["history"], minors, settings, audio=recorded, speak=speak)
        append_turn(conversation, turn, event_id)
        if recorded is not None and turn.message:
            conversation["messages"][-2]["transcribed"] = True
        st.session_state.last_turn = turn
        evidence = st.session_state.setdefault("component_evidence", {})
        record_turn(evidence, turn)
        st.rerun()
    else:
        st.info("Deze opname is al verwerkt. Maak een nieuwe opname voor een volgend bericht.")

last = st.session_state.get("last_turn")
if last:
    issues = [step for step in last.steps if step.status in {"FAIL", "BLOCKED"}]
    if issues:
        st.caption("Laatste beurt: " + " | ".join(f"{step.name}: {step.detail}" for step in issues))

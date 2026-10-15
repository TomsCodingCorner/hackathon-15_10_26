"""Gedeelde eenvoudige Streamlit-weergave; businesslogica blijft in core/AI."""

import streamlit as st

from config import Settings
from .diagnostics import dataset_check, environment_checks


def settings_and_status() -> tuple[Settings, list[dict]]:
    settings = Settings()
    check, minors = dataset_check(settings)
    with st.sidebar:
        st.subheader("Lokale status")
        st.write(f"Dataset: {len(minors)} gevalideerde minoren ({check.status})")
        checks = st.session_state.get("environment_checks", [])
        for label, name in (("AI-model", "Ollama model"), ("STT-bestanden", "Whisper modelbestanden"), ("TTS-bestanden", "Piper modelbestanden")):
            observed = next((item for item in checks if item.name == name), None)
            st.write(f"{label}: {observed.status if observed else 'NOT_TESTED'}")
        st.caption("Bestands-/modelvindbaarheid bewijst geen transcriptie, synthese of AI-generatie.")
        if st.button("Controleer lokale omgeving", key="check_environment"):
            with st.spinner("Lokale bestanden en Ollama controleren…"):
                st.session_state.environment_checks = environment_checks(settings)
            st.rerun()
        if checks:
            st.caption("Laatste controle: " + checks[0].checked_at)
        st.caption("PoC • lokaal • geen externe AI • geen permanente gespreksopslag")
    if check.status == "FAIL":
        st.error(check.detail)
    elif not minors:
        st.warning(check.detail)
    return settings, minors


def render_cards(cards: list[dict]) -> None:
    for card in cards[:3]:
        with st.container(border=True):
            st.subheader(card["title"])
            st.write(card["institution"])
            st.write(card["motivation"])
            st.link_button("Bekijk de oorspronkelijke minor", card["url"])


def render_turn(turn) -> None:
    st.write(turn.result["response"])
    render_cards(turn.cards)
    if turn.audio:
        st.audio(turn.audio, format="audio/wav")
    st.dataframe(turn.table(), hide_index=True, use_container_width=True)
    problem = next((step for step in turn.steps if step.status in {"FAIL", "BLOCKED"}), None)
    if problem:
        st.warning(f"Eerste blokkade/fout: {problem.name} — {problem.detail}")
    if turn.agent_run:
        st.caption(f"Modelaanroep: {turn.agent_run.model_ms:.0f} ms. Validatie: {turn.agent_run.error or 'geslaagd'}.")
        with st.expander("Ruwe modeloutput — uitsluitend voor foutopsporing"):
            st.warning("Ongevalideerde uitvoer kan onjuiste informatie bevatten. Deze wordt niet als aanbeveling gebruikt of uitgesproken.")
            st.code((turn.agent_run.raw_output or "Geen modeloutput.")[:12000], language="json")
        if turn.agent_run.validated_output:
            st.json(turn.agent_run.validated_output)

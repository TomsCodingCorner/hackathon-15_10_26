"""Ontwikkeldashboard; alle actieve tests vragen een expliciete klik."""

from dataclasses import asdict

import streamlit as st

from core.controller import run_turn
from core.diagnostics import component_checks, now, probe_local_model, record_turn, scrape_report, small_live_scrape
from core.scenarios import SCENARIOS
from core.session import append_turn, new_conversation
from core.test_service import start_tests
from core.ui import render_turn, settings_and_status
from speech import SpeechError
from speech.stt import transcribe, validate_wav
from speech.tts import synthesize

st.title("Testing & Diagnostics")
st.caption("PASS betekent dat de genoemde controle is uitgevoerd. Readiness, mocktests, live lokale tests en handmatige beoordeling zijn afzonderlijk bewijs.")
settings, minors = settings_and_status()
evidence = st.session_state.setdefault("component_evidence", {})
st.dataframe(component_checks(settings, evidence), hide_index=True, use_container_width=True)
tabs = st.tabs(["Omgeving", "Scraper & Data", "AI & Scenario's", "STT", "TTS", "End-to-end", "Automatische tests"])

with tabs[0]:
    st.info("Gebruik ‘Controleer lokale omgeving’ in de sidebar. Geen downloads of modelgeneratie tijdens deze controle.")
    checks = st.session_state.get("environment_checks", [])
    if checks:
        st.dataframe([asdict(check) for check in checks], hide_index=True, use_container_width=True)
    st.write("LLM:", settings.ollama_model, "•", settings.ollama_url)
    st.write("Whisper:", str(settings.whisper_path))
    st.write("Piper:", str(settings.piper_path))

with tabs[1]:
    st.subheader("Laatste opgeslagen scraperresultaat")
    report = scrape_report(settings)
    st.json(report)
    st.write(f"Momenteel {len(minors)} geldige records in het geconfigureerde bestand.")
    st.caption("Het rapport is historische evidence, geen actuele bereikbaarheidscontrole. De productieparser ontbreekt nog.")
    permitted = st.checkbox("Ik heb gecontroleerd dat deze kleine live-aanroep op productie is toegestaan.")
    if st.button("Controleer bron en scrape maximaal 5 records", disabled=not permitted):
        try:
            with st.spinner("Robots en bron controleren; stopt bij toegangsblokkade…"):
                fresh = small_live_scrape(settings, permitted)
            st.json(fresh)
            if fresh["status"] != "success":
                st.warning("Geen geslaagde scrape. Zie foutcode en HTTP-status; er wordt geen blokkade omzeild.")
        except (ValueError, OSError):
            st.error("Scrape kon niet worden uitgevoerd. Controleer toestemming, standaard bestandsnamen en schrijfrechten.")

with tabs[2]:
    st.subheader("Onafhankelijke lokale modelproef")
    st.caption("Test alleen JSON-generatie met een vast technisch bericht; werkt ook zonder minorendataset.")
    if st.button("Test lokale JSON-generatie"):
        with st.spinner("Lokaal model testen…"):
            st.session_state.model_probe = probe_local_model(settings)
        probe = st.session_state.model_probe
        evidence["AI-provider"] = {key: probe[key] for key in ("status", "detail", "mode", "checked_at")}
        st.rerun()
    if st.session_state.get("model_probe"):
        st.json(st.session_state.model_probe)
    mode = st.radio("Testmethode", ["Live lokaal via Ollama", "Gemockte contracttests (geen echte AI)"], key="ai_test_mode")
    if mode.startswith("Gemockte"):
        st.info("De gemockte scenario-, JSON-, onbekend-ID- en contexttests staan in de pytest-suite. Start ze expliciet op de tab Automatische tests. Er worden geen fictieve minoren aan deze chatbot toegevoegd.")
    scenario = st.selectbox("Hackathonscenario", list(SCENARIOS))
    selected = SCENARIOS[scenario]
    st.write("Voorbeeldinput:", selected["message"])
    st.write("Verwacht gedrag:", selected["expected"])
    if st.button("Start voorbeeldgesprek"):
        st.session_state.diagnostic_conversation = new_conversation()
        st.session_state.diagnostic_input = selected["message"]
        st.session_state.pop("diagnostic_turn", None)
    if "diagnostic_conversation" not in st.session_state:
        st.session_state.diagnostic_conversation = new_conversation()
    text = st.text_area("Testbericht / vervolgvraag", key="diagnostic_input")
    if st.button("Voer lokale AI-test uit", disabled=not text.strip() or mode.startswith("Gemockte")):
        history = st.session_state.diagnostic_conversation["history"]
        with st.spinner("Lokaal model en validatie uitvoeren…"):
            turn = run_turn(text, history, minors, settings)
        append_turn(st.session_state.diagnostic_conversation, turn, str(len(history)))
        st.session_state.diagnostic_turn = turn
        record_turn(evidence, turn)
        st.rerun()
    if st.session_state.diagnostic_conversation["messages"]:
        with st.expander("Diagnostische gesprekscontext"):
            for entry in st.session_state.diagnostic_conversation["messages"]:
                st.write(entry["role"] + ": " + entry["content"])
    if st.session_state.get("diagnostic_turn"):
        render_turn(st.session_state.diagnostic_turn)
        assessment = st.radio("Handmatige relevantiebeoordeling", ["NOT_TESTED — nog niet beoordeeld", "PASS — inhoudelijk passend", "FAIL — inhoudelijk niet passend"],
                              key="relevance_" + str(len(st.session_state.diagnostic_conversation["history"])))
        st.caption("Subjectieve beoordeling: " + assessment + ". Technische validatie staat afzonderlijk in de stappentabel.")

with tabs[3]:
    st.subheader("Nederlandse microfoontest")
    recording = st.audio_input("Neem Nederlands op (maximaal 60 seconden)", sample_rate=16000, key="stt_audio")
    if st.button("Transcribeer lokaal", disabled=recording is None):
        from time import perf_counter
        started = perf_counter()
        try:
            data = recording.getvalue()
            duration = validate_wav(data)
            transcript = transcribe(data, settings.whisper_path)
            st.session_state.stt_result = {"status": "PASS", "text": transcript, "audio_seconds": duration,
                                            "elapsed_ms": (perf_counter() - started) * 1000}
        except (SpeechError, OSError):
            st.session_state.stt_result = {"status": "FAIL", "error": "Transcriptie mislukt; controleer package, lokale modelbestanden en opname."}
        result = st.session_state.stt_result
        evidence["Speech-to-Text"] = {"status": result["status"], "detail": "Afzonderlijke transcriptietest uitgevoerd.", "checked_at": now()}
        st.rerun()
    if st.session_state.get("stt_result"):
        st.json(st.session_state.stt_result)

with tabs[4]:
    st.subheader("Nederlandse Piper-test")
    spoken_text = st.text_area("Uit te spreken Nederlandse tekst", "Hallo, ik ben je lokale AI-minoradviseur.", key="tts_input")
    if st.button("Genereer lokale spraak", disabled=not spoken_text.strip()):
        from time import perf_counter
        started = perf_counter()
        try:
            audio = synthesize(spoken_text, settings.piper_path)
            st.session_state.tts_result = {"status": "PASS", "audio": audio, "elapsed_ms": (perf_counter() - started) * 1000}
        except (SpeechError, OSError):
            st.session_state.tts_result = {"status": "FAIL", "error": "Synthese mislukt; controleer Piper en de Nederlandse stemconfiguratie."}
        result = st.session_state.tts_result
        evidence["Text-to-Speech"] = {"status": result["status"], "detail": "Afzonderlijke syntheseproef uitgevoerd; hoorbaarheid zelf beoordelen.", "checked_at": now()}
        st.rerun()
    if st.session_state.get("tts_result"):
        result = st.session_state.tts_result
        st.json({key: value for key, value in result.items() if key != "audio"})
        if result.get("audio"):
            st.audio(result["audio"], format="audio/wav")
    st.caption("Stem: " + str(settings.piper_path))

with tabs[5]:
    st.subheader("Audio → STT → Controller → Retrieval → LLM → Validatie → TTS → audio")
    chain_audio = st.audio_input("Neem een vraag op voor de volledige keten", sample_rate=16000, key="chain_audio")
    if st.button("Test audioketen lokaal", disabled=chain_audio is None):
        with st.spinner("Audioketen uitvoeren…"):
            turn = run_turn("", [], minors, settings, audio=chain_audio.getvalue(), speak=True)
        st.session_state.chain_turn = turn
        record_turn(evidence, turn)
        st.rerun()
    if st.session_state.get("chain_turn"):
        turn = st.session_state.chain_turn
        if turn.message:
            st.write("Herkende tekst:", turn.message)
        render_turn(turn)
    else:
        st.info("NOT_TESTED — nog geen audio-integratietest uitgevoerd. Downstream stappen blijven NOT_TESTED bij een eerdere blokkade.")

with tabs[6]:
    st.subheader("Offline pytest-suite")
    st.caption("Vaste opdracht in een achtergrondworker, timeout 90 seconden. Maximaal 12.000 tekens uitvoer. Aantallen uit JUnit, inclusief unittest-subtests. Geen shell-input, bronrequests of modeldownloads.")
    if st.button("Start automatische tests", disabled=bool(st.session_state.get("test_future") and not st.session_state.test_future.done())):
        st.session_state.test_future = start_tests(settings)

    @st.fragment(run_every=1)
    def test_progress():
        future = st.session_state.get("test_future")
        if future is not None:
            if not future.done():
                st.info("Tests draaien op de achtergrond. De overige tabs blijven bruikbaar.")
                return
            try:
                st.session_state.test_result = future.result()
            except Exception:
                st.session_state.test_result = {"status": "FAIL", "output": "Testworker mislukt."}
            st.session_state.pop("test_future", None)
            st.rerun()
        result = st.session_state.get("test_result")
        if result:
            st.json({key: value for key, value in result.items() if key != "output"})
            st.code(result.get("output", "")[-12000:])
        else:
            st.info("NOT_TESTED — automatische tests zijn in deze sessie nog niet gestart.")
    test_progress()

if st.button("Wis diagnostische gespreks- en audioresultaten"):
    for key in ("diagnostic_conversation", "diagnostic_turn", "diagnostic_input", "stt_result", "tts_result", "chain_turn", "stt_audio", "chain_audio"):
        st.session_state.pop(key, None)
    st.rerun()

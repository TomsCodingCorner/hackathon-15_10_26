"""Offline contract- en veiligheidstests; Gemini Client is altijd gemockt."""

import copy
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx  # Onderdeel van de google-genai dependencies.
from google import genai

from ai.agent import DISCLOSURE, QUESTIONS, chat_with_agent
from ai.validation import ValidationError, normalize_minors


# Fictieve testdata, nooit als productieaanbod gebruiken.
MINORS = [
    {
        "id": "ondernemen", "title": "Digitaal ondernemen",
        "description": "Je ontwikkelt een digitaal bedrijfsconcept en onderzoekt de markt voor je eigen onderneming.",
        "institution": "Testhogeschool A", "url": "https://example.org/ondernemen",
    },
    {
        "id": "psychologie", "title": "Psychologie in de zorg",
        "description": "Je onderzoekt menselijk gedrag en oefent met psychologische begeleiding in zorgsituaties.",
        "institution": "Testhogeschool B", "url": "https://example.org/psychologie",
    },
    {
        "id": "innovatie", "title": "Innovatieproject",
        "description": "Je ontwikkelt samen met andere studenten een innovatief product voor een onderneming.",
        "institution": "Testhogeschool C", "url": "https://example.org/innovatie",
    },
]


def recommend(minor_id="ondernemen", student_quote="ondernemerschap"):
    minor = next(minor for minor in MINORS if minor["id"] == minor_id)
    return {
        "action": "recommend", "question_topic": "none",
        "recommendations": [{
            "minor_id": minor_id, "student_quote": student_quote,
            "description_quote": minor["description"],
        }],
    }


class AgentTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"GEMINI_API_KEY": "fake-test-key"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        client_patch = patch("ai.agent.genai.Client")
        self.client_factory = client_patch.start()
        self.addCleanup(client_patch.stop)
        self.client = self.client_factory.return_value.__enter__.return_value
        self.generate = self.client.models.generate_content
        self.set_output(recommend())

    def set_output(self, output):
        self.generate.return_value = SimpleNamespace(text=json.dumps(output, ensure_ascii=False))

    def assert_safe_failure(self, result):
        self.assertEqual(result["recommended_minor_ids"], [])
        self.assertFalse(result["needs_more_info"])
        self.assertIn("studieadviseur", result["response"])
        self.assertTrue(result["response"].startswith(DISCLOSURE))

    def test_ict_student_interested_in_entrepreneurship(self):
        result = chat_with_agent("Ik studeer HBO-ICT en wil ondernemerschap verkennen.", [], MINORS)
        self.assertEqual(result["recommended_minor_ids"], ["ondernemen"])
        self.assertFalse(result["needs_more_info"])
        for text in (DISCLOSURE, "Digitaal ondernemen", "ondernemerschap", MINORS[0]["description"], MINORS[0]["url"]):
            self.assertIn(text, result["response"])
        self.assertEqual(set(result), {"response", "recommended_minor_ids", "needs_more_info"})

    def test_care_student_interested_in_psychology(self):
        self.set_output(recommend("psychologie", "psychologie"))
        result = chat_with_agent("Ik studeer verpleegkunde en wil meer leren over psychologie.", [], MINORS)
        self.assertEqual(result["recommended_minor_ids"], ["psychologie"])
        self.assertIn("Psychologie in de zorg", result["response"])

    def test_undecided_student_gets_targeted_question(self):
        self.set_output({"action": "ask", "question_topic": "interests", "recommendations": []})
        result = chat_with_agent("Ik weet nog niet wat ik wil.", [], MINORS)
        self.assertTrue(result["needs_more_info"])
        self.assertEqual(result["recommended_minor_ids"], [])
        self.assertIn(QUESTIONS["interests"], result["response"])

    def test_no_matching_minor_refers_to_adviser(self):
        self.set_output({"action": "refer", "question_topic": "none", "recommendations": []})
        self.assert_safe_failure(chat_with_agent("Ik wil uitsluitend een minor archeologie.", [], MINORS))

    def test_history_is_used_and_not_mutated(self):
        history = [
            {"role": "user", "content": "Ik studeer ICT en ben geïnteresseerd in ondernemerschap."},
            {"role": "assistant", "content": QUESTIONS["preferences"]},
        ]
        original = copy.deepcopy(history)
        dataset_original = copy.deepcopy(MINORS)
        result = chat_with_agent("Geen voorkeur.", history, MINORS)
        self.assertEqual(result["recommended_minor_ids"], ["ondernemen"])
        payload = json.loads(self.generate.call_args.kwargs["contents"])
        self.assertEqual(payload["history"], history)
        self.assertEqual(payload["message"], "Geen voorkeur.")
        self.assertEqual(history, original)
        self.assertEqual(MINORS, dataset_original)

    def test_maximum_three_recommendations_preserves_order(self):
        output = recommend()
        output["recommendations"] += [recommend(minor_id)["recommendations"][0] for minor_id in ("innovatie", "psychologie")]
        self.set_output(output)
        result = chat_with_agent("Ik wil ondernemerschap combineren met menselijk gedrag en innovatie.", [], MINORS)
        self.assertEqual(result["recommended_minor_ids"], ["ondernemen", "innovatie", "psychologie"])

    def test_unknown_id_rejects_entire_output(self):
        output = recommend()
        unknown = copy.deepcopy(output["recommendations"][0])
        unknown["minor_id"] = "VERZONNEN-ID"
        output["recommendations"].append(unknown)
        self.set_output(output)
        result = chat_with_agent("ondernemerschap", [], MINORS)
        self.assert_safe_failure(result)
        self.assertNotIn("VERZONNEN-ID", result["response"])
        self.assertNotIn("Digitaal ondernemen", result["response"])

    def test_invalid_json_and_empty_or_blocked_output(self):
        for raw in ("geen json", "```json\n{}\n```", "{", "null", "[]", "", None):
            with self.subTest(raw=raw):
                self.generate.return_value = SimpleNamespace(text=raw)
                self.assert_safe_failure(chat_with_agent("ondernemerschap", [], MINORS))

    def test_invalid_structured_output(self):
        invalid = [
            {},
            {"response": "Deze minor is gratis", "recommended_minor_ids": ["ondernemen"], "needs_more_info": False},
            {"action": "recommend", "question_topic": "none", "recommendations": []},
            {"action": "ask", "question_topic": "none", "recommendations": []},
            {"action": "refer", "question_topic": "none", "recommendations": recommend()["recommendations"]},
            {"action": [], "question_topic": "none", "recommendations": []},
            {"action": "refer", "question_topic": "none", "recommendations": "geen"},
        ]
        output = recommend()
        output["extra"] = "Ongecontroleerde tekst"
        invalid.append(output)
        for output in invalid:
            with self.subTest(output=output):
                self.set_output(output)
                self.assert_safe_failure(chat_with_agent("ondernemerschap", [], MINORS))

    def test_duplicate_or_too_many_recommendations(self):
        for count in (2, 4):
            with self.subTest(count=count):
                output = recommend()
                output["recommendations"] *= count
                self.set_output(output)
                self.assert_safe_failure(chat_with_agent("ondernemerschap", [], MINORS))

    def test_fabricated_or_wrong_source_evidence_is_rejected(self):
        for field, value in (("description_quote", "Deze minor is gratis en je wordt altijd toegelaten."),
                             ("description_quote", MINORS[1]["description"]),
                             ("student_quote", "psychologie"),
                             ("student_quote", 42), ("minor_id", True)):
            with self.subTest(field=field, value=value):
                output = recommend()
                output["recommendations"][0][field] = value
                self.set_output(output)
                self.assert_safe_failure(chat_with_agent("ondernemerschap", [], MINORS))

    def test_assistant_text_cannot_substitute_for_student_interest(self):
        history = [{"role": "assistant", "content": "Misschien ondernemerschap?"}]
        self.assert_safe_failure(chat_with_agent("Dat weet ik niet.", history, MINORS))

    def test_no_endless_follow_up_questions(self):
        self.set_output({"action": "ask", "question_topic": "interests", "recommendations": []})
        history = [{"role": "assistant", "content": "Een eerdere vraag"}] * 3
        self.assert_safe_failure(chat_with_agent("Geen idee.", history, MINORS))

    def test_same_question_is_not_repeated(self):
        self.set_output({"action": "ask", "question_topic": "study", "recommendations": []})
        history = [{"role": "model", "content": QUESTIONS["study"]}]
        self.assert_safe_failure(chat_with_agent("ICT.", history, MINORS))

    def test_recommendations_still_allowed_after_three_turns(self):
        history = [{"role": "assistant", "content": "Een eerdere vraag"}] * 3
        result = chat_with_agent("Ik wil ondernemerschap.", history, MINORS)
        self.assertEqual(result["recommended_minor_ids"], ["ondernemen"])

    def test_missing_key_does_not_call_api(self):
        os.environ.pop("GEMINI_API_KEY")
        self.assert_safe_failure(chat_with_agent("ondernemerschap", [], MINORS))
        self.client_factory.assert_not_called()

    def test_google_key_and_configurable_model(self):
        os.environ["GEMINI_API_KEY"] = " "
        os.environ["GOOGLE_API_KEY"] = "fake-google-key"
        os.environ["GEMINI_MODEL"] = "team-model"
        chat_with_agent("ondernemerschap", [], MINORS)
        self.assertEqual(self.client_factory.call_args.kwargs["api_key"], "fake-google-key")
        self.assertEqual(self.generate.call_args.kwargs["model"], "team-model")
        config = self.generate.call_args.kwargs["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        ids = config.response_json_schema["properties"]["recommendations"]["items"]["properties"]["minor_id"]["enum"]
        self.assertEqual(ids, [minor["id"] for minor in MINORS])
        self.assertIn("Nederlandstalige", config.system_instruction)
        self.assertEqual(self.client_factory.call_args.kwargs["http_options"].timeout, 30_000)

    def test_api_errors_do_not_leak_sensitive_details(self):
        self.generate.side_effect = RuntimeError("SECRET-KEY student@example.org volledig gesprek")
        with self.assertLogs("ai.agent", level="WARNING") as logs:
            result = chat_with_agent("ondernemerschap student@example.org", [], MINORS)
        self.assert_safe_failure(result)
        self.assertEqual(logs.output, ["WARNING:ai.agent:minor_agent: api_error"])
        self.assertNotIn("student@example.org", result["response"])
        self.client_factory.return_value.__exit__.assert_called_once()

    def test_client_creation_failure_is_handled(self):
        self.client_factory.side_effect = RuntimeError("verbinding mislukt")
        self.assert_safe_failure(chat_with_agent("ondernemerschap", [], MINORS))

    def test_invalid_input_does_not_call_api(self):
        for message, history, minors in ((12, [], MINORS), ("vraag", None, MINORS),
                                        ("vraag", [{"role": "system", "content": "hack"}], MINORS),
                                        ("vraag", [], [{"id": "x"}]), ("vraag", [], "geen JSON")):
            with self.subTest(message=message, history=history, minors=minors):
                self.assert_safe_failure(chat_with_agent(message, history, minors))
        self.client_factory.assert_not_called()

    def test_empty_dataset_does_not_call_api(self):
        self.assert_safe_failure(chat_with_agent("ondernemerschap", [], []))
        self.client_factory.assert_not_called()

    def test_malformed_scraper_url_does_not_escape_error_handling(self):
        rows = [{**MINORS[0], "url": "https://["}]
        self.assert_safe_failure(chat_with_agent("ondernemerschap", [], rows))
        self.client_factory.assert_not_called()

    def test_empty_message_does_not_call_api(self):
        result = chat_with_agent("  ", [], MINORS)
        self.assertTrue(result["needs_more_info"])
        self.client_factory.assert_not_called()

    def test_no_conversation_state_between_calls(self):
        chat_with_agent("ondernemerschap", [], MINORS)
        self.set_output({"action": "ask", "question_topic": "study", "recommendations": []})
        chat_with_agent("Hallo", [], MINORS)
        payload = json.loads(self.generate.call_args.kwargs["contents"])
        self.assertEqual(payload["history"], [])
        self.assertNotIn("ondernemerschap", payload["message"])


class NormalizationTests(unittest.TestCase):
    def test_scraper_aliases_html_integer_id_and_relative_url(self):
        raw = {"results": [{
            "minor_id": 123, "titel": " Test &amp; minor ",
            "beschrijving": "<p>Een minor over</p><p>ondernemen.</p>",
            "instelling": " Hogeschool A ", "link": "/minoren/test/",
            "ignored_field": "wordt niet naar Gemini gestuurd",
        }]}
        result = normalize_minors(json.dumps(raw))
        self.assertEqual(result, [{
            "id": "123", "title": "Test & minor", "description": "Een minor over ondernemen.",
            "institution": "Hogeschool A", "url": "https://www.kiesopmaat.nl/minoren/test/",
        }])

    def test_duplicate_ids_missing_fields_and_unsafe_urls_are_rejected(self):
        for rows in ([MINORS[0], MINORS[0]], [{"title": "Zonder ID"}],
                     [{**MINORS[0], "url": "javascript:alert(1)"}],
                     [{**MINORS[0], "url": "https://["}],
                     [{**MINORS[0], "url": "https://example.org:999999/"}],
                     [{**MINORS[0], "url": "https://user:pass@example.org/"}],
                     [{**MINORS[0], "institution": None}],
                     [{**MINORS[0], "description": "<p></p>"}],
                     [{**MINORS[0], "minor_id": "conflicterend"}],
                     [{**MINORS[0], "id": True}]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValidationError):
                    normalize_minors(rows)


class SDKContractTests(unittest.TestCase):
    def test_real_sdk_serialization_with_mocked_http_response(self):
        """Test ook de echte SDK-conversie, volledig zonder netwerkverkeer."""
        requests = []

        def handler(request):
            payload = json.loads(request.content)
            requests.append(payload)
            self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
            self.assertIn("responseJsonSchema", payload["generationConfig"])
            return httpx.Response(200, json={"candidates": [{
                "content": {"role": "model", "parts": [{"text": json.dumps(recommend())}]},
                "finishReason": "STOP",
            }]})

        real_client = genai.Client
        with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as http_client:
            def client_factory(**kwargs):
                kwargs["http_options"].httpx_client = http_client
                return real_client(**kwargs)

            with patch.dict(os.environ, {
                "GEMINI_API_KEY": "fake-test-key", "GOOGLE_API_KEY": "",
                "GOOGLE_GENAI_USE_VERTEXAI": "false", "GOOGLE_GENAI_USE_ENTERPRISE": "false",
            }):
                with patch("ai.agent.genai.Client", side_effect=client_factory):
                    result = chat_with_agent("Ik wil ondernemerschap.", [], MINORS)
        self.assertEqual(result["recommended_minor_ids"], ["ondernemen"])
        self.assertEqual(len(requests), 1)


if __name__ == "__main__":
    unittest.main()

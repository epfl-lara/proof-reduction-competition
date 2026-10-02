"""Unit and integration tests for RCP client and chat harness."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from proof_eval.rcp import (
    DEFAULT_MODEL,
    DEFAULT_RCP_BASE_URL,
    DEFAULT_REASONING,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TEMPERATURE,
    MODELS,
    RCPChat,
    RCPClient,
    RCPResponse,
    find_env_file,
    load_rcp_env,
    map_rcp_reasoning,
    normalize_model_name,
    parse_env_file,
)


class TestRCPConfigAndEnv(unittest.TestCase):
    """Test parsing .env and environment variable loading."""

    def test_default_constants(self):
        self.assertEqual(DEFAULT_TEMPERATURE, 0.3)
        self.assertEqual(DEFAULT_REASONING, True)
        self.assertEqual(DEFAULT_REASONING_EFFORT, "high")

    def test_parse_env_file_syntax(self):
        content = (
            "# Comment line\n"
            "export RCP_BASE_URL=\"https://inference.rcp.epfl.ch/v1\"\n"
            "export RCP_API_KEY='sk-test-secret-key'\n"
            "PLAIN_VAR=simple_value\n"
            "\n"
            "# Another comment\n"
            "EXPORT_WITHOUT_QUOTES=hello_world\n"
        )
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            parsed = parse_env_file(temp_path)
            self.assertEqual(parsed["RCP_BASE_URL"], "https://inference.rcp.epfl.ch/v1")
            self.assertEqual(parsed["RCP_API_KEY"], "sk-test-secret-key")
            self.assertEqual(parsed["PLAIN_VAR"], "simple_value")
            self.assertEqual(parsed["EXPORT_WITHOUT_QUOTES"], "hello_world")
        finally:
            os.remove(temp_path)

    def test_load_rcp_env_priority_and_safety(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("export RCP_API_KEY=\"sk-from-file\"\nexport RCP_BASE_URL=\"https://custom.rcp/v1\"\n")
            temp_path = f.name

        try:
            # When env vars are clear
            with patch.dict(os.environ, {}, clear=True):
                base_url, api_key = load_rcp_env(temp_path)
                self.assertEqual(base_url, "https://custom.rcp/v1")
                self.assertEqual(api_key, "sk-from-file")
                # Confirm standard OPENAI variables are untouched
                self.assertNotIn("OPENAI_API_KEY", os.environ)

            # When explicit env var overrides file
            with patch.dict(os.environ, {"RCP_API_KEY": "sk-from-env"}, clear=True):
                base_url, api_key = load_rcp_env(temp_path)
                self.assertEqual(api_key, "sk-from-env")
                self.assertEqual(base_url, "https://custom.rcp/v1")
        finally:
            os.remove(temp_path)

    def test_missing_api_key_raises_informative_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with tempfile.NamedTemporaryFile("w", delete=False) as f:
                f.write("# Empty env\n")
                temp_path = f.name
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    load_rcp_env(temp_path)
                self.assertIn("RCP_API_KEY is not set", str(ctx.exception))
            finally:
                os.remove(temp_path)


class TestModelAndReasoningMapping(unittest.TestCase):
    """Test model aliases and reasoning template mapping."""

    def test_normalize_model_name(self):
        self.assertEqual(normalize_model_name("deepseek-flash"), "deepseek-ai/DeepSeek-V4.1-Flash")
        self.assertEqual(normalize_model_name("qwen-397b"), "Qwen/Qwen3.5-397B-A17B")
        self.assertEqual(normalize_model_name("qwen-35b"), "Qwen/Qwen3.6-35B-A3B")
        self.assertEqual(normalize_model_name("qwen-27b"), "Qwen/Qwen3.8-27B")
        self.assertEqual(normalize_model_name("custom/my-model"), "custom/my-model")

    def test_default_reasoning_is_on_and_high(self):
        # When neither reasoning nor effort is passed, defaults are on (True) and effort is 'high'
        chat_kwargs, extra = map_rcp_reasoning("deepseek-ai/DeepSeek-V4.1-Flash")
        self.assertTrue(chat_kwargs["enable_thinking"])
        self.assertEqual(chat_kwargs["reasoning_effort"], "high")

    def test_deepseek_reasoning_mapping(self):
        # Reasoning disabled
        chat_kwargs, extra = map_rcp_reasoning("deepseek-ai/DeepSeek-V4.1-Flash", reasoning=False)
        self.assertFalse(chat_kwargs["enable_thinking"])

        # DeepSeek rejects 'medium'; must be mapped to 'high'
        chat_kwargs, extra = map_rcp_reasoning(
            "deepseek-ai/DeepSeek-V4.1-Flash", reasoning=True, reasoning_effort="medium"
        )
        self.assertTrue(chat_kwargs["enable_thinking"])
        self.assertEqual(chat_kwargs["reasoning_effort"], "high")

        # Explicit 'low'
        chat_kwargs, extra = map_rcp_reasoning(
            "deepseek-ai/DeepSeek-V4.1-Flash", reasoning=True, reasoning_effort="low"
        )
        self.assertEqual(chat_kwargs["reasoning_effort"], "low")

    def test_qwen38_reasoning_mapping(self):
        # Qwen 3.8 rejects 'high'; must be mapped to 'xhigh'
        chat_kwargs, extra = map_rcp_reasoning(
            "Qwen/Qwen3.8-27B", reasoning=True, reasoning_effort="high"
        )
        self.assertTrue(chat_kwargs["enable_thinking"])
        self.assertEqual(chat_kwargs["reasoning_effort"], "xhigh")

        # 'medium' is accepted by Qwen 3.8
        chat_kwargs, extra = map_rcp_reasoning(
            "Qwen/Qwen3.8-27B", reasoning=True, reasoning_effort="medium"
        )
        self.assertEqual(chat_kwargs["reasoning_effort"], "medium")

    def test_qwen35_and_36_reasoning_mapping(self):
        chat_kwargs, extra = map_rcp_reasoning("Qwen/Qwen3.6-35B-A3B", reasoning=True)
        self.assertTrue(chat_kwargs["enable_thinking"])

        chat_kwargs, extra = map_rcp_reasoning("Qwen/Qwen3.6-35B-A3B", reasoning=False)
        self.assertFalse(chat_kwargs["enable_thinking"])


class TestRCPResponseAndHarness(unittest.TestCase):
    """Test response structures and chat harness state transitions."""

    def test_response_dataclass(self):
        resp = RCPResponse(
            content="Hello world",
            reasoning_content="Step 1...",
            model="test-model",
            finish_reason="stop",
            usage={"total_tokens": 42},
        )
        self.assertEqual(resp.content, "Hello world")
        self.assertEqual(resp.reasoning, "Step 1...")
        self.assertEqual(str(resp), "Hello world")
        d = resp.to_dict()
        self.assertEqual(d["role"], "assistant")
        self.assertEqual(d["content"], "Hello world")
        self.assertEqual(d["reasoning_content"], "Step 1...")

    def test_client_defaults(self):
        with patch("proof_eval.rcp.load_rcp_env", return_value=("https://test", "sk-test")):
            client = RCPClient()
            self.assertEqual(client.default_temperature, 0.3)
            self.assertEqual(client.default_reasoning, True)
            self.assertEqual(client.default_reasoning_effort, "high")

    def test_chat_harness_lifecycle(self):
        client = MagicMock(spec=RCPClient)
        client.default_model = "deepseek-ai/DeepSeek-V4.1-Flash"
        client.default_temperature = 0.3
        client.default_reasoning = True
        client.default_reasoning_effort = "high"

        mock_resp1 = RCPResponse(
            content="Reply 1", reasoning_content="Think 1", model="test", finish_reason="stop"
        )
        mock_resp2 = RCPResponse(
            content="Reply 2", reasoning_content="Think 2", model="test", finish_reason="stop"
        )
        client.create_chat_completion.side_effect = [mock_resp1, mock_resp2]

        chat = RCPChat(client, system="Be concise.")
        self.assertEqual(len(chat.history), 1)
        self.assertEqual(chat.history[0]["role"], "system")
        self.assertEqual(chat.temperature, 0.3)
        self.assertEqual(chat.reasoning, True)
        self.assertEqual(chat.reasoning_effort, "high")

        # Turn 1
        r1 = chat.send("User 1")
        self.assertEqual(r1.content, "Reply 1")
        self.assertEqual(len(chat.history), 3)  # system, user1, assistant1

        # Turn 2
        r2 = chat.send("User 2")
        self.assertEqual(r2.content, "Reply 2")
        self.assertEqual(len(chat.history), 5)  # system, user1, assistant1, user2, assistant2

        # Fork
        forked = chat.fork()
        self.assertEqual(len(forked.history), 5)

        # Undo on main chat
        undone = chat.undo()
        self.assertIsNotNone(undone)
        user_turn, asst_turn = undone
        self.assertEqual(user_turn["content"], "User 2")
        self.assertEqual(asst_turn["content"], "Reply 2")
        self.assertEqual(len(chat.history), 3)
        self.assertEqual(len(forked.history), 5)  # Fork was unchanged

        # Reset
        chat.reset()
        self.assertEqual(len(chat.history), 1)
        self.assertEqual(chat.history[0]["content"], "Be concise.")


class TestRCPLiveIntegration(unittest.TestCase):
    """Live smoke checks against EPFL RCP endpoint using repository .env."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.client = RCPClient(timeout=25.0)
        except Exception:
            cls.client = None

    def setUp(self):
        if self.client is None:
            self.skipTest("RCP credentials not available in environment or .env")

    def test_live_models_endpoint(self):
        models = self.client.list_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 10)
        self.assertIn("deepseek-ai/DeepSeek-V4.1-Flash", models)

    def test_live_deepseek_flash(self):
        # By default reasoning=True, effort='high', temp=0.3
        resp = self.client.complete(
            prompt="Compute 7*8. Output only the integer 56.",
            model="deepseek-ai/DeepSeek-V4.1-Flash",
            max_tokens=256,
        )
        self.assertIn("56", resp.content)
        self.assertIsNotNone(resp.reasoning)

    def test_live_qwen_36(self):
        # By default reasoning=True, temp=0.3
        resp = self.client.complete(
            prompt="Compute 6*7. Output only the integer 42.",
            model="Qwen/Qwen3.6-35B-A3B",
            max_tokens=256,
        )
        self.assertIn("42", resp.content)


if __name__ == "__main__":
    unittest.main()


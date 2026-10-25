"""The original model configuration must survive the conventional training CLI."""

import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from proof_eval.training.command import training_command

PINNED_BASE_CONFIG = b'{\n    "architectures": [\n        "Qwen4ExpForConditionalGeneration"\n    ],\n    "image_token_id": 248056,\n    "language_model_only": false,\n    "model_type": "qwen4_exp",\n    "text_config": {\n        "attention_bias": false,\n        "attention_dropout": 0.0,\n        "bos_token_id": 248044,\n        "dtype": "bfloat16",\n        "eos_token_id": 248044,\n        "full_attention_interval": 4,\n        "hc_count": 4,\n        "hc_lowrank": 320,\n        "head_dim": 256,\n        "heads_per_ngram": 8,\n        "hidden_act": "silu",\n        "hidden_size": 2560,\n        "indexer_budget": 2048,\n        "indexer_compress_ratio": 4,\n        "indexer_head_dim": 128,\n        "indexer_kv_heads": 1,\n        "indexer_n_heads": 4,\n        "initializer_range": 0.02,\n        "layer_types": [\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention",\n            "linear_attention",\n            "linear_attention",\n            "linear_attention",\n            "full_attention"\n        ],\n        "linear_conv_kernel_dim": 4,\n        "linear_key_head_dim": 128,\n        "linear_num_key_heads": 16,\n        "linear_num_value_heads": 48,\n        "linear_value_head_dim": 128,\n        "make_ngram_vocab_size_divisible_by": 128,\n        "mamba_ssm_dtype": "float32",\n        "max_position_embeddings": 262144,\n        "model_type": "qwen4_exp_text",\n        "moe_intermediate_size": 640,\n        "mtp": {\n            "hybrid": true,\n            "layer_types": [\n                "full_attention"\n            ],\n            "mtp_use_hidden_state_from_layer": null,\n            "num_hidden_layers": 1,\n            "rope_theta": 10000000\n        },\n        "mtp_num_hidden_layers": 1,\n        "mtp_use_dedicated_embeddings": false,\n        "ngram_size": 3,\n        "ngram_vocab_size_base": 20000000,\n        "num_attention_heads": 24,\n        "num_experts": 512,\n        "num_experts_per_tok": 10,\n        "num_hidden_layers": 48,\n        "num_key_value_heads": 2,\n        "output_gate_type": "sigmoid",\n        "output_router_logits": false,\n        "pad_token_id": null,\n        "partial_rotary_factor": 0.25,\n        "ple_conv_kernel_size": 4,\n        "ple_embed_dim": 2560,\n        "ple_layer_ids": [\n            2\n        ],\n        "rms_norm_eps": 1e-06,\n        "rope_parameters": {\n            "mrope_interleaved": true,\n            "mrope_section": [\n                11,\n                11,\n                10\n            ],\n            "partial_rotary_factor": 0.25,\n            "rope_theta": 10000000,\n            "rope_type": "default"\n        },\n        "router_aux_loss_coef": 0.001,\n        "shared_expert_intermediate_size": 640,\n        "split_ngram_parts": 128,\n        "tie_word_embeddings": false,\n        "use_cache": true,\n        "vocab_size": 248320\n    },\n    "tie_word_embeddings": false,\n    "transformers_version": "5.8.0.dev0",\n    "video_token_id": 248057,\n    "vision_config": {\n        "deepstack_visual_indexes": [],\n        "depth": 27,\n        "hidden_act": "gelu_pytorch_tanh",\n        "hidden_size": 1152,\n        "in_channels": 3,\n        "initializer_range": 0.02,\n        "intermediate_size": 4304,\n        "model_type": "qwen4_exp",\n        "num_heads": 16,\n        "num_position_embeddings": 2304,\n        "out_hidden_size": 2560,\n        "patch_size": 16,\n        "spatial_merge_size": 2,\n        "temporal_patch_size": 2\n    },\n    "vision_end_token_id": 248054,\n    "vision_start_token_id": 248053\n}'


def test_training_command_retains_native_model_positions():
    plan = {
        "root": "/scratch/new",
        "home": "/home/new",
        "context_tokens": 32768,
        "model_revision": "original",
        "per_turn_max_tokens": 8192,
        "max_turns": 32,
    }
    command = training_command(plan, "/cache/original")
    assert "--rope_scaling" not in command
    assert command[command.index("--max_model_len") + 1] == "32768"
    assert command[command.index("--vllm_max_model_len") + 1] == "32768"


def test_actual_library_preserves_native_mrope_and_reproduces_old_override_failure():
    parser = pytest.importorskip("mcore_bridge.config.parser")
    transformers = pytest.importorskip("transformers")
    from swift.arguments.base_args.model_args import ModelArguments

    assert (
        hashlib.sha256(PINNED_BASE_CONFIG).hexdigest()
        == "889658f2508e8c61d409b02e70e0d78d8d4452ec65aaafbe129805d213d2e74b"
    )
    values = json.loads(PINNED_BASE_CONFIG)
    model = transformers.AutoConfig.for_model(values.pop("model_type"), **values)
    native = copy.deepcopy(model.text_config.rope_scaling)
    args = SimpleNamespace(
        rope_scaling=None,
        max_model_len=32768,
        model_info=SimpleNamespace(
            rope_scaling=copy.deepcopy(native), max_model_len=262144
        ),
    )
    ModelArguments._init_rope_scaling(args)
    model.text_config.rope_scaling = args.rope_scaling
    current = parser.hf_to_mcore_config(model)
    assert current["position_embedding_type"] == "mrope"
    assert current["mrope_section"] == [11, 11, 10]
    assert current["mrope_interleaved"] is True
    assert args.max_model_len == 32768

    model.text_config.rope_scaling = {
        "rope_type": "yarn",
        "factor": 4.0,
        "original_max_position_embeddings": 262144,
    }
    previous = parser.hf_to_mcore_config(model)
    assert previous.get("position_embedding_type", "rope") == "rope"
    assert "mrope_section" not in previous

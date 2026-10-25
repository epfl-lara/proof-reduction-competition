"""Copy FP8 PLE rows as bytes so Triton can compile the lookup on A100.

The lookup only copies values. Reinterpreting both pointers as uint8 preserves
every bit and avoids the unsupported SM80 FP8 pointer type. The base image is
pinned to the vLLM version providing this kernel; weights are never converted.
"""


def register():
    import torch
    from vllm.models.qwen4_exp.common import ngram_embedding as module

    original = module._lookup_ple_embedding_from_pinned_kernel
    if getattr(original, "_ampere_byte_copy", False):
        return

    class ByteCopyKernel:
        _ampere_byte_copy = True

        def __getitem__(self, grid):
            launch = original[grid]

            def run(weight, ids, output, *args, **kwargs):
                if weight.dtype == torch.float8_e4m3fn:
                    weight = weight.view(torch.uint8)
                    output = output.view(torch.uint8)
                return launch(weight, ids, output, *args, **kwargs)

            return run

    module._lookup_ple_embedding_from_pinned_kernel = ByteCopyKernel()

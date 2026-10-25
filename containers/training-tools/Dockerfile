FROM registry.rcp.epfl.ch/lara-milikic/swift-lean@sha256:6c0bb40e32a993a90610a84711ad8fc63082b1f03382e009ef5ce0d2e7b5c2a2
USER root
# LeanExplore's unrelated MCP server requires MCP1, while vLLM requires MCP2.
# Keep vLLM's MCP2 and install only the local search module's runtime imports.
# The real frozen host search query is a required deployment preflight.
COPY requirements.txt /opt/rcp/training-tools-requirements.txt
RUN /opt/rcp/bin/rcp-entrypoint python3 -c 'import importlib.metadata as m,json; from pathlib import Path; names={d.metadata["Name"] for d in m.distributions()}; pins={n:m.version(n) for n in names}; Path("/opt/rcp/training-base-versions.json").write_text(json.dumps(pins,sort_keys=True)); targets={"lean-explore","sentence-transformers","faiss-cpu","bm25s"}; Path("/opt/rcp/training-base-constraints.txt").write_text("".join(n+"=="+v+"\n" for n,v in sorted(pins.items()) if n.lower().replace("_","-") not in targets))' \
 && uv pip install --system --python /usr/bin/python3 --constraint /opt/rcp/training-base-constraints.txt -r /opt/rcp/training-tools-requirements.txt \
 && uv pip install --system --python /usr/bin/python3 --no-deps 'lean-explore==1.3.0' \
 && /opt/rcp/bin/rcp-entrypoint python3 -c 'import importlib.metadata as m,json; from pathlib import Path; prior=json.loads(Path("/opt/rcp/training-base-versions.json").read_text()); targets={"lean-explore","sentence-transformers","faiss-cpu","bm25s"}; changed={n:(v,m.version(n)) for n,v in prior.items() if n.lower().replace("_","-") not in targets and m.version(n)!=v}; assert not changed,changed; import lean_explore,sentence_transformers,faiss,bm25s,swift; Path("/opt/rcp/training-tools-versions.json").write_text(json.dumps({n:m.version(n) for n in ["lean-explore","sentence-transformers","faiss-cpu","bm25s","torch","transformers","ms-swift"]},sort_keys=True))'
USER 254622:30048

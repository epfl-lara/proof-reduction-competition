"""Read-only source lookup within each theorem's pinned Lean projects."""

import re
import subprocess

from . import semantic


class SourceTools:
    def __init__(self, evaluator, row, versions, *, semantic_config=None):
        self.evaluator, self.row, self.versions = evaluator, row, list(versions)
        self.semantic_config = semantic_config

    def source(self, request):
        op = request["op"]
        allowed = (
            {"op", "version", "query", "limit"}
            if op == "search"
            else (
                {"op", "version", "query", "limit", "packages"}
                if op == "semantic_search"
                else {"op", "version", "path"}
                | ({"start", "end"} if op == "read" else set())
            )
        )
        if not set(request) <= allowed:
            raise ValueError("Unsupported source fields")
        version = request.get("version") or self.versions[0]
        if version not in self.versions:
            raise ValueError("Version outside this theorem")
        project = self.evaluator.projects[(self.row["source"], version)].resolve()
        if op == "semantic_search":
            return semantic.search(self.semantic_config, project, request, version)
        if op == "search":
            query = request.get("query")
            if (
                not isinstance(query, str)
                or not query
                or "\n" in query
                or len(query) > 300
            ):
                raise ValueError("Use one nonempty literal source query")
            limit = request.get("limit", 30)
            if type(limit) is not int or not 1 <= limit <= 100:
                raise ValueError("Search limit must be in 1..100")
            result = subprocess.run(
                [
                    "rg",
                    "--hidden",
                    "--no-ignore",
                    "--follow",
                    "-n",
                    "-F",
                    "-g",
                    "*.lean",
                    "-g",
                    "!.git/**",
                    "-g",
                    "!_ProofEval_*",
                    "-g",
                    "!_ProofOptimize_*",
                    "-g",
                    "!.lake/build/**",
                    "-g",
                    "!**/.lake/build/**",
                    "-g",
                    "!**/.git/**",
                    "--",
                    query,
                    ".",
                ],
                cwd=project,
                text=True,
                capture_output=True,
                timeout=30,
            )
            if result.returncode not in (0, 1):
                raise ValueError("Source search failed: " + result.stderr[:500])
            matches = result.stdout.splitlines()
            local_matches = [
                s
                for s in matches
                if not s.startswith("./.lake/") and not s.startswith(".lake/")
            ]
            dep_matches = [
                s for s in matches if s.startswith("./.lake/") or s.startswith(".lake/")
            ]
            ordered = local_matches + dep_matches
            return {
                "kind": "source_search",
                "version": version,
                "query": query,
                "matches": [s[:1500] for s in ordered[:limit]],
                "truncated": len(ordered) > limit,
            }
        path = (project / request["path"]).resolve()
        packages = project / ".lake/packages"
        roots = [project] + (
            [p.resolve() for p in packages.iterdir() if p.is_dir()]
            if packages.is_dir()
            else []
        )
        if (
            not any(path.is_relative_to(root) for root in roots)
            or path.suffix != ".lean"
            or path.name.startswith("_Proof")
        ):
            raise ValueError("Only pinned Lean source files may be read")
        lines = path.read_text().splitlines()
        if op == "outline":
            pattern = re.compile(
                r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*(?:theorem|lemma|def|abbrev|inductive|structure|class|instance)\b"
            )
            matches = [
                {"line": i, "text": s[:1000]}
                for i, s in enumerate(lines, 1)
                if pattern.match(s)
            ]
            return {
                "kind": "source_outline",
                "path": request["path"],
                "version": version,
                "declarations": matches[:200],
                "truncated": len(matches) > 200,
            }
        start, end = request.get("start", 1), request.get("end", 180)
        if (
            type(start) is not int
            or type(end) is not int
            or start < 1
            or end < start
            or end - start >= 400
        ):
            raise ValueError("Read 1..400 lines at a time")
        text = "\n".join(
            f"{i}: {s}" for i, s in enumerate(lines, 1) if start <= i <= end
        )
        return {
            "kind": "source_excerpt",
            "path": request["path"],
            "version": version,
            "text": text[:32000],
            "truncated": len(text) > 32000,
        }

# Included third-party material

The complete ZIP contains the dependency payloads described below. The small ZIP includes their manifests and downloads the exact same files from the public asset repository during setup; `downloads.json` pins their URLs, sizes and checksums. License notices remain included in both ZIPs.

- Native Lemex executable and companion: Apache-2.0; see `licenses/lemex-LICENSE` and `licenses/lemex-NOTICE`. Exact binary checksums are authoritative in `native/manifest.json`. Source project: https://github.com/Lemmy00/lemex .
- Optional read-only-mount backend: unmodified Ubuntu Bubblewrap 0.9.0-1ubuntu0.3, LGPL-2.0-or-later, pinned in `third_party/bubblewrap/PROVENANCE.json`. Copyright, full license and the corresponding upstream source plus Ubuntu packaging/patches accompany the small `bin/bwrap` executable in `third_party/bubblewrap/`. No system installation or privileged binary is required.
- Lean benchmark projects and pinned Lake dependencies retain their original license files inside the plain source archives in `project-sources/`. The archives contain no Git databases or history. Setup validates the supplied source against genuine public pinned commits and restores the required local checkout identities.
- LeanExplore declaration search index is included for offline local retrieval. It is a public declaration index, not a bank of optimized benchmark answers. Apache-2.0 tool license: `licenses/lean-explore-LICENSE`. Tool source: https://github.com/justincasher/lean-explore .
- Model weights are downloaded at their pinned public Hugging Face revisions; their model licenses apply. No weights or tuned model checkpoints are redistributed in this code archive.
- Python dependencies retain their own package licenses. Exact versions are recorded by the installer.

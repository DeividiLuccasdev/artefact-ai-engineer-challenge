# Publication provenance

Development began locally while the GitHub App had account authorization but no
repository installation. The project was published after the connector was installed
on this repository only. No force push or fabricated development milestones were used.

The connector imports file trees and creates new commit objects, so public commit
identifiers and import timestamps differ from the original local commits. Each
imported commit message identifies its original development commit. The original
local repository preserves the development history. These imports are not claims
that development happened at the later publication timestamps.

For further development, clone the public repository using the README instructions.
The pre-publication local branch has different Git ancestry; do not force-push it
over the public branch.

## Milestone mapping

| Original local commit | Public import commit | Milestone |
| --- | --- | --- |
| `b6eb2b3cefa7b3467fbeb1b82be42b60fea89f56` | `8f334a4bf878796b996871b367e3f72bee4176f6` | chore: initialize Python prototype and document scope |
| `b0436e5e64e6d3bc85d67310613b17e732a3ba15` | `69f6dcd4a9b3a7aeb350de071823449ae44f3a1a` | feat: add immutable catalog snapshots and scoped order queries |
| `464c668d9e608deb7eb6b59be057878e3d6af5b2` | `7ddc4d497b19b39ce93a5f0f055648545578d73f` | feat: implement policy retrieval and session-isolated tool calling |
| `483866fe3d6ea88d983860c6c6a137fb6a8b5e34` | `88e1aa58472503d8e5f0799718b4624d3f7427c6` | docs: add setup guide, acceptance scenarios and concurrency guarantees |
| `7b0751d63cf3394c8691f9dcaaa54e76d3774f5c` | `758338146ec9b333ce66a6b8e75d3520695ed665` | feat: add local visual chat and verify real Qwen3 catalog responses |
| `d288b557995411e979a5a466af6e34c01dcd1fbd` | `d34d789e5745c35fa1aef6fd2ab993dfd0fa0544` | fix: establish browser sessions before concurrent chat requests |
| `0feef10ae925974b476f17f874e7fff81e135e1f` | `3426602f51e268da64ebcf2544f61adc3b116027` | fix: prevent competing Windows servers from sharing the chat port |
| `13ccdb60adfabd7f9bfd27fb1688ea0abc8ae101` | `51b922c28f80197512a07eef0b355b89d1687d03` | fix: ground commercial answers and online returns in retrieved data |
| `15beeab782c38f00dda56fbd87c071349431c3e1` | `51186c9a423b209058199400554fbcfba7416c16` | docs: record four English model conversations and evaluation findings |

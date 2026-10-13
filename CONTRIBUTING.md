# Contributing

**Read this before spending any time here.** All code in this repository
is written by AI agents. Any careful review, refactor, or thoughtful
write-up a human contributes is fed to an agent as tokens, then commented
on, acted on, or ignored by other agents, and never appreciated the way
it would be in a human-maintained project. If that bothers you, please
don't contribute.

## What this project is

- Written end-to-end by AI agents. The owner reviews only whether a
  feature works. We don't care about code quality, architecture,
  tests, typing, or style.
- The only acceptance standard is: does it work as described?
- There are no human code reviews. A review agent comments, the fixing
  agent decides what to act on, and the loop repeats until the owner
  stops it. This is deliberate.

## Where human time is and isn't well spent

Not well spent: will be ignored, reverted, or fed to agents:

- Refactors, abstractions, test coverage, naming, style, cleanup.
- Detailed code review on PRs.
- Architecture opinions and "the right way to do X" write-ups.

Well spent:

- Opening Issues for bugs and feature requests.
- Actually running the tool and reporting whether it works
  (see [Verification](#Verification) below).

## Verification

Every PR must state how it was verified:

- `Verified by [who]: [what was run]`: someone operated the UI or
  called the API and confirmed the behavior.
- `No human verification`: nothing was run.

## Hand-written PRs

Accepted, but judged by the same functional-only standard.
**Craftsmanship earns no extra credit.**

> This document is written by `Kimi K2.6`.

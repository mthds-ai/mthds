---
description: "Contribute to the MTHDS open standard — report issues, propose specification changes, build tooling, or publish packages."
---

# Contributing to MTHDS

MTHDS is an open standard. Contributions are welcome — whether they are bug reports, specification clarifications, tooling improvements, or new packages.

## Ways to Contribute

### Report Issues

If you find an inconsistency in the specification, a bug in a tool, or an edge case that is not documented, open an issue in the MTHDS standard repository. Include:

- What you expected to happen.
- What actually happened.
- A minimal `.mthds` or `METHODS.toml` example that demonstrates the issue.

### Propose Specification Changes

Specification changes follow a structured process:

1. **Open a discussion** describing the problem and your proposed solution. Include concrete `.mthds` examples showing before/after.
2. **Draft the change** as a pull request against the specification. Normative changes use RFC 2119 language (`MUST`, `SHOULD`, `MAY`).
3. **Review** by the maintainers and community. Changes to the specification require careful consideration of backward compatibility.
4. **Merge and release** as a new minor or major version of the standard.

### Build Packages

The ecosystem grows through packages. Publish packages that solve real problems in your domain. Well-documented packages with clear concept hierarchies and typed pipe signatures make the Know-How Graph more useful for everyone.

### Build Tools

The standard is tool-agnostic. If you build an MTHDS-related tool — an alternative runtime, an editor extension, a registry implementation, a visualization tool — share it with the community.

## Coding Standards for the Reference Implementation

The reference implementation (Pipelex) has its own coding standards and contribution guidelines. See the Pipelex repository for details.

## License

The MTHDS standard specification is open. Implementations may use any license. The reference implementation's license is specified in its repository.

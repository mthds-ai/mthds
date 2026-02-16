# Roadmap

The MTHDS standard is at version `1.0.0`. This page outlines planned and potential directions for future development.

## Near-Term

- **Registry reference implementation.** A reference implementation for the registry index, enabling `mthds pkg search` to query remote registries in addition to local packages.
- **Package signing.** Optional signed manifests for enterprise use, enabling verifiable authorship and integrity beyond SHA-256 content hashes.
- **Cross-package concept refinement validation at install time.** The specification allows validation of concept refinement across packages at both install time and load time. The current reference implementation validates at load time only. Install-time validation would detect breaking changes earlier.

## Medium-Term

- **Know-How Graph web interface.** A web-based explorer for the Know-How Graph, enabling visual navigation of concept hierarchies and pipe chains across the public ecosystem.
- **Proxy/mirror support.** Configurable proxy for package fetching, supporting speed, reliability, and air-gapped environments (similar to Go's `GOPROXY`).
- **MTHDS language server protocol (LSP).** A standalone LSP server that provides diagnostics, completion, hover, and go-to-definition for `.mthds` files, usable by any editor.

## Long-Term

- **Conditional concept fields.** Allow concept structure fields to be conditionally present based on the values of other fields.
- **Parametric concepts.** Concepts that accept type parameters (e.g., `Result<T>` where T is another concept).
- **Runtime interoperability standard.** A specification for how different MTHDS runtimes can exchange concept instances, enabling cross-runtime pipe invocation.

## Contributing to the Roadmap

The roadmap is shaped by community needs. If you have a use case that the standard does not yet support, open an issue in the MTHDS standard repository. Proposals that include concrete `.mthds` examples demonstrating the need are especially helpful.

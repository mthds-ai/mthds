# Design Philosophy

MTHDS was designed with a specific set of principles that inform every decision in the standard. Understanding these principles helps explain why the standard works the way it does.

## Declarative by Design

MTHDS separates *what* a method does from *how* it is executed. The method author declares intent — "given this input concept, produce that output concept, using this approach" — and the runtime decides how to fulfill it. This is analogous to how SQL separates data queries from storage engines: the query author describes the result they want, not the access path to get there. A method may specify which model to use, but it does not specify how to manage context windows, how to retry on failure, or how to allocate compute resources. Those are runtime concerns.

## Filesystem as Interface

MTHDS packages are directories of text files. `.mthds` bundles are TOML. `METHODS.toml` is TOML. `methods.lock` is TOML. There are no binary formats, no databases, no proprietary encodings.

This means:

- **Version control works natively.** Every change to a method is a diff. Merge conflicts are resolvable by humans.
- **Agents can read and write methods.** AI agents that work with text files can create, modify, and validate MTHDS files without special tooling.
- **No vendor lock-in.** Any tool that reads TOML can read MTHDS files. The standard does not require any specific runtime, editor, or platform.

## Progressive Enhancement

MTHDS is designed so that each layer of functionality is opt-in:

1. **A single `.mthds` file works on its own.** No manifest, no package, no configuration. This is the entry point for learning and prototyping.
2. **Add a `METHODS.toml` to get packaging.** A globally unique address, version, and visibility controls. No behavior changes for the bundles themselves.
3. **Add `[dependencies]` to compose with others.** Cross-package references become available. Existing bundles continue to work unchanged.
4. **Publish to the ecosystem.** Registry indexes crawl your package. The Know-How Graph discovers your methods. No changes to your files are required.

Each layer builds on the previous one without breaking it. A standalone bundle that works today continues to work unchanged inside a package.

## Type-Driven Composability

Every pipe in MTHDS declares a typed signature: the concepts it accepts and the concept it produces. This is not just documentation — it is the foundation of the system.

Typed signatures enable:

- **Compile-time validation.** A runtime can verify that the output of one pipe is compatible with the input of the next before executing anything.
- **Semantic discovery.** The Know-How Graph answers "I have a `Document`, I need a `NonCompeteClause`" by traversing typed signatures and refinement hierarchies.
- **Auto-composition.** When no single pipe transforms X to Y, the graph can discover multi-step chains through intermediate concepts.

This contrasts with text-based approaches where capabilities are described in natural language. Text descriptions enable keyword search but not type-safe composition.

## One Artifact, Three Audiences

A `.mthds` file serves as both specification and executable artifact. A domain expert reads the business logic — concepts named after real-world entities, pipes that declare intent in plain language. An engineer reads something testable and deployable — typed signatures, validated data flow, version-controlled definitions. An agent reads something it can build, modify, and execute — structured text with machine-readable types and composable transformations. No separate documentation layer, no translation step between what the method describes and what the method does.

## Federated Distribution

MTHDS follows a federated model: decentralized storage with centralized discovery.

- **Storage is decentralized.** Packages live in Git repositories owned by their authors. There is no central package host. The package address (e.g., `github.com/acme/legal-tools`) IS the fetch location.
- **Discovery is centralized.** Registry indexes crawl and index packages without owning them. Multiple registries can coexist, each serving different communities.

This mirrors how the web works: content is hosted anywhere, search engines index it. No single entity controls the ecosystem.

## Packages Own Namespaces, Domains Carry Meaning

Domains are semantic labels that carry meaning about what a bundle is about — `legal.contracts`, `scoring`, `recruitment`. But domains do not merge across packages. Two packages declaring `domain = "recruitment"` have completely independent namespaces.

The package is the isolation boundary. Cross-package references are always explicit (`alias->domain.name`). There is no implicit coupling through shared domain names.

This is a deliberate design choice. Merging domains across packages would create fragile implicit coupling: any package declaring a domain could inject concepts into your namespace. Instead, cross-package composition is explicit — through dependencies and typed references.

The domain name remains valuable for discovery. Searching the Know-How Graph for "all packages in the recruitment domain" is meaningful. But discovery is not namespace merging.

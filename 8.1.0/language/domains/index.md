# Domains

Domains are namespaces for concepts and pipes within a bundle. Every bundle declares exactly one domain in its header, and all concepts and pipes in that bundle belong to that domain.

## What Domains Are For

Domains serve two purposes:

1. **Organization** — group related concepts and pipes under a meaningful name. A domain like `legal.contracts` tells you what the bundle is about.
2. **Namespacing** — prevent naming collisions. Two bundles in different domains can define concepts or pipes with the same name without conflict.

## Declaring a Domain

The `domain` field in the bundle header sets the namespace:

```toml
domain = "legal.contracts"
```

Everything in this file — every concept and every pipe — belongs to `legal.contracts`.

## Hierarchical Domains

Domains can be hierarchical, using `.` as the separator:

```toml
legal
legal.contracts
legal.contracts.shareholder
```

This allows natural organization of complex knowledge areas. A large package covering legal methods might structure its domains as a tree:

- `legal` — general legal concepts and utilities
- `legal.contracts` — contract-specific methods
- `legal.contracts.shareholder` — shareholder agreement specifics

**The hierarchy is purely organizational.** There is no implicit scope or inheritance between parent and child domains. `legal.contracts` does not automatically have access to concepts defined in `legal`. If a bundle in `legal.contracts` needs a concept from `legal`, it uses an explicit domain-qualified reference — the same as any other cross-domain reference.

## Domain Naming Rules

- A domain code is one or more `snake_case` segments separated by `.`.
- Each segment must match `[a-z][a-z0-9_]*`.
- Recommended depth: 1–3 levels.
- Recommended segment length: 1–4 words.

## Reserved Domains

Three domain names are reserved and cannot be used as the first segment of any user-defined domain:

| Domain | Purpose |
|--------|---------|
| `native` | Built-in concept types (`Text`, `Image`, `Document`, etc.). |
| `mthds` | Reserved for the MTHDS standard. |
| `pipelex` | Reserved for the reference implementation. |

For example, `native.custom` and `pipelex.utils` are invalid domain names.

## Same Domain Across Bundles

Within a single package, multiple bundles can share the same domain. When they do, their concepts and pipes merge into a single namespace:

```
my-package/
├── METHODS.toml
├── general_legal.mthds       # domain = "legal"
└── legal_utils.mthds         # domain = "legal"
```

Both files contribute concepts and pipes to the `legal` domain. If both files define a concept `ContractClause`, that is a conflict — an error at load time.

## Domains Across Packages

Two packages can both declare `domain = "recruitment"`. Their concepts and pipes are completely independent — there is no merging of namespaces across packages. The package boundary is the true isolation boundary.

This means `recruitment.CandidateProfile` from Package A and `recruitment.CandidateProfile` from Package B are different things. To use something from another package, you must qualify the reference with the package alias (see [Namespace Resolution](namespace-resolution.md)).

The domain name remains valuable for **discovery**: searching for "all packages in the recruitment domain" is a meaningful query. But discovery does not merge namespaces.

## See Also

- [Specification: Domain Naming Rules](../spec/mthds-format.md#domain-naming-rules) — normative reference.
- [Namespace Resolution](namespace-resolution.md) — how references are resolved across bundles and packages.

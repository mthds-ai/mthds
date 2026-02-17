---
description: "Detailed algorithm for MTHDS dependency resolution, library assembly, and namespace isolation in package loading."
---

# Package Loading

This page details the dependency resolution algorithm, library assembly, and namespace isolation mechanics.

## Dependency Resolution Algorithm

Dependency resolution is a recursive process that handles local paths, remote fetching, cycle detection, and diamond dependencies.

```
function resolve_all_dependencies(manifest, package_root):
    local_resolved = []
    remote_deps = []

    for dep in manifest.dependencies:
        if dep.path is not null:
            local_resolved.append(resolve_from_filesystem(dep, package_root))
        else:
            remote_deps.append(dep)

    resolved_map = {}        // address -> resolved dependency
    constraints = {}         // address -> list of version constraints
    resolution_stack = set() // for cycle detection

    resolve_transitive_tree(remote_deps, resolution_stack, resolved_map, constraints)

    return local_resolved + values(resolved_map)
```

**Key rules:**

- **Local path dependencies** are resolved directly from the filesystem. They are NOT resolved transitively — only the root package's local paths are honored.
- **Remote dependencies** are resolved transitively. If Package A depends on Package B, and B depends on Package C, then C is also resolved.
- **Cycle detection** uses a DFS stack set. If an address is encountered while already on the stack, the resolver reports a cycle error.

## Diamond Dependency Handling

Diamond dependencies occur when the same package is required by multiple dependents with different version constraints.

```
function resolve_diamond(address, all_constraints, available_tags):
    parsed_constraints = [parse_constraint(c) for c in all_constraints]
    for version in sorted(available_tags, ascending):
        if all(constraint.matches(version) for constraint in parsed_constraints):
            return version
    error("No version satisfies all constraints")
```

This is Minimum Version Selection applied to multiple constraints simultaneously. The resolver:

1. Collects all version constraints from every dependent that requires the package.
2. Lists available version tags from the remote repository (cached to avoid repeated network calls).
3. Sorts versions in ascending order.
4. Selects the first version that satisfies ALL constraints.

When a diamond re-resolution picks a different version than previously resolved, the stale sub-dependency constraints contributed by the old version are recursively removed before re-resolving.

## VCS Fetching

Remote packages are fetched via Git with a three-tier resolution chain:

1. **Local cache check** — look in `~/.mthds/packages/{address}/{version}/`.
2. **VCS fetch** — if not cached, clone the repository:
    - Map address to clone URL: prepend `https://`, append `.git`.
    - List remote tags: `git ls-remote --tags {url}`.
    - Filter tags that parse as valid semver (strip optional `v` prefix).
    - Select version via MVS.
    - Clone at the selected tag: `git clone --depth 1 --branch {tag}`.
3. **Cache storage** — store the cloned directory under `~/.mthds/packages/{address}/{version}/`, removing the `.git` directory.

Cache writes use a staging directory with atomic rename for safety against partial writes.

## Library Assembly

After resolving all dependencies, the runtime assembles a **library** — the complete set of loaded bundles indexed by domain and package:

```
Library:
    local_bundles:     domain -> list of bundle blueprints
    dependency_bundles: (alias, domain) -> list of bundle blueprints
    exported_pipes:    (alias, domain) -> set of pipe codes
    main_pipes:        (alias, domain) -> pipe code
```

The library provides the lookup context for namespace resolution. When a pipe reference like `scoring_lib->scoring.compute_weighted_score` is encountered:

1. Find the dependency by alias `scoring_lib`.
2. Look up domain `scoring` in the dependency's bundles.
3. Find the pipe `compute_weighted_score`.
4. Verify it is exported (in the `[exports]` list or declared as `main_pipe`).

## Namespace Isolation

Packages isolate namespaces completely. Two packages declaring `domain = "recruitment"` have independent concept and pipe namespaces. The isolation boundary is the package, not the domain.

Within a single package, bundles sharing the same domain merge into a single namespace. Collisions (duplicate concept or pipe codes within the same domain of the same package) are errors.

The reference implementation enforces isolation through the library structure: lookups are always scoped to a specific package (identified by alias for dependencies, or "current package" for local references).

## Visibility Checking Algorithm

The visibility checker runs after library assembly:

```
function check_visibility(manifest, bundles):
    exported_pipes = build_export_index(manifest)
    main_pipes = build_main_pipe_index(bundles)

    errors = []

    // Check reserved domains
    for bundle in bundles:
        if bundle.domain starts with reserved segment:
            errors.append(reserved domain error)

    // Check intra-package cross-domain references
    for bundle in bundles:
        for (pipe_ref, context) in bundle.collect_pipe_references():
            if pipe_ref is special outcome ("fail", "continue"):
                skip
            if pipe_ref is cross-package (contains "->"):
                validate alias exists in dependencies
            else:
                ref = parse_pipe_ref(pipe_ref)
                if ref is qualified and not same domain as bundle:
                    if ref.pipe_code not in exported_pipes[ref.domain]:
                        if ref.pipe_code != main_pipes[ref.domain]:
                            errors.append(visibility error)

    return errors
```

The checker runs three passes:

1. **Reserved domain check** — ensures no bundle uses `native`, `mthds`, or `pipelex` as the first domain segment.
2. **Intra-package visibility** — ensures cross-domain pipe references target exported or main_pipe pipes.
3. **Cross-package alias validation** — ensures `->` references use aliases declared in `[dependencies]`.

## See Also

- [Specification: Namespace Resolution Rules](../spec/namespace-resolution.md) — the formal resolution algorithm.
- [The Package System: Version Resolution](../packages/version-resolution.md) — how MVS works.

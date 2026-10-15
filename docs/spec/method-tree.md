---
description: "The method tree — which files make up a method, how each is named and referenced, the tree digest that identifies them, the file entry that carries one, and how a method declares its Python."
---

# Method Tree

A method is a tree of files. Its bundles, its manifest, the Python modules its `PipeFunc` steps call, the templates and images its steps read, its `requirements.txt` and its `README.md` are all files of one tree, each named by its path from the tree's root, and the tree as a whole is identified by its digest. This page defines that object once: where the root is, which files belong, how a file is named and how one file names another, the digest, the file entry that carries a file from one program to another, and how a method declares its Python.

```
invoices/
├── METHODS.toml
├── README.md
├── main.mthds
├── requirements.txt
├── funcs/
│   ├── __init__.py
│   ├── totals.py
│   └── __pycache__/
├── templates/
│   ├── letter.html
│   └── logo.png
├── results/
│   ├── .gitignore        (holds the single pattern *)
│   └── run-1.json
├── .gitignore
└── .venv/
```

The method tree of this directory is:

```
METHODS.toml
README.md
funcs/__init__.py
funcs/totals.py
main.mthds
requirements.txt
templates/letter.html
templates/logo.png
```

`.gitignore` and `.venv/` are out because their names start with a dot, `funcs/__pycache__/` is out by default, and `results/run-1.json` is out because the `.gitignore` file in its directory ignores every file there. Every other file belongs to the tree and travels with the method, whether a step reads it or it is carried for people and agents to read.

!!! note "Implementation status"
    The method tree is committed design. This page is the contract implementations are brought into conformance with — the same forward-contract convention the [Library Crate Format](./library-crate.md#specification-status) uses for its unrealized sections. Conformance is asserted against this document as each piece lands.

## The Root

A **method tree** is the set of regular files under a **root** directory that the [membership rule](#the-membership-rule) admits, each named by its [tree path](#tree-paths) from the root. The root is the directory holding `METHODS.toml`. A compliant implementation finds it from what a caller hands over:

- **A directory.** The root is the nearest directory at or above the directory handed over that holds `METHODS.toml`, found by [Manifest Discovery](./manifest-format.md#manifest-discovery). When there is none, the method has no manifest, and the directory handed over is its root.
- **A `.mthds` file named alone.** The root is the nearest directory at or above the file's own directory that holds `METHODS.toml`, found the same way. When there is none, the tree is that one file, under its file name, and nothing else: a [file reference](#file-references) from it to any other file is refused, with a message saying to run the method's directory or to add a `METHODS.toml`.

A `.mthds` file named alone that the membership rule keeps out of its own tree, such as one whose name starts with a dot or one that a `.gitignore` file under its root ignores, is refused, naming the rule that excludes it.

Sending a directory is always the caller's explicit act. A `.mthds` file named alone never carries the files beside it unless a manifest makes their directory a method's root, so a bundle saved among unrelated documents never takes them anywhere.

A run loads one root tree and the trees of the packages it depends on, each with its own root and its own digest (see [Dependencies Are Trees of Their Own](#dependencies-are-trees-of-their-own)).

A method's files are its own: they are authored once, travel with the method, and are its identity. A file a caller supplies for one run reaches the run as an input, a stuff in the wire form of the [CLI I/O Contract](./cli-io-contract.md#stuffs-on-the-wire), and is never a file of the tree.

## The Membership Rule

A regular file under the root belongs to the tree unless one of the following excludes it, and a directory that one of them excludes is excluded with everything under it:

1. **A path segment starting with a dot.** This keeps out `.git/`, `.venv/`, `.env`, `.gitignore`, the `.mthds/` directory where a project keeps its installed packages, and every other dotfile and dot directory, the state of editors and tools included. It is the rule that keeps the commonest secret files out by construction.
2. **The defaults.** A directory named `__pycache__` or `node_modules`; any directory holding a file named `pyvenv.cfg`, which [PEP 405](https://peps.python.org/pep-0405/) places at the top of every Python virtual environment, so a virtual environment stays out whatever its name; any directory below the root holding a `.git` entry, whether a directory or the file a submodule or a worktree holds, so a nested repository stays out, as git leaves it out of every commit; and any directory below the root holding a file named `METHODS.toml`, so a nested package stays out, since it is another package and travels as a tree of its own (see [Dependencies Are Trees of Their Own](#dependencies-are-trees-of-their-own)). The `pyvenv.cfg` default applies to the root too, so a root that is itself a virtual environment holds an empty tree, which no surface accepts. The root's own `METHODS.toml` is the manifest that makes it the root, and it excludes nothing.
3. **The tree's own `.gitignore` files.** The patterns of every `.gitignore` file inside the root, at any depth, read with git's own semantics as [gitignore](https://git-scm.com/docs/gitignore) documents them: a pattern applies relative to the directory of the file that holds it, a deeper file's patterns take precedence over a shallower one's, git never descends into an excluded directory, and so a negation cannot re-include a file under an excluded directory. Only these files count: neither a user's global excludes, nor a repository's `info/exclude`, nor a `.gitignore` file above the root, so the same directory yields the same tree on every machine.
4. **The manifest's `exclude` patterns.** The patterns of [`[package] exclude`](./manifest-format.md#exclude), in the same syntax, read as git reads `core.excludesFile`: relative to the root, and below every `.gitignore` file in precedence, so a negation in a `.gitignore` file can re-include a file they exclude. They keep out of the tree what a method wants kept out of the tree but not out of git.

No pattern re-includes a file that the dot-segment rule or a default excludes. A default looks at a directory's own entries whatever the patterns say of them, so a pattern that ignores a nested `.git` entry, a `pyvenv.cfg` file or a nested `METHODS.toml` file does not bring its directory back.

The rule is deliberately close to what git would commit from the directory. A package is published by pushing a tag, so honouring the tree's own `.gitignore` files makes a local run, a run on a remote runner and a run of the published package see the same files.

### Symbolic Links and Other Entries

A symbolic link that the membership rule does not exclude is an error naming its path: it is never followed and never skipped silently, since a link is either a mistake or a reach outside the root, and both deserve to be seen. Exclusion prunes first, so a link inside an excluded directory is never visited, and a link the rule excludes is no error. An entry that is neither a regular file, nor a directory, nor a symbolic link, such as a named pipe or a device, is an error naming its path in the same way.

### Run Artifacts Beside a Method

A tool that creates a directory under a method's root to write its own files into, such as the results of a run, SHOULD make that directory self-excluding by writing into it a `.gitignore` file holding the single pattern `*`. The directory then stays out of the tree and out of git, and neither this rule nor its defaults need to know the directory's name.

### Checking the Rule Against Git

Because the membership rule follows git, git itself can produce the expected listing of a test tree, which keeps an implementation from sharing a misreading of git's semantics with the person who wrote its tests. In a scratch repository holding the test tree, with global and system configuration turned off and `core.excludesFile` holding the case's `exclude` patterns one per line, `git ls-files --others --exclude-standard -z` lists the files git would commit. Git applies the patterns and nothing else, so the dot-segment rule and the defaults are applied after its listing, which gives the same result because no pattern re-includes what they exclude and a `.gitignore` file inside an excluded directory reaches nothing outside it. Dropping from git's output the directories it lists for nested repositories, every path holding a segment that starts with a dot, every path inside a `__pycache__` or `node_modules` directory, every path inside a directory holding `pyvenv.cfg`, and every path inside a directory below the root holding `METHODS.toml` gives the tree's listing. The last two defaults are read from the test tree itself rather than from git's output, since a pattern may keep out of that output the very file that triggers them.

## Tree Paths

A **tree path** names a file of a tree from its root, such as `templates/letter.html`:

- It is a relative POSIX path: segments separated by `/`, with no leading or trailing `/` and no empty segment.
- No segment is `.` or `..`, and no segment holds a backslash (`\`), a colon (`:`), or a control character, meaning any character of Unicode general category `Cc`, NUL and the line breaks among them.
- It is encoded as UTF-8 in Unicode Normalization Form C (NFC), and tree paths are compared, sorted and matched byte for byte on that encoding.
- Each segment is at most 255 bytes long and the whole path at most 1024 bytes long, in that encoding.

Within one tree, no two paths differ only by letter case: no two paths are equal once both are converted to lowercase by Unicode's default case conversion, so a tree written out on a case-insensitive file system loses no file. And no path names a directory of another: one tree never holds both `templates` and `templates/letter.html`.

A name listed from a file system is normalized to NFC, since some file systems hand back a decomposed form of an accented name, and two names in one directory that are equal after normalization are refused, naming both. A path that breaks any rule above is refused, naming it.

A tree path is a name, never a storage location. A receiver that stores a file keeps it under its hash, as [the file entry](#the-file-entry) carries it, so a tree path may hold accents, spaces or a non-Latin script, and no storage system's naming rules reach an author.

## File References

A **file reference** is a relative path, written in a file of a tree, that names another file of the same tree: a field of a bundle that names a file, or a relative URL inside a template, such as the `src` of an image in an HTML template. Every field that names a method file, whether this specification defines it or an implementation adds it, is a file reference and follows this rule.

```
letters/
├── METHODS.toml
├── shared/
│   └── logo.png
└── templates/
    └── letter.html       (holds <img src="../shared/logo.png">)
```

A file reference is resolved against the directory of the file that holds it, as a relative URL is resolved in a web page:

1. Take the directory of the holding file's tree path, which is the root for a file at the root.
2. Join the reference to it with `/` and normalize the result lexically: drop each `.` segment, and let each `..` segment remove the segment before it.
3. The result MUST be a tree path, so a `..` that would climb above the root is refused as leaving the tree, and it MUST name a file of the tree.

In the example, `../shared/logo.png` held by `templates/letter.html` resolves to `shared/logo.png`. A reference is written with `/` separators: an absolute path, a backslash, or a reference that names a scheme is refused. In a URL, the path is percent-decoded before it is resolved, and the query and fragment take no part.

**Resolving a reference is a lookup in the tree's set of paths, never a file system access.** A reference can only name a file the tree holds, which is what makes `..` harmless, and no implementation opens a path that a method's author, or a caller, wrote.

A reference to a file the tree does not hold is refused, naming the reference and the tree path it resolved to. An implementation that listed the tree from a directory also names the rule that excluded the file, when one did, and for a file inside a nested repository or a nested package it names that directory, so an author who meant to ship the file learns why it is not in the tree. In the one-file tree of a `.mthds` file named alone, the refusal says to run the method's directory or to add a `METHODS.toml`.

## The Tree Digest

The **tree digest** identifies a tree by its bytes. It is `sha256:` followed by the lowercase hexadecimal SHA-256 of the tree's **listing**, which holds one line per file of the tree, sorted by tree path byte for byte, each line being exactly what `sha256sum` prints for that file: the SHA-256 of the file's bytes in lowercase hexadecimal, two spaces, the file's tree path, and a line feed.

```bash
mkdir -p greetings/funcs greetings/templates && cd greetings
printf '# Greetings\n' > README.md
printf 'domain = "greetings"\n' > main.mthds
printf 'def shout(text):\n    return text.upper()\n' > funcs/text_utils.py
printf '<p>Hello</p>\n' > templates/card.html
```

The listing of this tree is:

```
af12591480ada38cf107d1a76bc5e2e111ad4c7ec5f3a2a63d058f5f5ab6b91c  README.md
d78fff51f2aea9cb634456d3c83925ae047d967798f28e8a4b3e7b232a1dc097  funcs/text_utils.py
45b0d6a4796412598db6d328978990fc44563e59057d6e3bfc8419ae3ed3981f  main.mthds
3e9b68b71cc667168399f0bccfb64b2d16314cdc0ed78fac4819aba0dda121a0  templates/card.html
```

and its digest is `sha256:801fca61b41566e46d3fb1923e323590da7a539fd3e7af7455e7cba3934d4674`.

The encoding is injective: a hash has a fixed width and a tree path holds no line break, so two different trees never share a listing.

### The Reference Pipeline

Anyone can recompute a digest with coreutils. Given the tree's paths, one per line, sort them in the C locale, pass each to `sha256sum`, and pass the listing to `sha256sum` once more:

```bash
cd greetings
printf '%s\n' README.md funcs/text_utils.py main.mthds templates/card.html \
  | LC_ALL=C sort \
  | while IFS= read -r f; do sha256sum -- "$f"; done \
  | sha256sum
# 801fca61b41566e46d3fb1923e323590da7a539fd3e7af7455e7cba3934d4674  -
```

`LC_ALL=C` is what makes `sort` order the paths byte for byte. Under another locale it orders them differently, here `funcs/text_utils.py`, `main.mthds`, `README.md`, `templates/card.html`, and the digest it gives is wrong. `shasum -a 256` prints the same line format as `sha256sum` and can stand in for it. A conformance corpus takes its expected digests from this pipeline rather than from any implementation.

### Digest and Fingerprint

The tree digest and the [library crate fingerprint](./library-crate.md#fingerprint) answer different questions. The digest changes with any byte of any file and with any tree path, comments and formatting included, so it says whether two trees hold the same files. The fingerprint changes only when what the method means changes, so it says whether two methods do the same thing. The [lock file](./lock-format.md) records both for each dependency.

## The File Entry

A **file entry** is how one file of a tree travels from one program to another, under its tree path, as its bytes or as their hash. A tree travels as a map from tree path to file entry:

```json
{
  "README.md": "# Greetings\n",
  "main.mthds": "domain = \"greetings\"\n",
  "funcs/text_utils.py": { "base64": "ZGVmIHNob3V0KHRleHQpOgogICAgcmV0dXJuIHRleHQudXBwZXIoKQo=" },
  "templates/card.html": {
    "sha256": "3e9b68b71cc667168399f0bccfb64b2d16314cdc0ed78fac4819aba0dda121a0",
    "size": 13
  }
}
```

This map carries the `greetings` tree above, so its digest is `sha256:801fca61b41566e46d3fb1923e323590da7a539fd3e7af7455e7cba3934d4674` whichever form each file travels in. An entry takes exactly one of three forms:

- **A string** is the file's text: the file's bytes are the UTF-8 encoding of the string, exactly, with no line ending converted and no byte order mark added. A string holding a code point that UTF-8 cannot encode, such as a lone surrogate, is refused. This is the shorthand that keeps the commonest case, a bundle pasted as text, a one-liner.
- **`{ "base64": "…" }`** carries any bytes, encoded with the standard Base64 alphabet of [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648#section-4), padded, with no line breaks.
- **`{ "sha256": "…", "size": … }`** names bytes the receiver already holds: `sha256` is their SHA-256 in lowercase hexadecimal and `size` their length in bytes. It resolves only in the receiver's own blob store, and a receiver that does not hold those bytes, or holds them with another size, refuses the entry, naming the hash.

An entry object holds no other key, and no entry names a file by URL: a URL form would let a sender point the receiver at an address of its choosing, which is exactly what reading only the files it is sent prevents.

A map of entries is refused, naming the offending path, when one of its keys:

- is not a [tree path](#tree-paths), or holds a segment that the membership rule's dot-segment rule or its name defaults exclude (a segment starting with a dot, a `__pycache__` or `node_modules` directory, or a file named `pyvenv.cfg`), or names a file `METHODS.toml` anywhere but at the root, since no tree has such a member;
- is given twice in the document, verbatim or after normalization, which a receiver detects in the text it parses rather than keeping one of the values;
- differs from another key only by letter case, or names a directory of another key.

A map with no key is refused: a tree holds at least one file.

The same map is the method source of a request under the [HTTP Runner Protocol](./protocol.md#method-files), where a runner that keeps a blob store also lets a sender upload once the files it lacks and send the rest by hash. A map has no order, so no file of it is "the first": a request that names no pipe starts at the method's `main_pipe`, as the protocol states.

### Limits

The standard bounds a tree path's length and nothing else. Each implementation bounds as its own policy a file's size, a tree's file count and its total size, and the total of a request's inline entries, and refuses a tree past one of them with a message naming the limit. A program listing a tree for a receiver whose limits it knows SHOULD count files and sum their sizes as it walks the directory, and stop at the first limit passed, before hashing any file, with a message naming the root, the limit and the count reached, so that a directory handed over by mistake is refused in moments rather than read in full.

## Python Modules

A `PipeFunc` names its function by its Python import path from the root of the tree that holds the bundle, which is the import root: `function_name = "funcs.text_utils.shout"` names the function `shout` of the module `funcs/text_utils.py` of the `greetings` tree, and the modules that one imports are resolved from the same root. The rule is the [PipeFunc](./mthds-format.md#operator-pipefunc) field's own.

## Python Dependencies: `requirements.txt`

A method whose Python needs third-party packages declares them in a file named `requirements.txt` at the root of its tree:

```
# The packages funcs/totals.py imports
pandas>=2.2,<3
openpyxl==3.1.5
tzdata; python_version >= "3.12"
```

Each line is blank, a comment whose first character other than a space or a tab is `#`, or exactly one requirement written as [PEP 508](https://peps.python.org/pep-0508/) defines it, environment markers included. A requirement naming a URL (`name @ https://…`), an option of any kind (a line starting with `-`, such as `-e`, `-r`, `-c` or `--index-url`), a comment after a requirement, and a line continued with a backslash are refused, naming the line. Only the root's `requirements.txt` declares anything: a file of that name elsewhere in the tree is an ordinary file.

The standard specifies the file and nothing about how it is satisfied. A runtime decides how to satisfy it, and a runtime that cannot, such as one whose environment lacks a declared package or holds it at a version the requirement excludes, SHOULD refuse the method when it loads, naming each package it cannot satisfy, rather than fail later inside a function.

## Dependencies Are Trees of Their Own

A package a method depends on is a tree of its own, with its own root and its own digest, and never travels inside the tree that depends on it. The `.mthds/` directory where a project keeps its installed packages starts with a dot, so it is out of every tree, and a package kept in a directory below another package's root is out of that package's tree by the nested-package default, so the packages of a library repository never hold one another.

- A dependency with a local `path` is the method tree rooted at that directory, listed under the membership rule like any other.
- A fetched dependency's tree is the set of files of the package's directory in the commit its resolved version points at, **read from the commit's git objects as stored**, with no checkout filter, no line-ending conversion and no `export-ignore` attribute applied, so its digest is the same on every machine, and **filtered by the membership rule**, reading the `.gitignore` files that commit holds inside the package's directory and the package's own `exclude` patterns. A file committed despite a pattern that matches it is therefore out of the published tree as it is out of the local one, a submodule contributes no file, and a symbolic link committed in the package's directory is an error naming its path unless the rule excludes it.

**A tree written out is read back as written.** A copy of a tree that a program writes to disk, such as a package in a cache, holds the tree's files at their tree paths and nothing else, and those files are the tree: a reader takes every file of the copy as a file of the tree and never applies the membership rule to it again. The rule cannot be applied twice, since the `.gitignore` files that shaped the tree start with a dot and are left out of the copy, so a manifest `exclude` pattern that one of them overrode with a negation would exclude its file a second time.

The [lock file](./lock-format.md) records each fetched dependency's tree digest, which an install checks against the tree it fetched.

## See Also

- [`.mthds` File Format: PipeFunc](./mthds-format.md#operator-pipefunc) — how a step names its function by import path.
- [METHODS.toml Manifest Format](./manifest-format.md) — the root's manifest, its `exclude` patterns, and Manifest Discovery.
- [methods.lock Format](./lock-format.md) — the lock records each dependency's tree digest.
- [HTTP Runner Protocol](./protocol.md#method-files) — a request's `files` and the optional blob routes.
- [Distribution](../packages/distribution.md) — how a package is fetched and cached as a tree.

#!/usr/bin/env python3
"""Check that every package name used by the scripts still exists.

Package names are collected from the scripts:
  - dialog checklists          options+=("name" "description" on|off)
  - literal install lists      instpkg "a b", pkg="a b", aurpkg="a b", pacstrap /mnt a b
  - package groups             pacman -Sqg group
  - AUR clones                 git clone https://aur.archlinux.org/name.git
A checklist item goes to the AUR when its case branch adds it to aurpkg, or
when its description says (AUR).

They are compared with the official repositories (core, extra, multilib) and
the AUR. Names in the ignore file (one per line, # comments) are skipped.

Usage: check-packages.py [--ignore FILE] [--extra FILE] [--dbdir DIR] PATH...
Exit status: 0 all names found, 1 problems found, 2 package lists unavailable.
"""
import argparse
import gzip
import io
import os
import re
import sys
import tarfile
import urllib.request

MIRROR = 'https://geo.mirror.pkgbuild.com'
AUR_LIST = 'https://aur.archlinux.org/packages.gz'
REPOS = ('core', 'extra', 'multilib')

OPTION = re.compile(r'^\s*options\+=\("([^"]+)"\s+"([^"]*)"\s+(?:on|off|\$\w+)\)', re.M)
LITERAL = re.compile(r'''(?:instpkg\s+|\b(?:aur)?pkgs?\+?=\s*)"(?:\$(?:aur)?pkgs?\s+)?([a-z0-9][a-z0-9 @._+-]*)"''')
LITERAL_UNQUOTED = re.compile(r'^\s*instpkg\s+([a-z0-9][a-z0-9@._+-]*)\s*$', re.M)
PACSTRAP = re.compile(r'^\s*pacstrap(?:\s+-K)?\s+/mnt\s+([a-z0-9][a-z0-9 @._+-]*?)\s*$', re.M)
GROUP = re.compile(r'pacman\s+-Sqg\s+([a-z0-9][a-z0-9._+-]*)')
AUR_CLONE = re.compile(r'git clone https://aur\.archlinux\.org/([a-z0-9@._+-]+)\.git')
CASE_BLOCK = re.compile(r'for itm in \$sel; do\s*case \$itm in(.*?)esac', re.S)
NAME = re.compile(r'^[a-z0-9][a-z0-9@._+-]*$')


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def load_lists(dbdir):
    repo, groups = {}, {}
    for name in REPOS:
        path = dbdir and os.path.join(dbdir, name + '.db')
        data = open(path, 'rb').read() if path and os.path.exists(path) else fetch(f'{MIRROR}/{name}/os/x86_64/{name}.db')
        with tarfile.open(fileobj=io.BytesIO(data)) as db:
            for member in db.getmembers():
                if not member.name.endswith('/desc'):
                    continue
                fields = {}
                for block in db.extractfile(member).read().decode().strip().split('\n\n'):
                    key, *values = block.split('\n')
                    fields[key.strip('%')] = values
                pkgname = fields['NAME'][0]
                repo[pkgname] = name
                for group in fields.get('GROUPS', []):
                    groups.setdefault(group, set()).add(pkgname)
                for item in fields.get('PROVIDES', []) + fields.get('REPLACES', []):
                    repo.setdefault('hint:' + re.split('[<>=]', item)[0], pkgname)
    path = dbdir and os.path.join(dbdir, 'aur-packages.gz')
    data = open(path, 'rb').read() if path and os.path.exists(path) else fetch(AUR_LIST)
    aur = set(gzip.decompress(data).decode().split())
    return repo, groups, aur


def case_routes(text):
    """Map checklist items to 'aur' or 'skip' from the selection case block."""
    routes, default = {}, None
    for block in CASE_BLOCK.finditer(text):
        for clause in block.group(1).split(';;'):
            match = re.match(r'\s*((?:"[^"]+"\s*\|?\s*\\?\s*)+|\*)\)(.*)', clause, re.S)
            if not match:
                continue
            body = match.group(2)
            if 'aurpkg="$aurpkg $(echo' in body:
                route = 'aur'
            elif re.search(r'(?<!aur)pkg="\$pkg \$\(echo', body):
                route = 'repo'
            else:
                route = 'skip'
            if match.group(1).strip() == '*':
                default = default or route
            else:
                for item in re.findall(r'"([^"]+)"', match.group(1)):
                    routes.setdefault(item, route)
    return routes, default


def scan(paths):
    """Yield (file, name, source) with source repo, aur or group."""
    for top in paths:
        files = [top] if os.path.isfile(top) else [
            os.path.join(d, f) for d, _, fs in os.walk(top) if '.git' not in d for f in fs]
        for path in sorted(files):
            try:
                text = open(path, encoding='utf-8').read()
            except (UnicodeDecodeError, OSError):
                continue
            if not text.startswith('#!'):
                continue
            routes, default = case_routes(text)
            for name, desc in OPTION.findall(text):
                route = routes.get(name, default) or 'repo'
                if route == 'skip':
                    continue
                if '(AUR)' in desc:
                    route = 'aur'
                yield path, name, route
            for match in LITERAL.finditer(text):
                route = 'aur' if 'aurpkg' in match.group(0) else 'repo'
                for name in match.group(1).split():
                    yield path, name, route
            for regex in (LITERAL_UNQUOTED, PACSTRAP):
                for match in regex.finditer(text):
                    for name in match.group(1).split():
                        yield path, name, 'repo'
            for name in GROUP.findall(text):
                yield path, name, 'group'
            for name in AUR_CLONE.findall(text):
                yield path, name, 'aur'


def read_names(path):
    if not path or not os.path.exists(path):
        return set()
    return {line.split('#')[0].strip() for line in open(path)} - {''}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--ignore', help='file of names that are not packages')
    parser.add_argument('--extra', help='file of extra repo package names to check')
    parser.add_argument('--dbdir', help='use core.db, extra.db, multilib.db, aur-packages.gz from this dir')
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()

    try:
        repo, groups, aur = load_lists(args.dbdir)
    except OSError as error:
        print(f'Unable to download the package lists: {error}')
        return 2

    ignore = read_names(args.ignore)
    found = set(scan(args.paths))
    found |= {('(extra list)', name, 'repo') for name in read_names(args.extra)}
    problems = []
    for path, name, route in sorted(found, key=lambda x: (x[0], x[1])):
        if name in ignore or not NAME.match(name):
            continue
        if route == 'group':
            if name not in groups:
                problems.append((path, name, 'group not found'))
        elif route == 'aur':
            if name in repo:
                problems.append((path, name, f'now in [{repo[name]}], install it with pacman'))
            elif name not in aur:
                problems.append((path, name, 'not found in the AUR'))
        elif name not in repo and name not in groups:
            hint = repo.get('hint:' + name)
            if hint:
                problems.append((path, name, f'renamed or replaced, use {hint}'))
            elif name in aur:
                problems.append((path, name, 'only in the AUR now'))
            else:
                problems.append((path, name, 'not found'))

    checked = len({name for _, name, _ in found if name not in ignore and NAME.match(name)})
    for path, name, problem in problems:
        print(f'{path}: {name}: {problem}')
    print(f'{checked} package names checked, {len(problems)} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())

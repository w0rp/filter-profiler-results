#!/usr/bin/env python
"""
Filter profile results.

This script accepts a filename for a profiler file, and zero or more filters
to apply for excluding certain filenames from profiler results.

All filename globs will match recursively with '*'.

For example, a glob 'foo/*/bar' will match 'foo/one/two/bar'

Exact matches will be used for globs.

For example, a glob 'foo/bar' will match 'foo/bar', but not 'baz/foo/bar'.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

__copyright__ = """
Copyright (c) 2017, w0rp <devw0rp@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import argparse
import fnmatch
import itertools
import re
import sys
from pstats import Stats

import marshal

# A poor man's six module.
if sys.version_info[0] == 2:
    text_type = unicode # noqa

    def iteritems(x):
        return x.iteritems()
else:
    text_type = str # noqa

    def iteritems(x):
        return x.items()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'profile_filename',
        type=text_type,
        help='the profile file to filter',
    )
    parser.add_argument(
        'filename_filter_glob_list',
        metavar='glob',
        type=text_type,
        nargs='+',
        help='a glob for filenames to exclude',
    )
    parser.add_argument(
        '--remove-garbage',
        action='store_true',
        help='Remove various symbols and filenames which are probably useless',
    )
    parser.add_argument(
        '--print-included-filenames',
        action='store_true',
        help='print all filenames which will be included to stderr',
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()


def should_include_stats(stats_key, filename_filters):
    filename, line_number, symbol = stats_key

    if any(filter_re.match(filename) for filter_re in filename_filters):
        return False

    return True


def print_included_filenames(filtered_stats):
    unique_filename_iter = (
        match
        for match, groups in
        itertools.groupby(sorted(
            filename
            for filename, line_number, symbol in
            filtered_stats.keys()
        ))
    )

    for filename in unique_filename_iter:
        sys.stderr.write(filename)
        sys.stderr.write('\n')


def main():
    args = parse_arguments()

    # Load all filter globs as regular expressions.
    filename_filters = list(
        re.compile(fnmatch.translate(filter_glob))
        for filter_glob in
        args.filename_filter_glob_list
    )

    if args.remove_garbage:
        filename_filters = [
            # Remove all third party modules or Python modules.
            re.compile(r'.*lib[\\/]python\d?\.?\d?/.*'),
            # Remove strange filenames.
            re.compile(r'~|<string>|<frozen .*>'),
        ] + filename_filters

    stats = Stats(args.profile_filename)
    filtered_stats = {
        key: (nc, cc, tt, ct, {
            caller_key: timing_tuple
            for caller_key, timing_tuple in
            iteritems(callers)
            if should_include_stats(caller_key, filename_filters)
        })
        # The two letter variables represent various stats, like number
        # of calls. Read the pstats.py source code for more information.
        for key, (nc, cc, tt, ct, callers) in
        iteritems(stats.stats)
        if should_include_stats(key, filename_filters)
    }

    if args.print_included_filenames:
        print_included_filenames(filtered_stats)

    marshal.dump(filtered_stats, sys.stdout.buffer)

if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""
Tool to parse an EPICS database and get a field/info node
"""

import argparse
import pathlib
import sys
import re

import pyPDB
import pyPDB.dbd.expand
import pyPDB.dbd.yacc


DESCRIPTION = __doc__


def filter_records(db_file, *, field=None, info=None, record_type=None,
                   format='{record}\t{value}'):
    db_content = db_file.read()

    parsed_db = pyPDB.dbd.yacc.parse(db_content, file=db_file.name)
    db = pyPDB.dbd.expand.DBD(parsed_db)

    def find_node(block, block_type, block_name):
        if not block:
            return
        if hasattr(block, 'body'):
            for item in block.body or []:
                yield from find_node(item, block_type, block_name)
            this_type = getattr(block, 'name', None)
            args = getattr(block, 'args', [])
            if len(args) >= 2:
                this_name, this_value = args[:2]
                if this_type == block_type:
                    if any((this_name == block_name,
                            re.match(block_name, this_name))):
                        yield this_name, this_value
        elif isinstance(block, (list, tuple)):
            for item in block:
                yield from find_node(item, block_type, block_name)

    if info:
        find_args = dict(block_type='info', block_name=info)
    elif field:
        find_args = dict(block_type='field', block_name=field)
    else:
        raise ValueError('Must specify either info/field')

    for record_name, record in db.records.items():
        this_type = record[0].args[0]
        if not record_type or this_type in record_type:
            for key, value in find_node(record, **find_args):
                print(format.format(record=record_name, key=key, value=value,
                                    type=this_type))


def _build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.description = DESCRIPTION
    parser.formatter_class = argparse.RawTextHelpFormatter

    type_group = parser.add_mutually_exclusive_group()
    type_group.add_argument(
        '--info',
        type=str,
        help='Select info node with this name'
    )

    type_group.add_argument(
        '--field',
        type=str,
        help='Select a field with this name'
    )

    parser.add_argument(
        '--record-type',
        type=str,
        nargs='*',
        help='Limit results to these record types'
    )

    parser.add_argument(
        '--format',
        type=str,
        default='{record}\t{value}',
        help='Format for the output'
    )

    parser.add_argument(
        'db_file', metavar="INPUT",
        type=argparse.FileType('rt', encoding='ascii'),
        help='The EPICS database (.db) file'
    )

    return parser


if __name__ == '__main__':
    parser = _build_arg_parser()
    args = parser.parse_args()
    for fn in sys.argv[1:]:
        filter_records(**vars(args))

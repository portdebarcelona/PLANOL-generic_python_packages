#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 25/4/18 15:27
#  Copyright (c) 2019

from sqlparse import sql
from sqlparse.engine import grouping
from sqlparse.sql import TokenList


class ElemGroup(TokenList):
    pass


def group_elems_parenthesis(tlist):
    for tok_idx, tok in enumerate(tlist.tokens):
        if isinstance(tok, sql.Parenthesis) or isinstance(tok, sql.SquareBrackets):
            ini_idx = 1  # Comienza desde el segundo token distinto a ( o [
            fi_elem = fi_idx = len(tok.tokens) - 2  # Acaba en el penultimo token antes de ) o ]
            for tidx in range(fi_idx, ini_idx, -1):
                if tok.tokens[tidx].value == ",":
                    tok.group_tokens(ElemGroup, tidx + 1, fi_elem)
                    fi_elem = tidx - 1

            tok.group_tokens(ElemGroup, ini_idx, fi_elem)


def group(stmt):
    for func in [
        grouping.group_comments,

        # _group_matching
        grouping.group_brackets,
        grouping.group_parenthesis,
        group_elems_parenthesis,
        grouping.group_case,
        grouping.group_if,
        grouping.group_for,
        grouping.group_begin,

        grouping.group_functions,
        grouping.group_where,
        grouping.group_period,
        grouping.group_arrays,
        # grouping.group_identifier,
        grouping.group_operator,
        grouping.group_order,
        grouping.group_typecasts,
        grouping.group_as,
        grouping.group_aliased,
        grouping.group_assignment,
        grouping.group_comparison,

        grouping.align_comments,
        # group_identifier_list,
    ]:
        func(stmt)
    return stmt
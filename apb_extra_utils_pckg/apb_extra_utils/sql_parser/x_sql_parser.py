#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 25/4/18 15:27
#  Copyright (c) 2019

import math
import re

from sqlparse import engine, tokens as toks
from sqlparse.sql import TokenList, Token

from . import x_grouping

KEY = 'key'
VAL = 'val'
SEP = 'sep'
OPE = 'ope'
TXT = 'txt'
GEN = 'gen'
SQL = 'sql'
ERR = 'err'
GRP = 'grup'
STM = 'stmnt'
tipos_elem = {KEY: [toks.Keyword],
              VAL: [toks.Name,
                    toks.Literal,
                    toks.String,
                    toks.Number,
                    toks.Token.Name,
                    toks.Token.Literal,
                    toks.Token.String,
                    toks.Token.Literal.String.Single,
                    toks.Token.Literal.String.Symbol,
                    toks.Token.Number,
                    toks.Token.Literal.String.Symbol,
                    toks.Token.Literal.Number.Float,
                    toks.Token.Literal.Number.Integer],
              SEP: [toks.Punctuation],
              OPE: [toks.Operator,
                    toks.Comparison,
                    toks.Wildcard,
                    toks.Assignment],
              TXT: [toks.Comment,
                    toks.Text,
                    toks.Whitespace,
                    toks.Newline],
              GEN: [toks.Other,
                    toks.Generic],
              SQL: [toks.DML,
                    toks.DDL,
                    toks.CTE,
                    toks.Command],
              ERR: [toks.Error]}

default_sep_txt_regex = ("[" + re.escape('"') + re.escape("'") + "_-]")
limit_noms_sql = 30


def format_text_to_long(txt, long_max, regex_sep_parts=default_sep_txt_regex):
    """

    Args:
        txt:
        long_max:
        regex_sep_parts:

    Returns:
        txt_res (str)
    """
    # Quitar caracteres especiales duplicados
    txt_res = re.sub(r"(\_|\-|\'|\")\1*", r"\1", txt)
    # Quitar caracteres especiales en inicio o final de palabra
    p_ini = re.compile("^" + default_sep_txt_regex)
    txt_res = p_ini.sub("", txt_res)
    p_fin = re.compile(default_sep_txt_regex + "$")
    txt_res = p_fin.sub("", txt_res)

    num_extra_chars = len(txt_res) - long_max
    min_chars_part = 3
    txt_parts = re.split(regex_sep_parts, txt_res)
    l_seps = re.findall(regex_sep_parts, txt_res)

    txt_parts.reverse()  # Se invierte orden para tratar antes las ultimas partes
    while num_extra_chars > 0:
        txt_parts_aux = [p for p in txt_parts if len(p) > min_chars_part]
        len_total_parts = 0
        for p in txt_parts_aux:
            len_total_parts += len(p)
        factor_extra_total = num_extra_chars / len_total_parts

        for id, a_part in enumerate(txt_parts):
            len_part = len(a_part)
            if len_part > min_chars_part:
                rest_char = factor_extra_total * len_part
                if rest_char < 1:
                    rest_char = 1
                else:
                    rest_char = math.floor(rest_char)

                rest_aux = min((len_part - min_chars_part), rest_char)
                txt_parts[id] = a_part[:-rest_aux]
                num_extra_chars -= rest_aux

            if num_extra_chars == 0:
                break

        if min_chars_part > 1:
            min_chars_part -= 1
        else:
            break

    txt_parts.reverse()

    # Si aun habiendo reducido todas las partes a 1char supera se quitan separadores
    num_parts = len(txt_parts) + len(l_seps)
    if num_parts > long_max:
        rest_parts = num_parts - long_max
        if len(l_seps) < rest_parts:
            l_seps = []
        else:
            l_seps = l_seps[:-rest_parts]

    txt_res = ""
    for i, p in enumerate(txt_parts[:-1]):
        txt_res += p
        if i < len(l_seps):
            txt_res += l_seps[i]

    txt_res += txt_parts[-1]

    if len(txt_res) > long_max:
        txt_res = txt_res[:long_max]

    return txt_res


def get_nom_obj_sql(nom_base, prefix="", sufix=""):
    """

    Args:
        nom_base:
        prefix:
        sufix:

    Returns:
        nom_res (str)
    """
    len_nom = len(prefix) + len(nom_base) + len(sufix)
    nom_res = prefix + nom_base + sufix
    if len_nom > limit_noms_sql:
        extra_chars = limit_noms_sql - len(prefix) - len(sufix)
        if extra_chars > 5:
            nom_base = format_text_to_long(nom_base, extra_chars)
            nom_res = prefix + nom_base + sufix
        else:
            nom_res = format_text_to_long(nom_res, limit_noms_sql)

    return nom_res.upper()


def get_parser_sql(a_sql_file):
    """

    Args:
        a_sql_file:

    Returns:
        xSqlParser
    """
    with open(a_sql_file) as a_file:
        a_sql_text = a_file.read()

    return xSqlParser(a_sql_text)


class xElemPos(object):
    """
    """
    __slots__ = ('elem', 'index')

    def __init__(self, x_elem_stmnt, index_elems_stmnt):
        self.elem = x_elem_stmnt
        self.index = index_elems_stmnt


class xElemStmntSql(Token):
    """
    Representa un componente de sentencia SQL
    """
    __slots__ = ('parent_stmnt', 'tipo', 'valor')

    def __init__(self, parent_stmnt, token_tipo, str_val=""):
        super(xElemStmntSql, self).__init__(token_tipo, str_val)

        self.parent_stmnt = parent_stmnt
        self.set_tipo(token_tipo)
        self.set_val(str_val)

    def set_tipo(self, token_tipo):
        self.ttype = token_tipo

        a_tipo = None
        for k, tips in tipos_elem.items():
            if token_tipo in tips:
                a_tipo = k
                break

        if a_tipo is None:
            a_tipo = GEN

        self.tipo = a_tipo

    def set_val(self, val):
        self.value = str(val)
        self.normalized = val.upper() if self.is_keyword else val

        str_val = self.value.upper()
        if not self.is_whitespace:
            str_val = str_val.strip()

        self.valor = str_val

    def substitute_val(self, old_val, new_val, long_max=None):
        if re.search(old_val, self.format_val, re.IGNORECASE):
            set_val = re.sub(old_val, new_val, self.format_val, re.IGNORECASE)

            if long_max is not None:
                set_val = format_text_to_long(set_val, long_max)

            self.set_val(set_val)

    @property
    def format_val(self):
        str_res = re.sub(' +', ' ', self.valor)

        return str_res


class xStatementSql(TokenList):
    """
    Representa una sentencia SQL estructurada de tal modo que se pueda acceder
    a sus datos caracterizadores
    """
    __slots__ = ('parent_stmnt', 'elems_stmnt')

    def __init__(self, a_sqlparser_stmnt, parent_stmnt=None):
        super(xStatementSql, self).__init__(a_sqlparser_stmnt.tokens)

        self.parent_stmnt = parent_stmnt

        self.inicializar()

    def inicializar(self):
        self.elems_stmnt = []

        idx_tok = -1

        while idx_tok is not None:
            (idx_tok, tok) = self.token_next(idx_tok, False, True)

            if tok is None:
                break

            self.add_token_as_x_elem(tok)

    def elems_stmnt_sin_esp(self, index_ini=0, index_fi=None):
        return list(filter(lambda el: not el.is_whitespace, self.elems_stmnt[index_ini:index_fi]))

    @property
    def format_val(self):
        str_res = "".join([elem.format_val for elem in self.elems_stmnt])

        return str_res.strip()

    @property
    def tipo(self):
        if self.parent_stmnt is None:
            return STM
        else:
            return GRP

    # Retorna el primer keyword del statement que lo debería definir
    @property
    def keyword_principal(self):
        for el in self.elems_stmnt_sin_esp():
            if el.tipo == KEY:
                return el.format_val

    # Retorna el valor (ID se ha llamado) después del keyword principal
    @property
    def id_principal(self):
        elem_pos = self.get_next_elem_for_key(self.keyword_principal)

        if elem_pos is not None:
            return elem_pos.elem.format_val.replace("'", "").replace('"', "")

    def add_token_as_x_elem(self, tok, index=None):
        tok_tipo = tok.ttype
        tok_val = tok.value

        if index is None:
            index = len(self.elems_stmnt)

        if issubclass(tok.__class__, TokenList):
            new_x_elem = xStatementSql(tok, self)

        else:
            if tok.is_keyword:
                # Se verifica si hay varios KEYWORDS seguidos con los que se construye un KEYWORD unico
                ElemPos_ant = self.get_elem_ant()

                elem_ant = None
                idx_ant = None

                if ElemPos_ant is not None:
                    elem_ant = ElemPos_ant.elem
                    idx_ant = ElemPos_ant.index

                if elem_ant is not None and elem_ant.is_keyword:
                    elem_ant.set_val(" ".join([elem_ant.value, tok_val]))
                    elem_ant.set_tipo(tok_tipo)

                    # Se borra espacios intermedios si los hay
                    del self.elems_stmnt[idx_ant + 1:index]

                    return

            new_x_elem = xElemStmntSql(self, tok_tipo, tok_val)

        self.elems_stmnt.insert(index, new_x_elem)

    def get_elem_ant(self, index=None, espacios=False):
        if index is None:
            index = len(self.elems_stmnt)

        ret = None
        index_ant = index - 1
        while index_ant >= 0:
            elem_ant = self.elems_stmnt[index_ant]

            if espacios or not elem_ant.is_whitespace:
                ret = xElemPos(elem_ant, index_ant)
                break

            index_ant -= 1

        return ret

    def get_elem_post(self, index=None, espacios=False):
        if index is None:
            index = -1

        idx_fi = len(self.elems_stmnt)

        ret = None

        index_post = index + 1
        while index_post < idx_fi:
            elem_post = self.elems_stmnt[index_post]

            if espacios or not elem_post.is_whitespace:
                ret = xElemPos(elem_post, index_post)
                break

            index_post += 1

        return ret

    def get_next_elem_for_key(self, a_keyword_sql, from_index=0):
        for idx, elem in enumerate(self.elems_stmnt[from_index:]):
            if elem.tipo == KEY and elem.format_val == a_keyword_sql.upper():
                return self.get_elem_post(idx)

    def get_elem_match_val(self, match_val, from_index=0):
        for idx, elem in enumerate(self.elems_stmnt[from_index:]):
            if re.search(match_val, elem.format_val, re.IGNORECASE):
                if elem.tipo == GRP or elem.tipo == STM:
                    return elem.get_elem_match_val(match_val)
                else:
                    return xElemPos(elem, idx)

    def substitute_val(self, old_val, new_val, long_max=None):
        for elem in self.elems_stmnt:
            if elem.tipo == GRP or elem.tipo == VAL:
                elem.substitute_val(old_val, new_val, long_max)


class xSqlParser:
    __slots__ = ('sql_statements',
                 'sql_text',
                 'x_statements',
                 'func_group_orig',
                 'engine_parser_sql')

    def __init__(self, a_sql_text=""):
        self.sql_statements = []
        self.x_statements = []
        self.sql_text = a_sql_text
        self.func_group_orig = x_grouping.grouping.group
        x_grouping.grouping.group = x_grouping.group
        self.engine_parser_sql = engine.FilterStack()
        self.engine_parser_sql.enable_grouping()

        self.sql_statements = tuple(self.engine_parser_sql.run(self.sql_text))

        # Asigna statements_clas sin Tokens inutiles (newline, space) y clasificados por tipo
        for stmnt in self.sql_statements:
            a_new_x_stmnt = xStatementSql(stmnt)

            if a_new_x_stmnt is not None:
                self.x_statements.append(a_new_x_stmnt)

    def get_stmnt(self, key_principal, id_principal=None):
        for a_x_stmnt in self.x_statements:
            if a_x_stmnt.keyword_principal == key_principal.upper() and \
                    (id_principal is None or a_x_stmnt.id_principal == id_principal.upper()):
                return a_x_stmnt

    @property
    def as_script_sql(self):
        a_script = ""
        for a_stmnt in self.x_statements:
            a_script += a_stmnt.format_val
            a_script += "\n"
            a_script += "/"
            a_script += "\n"

        return a_script

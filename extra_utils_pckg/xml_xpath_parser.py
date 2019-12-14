#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

# Functions to convert a SQL query to XPATH query

from pyparsing import CaselessLiteral, Word, delimitedList, Optional, \
    Combine, Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString, \
    ZeroOrMore, Keyword

# Variables fijas globales
and_ = Keyword("and", caseless=True)
or_ = Keyword("or", caseless=True)
in_ = Keyword("in", caseless=True)
not_ = Keyword("not", caseless=True)
like_ = Keyword("like", caseless=True)


def get_parts_sql_filter(sql_query_text):
    """

    Args:
        sql_query_text:

    Returns:

    """
    ident = Word(alphas, alphanums + "_$").setName("identifier")
    columnName = delimitedList(ident, ".", combine=True)
    whereExpression = Forward()

    E = CaselessLiteral("E")
    binop = oneOf("= != < > >= <= eq ne lt le gt ge like ", caseless=True)
    arithSign = Word("+-", exact=1)
    realNum = Combine(Optional(arithSign) + (Word(nums) + "." + Optional(Word(nums)) |
                                             ("." + Word(nums))) +
                      Optional(E + Optional(arithSign) + Word(nums)))
    intNum = Combine(Optional(arithSign) + Word(nums) +
                     Optional(E + Optional("+") + Word(nums)))

    columnRval = realNum | intNum | quotedString | columnName  # need to add support for alg expressions
    whereCondition = Group(
        (columnName + Optional(not_) + binop + columnRval) |
        (columnName + in_ + "(" + delimitedList(columnRval) + ")") |
        ("(" + whereExpression + ")")
    )
    whereExpression << whereCondition + ZeroOrMore((and_ | or_) + whereExpression)

    tokens = None
    try:
        tokens = whereExpression.parseString(sql_query_text)
    except ParseException as err:
        print(" " * err.loc + "^\n" + err.msg)
        print(err)

    return tokens.asList()


def parse_sql_filter_to_xpath(filtro_sql, xpath_base=""):
    """

    Args:
        filtro_sql:
        xpath_base:

    Returns:

    """
    sql_filter_parts = get_parts_sql_filter(filtro_sql)

    xpath_parts = convert_sql_parts_to_xpath_parts(sql_filter_parts)

    xpath_query = get_xpath_string_from_xpath_parts(xpath_parts)

    xpath_str = "boolean(" + xpath_base + "[" + xpath_query + "])"

    return xpath_str


def get_xpath_string_from_xpath_parts(xpath_parts):
    """

    Args:
        xpath_parts:

    Returns:

    """
    xpath_str = ""
    for xpath_part in xpath_parts:
        if type(xpath_part) is list:
            xpath_str += get_xpath_string_from_xpath_parts(xpath_part)
        else:
            xpath_str += xpath_part

    return xpath_str


def encode_for_xml(unicode_data, encoding='ascii'):
    """
    Encode unicode_data for use as XML or HTML, with characters outside
    of the encoding converted to XML numeric character references.

    Args:
        unicode_data:
        encoding:

    Returns:
    """
    try:
        return unicode_data.encode(encoding, 'xmlcharrefreplace')
    except ValueError:
        # ValueError is raised if there are unencodable chars in the
        # data and the 'xmlcharrefreplace' error handler is not found.
        # Pre-2.3 Python doesn't support the 'xmlcharrefreplace' error
        # handler, so we'll emulate it.
        return _xmlcharref_encode(unicode_data, encoding)


def _xmlcharref_encode(unicode_data, encoding):
    """
    Emulate Python 2.3's 'xmlcharrefreplace' encoding error handler.

    Args:
        unicode_data:
        encoding:

    Returns:
    """
    chars = []
    # Step through the unicode_data string one character at a time in
    # order to catch unencodable characters:
    for char in unicode_data:
        try:
            chars.append(char.encode(encoding, 'strict'))
        except UnicodeError:
            chars.append('&#%i;' % ord(char))
    return ''.join(chars)


def convert_sql_parts_to_xpath_parts(sql_filter_parts):
    """

    Args:
        sql_filter_parts:

    Returns:

    """
    xpath_parts = []
    sufix_xpath_parts = []
    if "not" in sql_filter_parts:
        xpath_parts.append("not(")
        sufix_xpath_parts.append(")")

    for sql_elem in sql_filter_parts:
        if type(sql_elem) is list:
            xpath_parts.append(convert_sql_parts_to_xpath_parts(sql_elem))
        elif sql_elem != not_:
            if sql_elem == like_:
                # Lo convertimos en la funcion 'contains()'
                xpath_parts.append("[contains(text(),")
                sufix_xpath_parts.insert(0, ")]")
            elif sql_elem == and_ or sql_elem == or_:
                xpath_parts.append(" " + sql_elem + " ")
            else:
                val_elem = sql_elem
                # Si el sql_elem es un string entonces se convierte a texto XML en ascii
                try:
                    if type(eval(sql_elem)) is str:
                        val_elem = str(sql_elem, "utf-8")
                except:
                    val_elem = str(sql_elem)

                xpath_parts.append(val_elem)

    xpath_parts += sufix_xpath_parts

    return xpath_parts


if __name__ == '__main__':
    import fire

    fire.Fire()
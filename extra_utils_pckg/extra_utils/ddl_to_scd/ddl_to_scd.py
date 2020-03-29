#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

import os
import re
import sys

from ..sql_parser import x_sql_parser as SqlParser

rex_ini_pal = r"(^|,|\(|\s|\"|')"
rex_fin_pal = r"($|,|\)|\s|\"|')"


def val_in_txt(search_val, a_txt):
    """
    Busca valor (search_val) en texto (a_txt) ignorando mayusculas
    Args:
        search_val:
        a_txt:

    Returns:
        re.search
    """
    return re.search(search_val, a_txt, re.IGNORECASE)


def palabra_in_txt(palabra, a_txt):
    """
    Busca palabra (search_val) en texto (a_txt) ignorando mayusculas

    Args:
        palabra:
        a_txt:

    Returns:
        re.search
    """
    return re.search(rex_ini_pal + palabra + rex_fin_pal,
                     a_txt, re.IGNORECASE)


class xDdlParser(SqlParser.xSqlParser):
    """
    Clase que parsea elementos de DDL para definición de tablas
    """
    __slots__ = ('a_sql_parser', 'stmnt_create_tab', 'nom_tab', 'stmnt_grup_def_camps')

    sql_pk = "PRIMARY KEY"
    SEP = SqlParser.SEP
    tokPunctuation = SqlParser.toks.Punctuation
    ApbElemStmnt = SqlParser.xElemStmntSql
    SqlParser = SqlParser.xSqlParser

    def __init__(self, a_sql_text):
        """
        Inicializa el parseador a partir texto sql de una DDL de tabla
        Args:
            a_sql_text:
        """
        super(xDdlParser, self).__init__(a_sql_text)

        self.stmnt_create_tab = self.get_stmnt("CREATE TABLE")
        if self.stmnt_create_tab is None:
            raise NameError("ERROR: El texto sql no tiene sentencia 'CREATE TABLE'")

        self.nom_tab = self.stmnt_create_tab.id_principal

        idx_id_nom_tab = self.stmnt_create_tab.get_elem_match_val(self.nom_tab).index
        self.stmnt_grup_def_camps = self.stmnt_create_tab.get_elem_post(idx_id_nom_tab).elem
        # Se quitan los posibles campos con '?"
        self.stmnt_grup_def_camps.substitute_val(r"\?", "")

        # Se añaden campos definidos en sentencias 'ALTER TABLE nom_tab ADD (def_camp)'
        rex_add_col = re.compile(r"ALTER TABLE [']?" + self.nom_tab + "[']? ADD [(]", re.IGNORECASE)
        for a_stmnt in self.others_apb_statements():
            if rex_add_col.match(a_stmnt.format_val):
                for elem_def_camp in filter(lambda el: el.tipo != self.SEP,
                                            a_stmnt.get_next_elem_for_key("ADD").elem.elems_stmnt_sin_esp(1, -1)):
                    self.add_def_campo(elem_def_camp.format_val)

    @property
    def iter_elems_key_camps(self):
        for a_stmnt in self.x_statements:
            elem_pos_pk = a_stmnt.get_elem_match_val(self.sql_pk)
            if elem_pos_pk is not None:
                stmnt_grup_camps_key = elem_pos_pk.elem.parent_stmnt.get_elem_post(elem_pos_pk.index).elem

                if stmnt_grup_camps_key.is_group:
                    # Sin los parentesis y sin las comas
                    for el in filter(lambda el: el.tipo != self.SEP,
                                     stmnt_grup_camps_key.elems_stmnt_sin_esp(1, -1)):
                        yield el

    @property
    def list_key_camps(self):
        return [el.format_val.replace("'", "").replace('"', "") for el in self.iter_elems_key_camps]

    @property
    def iter_elems_def_camp(self):
        for el in self.stmnt_grup_def_camps.elems_stmnt[1:-1]:
            if el.tipo == self.SEP or palabra_in_txt(self.sql_pk, el.format_val):
                continue

            nom_camp = el.format_val.split(" ")[0].replace("'", "").replace('"', "")
            yield nom_camp, el

    @property
    def list_def_camps(self):
        return [el.format_val for nom_camp, el in self.iter_elems_def_camp]

    def add_def_campo(self, str_def_camp):
        """
        Añade definición de campo

        Args:
            str_def_camp:
        """
        # Si se está añadiendo una Constraint entonces NO se trata como definicion de campo
        if re.search(r"CONSTRAINT", str_def_camp, re.IGNORECASE):
            return

        elem_sep = self.ApbElemStmnt(None, self.tokPunctuation, ",")
        self.stmnt_grup_def_camps.add_token_as_x_elem(elem_sep, -1)

        a_parser_camp = self.SqlParser("(" + str_def_camp + ")")
        a_def_camp_stmnt = a_parser_camp.x_statements[0].elems_stmnt[0].elems_stmnt[1]

        self.stmnt_grup_def_camps.add_token_as_x_elem(a_def_camp_stmnt, -1)

    def others_apb_statements(self):
        for stmnt in self.x_statements:
            if stmnt.format_val != "" and stmnt != self.stmnt_create_tab:
                yield stmnt


class ApbDdlToScd(object):
    SCD4 = "SCD4"
    SCD4c = "SCD4C"
    SCD2 = "SCD2"
    prefix_val_param = "A_"
    sufix_taula_vers = "_VE"
    sufix_seq = "_SEQ"
    limit_noms_sql = 30
    nom_prev_reg_vers = "PREV_REG_VERS"
    nom_new_reg_vers = "NEW_REG_VERS"
    nom_regaux_vers = "REGAUX"
    nom_old_reg_vers = "OLD_REG"
    prefix_delete_trigger = "DEL_"
    prefix_insert_trigger = "INS_"
    prefix_update_trigger = "UPD_"
    prefix_primary_key = "PK_"
    prefix_ins_upd_trigger = prefix_insert_trigger + prefix_update_trigger
    prefix_index = "IDX_"
    sufix_unic = "_UN"
    sufix_trigger = "_TRG"
    sufix_fk = "_FK"
    sufix_check_constraint = "_CHK"
    prefix_check_constraint = "CHK_"
    default_date_version = "CURRENT_DATE"
    templates_tipo = {SCD4: "template_base_SCD4.sql",
                      SCD4c: "template_base_SCD4c.sql",
                      SCD2: "template_base_SCD2.sql"}

    __slots__ = ('ddl_parser',
                 'nom_taula',
                 'def_camps_taula',
                 'nom_camps_clau',
                 'sql_date_version')

    def convert_ddl_file_to_scd(self, ddl_file,
                                list_extra_camps=None,
                                a_sql_date_version=None,
                                tipo_scd='SCD4'):
        """
        Genera a partir de DDL de tabla de Oracle (ddl_file) un nuevo script sobre el subdirectorio 'ddl_[tipo_scd]' con el mismo nombre pero el sufijo '_VE', con los objectos SQL (create, triggers, index, ...) que permitirán la gestión de versiones de cada cambio sobre dicha tabla.

        Args:
            ddl_file: path del fichero DDL de la tabla Oracle que se quiere versionar
            list_extra_camps: (OPC) lista con definicion de campos sql
            a_sql_date_version: (OPC) senetencia sql que devolverá la fecha de versión. Por defecto 'CURRENT_DATE'
            tipo_scd: (OPC) el tipo de SCD que se quiere crear. Opciones disponibles: SCD4 y SCD4C. Por defecto 'SCD4' (Slowly changing dimension 4). El tipo SCD4C añade a la tabla de versiones compound triggers de Oracle para mantener integridad fechas sin incurrir en error 'mutating tables'

        Returns:
            path_file_scd (string)
        """

        ok = self._set_parser_ddl_file(ddl_file, list_extra_camps)
        if ok:
            self.sql_date_version = self.default_date_version
            if a_sql_date_version:
                self.sql_date_version = a_sql_date_version

            return self.create_ddl_scd_file(ddl_file, tipo_scd)

    def _set_parser_ddl_file(self, ddl_file, list_extra_camps=None):
        """

        Args:
            ddl_file:
            list_extra_camps:

        Returns:
            ok (boolean)
        """
        self.ddl_parser = None
        ok = False

        try:
            with open(ddl_file, encoding='utf8') as a_file:
                a_sql_text = a_file.read()

            self.ddl_parser = xDdlParser(a_sql_text)

            if list_extra_camps is not None:
                for extra_def_camp in list_extra_camps:
                    self.ddl_parser.add_def_campo(extra_def_camp)

            self._set_dades_taula()

            ok = True
        except NameError:
            print("El fichero '" + ddl_file + "' no tiene sentencia 'CREATE TABLE'")

        return ok

    def _set_dades_taula(self):
        """
        Asigna datos de la tabla
        """
        self.nom_taula = self.format_nom_ddl(self.ddl_parser.nom_tab)

        # Per si hi ha algun camp que és diu igual que els camps de DATA_INI i FI
        self.ddl_parser.stmnt_grup_def_camps.substitute_val(self.nom_datini, self.nom_datini + "_BASE")
        self.ddl_parser.stmnt_grup_def_camps.substitute_val(self.nom_datfi, self.nom_datfi + "_BASE")

        self.def_camps_taula = {}
        for nom_camp, elem_camp in self.ddl_parser.iter_elems_def_camp:
            def_camp = elem_camp.format_val
            vals_def_camp = def_camp.split(' ')
            self.def_camps_taula[self.format_nom_ddl(nom_camp)] = " ".join(vals_def_camp[1:])

        self.nom_camps_clau = self.ddl_parser.list_key_camps

    def create_ddl_scd_file(self, ddl_file, tipo_scd):
        """
        Crear fichero DDL SCD según tipo

        Args:
            ddl_file:
            tipo_scd:

        Returns:
            ddl_file_scd (string): path file SCD
        """
        parts_file = os.path.splitext(os.path.basename(ddl_file))
        dir_ver = os.path.join(os.path.dirname(ddl_file), "ddls_" + tipo_scd)
        ddl_file_ver = os.path.join(dir_ver, parts_file[0] + "_VE" + parts_file[1])

        if not os.path.exists(dir_ver):
            os.makedirs(dir_ver)

        mode_io = "w"
        if not os.path.exists(ddl_file_ver):
            mode_io = "x"

        with open(ddl_file_ver, mode_io, encoding='utf-8') as a_file:
            a_file.write(self.ddl_parser.as_script_sql)
            a_file.write("\n")
            a_file.write(self.get_ddl_scd(tipo_scd=tipo_scd))

            # Se añade los sql_statements al DDL de la tabla versionada que no hagan referencia a 'ALTER TABLE tab ADD'
            rex_alter_add = re.compile(r"ALTER TABLE [']?" + self.nom_taula + "[']? ADD", re.IGNORECASE)
            rex_nom_tab_ve = re.compile(r"[\w'\"]*" + self.nom_taula_vers + r"[\w'\"]*", re.IGNORECASE)
            for a_stmnt in self.ddl_parser.others_apb_statements():
                if rex_alter_add.match(a_stmnt.format_val):
                    continue

                a_elem_pos_stmnt = a_stmnt.get_elem_match_val(rex_ini_pal + self.nom_taula + rex_fin_pal)
                if a_elem_pos_stmnt:
                    a_elem_pos_stmnt.elem.substitute_val(self.nom_taula, self.nom_taula_vers)

                id_stmnt = a_stmnt.id_principal
                if id_stmnt is not None and not rex_nom_tab_ve.match(id_stmnt):
                    a_stmnt.substitute_val(id_stmnt,
                                           self.get_nom_obj_sql(id_stmnt, sufix=self.sufix_taula_vers))

                a_file.write("\n\n")
                a_file.write(a_stmnt.format_val)
                a_file.write("\n")
                a_file.write("/")
                a_file.write("\n")

        return ddl_file_ver

    def get_ddl_tmpl(self, tipo_scd=SCD4):
        """
        Retorna template a usar según tipo_scd

        Args:
            tipo_scd:

        Returns:
            template_scd (string): path del template a utilizar
        """
        a_template_scd = ""
        tipo_scd = tipo_scd.upper()

        if tipo_scd == self.SCD4c:
            with open(os.path.join(os.path.dirname(__file__), self.templates_tipo[self.SCD4]),
                      encoding='utf8') as a_file:
                a_template_scd += a_file.read()
                a_template_scd += "\n"

        with open(os.path.join(os.path.dirname(__file__), self.templates_tipo[tipo_scd]),
                  encoding='utf8') as a_file:
            a_template_scd += a_file.read()

        return a_template_scd

    def get_ddl_scd(self, tipo_scd=SCD4):
        """
        Retorna ddl SCD base
        Args:
            tipo_scd:

        Returns:
            a_ddl_scd (string): path ddl scd base
        """
        a_ddl_scd = self.get_ddl_tmpl(tipo_scd).format(self=self)

        return a_ddl_scd

    def add_property_func(self, nom_prop, a_func):
        """
        Añade funcion a self.__class__ para poder usar templates personalizados

        Args:
            nom_prop:
            a_func:
        """
        setattr(self.__class__, nom_prop, property(a_func))

    @staticmethod
    def format_nom_ddl(nom_ddl):
        """
        Para cualquier string que reciba como nombre de elemento en DDL lo formatea a mayúsculas y sin "
        Args:
            nom_ddl:

        Returns:
            string
        """
        #
        return nom_ddl.strip().replace('"', '').upper()

    def clau_as_def_params_func(self, prefix_param_templ=prefix_val_param, def_param=False):
        """
        Retorna clave tabla como parametros de funcion de PL/SQL
        Args:
            prefix_param_templ:
            def_param:

        Returns:
            string
        """
        sufix_param_templ = ""
        if def_param:
            sufix_param_templ = " " + self.nom_taula_vers + ".{nom_camp_clau}%TYPE"

        param_templ = prefix_param_templ + "{nom_camp_clau}" + sufix_param_templ
        claus_as_params = []
        for nom_camp in self.nom_camps_clau:
            claus_as_params.append(param_templ.format(nom_camp_clau=nom_camp))

        return ", ".join(claus_as_params)

    def sql_query_eq_clau(self, prefix_param=prefix_val_param):
        """
        Retorna clave tabla como query SQL
        Args:
            prefix_param:

        Returns:
            string
        """
        prefix_param_templ = ""
        if prefix_param is not None:
            prefix_param_templ = prefix_param

        query_eq_clau_templ = self.nom_taula_vers + ".{nom_clau} = " + prefix_param_templ + "{nom_clau}"
        list_query_claus = []
        for nom_camp in self.nom_camps_clau:
            list_query_claus.append(query_eq_clau_templ.format(nom_clau=nom_camp))

        return " AND ".join(list_query_claus)

    def def_set_camps_clau(self,
                           oper_set="=",
                           sep_set_camp=", ",
                           prefix_camp="",
                           prefix_val=""):
        """
        Retorna SQL para hacer SET de valores de los campos clave
        Args:
            oper_set:
            sep_set_camp:
            prefix_camp:
            prefix_val:

        Returns:
            string
        """
        if len(prefix_camp) != 0:
            prefix_camp += "."
        if len(prefix_val) != 0:
            prefix_val += "."

        set_camp_templ = prefix_camp + "{nom_camp} " + oper_set + " " + prefix_val + "{nom_camp}"

        list_set_camps = []
        for a_nom_camp in self.nom_camps_clau:
            list_set_camps.append(set_camp_templ.format(nom_camp=a_nom_camp))

        return sep_set_camp.join(list_set_camps)

    def def_set_camps_taula(self,
                            oper_set="=",
                            sep_set_camp=", ",
                            prefix_camp="",
                            prefix_val="",
                            set_camps_clau=False):
        """
        Retorna SQL para hacer SET de los valores de los campos
        Args:
            oper_set:
            sep_set_camp:
            prefix_camp:
            prefix_val:
            set_camps_clau:

        Returns:
            string
        """
        if len(prefix_camp) != 0:
            prefix_camp += "."
        if len(prefix_val) != 0:
            prefix_val += "."

        set_camp_templ = prefix_camp + "{nom_camp} " + oper_set + " " + prefix_val + "{nom_camp}"

        list_set_camps = []
        for a_nom_camp in self.def_camps_taula.keys():
            if not set_camps_clau and a_nom_camp in self.nom_camps_clau:
                continue

            list_set_camps.append(set_camp_templ.format(nom_camp=a_nom_camp))

        return sep_set_camp.join(list_set_camps)

    def get_nom_obj_sql(self, nom_base, prefix="", sufix=""):
        """
        Devuelve nombre objecto SQL con prefijo y sufijo ajustado a la longitud máxima de nombres en PL/SQL
        Args:
            nom_base:
            prefix:
            sufix:

        Returns:
            string
        """
        return SqlParser.get_nom_obj_sql(nom_base, prefix, sufix)

    @property
    def date_version(self):
        return self.sql_date_version

    def camps_clau(self):
        for nom_camp in self.nom_camps_clau:
            yield "{} {}".format(nom_camp, self.def_camps_taula.get(nom_camp))

    @property
    def def_camps_clau(self):
        return ", ".join(self.camps_clau())

    def camps_dades(self):
        for nom_camp in sorted(self.def_camps_taula):
            if nom_camp not in self.nom_camps_clau:
                yield "{} {}".format(nom_camp, self.def_camps_taula.get(nom_camp))

    @property
    def def_camps_dades(self):
        return ", ".join(self.camps_dades())

    @property
    def alter_camps_dades_taula_orig(self):
        return "\n".join(["ALTER TABLE {nom_taula} ADD ({def_col});".format(nom_taula=self.nom_taula,
                                                                            def_col=def_col)
                          for def_col in self.camps_dades()])

    @property
    def alter_camps_dades_taula_vers(self):
        return "\n".join(["ALTER TABLE {nom_taula} ADD ({def_col});".format(nom_taula=self.nom_taula_vers,
                                                                            def_col=def_col)
                          for def_col in self.camps_dades()])

    @property
    def str_camps_clau(self):
        return ", ".join(self.nom_camps_clau)

    @property
    def primer_camp_clau(self):
        return self.nom_camps_clau[0]

    @property
    def nom_taula_vers(self):
        return self.get_nom_obj_sql(self.nom_taula, sufix=self.sufix_taula_vers)

    @property
    def nom_seq_vers(self):
        return self.get_nom_obj_sql(self.nom_taula, sufix=self.sufix_taula_vers + self.sufix_seq)

    @property
    def def_cursor_prev_date_reg_vers(self):
        def_curs_templ = "({params_clau}, A_DAT_VER DATE) IS " \
                         "SELECT * FROM " + self.nom_taula_vers + \
                         " WHERE {query_clau} AND " + \
                         self.nom_taula_vers + "." + self.nom_datini + \
                         " <= A_DAT_VER ORDER BY " + self.nom_datini + " DESC"

        return def_curs_templ.format(params_clau=self.clau_as_def_params_func(def_param=True),
                                     query_clau=self.sql_query_eq_clau())

    @property
    def def_cursor_actual_reg_vers(self):
        def_curs_templ = "({params_clau}) IS " \
                         "SELECT * FROM " + self.nom_taula_vers + \
                         " WHERE {query_clau} AND " + \
                         self.nom_taula_vers + "." + self.nom_datfi + \
                         " IS NULL ORDER BY " + self.nom_datini + " DESC"

        return def_curs_templ.format(params_clau=self.clau_as_def_params_func(def_param=True),
                                     query_clau=self.sql_query_eq_clau())

    @property
    def params_cursor_clau_reg_new(self):
        return self.clau_as_def_params_func(prefix_param_templ=":NEW.")

    @property
    def params_cursor_clau_reg_old(self):
        return self.clau_as_def_params_func(prefix_param_templ=":OLD.")

    @property
    def sql_query_eq_clau_for_regaux(self):
        return self.sql_query_eq_clau(prefix_param=(self.nom_regaux_vers + "."))

    @property
    def sql_query_eq_clau_for_new_reg(self):
        return self.sql_query_eq_clau(prefix_param=":NEW.")

    @property
    def sql_query_eq_clau_for_prev_reg(self):
        return self.sql_query_eq_clau(prefix_param=(self.nom_prev_reg_vers + "."))

    @property
    def sql_query_eq_clau_for_old_reg(self):
        return self.sql_query_eq_clau(prefix_param=(self.nom_old_reg_vers + "."))

    @property
    def set_camps_new_reg_ver(self):
        return self.def_set_camps_taula(oper_set=":=",
                                        sep_set_camp=";\n",
                                        prefix_camp=self.nom_new_reg_vers,
                                        prefix_val=":NEW",
                                        set_camps_clau=True)

    @property
    def set_camps_update_reg_ver(self):
        return self.def_set_camps_taula(prefix_val=":NEW")

    @property
    def nom_trigger_del_tab_base(self):
        return self.get_nom_obj_sql(self.nom_taula,
                                    self.prefix_delete_trigger,
                                    self.sufix_trigger)

    @property
    def nom_trigger_ins_upd_tab_base(self):
        return self.get_nom_obj_sql(self.nom_taula,
                                    self.prefix_ins_upd_trigger,
                                    self.sufix_trigger)

    @property
    def nom_trigger_del_tab_vers(self):
        return self.get_nom_obj_sql(self.nom_taula,
                                    self.prefix_delete_trigger,
                                    self.sufix_taula_vers + self.sufix_trigger)

    @property
    def nom_trigger_ins_tab_vers(self):
        return self.get_nom_obj_sql(self.nom_taula,
                                    self.prefix_insert_trigger,
                                    self.sufix_taula_vers + self.sufix_trigger)

    @property
    def nom_trigger_upd_tab_vers(self):
        return self.get_nom_obj_sql(self.nom_taula,
                                    self.prefix_update_trigger,
                                    self.sufix_taula_vers + self.sufix_trigger)

    @property
    def nom_constraint_chk_vers(self):
        return self.get_nom_obj_sql(self.nom_taula,
                                    sufix=self.sufix_check_constraint)

    @property
    def nom_var_prev_reg_vers(self):
        return self.nom_prev_reg_vers

    @property
    def nom_var_new_reg_vers(self):
        return self.nom_new_reg_vers

    @property
    def nom_var_regaux_vers(self):
        return self.nom_regaux_vers

    @property
    def set_camps_clau_regaux_from_new(self):
        return self.def_set_camps_clau(oper_set=":=",
                                       sep_set_camp=";",
                                       prefix_camp=self.nom_regaux_vers,
                                       prefix_val=":NEW")

    @property
    def set_camps_clau_regaux_from_old(self):
        return self.def_set_camps_clau(oper_set=":=",
                                       sep_set_camp=";",
                                       prefix_camp=self.nom_regaux_vers,
                                       prefix_val=":OLD")

    @property
    def nom_var_old_reg_vers(self):
        return self.nom_old_reg_vers

    @property
    def set_camps_oldreg_from_old(self):
        return self.def_set_camps_taula(oper_set=":=",
                                        sep_set_camp=";\n",
                                        prefix_camp=self.nom_old_reg_vers,
                                        prefix_val=":OLD",
                                        set_camps_clau=True)

    @property
    def nom_datini(self):
        return "DAT_INI_VER"

    @property
    def nom_datfi(self):
        return "DAT_FI_VER"

    @property
    def nom_idx_datini(self):
        return self.get_nom_obj_sql(self.nom_taula, self.prefix_index, self.sufix_taula_vers + "_" + self.nom_datini)

    @property
    def nom_idx_datfi(self):
        return self.get_nom_obj_sql(self.nom_taula, self.prefix_index, self.sufix_taula_vers + "_" + self.nom_datfi)

    @property
    def nom_taula_vers_pk(self):
        return self.get_nom_obj_sql(self.nom_taula, self.prefix_primary_key, self.sufix_taula_vers)

    @property
    def idx_nom_taula_vers_pk_datini(self):
        return self.get_nom_obj_sql(self.nom_taula, "PKDAT_", self.sufix_taula_vers + self.sufix_unic)

    @property
    def nom_taula_vers_datini_chk(self):
        return self.get_nom_obj_sql(self.nom_taula, "DAT_", self.sufix_taula_vers + self.sufix_check_constraint)

    def get_triggers_extra_tab_base(self):
        """
        (SUBCLASEAR) Retorna lista strings con las definiciones de triggers extra a incluir
        """
        return []

    @property
    def triggers_extra_tab_base(self):
        str_ret = ""
        l_trgs = self.get_triggers_extra_tab_base()
        if l_trgs:
            str_ret = "{a_sql}".format(a_sql="\n".join(l_trgs))

        return str_ret

    def get_follows_trigger_ins_upd_tab_base(self):
        """
        (SUBCLASEAR) Retorna lista de strings con los nombres de triggers que precederán al trigger de la tabla
        base que se encargará del versionado (el del nombre dado por property 'self.nom_nom_trigger_ins_upd_tab_base')
        """
        return []

    @property
    def follows_trigger_ins_upd_tab_base(self):
        str_ret = ""
        l_trgs = self.get_follows_trigger_ins_upd_tab_base()
        if l_trgs:
            str_ret = "\nFOLLOWS {a_sql}".format(a_sql=", ".join(l_trgs))

        return str_ret


if __name__ == '__main__':
    a_eng = ApbDdlToScd()

    import fire
    path_scd = fire.Fire(a_eng.convert_ddl_file_to_scd)

    ret = 1
    if path_scd:
        print("Fichero '{path_scd}' creado con éxito".format(path_scd=path_scd))
        ret = 0

    sys.exit(ret)

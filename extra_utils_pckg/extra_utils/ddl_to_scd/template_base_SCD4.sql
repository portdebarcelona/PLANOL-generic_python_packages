/* MODEL TABLA VERSIONADA TIPO SCD4 */

/* ALTER TABLE ORIGINAL DE LAS COLUMNAS DE DATOS */
{self.alter_camps_dades_taula_orig}
/

/* MODIFICACION TABLA ORIGINAL */
alter table {self.nom_taula} add (VERSIONAR VARCHAR2(1 CHAR));
alter table {self.nom_taula} add CONSTRAINT "{self.nom_constraint_chk_vers}" CHECK (UPPER(VERSIONAR) IN (NULL, 'S', 'N')) ENABLE;
/

/* CREACION TABLA VERSIONES DE LA ORIGINAL */
CREATE TABLE {self.nom_taula_vers}
({self.def_camps_clau},
SEQVER NUMBER(10,0) NOT NULL ENABLE,
{self.nom_datini} DATE NOT NULL ENABLE,
{self.nom_datfi} DATE,
{self.def_camps_dades},
OBSERVS VARCHAR2(200 CHAR),
DAT_ALTA DATE,
DAT_MODIF DATE,
DAT_BAJA DATE,
CONSTRAINT {self.nom_taula_vers_pk} PRIMARY KEY ({self.str_camps_clau}, SEQVER)  ENABLE,
CONSTRAINT {self.idx_nom_taula_vers_pk_datini} UNIQUE ({self.str_camps_clau}, {self.nom_datini})  ENABLE,
CONSTRAINT {self.nom_taula_vers_datini_chk} CHECK ({self.nom_datini} <= NVL({self.nom_datfi}, {self.nom_datini})) ENABLE );
/

/* ALTER TABLE VERSIONADA DE LAS COLUMNAS DE DATOS */
{self.alter_camps_dades_taula_vers}
/

CREATE INDEX {self.nom_idx_datini} ON {self.nom_taula_vers} ({self.nom_datini});
CREATE INDEX {self.nom_idx_datfi} ON {self.nom_taula_vers} ({self.nom_datfi});
/

COMMENT ON COLUMN {self.nom_taula_vers}.SEQVER IS 'Secuencia de la version por cada entidad';
COMMENT ON COLUMN {self.nom_taula_vers}.{self.nom_datini} IS 'Fecha inicio vigencia para filtros historicos';
COMMENT ON COLUMN {self.nom_taula_vers}.{self.nom_datfi} IS 'Fecha final vigencia para filtros historicos';
COMMENT ON COLUMN {self.nom_taula_vers}.DAT_MODIF IS 'Fecha modificacion registro versión';
COMMENT ON COLUMN {self.nom_taula_vers}.DAT_BAJA IS 'Fecha baja del registro version = fecha en la que se informa la {self.nom_datfi}';
COMMENT ON COLUMN {self.nom_taula_vers}.DAT_ALTA IS 'Fecha creación del registro versión de una entidad';
/

/* SECUENCIAS */
CREATE SEQUENCE "{self.nom_seq_vers}" INCREMENT BY 1 MAXVALUE 999999999 MINVALUE 1;
/

/* TRIGGERS TABLA ORIGINAL */
{self.triggers_extra_tab_base}

create or replace TRIGGER {self.nom_trigger_ins_upd_tab_base}
BEFORE INSERT OR UPDATE ON {self.nom_taula}
    FOR EACH ROW {self.follows_trigger_ins_upd_tab_base}
DECLARE
    {self.nom_var_new_reg_vers}       {self.nom_taula_vers}%ROWTYPE;
    {self.nom_var_prev_reg_vers}      {self.nom_taula_vers}%ROWTYPE;
    NOVA_DAT_VERS         DATE;
    PREV_{self.nom_datini}      DATE;
    NOVA_VERSIO           BOOLEAN := TRUE;
    CURSOR C1 {self.def_cursor_prev_date_reg_vers};
BEGIN
    NOVA_DAT_VERS := {self.date_version};

    /* SE VERIFICA QUE EXISTA YA ALGUNA VERSIÓN DEL REG */
    OPEN C1({self.params_cursor_clau_reg_new}, NOVA_DAT_VERS);
    FETCH C1 INTO {self.nom_var_prev_reg_vers};
    CLOSE C1;

    IF UPPER(:NEW.VERSIONAR) = 'N' THEN
        NOVA_VERSIO := FALSE;
    END IF;

    /* Se vuelve a dejar siempre a NULL */
    :NEW.VERSIONAR := NULL;

    /* SI HAY VERSIONES POSTERIORES SE BORRAN PORQUE ESTA ES LA VIGENTE */
    DELETE FROM {self.nom_taula_vers}
    WHERE {self.sql_query_eq_clau_for_new_reg} AND
    {self.nom_taula_vers}.{self.nom_datini} > NOVA_DAT_VERS;

    IF  {self.nom_var_prev_reg_vers}.{self.primer_camp_clau} IS NULL OR
    (NOVA_VERSIO AND {self.nom_var_prev_reg_vers}.{self.nom_datini} <> NOVA_DAT_VERS) THEN
        /* SE CREA NUEVO REGISTRO EN TABLA DE VERSIONES */
        {self.nom_var_new_reg_vers}.{self.nom_datini}   := NOVA_DAT_VERS;
        SELECT {self.nom_seq_vers}.NEXTVAL INTO {self.nom_var_new_reg_vers}.SEQVER FROM DUAL;
        {self.nom_var_new_reg_vers}.DAT_ALTA      := CURRENT_DATE;
        {self.set_camps_new_reg_ver};

        /* SE ACTUALIZA LA FECHA FINAL DE LA VERSION ANTERIOR SI ESTA EXISTE */
        IF {self.nom_var_prev_reg_vers}.{self.primer_camp_clau} IS NOT NULL THEN
            UPDATE {self.nom_taula_vers}
                SET {self.nom_datfi} = TRUNC(NOVA_DAT_VERS - 1),
                DAT_MODIF = CURRENT_DATE
            WHERE {self.sql_query_eq_clau_for_prev_reg} AND
                {self.nom_taula_vers}.SEQVER = {self.nom_var_prev_reg_vers}.SEQVER;
        END IF;

        INSERT INTO {self.nom_taula_vers} VALUES {self.nom_var_new_reg_vers};

        /* SIEMPRE SE ACTUALIZA EL REG. CREADO PARA QUE VUELVA CALCULAR TRIGGERS DE UPDATE */
        UPDATE {self.nom_taula_vers} SET OBSERVS = NULL
        WHERE {self.sql_query_eq_clau_for_new_reg} AND
            {self.nom_taula_vers}.SEQVER = {self.nom_var_new_reg_vers}.SEQVER;

    ELSIF {self.nom_var_prev_reg_vers}.{self.primer_camp_clau} IS NOT NULL THEN
        /* SE ACTUALIZA LA ULTIMA VERSION */
        UPDATE {self.nom_taula_vers} SET
            {self.nom_datfi} = NULL,
            DAT_MODIF  = CURRENT_DATE,
            {self.set_camps_update_reg_ver}
        WHERE {self.sql_query_eq_clau_for_prev_reg} AND {self.nom_taula_vers}.SEQVER = {self.nom_var_prev_reg_vers}.SEQVER;
    END IF;
END;
/

create or replace TRIGGER {self.nom_trigger_del_tab_base}
AFTER DELETE ON {self.nom_taula}
FOR EACH ROW
DECLARE
    {self.nom_var_prev_reg_vers}         {self.nom_taula_vers}%ROWTYPE;
    CURSOR C1 {self.def_cursor_actual_reg_vers};
BEGIN
    OPEN C1({self.params_cursor_clau_reg_old});
    FETCH C1 INTO {self.nom_var_prev_reg_vers};
    CLOSE C1;

    /* SE CIERRA LA ULTIMA VERSION */
    IF {self.nom_var_prev_reg_vers}.{self.primer_camp_clau} IS NOT NULL THEN
        UPDATE {self.nom_taula_vers} SET
            {self.nom_datfi} = {self.date_version},
            DAT_BAJA = CURRENT_DATE
        WHERE {self.sql_query_eq_clau_for_prev_reg} AND
        {self.nom_taula_vers}.SEQVER = {self.nom_var_prev_reg_vers}.SEQVER;
    END IF;
END;
/
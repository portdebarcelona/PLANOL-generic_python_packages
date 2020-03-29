/* MODEL TABLA VERSIONADA TIPO SCD4C (Oracle Compound Triggers) */

/* TRIGGERS TABLA VERSIONADA */

create or replace TRIGGER {self.nom_trigger_ins_tab_vers}
FOR INSERT ON {self.nom_taula_vers}
COMPOUND TRIGGER
    {self.nom_var_regaux_vers}       {self.nom_taula_vers}%ROWTYPE;
    NEW_SEQVER            NUMBER;
    NEW_{self.nom_datini}       DATE;
    NEW_{self.nom_datfi}        DATE;
    NEXT_{self.nom_datini}      DATE;
    PREV_{self.nom_datini}      DATE;
BEFORE EACH ROW IS
BEGIN
    IF :NEW.{self.nom_datini} IS NULL THEN
        :NEW.{self.nom_datini} := {self.date_version};
    END IF;
    IF :NEW.SEQVER IS NULL THEN
        SELECT {self.nom_seq_vers}.NEXTVAL INTO :NEW.SEQVER FROM DUAL;
    END IF;

    {self.set_camps_clau_regaux_from_new};
    NEW_SEQVER          := :NEW.SEQVER;
    NEW_{self.nom_datini}     := :NEW.{self.nom_datini};
    NEW_{self.nom_datfi}      := :NEW.{self.nom_datfi};
    :NEW.DAT_ALTA       := CURRENT_DATE;
END BEFORE EACH ROW;

AFTER STATEMENT IS
BEGIN
    /* SE CALCULA LA FECHA FINAL DE LA VERSION INSERTADA SI HAY VERSIONES POSTERIORES */
    SELECT MIN({self.nom_datini}) INTO NEXT_{self.nom_datini} FROM {self.nom_taula_vers}
    WHERE {self.sql_query_eq_clau_for_regaux} AND {self.nom_datini} > NEW_{self.nom_datini};

    IF NEXT_{self.nom_datini} IS NOT NULL THEN
        NEW_{self.nom_datfi} := NEXT_{self.nom_datini} - 1;
    END IF;

    /* SIEMPRE SE ACTUALIZA EL REG. CREADO PARA APLIQUE TRIGGERS de UPDATE */
    UPDATE {self.nom_taula_vers} SET {self.nom_datfi} = NEW_{self.nom_datfi}
    WHERE {self.sql_query_eq_clau_for_regaux} AND SEQVER = NEW_SEQVER;

    /* SE CALCULA LA FECHA FINAL DE LA VERSION ANTERIOR SI ESTA EXISTE */
    SELECT MAX({self.nom_datini}) INTO PREV_{self.nom_datini} FROM {self.nom_taula_vers}
    WHERE {self.sql_query_eq_clau_for_regaux} AND {self.nom_datini} < NEW_{self.nom_datini};

    IF PREV_{self.nom_datini} IS NOT NULL THEN
        UPDATE {self.nom_taula_vers} SET {self.nom_datfi} = NEW_{self.nom_datini} - 1
        WHERE {self.sql_query_eq_clau_for_regaux} AND {self.nom_datini} = PREV_{self.nom_datini};
    END IF;
END AFTER STATEMENT;
END;
/

create or replace TRIGGER {self.nom_trigger_upd_tab_vers}
FOR UPDATE ON {self.nom_taula_vers}
COMPOUND TRIGGER
    {self.nom_old_reg_vers}         {self.nom_taula_vers}%ROWTYPE;
    {self.nom_var_regaux_vers}      {self.nom_taula_vers}%ROWTYPE;
    SQL_INS               VARCHAR(4000);
    PREV_{self.nom_datini}      DATE;
    PREV_{self.nom_datfi}       DATE;

BEFORE EACH ROW IS
BEGIN
    IF :NEW.{self.nom_datini} IS NULL THEN
        :NEW.{self.nom_datini} := {self.date_version};
    END IF;

    IF :NEW.{self.nom_datini} < :OLD.{self.nom_datini} THEN
        RAISE_APPLICATION_ERROR(-20444,
            'ERROR AL ACTUALITZAR! - NO ES POT POSAR UNA DATA INFERIOR');
    END IF;

    IF :OLD.{self.nom_datini} <> :NEW.{self.nom_datini} THEN
        /* SE VERSIONARÁ REGISTRO SI SE HA MODIFICADO LA FECHA DE INICIO, ES LA
        VERSION ACTUAL Y NO VIENE INFORMADA LA FECHA DE CIERRE */
        IF :OLD.{self.nom_datfi} IS NULL AND :NEW.{self.nom_datfi} IS NULL THEN
            {self.nom_old_reg_vers}.{self.nom_datini}   := :OLD.{self.nom_datini};
            {self.nom_old_reg_vers}.OBSERVS       := :OLD.OBSERVS;
            {self.nom_old_reg_vers}.DAT_ALTA      := :OLD.DAT_ALTA;
            {self.nom_old_reg_vers}.DAT_MODIF     := :OLD.DAT_MODIF;
            {self.nom_old_reg_vers}.DAT_BAJA      := :OLD.DAT_BAJA;
            {self.set_camps_oldreg_from_old};

            SELECT {self.nom_seq_vers}.NEXTVAL INTO {self.nom_old_reg_vers}.SEQVER FROM DUAL;

            {self.nom_old_reg_vers}.{self.nom_datfi}   := :NEW.{self.nom_datini} - 1;
        ELSE
            /* EN CASO DE QUE SE MODIFIQUE FECHA INI DE VERSION NO ACTUAL SOLO SE
            MANTIENE COHERENCIA DE FECHAS CON VERSION PREVIA */
            {self.set_camps_clau_regaux_from_old};
            PREV_{self.nom_datfi} := :NEW.{self.nom_datini} - 1;
        END IF;
    ELSE
        IF :NEW.{self.nom_datfi} IS NOT NULL THEN
            :NEW.DAT_BAJA         := CURRENT_DATE;
        ELSE
            /* SE INFORMA FECHA DE ACTUALIZACIÓN */
            :NEW.DAT_MODIF        := CURRENT_DATE;
        END IF;
    END IF;
END BEFORE EACH ROW;

AFTER STATEMENT IS
BEGIN
    /* SE INSERTA VERSION NUEVA CON LOS DATOS ANTIGUOS */
    IF {self.nom_old_reg_vers}.{self.primer_camp_clau} IS NOT NULL THEN
        INSERT INTO {self.nom_taula_vers} VALUES {self.nom_old_reg_vers};

    ELSIF PREV_{self.nom_datfi} IS NOT NULL THEN
        SELECT MAX({self.nom_datini}) INTO PREV_{self.nom_datini} FROM {self.nom_taula_vers}
        WHERE {self.sql_query_eq_clau_for_regaux} AND
        {self.nom_datini} <= PREV_{self.nom_datfi};

        IF PREV_{self.nom_datini} IS NOT NULL THEN
            UPDATE {self.nom_taula_vers} SET {self.nom_datfi} = PREV_{self.nom_datfi}
            WHERE {self.sql_query_eq_clau_for_regaux} AND {self.nom_datini} = PREV_{self.nom_datini};
        END IF;
    END IF;
END AFTER STATEMENT;
END;
/

create or replace TRIGGER {self.nom_trigger_del_tab_vers}
FOR DELETE ON {self.nom_taula_vers}
COMPOUND TRIGGER
    PREV_{self.nom_datini}     DATE;
    REG_{self.nom_datini}      DATE;
    REG_{self.nom_datfi}       DATE;
    {self.nom_var_regaux_vers}      {self.nom_taula_vers}%ROWTYPE;

BEFORE EACH ROW IS
BEGIN
    {self.set_camps_clau_regaux_from_old};
    REG_{self.nom_datfi}   := :OLD.{self.nom_datfi};
    REG_{self.nom_datini}  := :OLD.{self.nom_datini};
END BEFORE EACH ROW;

AFTER STATEMENT IS
BEGIN
    SELECT MAX({self.nom_datini}) INTO PREV_{self.nom_datini} FROM {self.nom_taula_vers}
    WHERE {self.sql_query_eq_clau_for_regaux} AND
    {self.nom_datini} <= REG_{self.nom_datini};

    IF PREV_{self.nom_datini} IS NOT NULL THEN
        UPDATE {self.nom_taula_vers} SET {self.nom_datfi} = REG_{self.nom_datfi}
        WHERE {self.sql_query_eq_clau_for_regaux} AND {self.nom_datini} = PREV_{self.nom_datini};
    END IF;
END AFTER STATEMENT;
END;
/
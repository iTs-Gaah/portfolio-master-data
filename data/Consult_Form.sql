SELECT
    "ID",
    "VERSAO",
    "CRIACAO FORM",
    "EDICAO FORM",
    "DESC CC",
    "C CUSTO",
    "SECAO",
    "NOME FORM",
    "ENCARREGADO",
    "ENGENHEIRO",
    "RH LOCAL",
    "SUPERINTENDENTE",
    "DIRETOR",
    "CONT MANUT",
    "GRUPO USUARIOS"
FROM (
    SELECT 
        documentid AS "ID",
        version AS "VERSAO",
        data_create_form AS "CRIACAO FORM",
        data_edit_form AS "EDICAO FORM",
        descriForm AS "NOME FORM",
        TRIM(S0_txt_ccusto) AS "C CUSTO",
        S0_txt_cod AS "SECAO",
        S0_txt_desc AS "DESC CC",
        S0_txt_enca AS "ENCARREGADO",
        S0_txt_eng AS "ENGENHEIRO",
        S0_txt_rh AS "RH LOCAL",
        S0_txt_cordeng AS "SUPERINTENDENTE",
        S0_txt_dire AS "DIRETOR",
        S0_txt_controlador AS "CONT MANUT",
        S0_txt_grupo_user AS "GRUPO USUARIOS",
        ROW_NUMBER() OVER (
            PARTITION BY documentid
            ORDER BY version::integer DESC
        ) AS rn
    FROM datalake_fluig_bronze.ml001010
    WHERE documentid::integer > 55799
    AND documentid::integer != 55922
) t
WHERE rn = 1;
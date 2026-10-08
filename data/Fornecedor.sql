SELECT
    SA2.EMPRESA,
    A2_FILIAL,
    A2_COD,
    A2_LOJA,
    A2_CGC,
    A2_NOME,
    A2_TIPO,
    A2_CNAE,
    A2_INSCR,
    A2_INSCRM,
    A2_EMAIL,
    A2_DDD,
    A2_TEL,
    A2_FAX,
    A2_BANCO,
    A6_NREDUZ,
    A2_AGENCIA,
    A2_DVAGE,
    A2_NUMCON,
    A2_DVCTA,
    A2_FORMPAG,
    A2_REPRCGC,
    A2_NOMRESP,
    A2_PJ,
    A2_MSBLQL,
    A2_END,
    A2_CEP,
    A2_BAIRRO,
    A2_MUN,
    A2_EST,
    A2_CODANP,
    A2_AUTSPED
FROM datalake_protheus_silver.sa2_cadastro_fornecedor AS SA2
LEFT JOIN (
    SELECT 
        a6_cod AS A6_COD,
        MAX(TRIM(a6_nreduz)) AS A6_NREDUZ
    FROM datalake_protheus_silver.sa6_cadastro_bancario
    WHERE d_e_l_e_t_ <> '*' OR d_e_l_e_t_ IS NULL
    GROUP BY a6_cod
) AS SA6
    ON SA2.a2_banco = SA6.A6_COD
WHERE (SA2.d_e_l_e_t_ <> '*' OR SA2.d_e_l_e_t_ IS NULL)
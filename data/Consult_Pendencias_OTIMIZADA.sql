-- =============================================================================
-- PROPOSTA OTIMIZADA de Consult_Pendencias.sql
-- =============================================================================
-- IDEIA PRINCIPAL:
--   1) Filtrar a tabela CTT (cadastro pequeno de centros de custo) UMA vez,
--      em um CTE, deixando só os CC "problema" (bloqueado / fim de exercício).
--      Assim o STR_TO_DATE roda ~1x por centro de custo, e NÃO 1x por linha de
--      item (milhões de linhas em SC1/SC6/SC7/SD1).
--   2) Trocar LEFT JOIN por INNER JOIN. É semanticamente IDÊNTICO aqui, porque
--      o WHERE original exigia colunas da CTT (linhas sem match já eram
--      descartadas). Isso libera o otimizador a usar a CTT pequena como filtro.
--
-- VALIDAÇÃO: rode esta query e a original e compare a contagem de linhas /
-- alguns totais antes de substituir. O resultado deve ser igual.
-- =============================================================================

WITH ctt_inativo AS (
    SELECT
        CTT_FILIAL,
        CTT_CUSTO,
        CTT_DESC01,
        CTT_BLOQ,
        CTT_DTEXSF,
        CASE
            WHEN CTT_BLOQ = '1' THEN 'Bloqueado'
            WHEN TRIM(CTT_DTEXSF) <> ''
             AND STR_TO_DATE(CTT_DTEXSF, '%Y%m%d') < CURDATE() THEN 'Fim de Exercício'
        END AS MOTIVO_INATIVO
    FROM CTT_CADASTRO_CENTRO_CUSTO
    WHERE CTT_BLOQ = '1'
       OR (TRIM(CTT_DTEXSF) <> ''
           AND STR_TO_DATE(CTT_DTEXSF, '%Y%m%d') < CURDATE())
)

SELECT
    'Pedido de Venda (SC6)' AS ORIGEM_DOC,
    SC6.C6_FILIAL AS FILIAL,
    SC6.C6_NUM AS NUMERO,
    MAX(SC6.C6_DATFAT) AS EMISSAO,
    SUM(SC6.C6_VALOR) AS TOTAL_DOC,
    CASE WHEN SUM(SC6.C6_QTDENT) > 0 THEN 'Atendido Parcialmente' ELSE 'Aberto' END AS SITUACAO,
    SC6.C6_CC AS CENTRO_CUSTO,
    CTT.CTT_DESC01 AS DESC_CC,
    CTT.CTT_BLOQ AS STATUS_BLOQ,
    CTT.MOTIVO_INATIVO
FROM SC6_ITENS_PEDIDO_VENDA AS SC6
INNER JOIN ctt_inativo AS CTT
    ON TRIM(CTT.CTT_CUSTO) = TRIM(SC6.C6_CC)
   AND TRIM(CTT.CTT_FILIAL) = SUBSTRING(TRIM(SC6.C6_FILIAL), 1, 2)
WHERE SC6.C6_QTDENT < SC6.C6_QTDVEN
  AND SC6.C6_BLQ <> 'R'
GROUP BY
    SC6.C6_FILIAL, SC6.C6_NUM, SC6.C6_CC, CTT.CTT_DESC01, CTT.CTT_BLOQ, CTT.MOTIVO_INATIVO

UNION ALL

SELECT
    'Solicitação de Compra (SC1)' AS ORIGEM_DOC,
    SC1.C1_FILIAL AS FILIAL,
    SC1.C1_NUM AS NUMERO,
    MAX(SC1.C1_EMISSAO) AS EMISSAO,
    SUM(SC1.C1_TOTAL) AS TOTAL_DOC,
    CASE WHEN SUM(SC1.C1_QUJE) > 0 THEN 'Atendido Parcialmente' ELSE 'Aberto' END AS SITUACAO,
    SC1.C1_CC AS CENTRO_CUSTO,
    CTT.CTT_DESC01 AS DESC_CC,
    CTT.CTT_BLOQ AS STATUS_BLOQ,
    CTT.MOTIVO_INATIVO
FROM SC1_SOLICITACAO_COMPRA AS SC1
INNER JOIN ctt_inativo AS CTT
    ON TRIM(SC1.C1_CC) = TRIM(CTT.CTT_CUSTO)
   AND TRIM(CTT.CTT_FILIAL) = SUBSTRING(TRIM(SC1.C1_FILIAL), 1, 2)
WHERE SC1.C1_QUJE < SC1.C1_QUANT
  AND SC1.C1_RESIDUO <> 'S'
GROUP BY
    SC1.C1_FILIAL, SC1.C1_NUM, SC1.C1_CC, CTT.CTT_DESC01, CTT.CTT_BLOQ, CTT.MOTIVO_INATIVO

UNION ALL

SELECT
    'Pedido de Compra (SC7)' AS ORIGEM_DOC,
    SC7.C7_FILIAL AS FILIAL,
    SC7.C7_NUM AS NUMERO,
    MAX(SC7.C7_EMISSAO) AS EMISSAO,
    SUM(SC7.C7_TOTAL) AS TOTAL_DOC,
    CASE
        WHEN SUM(SC7.C7_QTDACLA) > 0 THEN 'Falta Classificar Pré Nota'
        WHEN MAX(SC7.C7_CONAPRO) = 'B' THEN 'Em Aprovação'
        WHEN SUM(SC7.C7_QUJE) > 0 THEN 'Recebido Parcialmente'
        ELSE 'Aguardando lançamento Pré Nota'
    END AS SITUACAO,
    SC7.C7_CC AS CENTRO_CUSTO,
    CTT.CTT_DESC01 AS DESC_CC,
    CTT.CTT_BLOQ AS STATUS_BLOQ,
    CTT.MOTIVO_INATIVO
FROM SC7_PEDIDO_COMPRA AS SC7
INNER JOIN ctt_inativo AS CTT
    ON TRIM(SC7.C7_CC) = TRIM(CTT.CTT_CUSTO)
   AND TRIM(CTT.CTT_FILIAL) = SUBSTRING(TRIM(SC7.C7_FILIAL), 1, 2)
WHERE SC7.C7_EMPRESA LIKE 'EMPRESA_X%'
  AND SC7.C7_QUJE < SC7.C7_QUANT
  AND SC7.C7_RESIDUO <> 'S'
GROUP BY
    SC7.C7_FILIAL, SC7.C7_NUM, SC7.C7_CC, CTT.CTT_DESC01, CTT.CTT_BLOQ, CTT.MOTIVO_INATIVO

UNION ALL

SELECT
    'Pré-Nota de Entrada (SD1)' AS ORIGEM_DOC,
    SD1.D1_FILIAL AS FILIAL,
    SD1.D1_DOC AS NUMERO,
    MAX(SD1.D1_EMISSAO) AS EMISSAO,
    SUM(SD1.D1_TOTAL) AS TOTAL_DOC,
    'Pendente Classificação' AS SITUACAO,
    SD1.D1_CC AS CENTRO_CUSTO,
    CTT.CTT_DESC01 AS DESC_CC,
    CTT.CTT_BLOQ AS STATUS_BLOQ,
    CTT.MOTIVO_INATIVO
FROM SD1_ITENS_NF_ENTRADA AS SD1
INNER JOIN ctt_inativo AS CTT
    ON TRIM(SD1.D1_CC) = TRIM(CTT.CTT_CUSTO)
   AND TRIM(CTT.CTT_FILIAL) = SUBSTRING(TRIM(SD1.D1_FILIAL), 1, 2)
WHERE (SD1.D1_USRCLAS IS NULL OR TRIM(SD1.D1_USRCLAS) = '')
GROUP BY
    SD1.D1_FILIAL, SD1.D1_DOC, SD1.D1_CC, CTT.CTT_DESC01, CTT.CTT_BLOQ, CTT.MOTIVO_INATIVO;

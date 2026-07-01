WITH current_financial_rules (
    region,
    category,
    rule_year,
    rule_key,
    rule_value,
    source_name,
    source_url
) AS (
    VALUES
    (
        'Australia',
        'tax',
        '2025-2026',
        'resident_income_tax_bracket_0_18200',
        $json${"bracket_label":"$0 – $18,200","income_from":0,"income_to":18200,"base_tax":0,"threshold":0,"marginal_rate":0,"formula":"Nil","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia',
        'tax',
        '2025-2026',
        'resident_income_tax_bracket_18201_45000',
        $json${"bracket_label":"$18,201 – $45,000","income_from":18200.01,"income_to":45000,"base_tax":0,"threshold":18200,"marginal_rate":0.16,"formula":"16c for each $1 over $18,200","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia',
        'tax',
        '2025-2026',
        'resident_income_tax_bracket_45001_135000',
        $json${"bracket_label":"$45,001 – $135,000","income_from":45000.01,"income_to":135000,"base_tax":4288,"threshold":45000,"marginal_rate":0.30,"formula":"$4,288 plus 30c for each $1 over $45,000","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia',
        'tax',
        '2025-2026',
        'resident_income_tax_bracket_135001_190000',
        $json${"bracket_label":"$135,001 – $190,000","income_from":135000.01,"income_to":190000,"base_tax":31288,"threshold":135000,"marginal_rate":0.37,"formula":"$31,288 plus 37c for each $1 over $135,000","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia',
        'tax',
        '2025-2026',
        'resident_income_tax_bracket_190001_over',
        $json${"bracket_label":"$190,001 and over","income_from":190000.01,"income_to":null,"base_tax":51638,"threshold":190000,"marginal_rate":0.45,"formula":"$51,638 plus 45c for each $1 over $190,000","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia',
        'superannuation',
        '2025-2026',
        'employer_super_contribution',
        $json${"period":"1 July 2025 – 30 June 2026","general_super_guarantee_percent":12.00,"earnings_basis":"ordinary time earnings","source_last_updated":"2026-04-17"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee'
    ),
    (
        'Australia',
        'superannuation',
        '2026-2027',
        'employer_super_contribution',
        $json${"period":"1 July 2026 – 30 June 2027","general_super_guarantee_percent":12.00,"earnings_basis":"qualifying earnings","payment_timing":"Payday Super from 1 July 2026","source_last_updated":"2026-04-17"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee'
    ),
    (
        'Australia',
        'superannuation',
        '2025-2026',
        'concessional_contributions_cap',
        $json${"period":"1 July 2025 – 30 June 2026","cap_amount":30000,"cap_type":"concessional","applies_to":"all ages","includes":["employer contributions","salary sacrifice contributions","personal contributions claimed as a tax deduction"],"source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    ),
    (
        'Australia',
        'superannuation',
        '2026-2027',
        'concessional_contributions_cap',
        $json${"period":"1 July 2026 – 30 June 2027","cap_amount":32500,"cap_type":"concessional","applies_to":"all ages","includes":["employer contributions","salary sacrifice contributions","personal contributions claimed as a tax deduction"],"source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    ),
    (
        'Australia',
        'superannuation',
        '2025-2026',
        'non_concessional_contributions_cap',
        $json${"period":"1 July 2025 – 30 June 2026","cap_amount":120000,"cap_type":"non-concessional","applies_to":"personal contributions not claimed as an income tax deduction","important_condition":"The non-concessional cap can be nil if total superannuation balance is greater than or equal to the general transfer balance cap at the end of the previous financial year.","source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    ),
    (
        'Australia',
        'superannuation',
        '2026-2027',
        'non_concessional_contributions_cap',
        $json${"period":"1 July 2026 – 30 June 2027","cap_amount":130000,"cap_type":"non-concessional","applies_to":"personal contributions not claimed as an income tax deduction","important_condition":"The non-concessional cap can be nil if total superannuation balance is greater than or equal to the general transfer balance cap at the end of the previous financial year.","source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    )
)
UPDATE financial_rules
SET
    rule_value = current_financial_rules.rule_value::jsonb,
    source_name = current_financial_rules.source_name,
    source_url = current_financial_rules.source_url
FROM current_financial_rules
WHERE financial_rules.region = current_financial_rules.region
  AND financial_rules.category = current_financial_rules.category
  AND financial_rules.rule_year = current_financial_rules.rule_year
  AND financial_rules.rule_key = current_financial_rules.rule_key;

WITH current_financial_rules (
    region,
    category,
    rule_year,
    rule_key,
    rule_value,
    source_name,
    source_url
) AS (
    VALUES
    (
        'Australia', 'tax', '2025-2026',
        'resident_income_tax_bracket_0_18200',
        $json${"bracket_label":"$0 – $18,200","income_from":0,"income_to":18200,"base_tax":0,"threshold":0,"marginal_rate":0,"formula":"Nil","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia', 'tax', '2025-2026',
        'resident_income_tax_bracket_18201_45000',
        $json${"bracket_label":"$18,201 – $45,000","income_from":18200.01,"income_to":45000,"base_tax":0,"threshold":18200,"marginal_rate":0.16,"formula":"16c for each $1 over $18,200","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia', 'tax', '2025-2026',
        'resident_income_tax_bracket_45001_135000',
        $json${"bracket_label":"$45,001 – $135,000","income_from":45000.01,"income_to":135000,"base_tax":4288,"threshold":45000,"marginal_rate":0.30,"formula":"$4,288 plus 30c for each $1 over $45,000","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia', 'tax', '2025-2026',
        'resident_income_tax_bracket_135001_190000',
        $json${"bracket_label":"$135,001 – $190,000","income_from":135000.01,"income_to":190000,"base_tax":31288,"threshold":135000,"marginal_rate":0.37,"formula":"$31,288 plus 37c for each $1 over $135,000","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia', 'tax', '2025-2026',
        'resident_income_tax_bracket_190001_over',
        $json${"bracket_label":"$190,001 and over","income_from":190000.01,"income_to":null,"base_tax":51638,"threshold":190000,"marginal_rate":0.45,"formula":"$51,638 plus 45c for each $1 over $190,000","medicare_levy_included":false,"source_last_updated":"2026-06-01"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
    ),
    (
        'Australia', 'superannuation', '2025-2026',
        'employer_super_contribution',
        $json${"period":"1 July 2025 – 30 June 2026","general_super_guarantee_percent":12.00,"earnings_basis":"ordinary time earnings","source_last_updated":"2026-04-17"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee'
    ),
    (
        'Australia', 'superannuation', '2026-2027',
        'employer_super_contribution',
        $json${"period":"1 July 2026 – 30 June 2027","general_super_guarantee_percent":12.00,"earnings_basis":"qualifying earnings","payment_timing":"Payday Super from 1 July 2026","source_last_updated":"2026-04-17"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee'
    ),
    (
        'Australia', 'superannuation', '2025-2026',
        'concessional_contributions_cap',
        $json${"period":"1 July 2025 – 30 June 2026","cap_amount":30000,"cap_type":"concessional","applies_to":"all ages","includes":["employer contributions","salary sacrifice contributions","personal contributions claimed as a tax deduction"],"source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    ),
    (
        'Australia', 'superannuation', '2026-2027',
        'concessional_contributions_cap',
        $json${"period":"1 July 2026 – 30 June 2027","cap_amount":32500,"cap_type":"concessional","applies_to":"all ages","includes":["employer contributions","salary sacrifice contributions","personal contributions claimed as a tax deduction"],"source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    ),
    (
        'Australia', 'superannuation', '2025-2026',
        'non_concessional_contributions_cap',
        $json${"period":"1 July 2025 – 30 June 2026","cap_amount":120000,"cap_type":"non-concessional","applies_to":"personal contributions not claimed as an income tax deduction","important_condition":"The non-concessional cap can be nil if total superannuation balance is greater than or equal to the general transfer balance cap at the end of the previous financial year.","source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    ),
    (
        'Australia', 'superannuation', '2026-2027',
        'non_concessional_contributions_cap',
        $json${"period":"1 July 2026 – 30 June 2027","cap_amount":130000,"cap_type":"non-concessional","applies_to":"personal contributions not claimed as an income tax deduction","important_condition":"The non-concessional cap can be nil if total superannuation balance is greater than or equal to the general transfer balance cap at the end of the previous financial year.","source_last_updated":"2026-04-24"}$json$,
        'Australian Taxation Office',
        'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
    )
)
INSERT INTO financial_rules (
    region,
    category,
    rule_year,
    rule_key,
    rule_value,
    source_name,
    source_url
)
SELECT
    current_financial_rules.region,
    current_financial_rules.category,
    current_financial_rules.rule_year,
    current_financial_rules.rule_key,
    current_financial_rules.rule_value::jsonb,
    current_financial_rules.source_name,
    current_financial_rules.source_url
FROM current_financial_rules
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE financial_rules.region = current_financial_rules.region
      AND financial_rules.category = current_financial_rules.category
      AND financial_rules.rule_year = current_financial_rules.rule_year
      AND financial_rules.rule_key = current_financial_rules.rule_key
);

DELETE FROM financial_rules
WHERE region = 'Australia'
  AND category = 'tax'
  AND rule_year IN ('2021-2022', '2022-2023');

DELETE FROM financial_rules
WHERE region = 'Australia'
  AND category IN (
      'resident_income_tax',
      'superannuation_guarantee'
  );

CREATE TEMP TABLE financial_rules_2026_2027 (
    region VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    rule_year VARCHAR(20) NOT NULL,
    rule_key VARCHAR(100) NOT NULL,
    rule_value TEXT NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL
);

INSERT INTO financial_rules_2026_2027 (
    region,
    category,
    rule_year,
    rule_key,
    rule_value,
    source_name,
    source_url
) VALUES
(
    'Australia',
    'tax',
    '2026-2027',
    'resident_income_tax_bracket_0_18200',
    $json${"bracket_label":"$0 – $18,200","income_from":0,"income_to":18200,"base_tax":0,"threshold":0,"marginal_rate":0,"formula":"Nil","medicare_levy_included":false,"source_verified_on":"2026-07-18"}$json$,
    'Australian Government – Federal Register of Legislation',
    'https://www.legislation.gov.au/C2025A00028/asmade'
),
(
    'Australia',
    'tax',
    '2026-2027',
    'resident_income_tax_bracket_18201_45000',
    $json${"bracket_label":"$18,201 – $45,000","income_from":18200.01,"income_to":45000,"base_tax":0,"threshold":18200,"marginal_rate":0.15,"formula":"15c for each $1 over $18,200","medicare_levy_included":false,"source_verified_on":"2026-07-18"}$json$,
    'Australian Government – Federal Register of Legislation',
    'https://www.legislation.gov.au/C2025A00028/asmade'
),
(
    'Australia',
    'tax',
    '2026-2027',
    'resident_income_tax_bracket_45001_135000',
    $json${"bracket_label":"$45,001 – $135,000","income_from":45000.01,"income_to":135000,"base_tax":4020,"threshold":45000,"marginal_rate":0.30,"formula":"$4,020 plus 30c for each $1 over $45,000","medicare_levy_included":false,"source_verified_on":"2026-07-18"}$json$,
    'Australian Government – Federal Register of Legislation',
    'https://www.legislation.gov.au/C2025A00028/asmade'
),
(
    'Australia',
    'tax',
    '2026-2027',
    'resident_income_tax_bracket_135001_190000',
    $json${"bracket_label":"$135,001 – $190,000","income_from":135000.01,"income_to":190000,"base_tax":31020,"threshold":135000,"marginal_rate":0.37,"formula":"$31,020 plus 37c for each $1 over $135,000","medicare_levy_included":false,"source_verified_on":"2026-07-18"}$json$,
    'Australian Government – Federal Register of Legislation',
    'https://www.legislation.gov.au/C2025A00028/asmade'
),
(
    'Australia',
    'tax',
    '2026-2027',
    'resident_income_tax_bracket_190001_over',
    $json${"bracket_label":"$190,001 and over","income_from":190000.01,"income_to":null,"base_tax":51370,"threshold":190000,"marginal_rate":0.45,"formula":"$51,370 plus 45c for each $1 over $190,000","medicare_levy_included":false,"source_verified_on":"2026-07-18"}$json$,
    'Australian Government – Federal Register of Legislation',
    'https://www.legislation.gov.au/C2025A00028/asmade'
),
(
    'Australia',
    'superannuation',
    '2026-2027',
    'employer_super_contribution',
    $json${"period":"1 July 2026 – 30 June 2027","general_super_guarantee_percent":12.00,"earnings_basis":"qualifying earnings","payment_timing":"Payday Super from 1 July 2026; contributions must generally reach the employee's super fund within 7 business days after payday","source_last_updated":"2026-07-09"}$json$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/businesses-and-organisations/super-for-employers/about-payday-super'
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
    '2026-2027',
    'non_concessional_contributions_cap',
    $json${"period":"1 July 2026 – 30 June 2027","cap_amount":130000,"cap_type":"non-concessional","applies_to":"personal contributions not claimed as an income tax deduction","important_condition":"The non-concessional cap is nil if the total superannuation balance is greater than or equal to the general transfer balance cap at the end of the previous financial year.","source_last_updated":"2026-04-24"}$json$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps'
);

UPDATE financial_rules AS stored_rule
SET
    rule_value = current_rule.rule_value,
    source_name = current_rule.source_name,
    source_url = current_rule.source_url
FROM financial_rules_2026_2027 AS current_rule
WHERE stored_rule.region = current_rule.region
  AND stored_rule.category = current_rule.category
  AND stored_rule.rule_year = current_rule.rule_year
  AND stored_rule.rule_key = current_rule.rule_key;

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
    current_rule.region,
    current_rule.category,
    current_rule.rule_year,
    current_rule.rule_key,
    current_rule.rule_value,
    current_rule.source_name,
    current_rule.source_url
FROM financial_rules_2026_2027 AS current_rule
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules AS stored_rule
    WHERE stored_rule.region = current_rule.region
      AND stored_rule.category = current_rule.category
      AND stored_rule.rule_year = current_rule.rule_year
      AND stored_rule.rule_key = current_rule.rule_key
);

DELETE FROM financial_rules
WHERE region = 'Australia'
  AND rule_year <> '2026-2027';

DELETE FROM financial_rules
WHERE region = 'Australia'
  AND category IN (
      'resident_income_tax',
      'superannuation_guarantee'
  );

DROP TABLE financial_rules_2026_2027;

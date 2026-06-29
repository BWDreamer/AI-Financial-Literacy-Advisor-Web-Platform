UPDATE financial_rules
SET
    rule_value = $$
{
  "bracket_label": "$0 – $18,200",
  "income_from": 0,
  "income_to": 18200,
  "base_tax": 0,
  "threshold": 0,
  "marginal_rate": 0,
  "formula": "Nil",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    source_name = 'Australian Taxation Office',
    source_url = 'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE region = 'Australia'
  AND category = 'tax'
  AND rule_year = '2025-2026'
  AND rule_key = 'resident_income_tax_bracket_0_18200';

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
    'Australia',
    'tax',
    '2025-2026',
    'resident_income_tax_bracket_0_18200',
    $$
{
  "bracket_label": "$0 – $18,200",
  "income_from": 0,
  "income_to": 18200,
  "base_tax": 0,
  "threshold": 0,
  "marginal_rate": 0,
  "formula": "Nil",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'tax'
      AND rule_year = '2025-2026'
      AND rule_key = 'resident_income_tax_bracket_0_18200'
);

UPDATE financial_rules
SET
    rule_value = $$
{
  "bracket_label": "$18,201 – $45,000",
  "income_from": 18200.01,
  "income_to": 45000,
  "base_tax": 0,
  "threshold": 18200,
  "marginal_rate": 0.16,
  "formula": "16c for each $1 over $18,200",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    source_name = 'Australian Taxation Office',
    source_url = 'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE region = 'Australia'
  AND category = 'tax'
  AND rule_year = '2025-2026'
  AND rule_key = 'resident_income_tax_bracket_18201_45000';

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
    'Australia',
    'tax',
    '2025-2026',
    'resident_income_tax_bracket_18201_45000',
    $$
{
  "bracket_label": "$18,201 – $45,000",
  "income_from": 18200.01,
  "income_to": 45000,
  "base_tax": 0,
  "threshold": 18200,
  "marginal_rate": 0.16,
  "formula": "16c for each $1 over $18,200",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'tax'
      AND rule_year = '2025-2026'
      AND rule_key = 'resident_income_tax_bracket_18201_45000'
);

UPDATE financial_rules
SET
    rule_value = $$
{
  "bracket_label": "$45,001 – $135,000",
  "income_from": 45000.01,
  "income_to": 135000,
  "base_tax": 4288,
  "threshold": 45000,
  "marginal_rate": 0.30,
  "formula": "$4,288 plus 30c for each $1 over $45,000",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    source_name = 'Australian Taxation Office',
    source_url = 'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE region = 'Australia'
  AND category = 'tax'
  AND rule_year = '2025-2026'
  AND rule_key = 'resident_income_tax_bracket_45001_135000';

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
    'Australia',
    'tax',
    '2025-2026',
    'resident_income_tax_bracket_45001_135000',
    $$
{
  "bracket_label": "$45,001 – $135,000",
  "income_from": 45000.01,
  "income_to": 135000,
  "base_tax": 4288,
  "threshold": 45000,
  "marginal_rate": 0.30,
  "formula": "$4,288 plus 30c for each $1 over $45,000",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'tax'
      AND rule_year = '2025-2026'
      AND rule_key = 'resident_income_tax_bracket_45001_135000'
);

UPDATE financial_rules
SET
    rule_value = $$
{
  "bracket_label": "$135,001 – $190,000",
  "income_from": 135000.01,
  "income_to": 190000,
  "base_tax": 31288,
  "threshold": 135000,
  "marginal_rate": 0.37,
  "formula": "$31,288 plus 37c for each $1 over $135,000",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    source_name = 'Australian Taxation Office',
    source_url = 'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE region = 'Australia'
  AND category = 'tax'
  AND rule_year = '2025-2026'
  AND rule_key = 'resident_income_tax_bracket_135001_190000';

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
    'Australia',
    'tax',
    '2025-2026',
    'resident_income_tax_bracket_135001_190000',
    $$
{
  "bracket_label": "$135,001 – $190,000",
  "income_from": 135000.01,
  "income_to": 190000,
  "base_tax": 31288,
  "threshold": 135000,
  "marginal_rate": 0.37,
  "formula": "$31,288 plus 37c for each $1 over $135,000",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'tax'
      AND rule_year = '2025-2026'
      AND rule_key = 'resident_income_tax_bracket_135001_190000'
);

UPDATE financial_rules
SET
    rule_value = $$
{
  "bracket_label": "$190,001 and over",
  "income_from": 190000.01,
  "income_to": null,
  "base_tax": 51638,
  "threshold": 190000,
  "marginal_rate": 0.45,
  "formula": "$51,638 plus 45c for each $1 over $190,000",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    source_name = 'Australian Taxation Office',
    source_url = 'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE region = 'Australia'
  AND category = 'tax'
  AND rule_year = '2025-2026'
  AND rule_key = 'resident_income_tax_bracket_190001_over';

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
    'Australia',
    'tax',
    '2025-2026',
    'resident_income_tax_bracket_190001_over',
    $$
{
  "bracket_label": "$190,001 and over",
  "income_from": 190000.01,
  "income_to": null,
  "base_tax": 51638,
  "threshold": 190000,
  "marginal_rate": 0.45,
  "formula": "$51,638 plus 45c for each $1 over $190,000",
  "medicare_levy_included": false,
  "source_last_updated": "2026-06-01"
}
$$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'tax'
      AND rule_year = '2025-2026'
      AND rule_key = 'resident_income_tax_bracket_190001_over'
);

UPDATE financial_rules
SET
    rule_value = $$
{
  "period": "1 July 2025 – 30 June 2026",
  "general_super_guarantee_percent": 12.00,
  "earnings_basis": "ordinary time earnings",
  "source_last_updated": "2026-04-17"
}
$$,
    source_name = 'Australian Taxation Office',
    source_url = 'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee'
WHERE region = 'Australia'
  AND category = 'superannuation'
  AND rule_year = '2025-2026'
  AND rule_key = 'employer_super_contribution';

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
    'Australia',
    'superannuation',
    '2025-2026',
    'employer_super_contribution',
    $$
{
  "period": "1 July 2025 – 30 June 2026",
  "general_super_guarantee_percent": 12.00,
  "earnings_basis": "ordinary time earnings",
  "source_last_updated": "2026-04-17"
}
$$,
    'Australian Taxation Office',
    'https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'superannuation'
      AND rule_year = '2025-2026'
      AND rule_key = 'employer_super_contribution'
);

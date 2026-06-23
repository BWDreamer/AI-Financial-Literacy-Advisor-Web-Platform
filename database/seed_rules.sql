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
    'Employer superannuation contribution rules should be retrieved from official ATO sources and updated by administrators.',
    'Australian Taxation Office',
    'https://www.ato.gov.au/'
WHERE NOT EXISTS (
    SELECT 1
    FROM financial_rules
    WHERE region = 'Australia'
      AND category = 'superannuation'
      AND rule_year = '2025-2026'
      AND rule_key = 'employer_super_contribution'
);
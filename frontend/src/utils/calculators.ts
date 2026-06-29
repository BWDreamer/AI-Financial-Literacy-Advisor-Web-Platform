export type BudgetInput = {
  income: number;
  housing: number;
  utilities: number;
  groceries: number;
  transport: number;
  insurance: number;
  debt: number;
  savings: number;
  other: number;
};

export function calculateBudget(input: BudgetInput) {
  const totalAllocated = Object.entries(input)
    .filter(([key]) => key !== "income")
    .reduce((total, [, value]) => total + value, 0);
  const expenses = totalAllocated - input.savings;
  return {
    totalAllocated,
    remaining: input.income - totalAllocated,
    expenseRatio: input.income ? expenses / input.income * 100 : 0,
    savingsRate: input.income ? input.savings / input.income * 100 : 0,
  };
}

export function calculateLoan(principal: number, annualRate: number, years: number) {
  const payments = Math.round(years * 12);
  const monthlyRate = annualRate / 100 / 12;
  const monthlyPayment = monthlyRate === 0
    ? principal / payments
    : principal * monthlyRate * (1 + monthlyRate) ** payments / ((1 + monthlyRate) ** payments - 1);
  const totalRepayment = monthlyPayment * payments;
  return { monthlyPayment, totalRepayment, totalInterest: totalRepayment - principal, payments };
}

function basicIncomeTax(income: number) {
  if (income <= 18_200) return 0;
  if (income <= 45_000) return (income - 18_200) * 0.16;
  if (income <= 135_000) return 4_288 + (income - 45_000) * 0.3;
  if (income <= 190_000) return 31_288 + (income - 135_000) * 0.37;
  return 51_638 + (income - 190_000) * 0.45;
}

function lowIncomeTaxOffset(income: number) {
  if (income <= 37_500) return 700;
  if (income <= 45_000) return 700 - (income - 37_500) * 0.05;
  if (income <= 66_667) return Math.max(0, 325 - (income - 45_000) * 0.015);
  return 0;
}

function medicareLevy(income: number) {
  const threshold = 28_011;
  if (income <= threshold) return 0;
  return Math.min(income * 0.02, (income - threshold) * 0.1);
}

export function calculateAustralianTax(grossIncome: number, deductions: number) {
  const taxableIncome = Math.max(0, grossIncome - deductions);
  const incomeTax = Math.max(0, basicIncomeTax(taxableIncome) - lowIncomeTaxOffset(taxableIncome));
  const medicare = medicareLevy(taxableIncome);
  const totalTax = incomeTax + medicare;
  return {
    taxableIncome, incomeTax, medicare, totalTax,
    afterTaxIncome: grossIncome - totalTax,
    effectiveRate: grossIncome ? totalTax / grossIncome * 100 : 0,
  };
}

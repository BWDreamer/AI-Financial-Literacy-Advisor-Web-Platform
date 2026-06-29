import { apiRequest } from "./client";

export type CompoundInterestInput = {
  principal: number;
  annual_interest_rate: number;
  years: number;
  compounds_per_year: number;
};

export type CompoundInterestResult = CompoundInterestInput & {
  final_amount: number;
  interest_earned: number;
};

export function calculateCompoundInterest(input: CompoundInterestInput) {
  return apiRequest<CompoundInterestResult>("/calculator/compound-interest", {
    method: "POST", authenticated: true, body: JSON.stringify(input),
  });
}

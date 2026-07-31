import assert from "node:assert/strict";
import test from "node:test";

import {
  goalRatiosFromAllocation,
  monthlyAllocationFromRatios,
} from "../src/utils/goalAllocation.ts";

test("scales an existing goal allocation with the monthly allocatable ratio", () => {
  const goals = [{ id: "1" }];
  const existingAllocation = {
    monthly_net_income: 1290,
    monthly_allocatable: 1290,
    already_assigned: 957,
    unassigned: 333,
    goals: [{
      goal_id: 1,
      ratio: 74.186047,
      monthly_amount: 957,
    }],
  };

  const goalRatios = goalRatiosFromAllocation(goals, existingAllocation);
  const reducedAllocation = monthlyAllocationFromRatios(
    1290,
    50,
    goals,
    goalRatios,
  );

  assert.equal(reducedAllocation.monthly_allocatable, 645);
  assert.equal(reducedAllocation.already_assigned, 478.5);
  assert.equal(reducedAllocation.goals[0].monthly_amount, 478.5);
  assert.equal(reducedAllocation.goals[0].ratio, 74.186047);
});

test("aligns ratios to active goals by goal id", () => {
  const allocation = {
    monthly_net_income: 1000,
    monthly_allocatable: 1000,
    already_assigned: 600,
    unassigned: 400,
    goals: [
      { goal_id: 2, ratio: 40, monthly_amount: 400 },
      { goal_id: 1, ratio: 20, monthly_amount: 200 },
    ],
  };

  assert.deepEqual(
    goalRatiosFromAllocation([{ id: "1" }, { id: "2" }], allocation),
    [20, 40],
  );
});

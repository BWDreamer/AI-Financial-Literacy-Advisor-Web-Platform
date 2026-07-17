# Architecture Notes

The frontend does not access the database or LLM directly. All requests go through authenticated backend APIs.

Main layers:

1. Frontend PWA
2. Backend API server
3. Controller layer
4. Service layer
5. Data access layer
6. PostgreSQL database
7. Controlled AI service layer
8. Calculation engine
9. Rules knowledge base
10. File storage

Business calculations live in backend services. Financial totals, recurring
frequency normalization, cash-savings trends, goal analysis, progress and goal
allocation amounts are returned by authenticated APIs. Each resource has one
public write path: goal progress uses `/goals/{id}/progress`, and allocation
settings use `/goals/allocation-settings`.

The frontend owns form state, formatting, filtering, chart coordinates and UI
interaction state. It does not maintain a parallel financial localStorage
database or recalculate authoritative financial and goal totals.

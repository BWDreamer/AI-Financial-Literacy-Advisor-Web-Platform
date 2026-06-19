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

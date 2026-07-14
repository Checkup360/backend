# ADR 0001: Hexagonal backend structure

- Status: Accepted
- Date: 2026-07-13

## Context

Framework code, persistence, HTTP models and domain rules previously lived in
parallel top-level packages. Domain services also depended on concrete
SQLAlchemy repositories, making dependency direction inconsistent.

## Decision

The backend is organized into four explicit layers:

- `domain` contains pure entities, value objects, domain services and repository
  interfaces.
- `application` contains use cases, application DTOs and outbound service
  interfaces.
- `infrastructure` implements persistence, authentication, email and runtime
  configuration.
- `presentation` owns FastAPI routes, HTTP models, authorization dependencies
  and the application composition root.

Dependencies point inward. Domain and application modules cannot import
presentation or infrastructure modules. Presentation controllers cannot query
SQLAlchemy directly.

## Consequences

External providers and persistence implementations can be replaced without
changing domain rules. More mapping code is required at layer boundaries, but
ORM and HTTP models no longer act as domain entities.

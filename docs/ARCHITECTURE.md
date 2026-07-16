# CodeDNA Architecture

## Repository Structure

```
CoDNA/

├── apps/
├── services/
├── packages/
├── docs/
└── package.json
```

---

# Root

## package.json

Purpose:
Acts as the workspace manager for the entire repository.

Responsibilities:
- Defines npm workspaces
- Runs scripts for all applications
- Never contains application logic

Owner:
Repository

---

# apps/

Contains all runnable applications.

Current Applications:

## web/

Next.js frontend responsible for:

- Dashboard
- Authentication
- Repository Explorer
- AI Chat
- Architecture Graph
- Timeline

---

## apps/web/package.json

Purpose:
Defines dependencies required only by the frontend.

Examples:

- React
- Next.js
- Tailwind
- TypeScript

---

## app/

Contains Next.js App Router pages.

Every folder inside `app/` corresponds to a route.

Example:

```
app/dashboard/page.tsx

↓

localhost:3000/dashboard
```

---

## public/

Static assets.

Examples:

- logos
- favicon
- screenshots

---

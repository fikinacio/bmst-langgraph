# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Swiss Process Hub is a profile-based, multi-tenant document processing platform for Swiss businesses. Built with React 18, TypeScript, Vite, and Supabase backend. Uses shadcn/ui components with Tailwind CSS.

## Commands

```bash
npm run dev          # Start dev server on localhost:8080
npm run build        # Production build
npm run lint         # ESLint check
npm run test         # Run Vitest once
npm run test:watch   # Vitest in watch mode
```

## Architecture

### Core Patterns

**Feature Flags System**: Organization profiles (`ap_team`, `sme_accounting`, `internal_accounting`, `fiduciary`) control feature availability. Flags defined in `src/lib/featureFlags.ts`. Use `<FeatureGate>` or `<MultiFeatureGate>` components for conditional rendering.

**Feature Catalog** (`src/lib/featureCatalog.ts`): Separates enabled flags from implementation status - prevents showing unbuilt features.

**State Management**:
- React Context for auth, organization, theme, language (FR/DE/EN)
- React Query for server state (documents, stats, audit logs)

**Data Flow**:
```
User Action → Hook (useDocuments, etc.) → Service Layer → Supabase → React Query Cache → UI
```

### Key Directories

- `src/contexts/` - AuthContext, OrganizationContext, ThemeContext, LanguageContext
- `src/features/` - Feature modules by profile (ap/, sme/, internal/, fiduciary/)
- `src/services/` - Business logic: documentService, extractionService, exportService, auditService, storageService
- `src/hooks/` - useDocuments, useDocumentUpload, useFeatureFlags, useErrorHandler
- `src/lib/` - featureFlags, featureCatalog, validation (Swiss IBAN/VAT), i18n translations
- `src/components/ui/` - shadcn/ui components (70+)

### Validation

Swiss-specific validation in `src/lib/validation.ts`:
- IBAN: `CH` or `LI` prefix + checksum
- VAT: `CHE-XXX.XXX.XXX` format
- Profile-aware via `validateDocumentByProfile()`

### Internationalization

Default language is French. Translations in `src/lib/i18n/translations/` (fr.json, de.json, en.json). Access via `useLanguage()` hook.

### Document Processing Pipeline

Upload (DropZone) → storageService → documentService.createDocument() → extractionService.extractData() → validateDocumentByProfile() → auditService.logAction()

## Adding Features

1. Add flag to `FEATURE_FLAGS` in `src/lib/featureFlags.ts`
2. Add to `FEATURE_CATALOG` with `implemented: true/false`
3. Gate UI with `<FeatureGate feature="yourFeature">`
4. Add translations to all three language files
5. Create service in `src/services/` if needed
6. Create hook in `src/hooks/` for React Query integration

## Environment Variables

```
VITE_SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY
```

## TypeScript Configuration

Path alias `@/*` maps to `./src/*`. Config is relaxed (`noImplicitAny: false`, `strictNullChecks: false`).

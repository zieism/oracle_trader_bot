# Compatibility Layer Documentation

This directory contains compatibility shims and import rewriters to enable seamless migration from the current structure to the new professional folder structure.

## 🛡️ Backend Compatibility Shims

### Purpose
Maintain backward compatibility while the codebase is being refactored from the current `oracle_trader_bot/app/` structure to the new `backend/app/` structure with domain-based routers.

### Files Created

#### 1. `oracle_trader_bot/__init__.py`
- **Purpose**: Main compatibility shim for the entire package
- **Function**: Redirects imports from `oracle_trader_bot.*` to `backend.*`
- **Features**: Shows deprecation warnings to guide developers to new import paths

#### 2. `oracle_trader_bot/app/__init__.py`
- **Purpose**: App-level compatibility for all app modules
- **Function**: Handles complex import mapping between old endpoints and new routers
- **Features**: Maps old endpoint modules to new domain-based routers

#### 3. `oracle_trader_bot/app/api/endpoints/__init__.py`
- **Purpose**: Specific compatibility for API endpoints → routers migration
- **Function**: Maps individual endpoint files to their new domain-based router locations
- **Features**: Handles both direct imports and merged functionality

#### 4. `oracle_trader_bot/app/services/__init__.py`
- **Purpose**: Services compatibility for renamed service modules
- **Function**: Maps old service names to new standardized names
- **Features**: Handles service renaming (e.g., `position_monitor` → `position_service`)

### Import Mapping Strategy

```python
# OLD STRUCTURE → NEW STRUCTURE
'app.api.endpoints.bot_settings_api'     → 'backend.app.api.routers.settings'
'app.api.endpoints.bot_management_api'   → 'backend.app.api.routers.settings' 
'app.api.endpoints.trading'              → 'backend.app.api.routers.trading'
'app.api.endpoints.order_management'     → 'backend.app.api.routers.trading'
'app.api.endpoints.trades'               → 'backend.app.api.routers.trading'
'app.services.position_monitor'          → 'backend.app.services.position_service'
'app.core.bot_process_manager'           → 'backend.app.services.bot_manager'
```

## 🌐 Frontend Path Aliases

### Configuration Files

#### 1. `frontend/tsconfig.json`
- **Path Aliases**: Configured to support feature-based architecture
- **Aliases Available**:
  - `@/*` → `src/*`
  - `@app/*` → `src/app/*` 
  - `@components/*` → `src/components/*`
  - `@features/*` → `src/features/*`
  - `@services/*` → `src/services/*`
  - `@hooks/*` → `src/hooks/*`
  - `@utils/*` → `src/utils/*`
  - `@types/*` → `src/types/*`

#### 2. `frontend/vite.config.ts` 
- **Vite Aliases**: Mirror TypeScript path aliases for build-time resolution
- **Legacy Compatibility**: Includes deprecated aliases for smooth transition

### Legacy Compatibility Aliases
```typescript
// DEPRECATED (will show warnings)
'@pages/*' → '@features/*/components/*'
'@api/*'   → '@services/api/*'
```

## 🔧 Import Rewriter Scripts

### 1. Backend Import Rewriter (`scripts/rewrite_backend_imports.py`)

**Features**:
- AST-based parsing for safe import rewriting
- Handles both `import` and `from...import` statements
- Maps old endpoint imports to new router-based imports
- Supports dry-run mode for testing

**Usage**:
```bash
python scripts/rewrite_backend_imports.py [--dry-run] [--verbose]
```

### 2. Frontend Import Rewriter (`scripts/rewrite_frontend_imports.js`)

**Features**:
- RegEx-based pattern matching for TypeScript/JavaScript
- Handles standard imports, dynamic imports, and re-exports
- Converts relative imports to absolute with aliases
- Maps old page imports to new feature-based structure

**Usage**:
```bash
node scripts/rewrite_frontend_imports.js [--dry-run] [--verbose]
```

### 3. Unified Rewriter (`scripts/rewrite_all_imports.py`)

**Features**:
- Coordinates both backend and frontend rewriting
- Can run both rewriters or individually
- Provides unified reporting and error handling

**Usage**:
```bash
python scripts/rewrite_all_imports.py [--dry-run] [--verbose] [--backend-only] [--frontend-only]
```

## 🚨 Migration Workflow

### Phase 1: Compatibility Setup ✅ (Current)
1. ✅ Create directory structure placeholders
2. ✅ Install compatibility shims  
3. ✅ Configure path aliases
4. ✅ Create import rewriter scripts

### Phase 2: Import Rewriting (Next)
1. Run import rewriters in dry-run mode
2. Review proposed changes
3. Apply import updates
4. Test that applications still work

### Phase 3: File Migration (Future)
1. Move files to new locations
2. Update any remaining references
3. Test compatibility shims work correctly
4. Update CI/CD and deployment scripts

### Phase 4: Cleanup (Final)
1. Remove compatibility shims gradually
2. Update documentation
3. Remove deprecated aliases
4. Celebrate professional structure! 🎉

## ⚠️ Important Notes

### Deprecation Warnings
All compatibility shims emit `DeprecationWarning` messages to help developers update their import statements. These warnings include:
- The old import path being used
- The new import path to use instead
- Clear guidance on required changes

### Testing Compatibility
The compatibility layer is designed to maintain 100% functional compatibility during migration:
- All existing APIs continue to work
- Import statements continue to resolve correctly  
- No breaking changes to public interfaces
- Gradual migration path with clear deprecation notices

### Performance Considerations
- Shims add minimal runtime overhead
- Import redirections happen at module load time only
- No impact on application runtime performance
- Warnings can be suppressed in production if needed

## 🎯 Success Metrics

The compatibility layer is successful when:
1. ✅ All existing imports continue to work
2. ✅ New import paths are properly configured
3. ✅ Import rewriters can update codebases safely
4. ✅ Applications run without functional changes
5. ✅ Clear migration path is provided with deprecation warnings

This compatibility layer enables confident refactoring while maintaining zero downtime and zero feature loss.

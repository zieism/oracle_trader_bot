#!/usr/bin/env node
/**
 * Frontend Import Rewriter
 * 
 * This script updates TypeScript/JavaScript import statements to use the new
 * feature-based structure with path aliases.
 * 
 * Usage:
 *   node scripts/rewrite_frontend_imports.js [--dry-run] [--verbose]
 *   
 * Options:
 *   --dry-run    Show what would be changed without making modifications
 *   --verbose    Show detailed information about changes
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Import mapping from old paths to new paths with aliases
const FRONTEND_IMPORT_MAPPING = {
    // Pages → Features
    './pages/DashboardPage': '@features/dashboard/components/Dashboard',
    './pages/BotSettingsPage': '@features/settings/components/BotSettings', 
    './pages/TradesLogPage': '@features/trades/components/TradesHistory',
    './pages/ServerLogPage': '@features/logs/components/ServerLogs',
    './pages/AnalysisLogPage': '@features/logs/components/AnalysisLogs',
    
    // Services
    './services/apiService': '@services/api/client',
    '../services/apiService': '@services/api/client',
    '../../services/apiService': '@services/api/client',
    
    // Relative imports that should use aliases
    '../components/': '@components/',
    '../../components/': '@components/',
    '../hooks/': '@hooks/',
    '../../hooks/': '@hooks/',
    '../utils/': '@utils/',
    '../../utils/': '@utils/',
    '../types/': '@types/',
    '../../types/': '@types/',
    
    // Legacy compatibility (will add deprecation warnings)
    '@pages/': '@features/',
    '@api/': '@services/api/',
};

// Regex patterns for different import styles
const IMPORT_PATTERNS = [
    // Standard imports: import ... from '...'
    /import\s+(?:(?:\{[^}]*\})|(?:\*\s+as\s+\w+)|(?:\w+))\s+from\s+['"]([^'"]+)['"]/g,
    // Dynamic imports: import('...')
    /import\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    // Re-exports: export ... from '...'
    /export\s+(?:(?:\{[^}]*\})|(?:\*\s+as\s+\w+))\s+from\s+['"]([^'"]+)['"]/g,
];

class FrontendImportRewriter {
    constructor(dryRun = false, verbose = false) {
        this.dryRun = dryRun;
        this.verbose = verbose;
        this.changes = [];
    }
    
    /**
     * Normalize a file path for consistent comparison
     */
    normalizePath(filePath) {
        return filePath.replace(/\\/g, '/');
    }
    
    /**
     * Find the best matching import mapping for a given import path
     */
    findMapping(importPath, currentFilePath) {
        // Try exact match first
        if (FRONTEND_IMPORT_MAPPING[importPath]) {
            return FRONTEND_IMPORT_MAPPING[importPath];
        }
        
        // Try prefix matching for directory-based mappings
        for (const [oldPath, newPath] of Object.entries(FRONTEND_IMPORT_MAPPING)) {
            if (oldPath.endsWith('/') && importPath.startsWith(oldPath)) {
                return importPath.replace(oldPath, newPath);
            }
        }
        
        // Handle relative paths that should become absolute with aliases
        if (importPath.startsWith('./') || importPath.startsWith('../')) {
            // Try to resolve relative to features structure
            const relativeParts = importPath.split('/');
            const fileName = path.basename(currentFilePath, path.extname(currentFilePath));
            
            // If this looks like a page import, convert to feature
            if (relativeParts.includes('pages')) {
                const pageName = relativeParts[relativeParts.length - 1];
                return this.convertPageToFeature(pageName);
            }
        }
        
        return null;
    }
    
    /**
     * Convert old page names to new feature component paths
     */
    convertPageToFeature(pageName) {
        const pageToFeatureMap = {
            'DashboardPage': '@features/dashboard/components/Dashboard',
            'BotSettingsPage': '@features/settings/components/BotSettings',
            'TradesLogPage': '@features/trades/components/TradesHistory',
            'ServerLogPage': '@features/logs/components/ServerLogs',
            'AnalysisLogPage': '@features/logs/components/AnalysisLogs',
        };
        
        return pageToFeatureMap[pageName] || null;
    }
    
    /**
     * Rewrite imports in a single file
     */
    rewriteFileImports(filePath) {
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            let newContent = content;
            let hasChanges = false;
            
            // Apply each import pattern
            for (const pattern of IMPORT_PATTERNS) {
                newContent = newContent.replace(pattern, (match, importPath) => {
                    const newImportPath = this.findMapping(importPath, filePath);
                    
                    if (newImportPath && newImportPath !== importPath) {
                        hasChanges = true;
                        const change = `${importPath} → ${newImportPath}`;
                        this.changes.push(change);
                        
                        if (this.verbose) {
                            console.log(`  • ${change}`);
                        }
                        
                        return match.replace(importPath, newImportPath);
                    }
                    
                    return match;
                });
            }
            
            if (hasChanges && !this.dryRun) {
                fs.writeFileSync(filePath, newContent, 'utf8');
            }
            
            return hasChanges;
            
        } catch (error) {
            console.error(`⚠️  Error processing ${filePath}: ${error.message}`);
            return false;
        }
    }
}

/**
 * Find all TypeScript/JavaScript files in the given directory
 */
function findTSFiles(rootPath) {
    const files = [];
    
    function scanDirectory(dir) {
        try {
            const entries = fs.readdirSync(dir);
            
            for (const entry of entries) {
                const fullPath = path.join(dir, entry);
                const stats = fs.statSync(fullPath);
                
                if (stats.isDirectory()) {
                    // Skip node_modules and other unwanted directories
                    if (!['node_modules', '.git', 'dist', 'build', '.next'].includes(entry)) {
                        scanDirectory(fullPath);
                    }
                } else if (stats.isFile()) {
                    // Include TypeScript and JavaScript files
                    if (/\.(ts|tsx|js|jsx)$/.test(entry) && !entry.endsWith('.d.ts')) {
                        files.push(fullPath);
                    }
                }
            }
        } catch (error) {
            console.error(`⚠️  Error scanning directory ${dir}: ${error.message}`);
        }
    }
    
    scanDirectory(rootPath);
    return files;
}

/**
 * Main function
 */
function main() {
    const args = process.argv.slice(2);
    const dryRun = args.includes('--dry-run');
    const verbose = args.includes('--verbose') || args.includes('-v');
    const pathArg = args.find(arg => arg.startsWith('--path='));
    const rootPath = pathArg ? pathArg.split('=')[1] : './oracle-trader-frontend/src';
    
    console.log(`🔍 Searching for TypeScript/JavaScript files in: ${rootPath}`);
    
    if (!fs.existsSync(rootPath)) {
        console.error(`❌ Path does not exist: ${rootPath}`);
        process.exit(1);
    }
    
    const tsFiles = findTSFiles(rootPath);
    
    if (tsFiles.length === 0) {
        console.error('❌ No TypeScript/JavaScript files found');
        process.exit(1);
    }
    
    console.log(`📁 Found ${tsFiles.length} TypeScript/JavaScript files`);
    
    if (dryRun) {
        console.log('🔍 DRY RUN MODE - No files will be modified');
    }
    
    const rewriter = new FrontendImportRewriter(dryRun, verbose);
    let changedFiles = 0;
    
    for (const filePath of tsFiles) {
        const fileChanges = rewriter.changes.length;
        
        if (rewriter.rewriteFileImports(filePath)) {
            changedFiles++;
            if (!verbose) {
                console.log(`✏️  Modified: ${path.relative(process.cwd(), filePath)}`);
            } else if (rewriter.changes.length > fileChanges) {
                console.log(`\n📝 Changes for ${path.relative(process.cwd(), filePath)}:`);
            }
        }
    }
    
    if (changedFiles) {
        const action = dryRun ? 'would be modified' : 'modified';
        console.log(`\n✅ ${changedFiles} files ${action}`);
        console.log(`📊 Total import changes: ${rewriter.changes.length}`);
    } else {
        console.log('\n✅ No import changes needed');
    }
    
    if (dryRun && changedFiles) {
        console.log('\n💡 Run without --dry-run to apply changes');
    }
}

// Handle both ES modules and CommonJS
if (import.meta.url === `file://${__filename}`) {
    main();
}

export { FrontendImportRewriter };

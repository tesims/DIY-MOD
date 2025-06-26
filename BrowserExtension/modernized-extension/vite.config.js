import { defineConfig } from 'vite';
import webExtension from 'vite-plugin-web-extension';
import path from 'path';
import fs from 'fs';

// Custom plugin to fix manifest extensions after build
function fixManifestExtensionsPlugin() {
  return {
    name: 'fix-manifest-extensions',
    writeBundle: {
      order: 'post', // Run after all other plugins
      handler() {
        const manifestPath = path.resolve('./dist/manifest.json');
        console.log('⚙️ Running post-build manifest extension fix...');
        
        if (fs.existsSync(manifestPath)) {
          try {
            // Read the current manifest
            const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
            let modified = false;
            
            // Fix background service worker
            if (manifest.background && manifest.background.service_worker) {
              const oldValue = manifest.background.service_worker;
              manifest.background.service_worker = oldValue.replace('.ts', '.js');
              modified = modified || (oldValue !== manifest.background.service_worker);
              console.log(`📝 Fixed background service worker: ${oldValue} → ${manifest.background.service_worker}`);
            }
            
            // Fix content scripts
            if (manifest.content_scripts && Array.isArray(manifest.content_scripts)) {
              manifest.content_scripts.forEach((script, index) => {
                if (script.js) {
                  const oldValues = [...script.js];
                  script.js = script.js.map(file => 
                    typeof file === 'string' ? file.replace('.ts', '.js') : file
                  );
                  
                  // Log changes
                  oldValues.forEach((old, i) => {
                    if (old !== script.js[i]) {
                      console.log(`📝 Fixed content script: ${old} → ${script.js[i]}`);
                      modified = true;
                    }
                  });
                }
              });
            }
            
            if (modified) {
              // Write the fixed manifest back
              fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
              console.log('✅ Successfully fixed TypeScript extensions in manifest.json');
            } else {
              console.log('ℹ️ No TypeScript extensions found in manifest.json to fix');
            }
          } catch (err) {
            console.error('❌ Error fixing manifest.json:', err);
          }
        } else {
          console.error('❌ Manifest file not found at:', manifestPath);
        }
      }
    }
  };
}

export default defineConfig({
  plugins: [
    webExtension({
      manifest: './public/manifest.json',
      browser: 'chrome',
      webExtConfig: {
        // This ensures HTML files are properly processed
        html: {
          loadHtmlParser: true,
          inlineViteAssets: true,
        },
        // Allow TypeScript entry points in manifest.json
        manifest: {
          useTypescript: true
        },
        // Add custom loader for interceptor.ts and content styles
        additionalInputs: [
          {
            from: './src/content/interceptor/interceptor.ts',
            to: 'injected.js'
          },
          {
            from: './src/content/content-styles.css',
            to: 'src/content/content-styles.css'
          }
        ]
      },
      verbose: true, // Enable verbose logging
      disableAutoLaunch: false, // For dev mode
    }),
    // Add our custom plugin to fix manifest extensions
    fixManifestExtensionsPlugin()
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    modulePreload: {
      polyfill: true, 
    },
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          // Keep CSS file paths as they are in manifest
          if (assetInfo.name.endsWith('.css')) {
            return '[name][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        }
      }
    }
  }
});
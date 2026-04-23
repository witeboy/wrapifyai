from http.server import BaseHTTPRequestHandler
import json
import base64
import zipfile
import io
from datetime import datetime
from urllib.parse import parse_qs


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler"""

    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            config = json.loads(body.decode('utf-8'))

            # Validate required fields
            errors = self._validate_config(config)
            if errors:
                self._send_json_response(400, {'success': False, 'errors': errors})
                return

            # Generate the Capacitor project
            generator = CapacitorGenerator(config)
            zip_bytes = generator.generate()

            # Send ZIP file as base64
            zip_base64 = base64.b64encode(zip_bytes).decode('utf-8')

            self._send_json_response(200, {
                'success': True,
                'filename': f"{config['appName'].replace(' ', '_')}_capacitor.zip",
                'data': zip_base64
            })

        except Exception as e:
            self._send_json_response(500, {'success': False, 'errors': [str(e)]})

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json_response(self, status_code, data):
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        response_body = json.dumps(data).encode('utf-8')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def _validate_config(self, config):
        errors = []

        if not config.get('appName'):
            errors.append('App Name is required')

        if not config.get('packageName'):
            errors.append('Package Name is required')
        elif config.get('packageName', '').count('.') < 2:
            errors.append('Package Name must have at least 2 dots (e.g., com.company.app)')

        if not config.get('appUrl'):
            errors.append('App URL is required')
        elif not config.get('appUrl', '').startswith(('http://', 'https://')):
            errors.append('App URL must start with http:// or https://')

        admob = config.get('admob', {})
        if admob.get('enabled'):
            android_app_id = admob.get('android', {}).get('appId', '')
            ios_app_id = admob.get('ios', {}).get('appId', '')
            
            if not android_app_id and not ios_app_id:
                errors.append('At least one AdMob App ID is required when AdMob is enabled')
            
            if android_app_id and not android_app_id.startswith('ca-app-pub-'):
                errors.append('Android AdMob App ID must start with ca-app-pub-')
            
            if ios_app_id and not ios_app_id.startswith('ca-app-pub-'):
                errors.append('iOS AdMob App ID must start with ca-app-pub-')

        return errors


class CapacitorGenerator:
    """Generates complete Capacitor project"""

    PLUGIN_VERSIONS = {
        '@capacitor/core': '^5.6.0',
        '@capacitor/cli': '^5.6.0',
        '@capacitor/android': '^5.6.0',
        '@capacitor/ios': '^5.6.0',
        '@capacitor/browser': '^5.1.0',
        '@capacitor/camera': '^5.0.8',
        '@capacitor/geolocation': '^5.0.6',
        '@capacitor/push-notifications': '^5.1.1',
        '@capacitor/share': '^5.0.6',
        '@capacitor/status-bar': '^5.0.6',
        '@capacitor/splash-screen': '^5.0.6',
        '@capacitor/keyboard': '^5.0.6',
        '@capacitor/network': '^5.0.6',
        '@capacitor/preferences': '^5.0.6',
        '@capacitor/app': '^5.0.6',
        '@capacitor/haptics': '^5.0.6',
        '@capacitor/device': '^5.0.6',
        '@capacitor-community/admob': '^5.0.0',
        '@capacitor-firebase/app': '^5.4.1',
        '@capacitor-firebase/authentication': '^5.4.1',
        '@capacitor-firebase/messaging': '^5.4.1',
        '@codetrix-studio/capacitor-google-auth': '^3.3.0',
    }

    def __init__(self, config):
        self.config = config
        self.files = {}

    def generate(self):
        """Generate all files and return ZIP bytes"""
        self._generate_package_json()
        self._generate_capacitor_config()
        self._generate_tsconfig()
        self._generate_gitignore()
        self._generate_www_files()
        self._generate_admob_service()
        self._generate_firebase_service()
        self._generate_android_files()
        self._generate_ios_files()
        self._generate_readme()

        return self._create_zip()

    def _generate_package_json(self):
        """Generate package.json"""
        config = self.config
        plugins = config.get('plugins', {})
        admob = config.get('admob', {})
        firebase = config.get('firebase', {})
        google_auth = config.get('googleAuth', {})

        dependencies = {
            "@capacitor/core": self.PLUGIN_VERSIONS['@capacitor/core'],
            "@capacitor/android": self.PLUGIN_VERSIONS['@capacitor/android'],
            "@capacitor/ios": self.PLUGIN_VERSIONS['@capacitor/ios'],
        }

        dev_dependencies = {
            "@capacitor/cli": self.PLUGIN_VERSIONS['@capacitor/cli'],
            "typescript": "^5.3.3",
        }

        # Add plugins based on selection
        plugin_mapping = {
            'browser': '@capacitor/browser',
            'camera': '@capacitor/camera',
            'geolocation': '@capacitor/geolocation',
            'share': '@capacitor/share',
            'statusBar': '@capacitor/status-bar',
            'splashScreen': '@capacitor/splash-screen',
            'keyboard': '@capacitor/keyboard',
            'network': '@capacitor/network',
            'storage': '@capacitor/preferences',
            'pushNotifications': '@capacitor/push-notifications',
            'haptics': '@capacitor/haptics',
            'device': '@capacitor/device',
            'app': '@capacitor/app',
        }

        for key, package in plugin_mapping.items():
            if plugins.get(key):
                dependencies[package] = self.PLUGIN_VERSIONS.get(package, '^5.0.0')

        # AdMob
        if admob.get('enabled'):
            dependencies['@capacitor-community/admob'] = self.PLUGIN_VERSIONS['@capacitor-community/admob']

        # Firebase
        if firebase.get('enabled'):
            dependencies['@capacitor-firebase/app'] = self.PLUGIN_VERSIONS['@capacitor-firebase/app']
            if firebase.get('messaging'):
                dependencies['@capacitor-firebase/messaging'] = self.PLUGIN_VERSIONS['@capacitor-firebase/messaging']
            if firebase.get('authentication'):
                dependencies['@capacitor-firebase/authentication'] = self.PLUGIN_VERSIONS['@capacitor-firebase/authentication']

        # Google Auth
        if google_auth.get('enabled'):
            dependencies['@codetrix-studio/capacitor-google-auth'] = self.PLUGIN_VERSIONS['@codetrix-studio/capacitor-google-auth']

        package_name_short = config['packageName'].split('.')[-1].lower()

        package_json = {
            "name": package_name_short,
            "version": config.get('version', '1.0.0'),
            "description": config.get('description', f"{config['appName']} - Capacitor App"),
            "author": config.get('author', ''),
            "license": "MIT",
            "scripts": {
                "build": "echo 'Build complete'",
                "sync": "npx cap sync",
                "open:android": "npx cap open android",
                "open:ios": "npx cap open ios",
                "build:android": "cd android && ./gradlew assembleDebug",
                "build:android:release": "cd android && ./gradlew assembleRelease",
                "run:android": "npx cap run android",
                "run:ios": "npx cap run ios"
            },
            "dependencies": dependencies,
            "devDependencies": dev_dependencies
        }

        self.files['package.json'] = json.dumps(package_json, indent=2)

    def _generate_capacitor_config(self):
        """Generate capacitor.config.ts"""
        config = self.config
        admob = config.get('admob', {})
        plugins = config.get('plugins', {})

        plugins_config = {}

        # SplashScreen
        if plugins.get('splashScreen'):
            plugins_config['SplashScreen'] = {
                'launchShowDuration': 2000,
                'backgroundColor': config.get('backgroundColor', '#ffffff'),
                'showSpinner': False,
                'androidScaleType': 'CENTER_CROP',
            }

        # StatusBar
        if plugins.get('statusBar'):
            plugins_config['StatusBar'] = {
                'style': config.get('statusBarStyle', 'dark'),
                'backgroundColor': config.get('statusBarColor', config.get('themeColor', '#3880ff')),
            }

        # Keyboard
        if plugins.get('keyboard'):
            plugins_config['Keyboard'] = {
                'resize': 'body',
                'resizeOnFullScreen': True,
            }

        # PushNotifications
        if plugins.get('pushNotifications'):
            plugins_config['PushNotifications'] = {
                'presentationOptions': ['badge', 'sound', 'alert'],
            }

        plugins_json = json.dumps(plugins_config, indent=4) if plugins_config else '{}'

        cap_config = f'''import {{ CapacitorConfig }} from '@capacitor/cli';

const config: CapacitorConfig = {{
  appId: '{config['packageName']}',
  appName: '{config['appName']}',
  webDir: 'www',
  server: {{
    url: '{config['appUrl']}',
    cleartext: true
  }},
  android: {{
    backgroundColor: '{config.get('backgroundColor', '#ffffff')}',
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: false
  }},
  ios: {{
    backgroundColor: '{config.get('backgroundColor', '#ffffff')}',
    contentInset: 'always',
    allowsLinkPreview: false,
    scrollEnabled: true
  }},
  plugins: {plugins_json}
}};

export default config;
'''
        self.files['capacitor.config.ts'] = cap_config

    def _generate_tsconfig(self):
        """Generate tsconfig.json"""
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "node",
                "esModuleInterop": True,
                "strict": True,
                "skipLibCheck": True,
                "resolveJsonModule": True
            },
            "include": ["src/**/*", "capacitor.config.ts"]
        }
        self.files['tsconfig.json'] = json.dumps(tsconfig, indent=2)

    def _generate_gitignore(self):
        """Generate .gitignore"""
        gitignore = '''# Dependencies
node_modules/

# Build
dist/
.cache/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Capacitor
android/app/build/
android/.gradle/
ios/App/Pods/
ios/App/App.xcworkspace/
ios/App/build/

# Environment
.env
.env.local

# Logs
*.log
npm-debug.log*

# Signing
*.keystore
*.jks
'''
        self.files['.gitignore'] = gitignore

    def _generate_www_files(self):
        """Generate www/ directory files"""
        config = self.config
        admob = config.get('admob', {})

        # index.html
        banner_css = '''
        #banner-container {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 50px;
            z-index: 9998;
        }
        body.banner-active #app-
 def _generate_www_files(self):
        """Generate www/ directory files"""
        config = self.config
        admob = config.get('admob', {})

        # index.html
        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="{config.get('themeColor', '#3880ff')}">
    <meta name="format-detection" content="telephone=no">
    <meta name="msapplication-tap-highlight" content="no">
    
    <title>{config['appName']}</title>
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: {config.get('backgroundColor', '#ffffff')};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }}
        
        #app-frame {{
            width: 100%;
            height: 100%;
            border: none;
            background-color: {config.get('backgroundColor', '#ffffff')};
        }}
        
        /* Loading Screen */
        #loading-screen {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: {config.get('backgroundColor', '#ffffff')};
            z-index: 9999;
            transition: opacity 0.3s ease;
        }}
        
        #loading-screen.hidden {{
            opacity: 0;
            pointer-events: none;
        }}
        
        .spinner {{
            width: 50px;
            height: 50px;
            border: 4px solid #e0e0e0;
            border-top-color: {config.get('themeColor', '#3880ff')};
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        
        .loading-text {{
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        /* Error Screen */
        #error-screen {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: {config.get('backgroundColor', '#ffffff')};
            z-index: 9999;
            padding: 20px;
            text-align: center;
        }}
        
        #error-screen.visible {{
            display: flex;
        }}
        
        .error-icon {{
            font-size: 60px;
            margin-bottom: 20px;
        }}
        
        .error-title {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .error-message {{
            font-size: 14px;
            color: #666;
            margin-bottom: 20px;
        }}
        
        .retry-button {{
            padding: 12px 30px;
            background-color: {config.get('themeColor', '#3880ff')};
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }}
        
        /* Banner Ad Space */
        #banner-container {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            min-height: 50px;
            background-color: transparent;
            z-index: 9998;
            display: none;
        }}
        
        body.banner-active #banner-container {{
            display: block;
        }}
        
        body.banner-active #app-frame {{
            height: calc(100% - 50px);
        }}
        
        /* Safe areas for notched devices */
        @supports (padding: max(0px)) {{
            body {{
                padding-top: max(0px, env(safe-area-inset-top));
                padding-bottom: max(0px, env(safe-area-inset-bottom));
                padding-left: max(0px, env(safe-area-inset-left));
                padding-right: max(0px, env(safe-area-inset-right));
            }}
        }}
    </style>
</head>
<body>
    <!-- Loading Screen -->
    <div id="loading-screen">
        <div class="spinner"></div>
        <p class="loading-text">Loading...</p>
    </div>
    
    <!-- Error Screen -->
    <div id="error-screen">
        <div class="error-icon">📡</div>
        <h1 class="error-title">Connection Error</h1>
        <p class="error-message">Unable to connect. Please check your internet connection.</p>
        <button class="retry-button" onclick="retryConnection()">Retry</button>
    </div>
    
    <!-- Main App Frame -->
    <iframe id="app-frame" src="{config['appUrl']}" allowfullscreen></iframe>
    
    <!-- Banner Ad Container -->
    <div id="banner-container"></div>

    <!-- Scripts -->
    <script src="js/app.js"></script>
</body>
</html>
'''
        self.files['www/index.html'] = index_html

        # app.js - Main Application JavaScript
        app_js = self._generate_app_js()
        self.files['www/js/app.js'] = app_js

    def _generate_app_js(self):
        """Generate the main app.js file"""
        config = self.config
        admob = config.get('admob', {})
        firebase = config.get('firebase', {})
        google_auth = config.get('googleAuth', {})
        plugins = config.get('plugins', {})

        # Build AdMob config string
        admob_android = admob.get('android', {})
        admob_ios = admob.get('ios', {})

        app_js = f'''/**
 * {config['appName']}
 * Generated by WrapifyAI
 * Version: {config.get('version', '1.0.0')}
 */

// ============================================
// APP CONFIGURATION
// ============================================

const APP_CONFIG = {{
    appName: '{config['appName']}',
    packageName: '{config['packageName']}',
    appUrl: '{config['appUrl']}',
    version: '{config.get('version', '1.0.0')}',
    themeColor: '{config.get('themeColor', '#3880ff')}',
    backgroundColor: '{config.get('backgroundColor', '#ffffff')}',
}};

// ============================================
// ADMOB CONFIGURATION
// ============================================

const ADMOB_CONFIG = {{
    enabled: {'true' if admob.get('enabled') else 'false'},
    testMode: {'true' if admob.get('testMode') else 'false'},
    android: {{
        appId: '{admob_android.get('appId', '')}',
        bannerId: '{admob_android.get('bannerId', '')}',
        interstitialId: '{admob_android.get('interstitialId', '')}',
        rewardedId: '{admob_android.get('rewardedId', '')}',
    }},
    ios: {{
        appId: '{admob_ios.get('appId', '')}',
        bannerId: '{admob_ios.get('bannerId', '')}',
        interstitialId: '{admob_ios.get('interstitialId', '')}',
        rewardedId: '{admob_ios.get('rewardedId', '')}',
    }}
}};

// ============================================
// FIREBASE CONFIGURATION
// ============================================

const FIREBASE_CONFIG = {{
    enabled: {'true' if firebase.get('enabled') else 'false'},
    messaging: {'true' if firebase.get('messaging') else 'false'},
    authentication: {'true' if firebase.get('authentication') else 'false'},
}};

// ============================================
// GOOGLE AUTH CONFIGURATION
// ============================================

const GOOGLE_AUTH_CONFIG = {{
    enabled: {'true' if google_auth.get('enabled') else 'false'},
    webClientId: '{google_auth.get('webClientId', '')}',
    iosClientId: '{google_auth.get('iosClientId', '')}',
}};

// ============================================
// DOM ELEMENTS
// ============================================

const loadingScreen = document.getElementById('loading-screen');
const errorScreen = document.getElementById('error-screen');
const appFrame = document.getElementById('app-frame');
const bannerContainer = document.getElementById('banner-container');

// ============================================
// CAPACITOR IMPORTS (loaded dynamically)
// ============================================

let Capacitor = null;
let AdMob = null;
let Browser = null;
let StatusBar = null;
let SplashScreen = null;
let PushNotifications = null;
let Device = null;
let Network = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {{
    console.log(`[${{APP_CONFIG.appName}}] Initializing app...`);
    
    try {{
        // Wait for Capacitor to be ready
        await initializeCapacitor();
        
        // Initialize plugins
        await initializePlugins();
        
        // Setup iframe events
        setupIframeEvents();
        
        // Initialize AdMob if enabled
        if (ADMOB_CONFIG.enabled) {{
            await initializeAdMob();
        }}
        
        // Initialize Firebase if enabled
        if (FIREBASE_CONFIG.enabled) {{
            await initializeFirebase();
        }}
        
        console.log(`[${{APP_CONFIG.appName}}] App initialized successfully`);
        
    }} catch (error) {{
        console.error('Initialization error:', error);
    }}
}});

// ============================================
// CAPACITOR INITIALIZATION
// ============================================

async function initializeCapacitor() {{
    return new Promise((resolve) => {{
        if (window.Capacitor) {{
            Capacitor = window.Capacitor;
            console.log('[Capacitor] Platform:', Capacitor.getPlatform());
            resolve();
        }} else {{
            // Running in browser
            console.log('[Capacitor] Running in browser mode');
            resolve();
        }}
    }});
}}

// ============================================
// PLUGIN INITIALIZATION
// ============================================

async function initializePlugins() {{
    try {{
        // Status Bar
        if (window.Capacitor?.Plugins?.StatusBar) {{
            StatusBar = window.Capacitor.Plugins.StatusBar;
            await StatusBar.setBackgroundColor({{ color: APP_CONFIG.themeColor }});
            console.log('[StatusBar] Initialized');
        }}
        
        // Splash Screen
        if (window.Capacitor?.Plugins?.SplashScreen) {{
            SplashScreen = window.Capacitor.Plugins.SplashScreen;
            // Hide splash after app loads
            setTimeout(() => {{
                SplashScreen.hide();
            }}, 2000);
            console.log('[SplashScreen] Initialized');
        }}
        
        // Network
        if (window.Capacitor?.Plugins?.Network) {{
            Network = window.Capacitor.Plugins.Network;
            Network.addListener('networkStatusChange', (status) => {{
                console.log('[Network] Status changed:', status);
                if (!status.connected) {{
                    showError('No internet connection');
                }}
            }});
            console.log('[Network] Initialized');
        }}
        
        // Device
        if (window.Capacitor?.Plugins?.Device) {{
            Device = window.Capacitor.Plugins.Device;
            const info = await Device.getInfo();
            console.log('[Device] Info:', info);
        }}
        
        // Push Notifications
        if (window.Capacitor?.Plugins?.PushNotifications) {{
            PushNotifications = window.Capacitor.Plugins.PushNotifications;
            await setupPushNotifications();
        }}
        
        // Browser (for external links)
        if (window.Capacitor?.Plugins?.Browser) {{
            Browser = window.Capacitor.Plugins.Browser;
            console.log('[Browser] Initialized');
        }}
        
    }} catch (error) {{
        console.error('[Plugins] Error initializing:', error);
    }}
}}

// ============================================
// ADMOB FUNCTIONS
// ============================================

async function initializeAdMob() {{
    try {{
        if (!window.Capacitor?.Plugins?.AdMob) {{
            console.log('[AdMob] Plugin not available');
            return;
        }}
        
        AdMob = window.Capacitor.Plugins.AdMob;
        
        // Initialize AdMob
        await AdMob.initialize({{
            testingDevices: ADMOB_CONFIG.testMode ? ['TEST_DEVICE_ID'] : [],
            initializeForTesting: ADMOB_CONFIG.testMode,
        }});
        
        console.log('[AdMob] Initialized successfully');
        
        // Setup event listeners
        AdMob.addListener('bannerAdLoaded', () => {{
            console.log('[AdMob] Banner loaded');
            document.body.classList.add('banner-active');
        }});
        
        AdMob.addListener('bannerAdFailedToLoad', (error) => {{
            console.error('[AdMob] Banner failed to load:', error);
            document.body.classList.remove('banner-active');
        }});
        
        AdMob.addListener('interstitialAdLoaded', () => {{
            console.log('[AdMob] Interstitial loaded');
        }});
        
        AdMob.addListener('rewardedAdLoaded', () => {{
            console.log('[AdMob] Rewarded ad loaded');
        }});
        
        AdMob.addListener('rewardedAdRewarded', (reward) => {{
            console.log('[AdMob] User rewarded:', reward);
            // Handle reward
            handleAdReward(reward);
        }});
        
        // Show banner ad
        await showBannerAd();
        
        // Preload interstitial
        await loadInterstitialAd();
        
        // Preload rewarded ad
        await loadRewardedAd();
        
    }} catch (error) {{
        console.error('[AdMob] Initialization error:', error);
    }}
}}

async function showBannerAd() {{
    if (!AdMob) return;
    
    const platform = Capacitor?.getPlatform() || 'web';
    const bannerId = platform === 'ios' 
        ? ADMOB_CONFIG.ios.bannerId 
        : ADMOB_CONFIG.android.bannerId;
    
    if (!bannerId) {{
        console.log('[AdMob] No banner ID configured');
        return;
    }}
    
    try {{
        await AdMob.showBanner({{
            adId: bannerId,
            adSize:
 adSize: 'BANNER',
            position: 'BOTTOM_CENTER',
            margin: 0,
        }});
        console.log('[AdMob] Banner shown');
    }} catch (error) {{
        console.error('[AdMob] Show banner error:', error);
    }}
}}

async function hideBannerAd() {{
    if (!AdMob) return;
    
    try {{
        await AdMob.hideBanner();
        document.body.classList.remove('banner-active');
        console.log('[AdMob] Banner hidden');
    }} catch (error) {{
        console.error('[AdMob] Hide banner error:', error);
    }}
}}

async function loadInterstitialAd() {{
    if (!AdMob) return;
    
    const platform = Capacitor?.getPlatform() || 'web';
    const interstitialId = platform === 'ios' 
        ? ADMOB_CONFIG.ios.interstitialId 
        : ADMOB_CONFIG.android.interstitialId;
    
    if (!interstitialId) return;
    
    try {{
        await AdMob.prepareInterstitial({{
            adId: interstitialId,
        }});
        console.log('[AdMob] Interstitial loaded');
    }} catch (error) {{
        console.error('[AdMob] Load interstitial error:', error);
    }}
}}

async function showInterstitialAd() {{
    if (!AdMob) return false;
    
    try {{
        await AdMob.showInterstitial();
        console.log('[AdMob] Interstitial shown');
        // Reload for next time
        await loadInterstitialAd();
        return true;
    }} catch (error) {{
        console.error('[AdMob] Show interstitial error:', error);
        return false;
    }}
}}

async function loadRewardedAd() {{
    if (!AdMob) return;
    
    const platform = Capacitor?.getPlatform() || 'web';
    const rewardedId = platform === 'ios' 
        ? ADMOB_CONFIG.ios.rewardedId 
        : ADMOB_CONFIG.android.rewardedId;
    
    if (!rewardedId) return;
    
    try {{
        await AdMob.prepareRewardVideoAd({{
            adId: rewardedId,
        }});
        console.log('[AdMob] Rewarded ad loaded');
    }} catch (error) {{
        console.error('[AdMob] Load rewarded error:', error);
    }}
}}

async function showRewardedAd() {{
    if (!AdMob) return false;
    
    try {{
        const result = await AdMob.showRewardVideoAd();
        console.log('[AdMob] Rewarded ad shown');
        // Reload for next time
        await loadRewardedAd();
        return true;
    }} catch (error) {{
        console.error('[AdMob] Show rewarded error:', error);
        return false;
    }}
}}

function handleAdReward(reward) {{
    console.log('[AdMob] Reward received:', reward);
    // Send message to iframe if needed
    if (appFrame && appFrame.contentWindow) {{
        appFrame.contentWindow.postMessage({{
            type: 'AD_REWARD',
            reward: reward
        }}, '*');
    }}
}}

// ============================================
// FIREBASE FUNCTIONS
// ============================================

async function initializeFirebase() {{
    try {{
        console.log('[Firebase] Initializing...');
        
        // Firebase App
        if (window.Capacitor?.Plugins?.FirebaseApp) {{
            console.log('[Firebase] App initialized');
        }}
        
        // Firebase Messaging
        if (FIREBASE_CONFIG.messaging && window.Capacitor?.Plugins?.FirebaseMessaging) {{
            const FirebaseMessaging = window.Capacitor.Plugins.FirebaseMessaging;
            
            // Request permission
            const permission = await FirebaseMessaging.requestPermissions();
            console.log('[Firebase] Messaging permission:', permission);
            
            if (permission.receive === 'granted') {{
                // Get FCM token
                const token = await FirebaseMessaging.getToken();
                console.log('[Firebase] FCM Token:', token.token);
                
                // Listen for messages
                FirebaseMessaging.addListener('notificationReceived', (notification) => {{
                    console.log('[Firebase] Notification received:', notification);
                }});
                
                FirebaseMessaging.addListener('notificationActionPerformed', (action) => {{
                    console.log('[Firebase] Notification action:', action);
                }});
            }}
        }}
        
        console.log('[Firebase] Initialized successfully');
        
    }} catch (error) {{
        console.error('[Firebase] Initialization error:', error);
    }}
}}

// ============================================
// PUSH NOTIFICATIONS
// ============================================

async function setupPushNotifications() {{
    if (!PushNotifications) return;
    
    try {{
        // Request permission
        const permission = await PushNotifications.requestPermissions();
        
        if (permission.receive === 'granted') {{
            // Register for push notifications
            await PushNotifications.register();
            
            // Listen for registration
            PushNotifications.addListener('registration', (token) => {{
                console.log('[Push] Token:', token.value);
            }});
            
            // Listen for errors
            PushNotifications.addListener('registrationError', (error) => {{
                console.error('[Push] Registration error:', error);
            }});
            
            // Listen for notifications
            PushNotifications.addListener('pushNotificationReceived', (notification) => {{
                console.log('[Push] Received:', notification);
            }});
            
            // Listen for notification actions
            PushNotifications.addListener('pushNotificationActionPerformed', (action) => {{
                console.log('[Push] Action:', action);
            }});
            
            console.log('[Push] Notifications initialized');
        }}
        
    }} catch (error) {{
        console.error('[Push] Setup error:', error);
    }}
}}

// ============================================
// IFRAME EVENTS
// ============================================

function setupIframeEvents() {{
    // Handle iframe load
    appFrame.addEventListener('load', () => {{
        console.log('[App] Iframe loaded');
        hideLoading();
    }});
    
    // Handle iframe errors
    appFrame.addEventListener('error', () => {{
        console.error('[App] Iframe error');
        showError('Failed to load content');
    }});
    
    // Listen for messages from iframe
    window.addEventListener('message', handleIframeMessage);
    
    // Set timeout for loading
    setTimeout(() => {{
        if (!loadingScreen.classList.contains('hidden')) {{
            hideLoading();
        }}
    }}, 10000); // 10 second timeout
}}

function handleIframeMessage(event) {{
    const data = event.data;
    
    if (!data || typeof data !== 'object') return;
    
    console.log('[App] Message from iframe:', data);
    
    switch (data.type) {{
        case 'SHOW_INTERSTITIAL':
            showInterstitialAd();
            break;
            
        case 'SHOW_REWARDED':
            showRewardedAd();
            break;
            
        case 'HIDE_BANNER':
            hideBannerAd();
            break;
            
        case 'SHOW_BANNER':
            showBannerAd();
            break;
            
        case 'OPEN_BROWSER':
            openInBrowser(data.url);
            break;
            
        case 'SHARE':
            shareContent(data.title, data.text, data.url);
            break;
    }}
}}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function hideLoading() {{
    loadingScreen.classList.add('hidden');
}}

function showLoading() {{
    loadingScreen.classList.remove('hidden');
    errorScreen.classList.remove('visible');
}}

function showError(message) {{
    document.querySelector('.error-message').textContent = message;
    errorScreen.classList.add('visible');
    loadingScreen.classList.add('hidden');
}}

function retryConnection() {{
    showLoading();
    errorScreen.classList.remove('visible');
    appFrame.src = APP_CONFIG.appUrl;
}}

async function openInBrowser(url) {{
    if (Browser) {{
        await Browser.open({{ url: url }});
    }} else {{
        window.open(url, '_blank');
    }}
}}

async function shareContent(title, text, url) {{
    if (window.Capacitor?.Plugins?.Share) {{
        try {{
            await window.Capacitor.Plugins.Share.share({{
                title: title,
                text: text,
                url: url,
            }});
        }} catch (error) {{
            console.error('[Share] Error:', error);
        }}
    }}
}}

// ============================================
// EXPOSE FUNCTIONS TO IFRAME
// ============================================

window.WrapifyAI = {{
    showInterstitialAd,
    showRewardedAd,
    showBannerAd,
    hideBannerAd,
    openInBrowser,
    shareContent,
    getConfig: () => APP_CONFIG,
    getAdMobConfig: () => ADMOB_CONFIG,
}};

// Make retry function global
window.retryConnection = retryConnection;

console.log('[{config['appName']}] App script loaded');
'''
        return app_js

    def _generate_admob_service(self):
        """Generate dedicated AdMob service file"""
        config = self.config
        admob = config.get('admob', {})
        
        if not admob.get('enabled'):
            return
        
        admob_android = admob.get('android', {})
        admob_ios = admob.get('ios', {})
        
        admob_service = f'''/**
 * AdMob Service for {config['appName']}
 * Generated by WrapifyAI
 * 
 * This file contains all AdMob configuration and helper functions.
 * Import this in your main app to use AdMob features.
 */

export const AdMobConfig = {{
    // ============================================
    // ANDROID AD UNIT IDS
    // ============================================
    android: {{
        appId: '{admob_android.get('appId', '')}',
        banner: '{admob_android.get('bannerId', '')}',
        interstitial: '{admob_android.get('interstitialId', '')}',
        rewarded: '{admob_android.get('rewardedId', '')}',
    }},
    
    // ============================================
    // IOS AD UNIT IDS
    // ============================================
    ios: {{
        appId: '{admob_ios.get('appId', '')}',
        banner: '{admob_ios.get('bannerId', '')}',
        interstitial: '{admob_ios.get('interstitialId', '')}',
        rewarded: '{admob_ios.get('rewardedId', '')}',
    }},
    
    // ============================================
    // SETTINGS
    // ============================================
    testMode: {'true' if admob.get('testMode') else 'false'},
    
    // Test device IDs (add your test devices here)
    testDevices: [
        // 'YOUR_TEST_DEVICE_ID_HERE',
    ],
}};

/**
 * Get the appropriate ad unit ID based on platform
 */
export function getAdUnitId(type, platform) {{
    const platformConfig = platform === 'ios' ? AdMobConfig.ios : AdMobConfig.android;
    
    switch (type) {{
        case 'banner':
            return platformConfig.banner;
        case 'interstitial':
            return platformConfig.interstitial;
        case 'rewarded':
            return platformConfig.rewarded;
        default:
            return null;
    }}
}}

export default AdMobConfig;
'''
        self.files['www/js/admob-config.js'] = admob_service

    def _generate_firebase_service(self):
        """Generate Firebase service file"""
        config = self.config
        firebase = config.get('firebase', {})
        
        if not firebase.get('enabled'):
            return
        
        firebase_service = f'''/**
 * Firebase Service for {config['appName']}
 * Generated by WrapifyAI
 */

export const FirebaseConfig = {{
    enabled: true,
    messaging: {'true' if firebase.get('messaging') else 'false'},
    authentication: {'true' if firebase.get('authentication') else 'false'},
}};

/**
 * Initialize Firebase services
 */
export async function initializeFirebase() {{
    if (!window.Capacitor?.Plugins) {{
        console.log('[Firebase] Capacitor not available');
        return false;
    }}
    
    try {{
        // Initialize messaging if enabled
        if (FirebaseConfig.messaging) {{
            await initializeMessaging();
        }}
        
        // Initialize authentication if enabled
        if (FirebaseConfig.authentication) {{
            await initializeAuthentication();
        }}
        
        return true;
    }} catch (error) {{
        console.error('[Firebase] Init error:', error);
        return false;
    }}
}}

async function initializeMessaging() {{
    const {{ FirebaseMessaging }} = window.Capacitor.Plugins;
    
    if (!FirebaseMessaging) return;
    
    const permission = await FirebaseMessaging.requestPermissions();
    
    if (permission.receive === 'granted') {{
        const {{ token }} = await FirebaseMessaging.getToken();
        console.log('[Firebase] FCM Token:', token);
        return token;
    }}
    
    return null;
}}

async function initializeAuthentication() {{
    // Authentication initialization logic
    console.log('[Firebase] Authentication ready');
}}

export default FirebaseConfig;
'''
        self.files['www/js/firebase-config.js'] = firebase_service

    def _generate_android_files(self):
        """Generate Android-specific files"""
        config = self.config
        admob = config.get('admob', {})
        firebase = config.get('firebase', {})
        package_path = config['packageName'].replace('.', '/')
        
        # ============================================
        # AndroidManifest.xml
        # ============================================
        
        admob_meta = ''
        if admob.get('enabled') and admob.get('android', {}).get('appId'):
            admob_meta = f'''
        <!-- AdMob App ID -->
        <meta-data
            android:name="com.google.android.gms.ads.APPLICATION_ID"
            android:value="{admob['android']['appId']}"/>'''
        
        permissions = '''
    <!-- Basic Permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />'''
        
        if config.get('plugins', {}).get('camera'):
            permissions += '''
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />'''
        
        if config.get('plugins', {}).get('geolocation'):
            permissions += '''
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />'''
        
        android_manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{config['packageName']}">
{permissions}

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round
 android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true"
        android:hardwareAccelerated="true">{admob_meta}

        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|smallestScreenSize|screenLayout|uiMode"
            android:exported="true"
            android:launchMode="singleTask"
            android:screenOrientation="{config.get('orientation', 'portrait')}"
            android:theme="@style/AppTheme.NoActionBar">

            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>

            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="@string/custom_url_scheme" />
            </intent-filter>

        </activity>

        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${{applicationId}}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>

    </application>
</manifest>
'''
        self.files[f'android/app/src/main/AndroidManifest.xml'] = android_manifest

        # ============================================
        # strings.xml
        # ============================================
        strings_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{config['appName']}</string>
    <string name="title_activity_main">{config['appName']}</string>
    <string name="package_name">{config['packageName']}</string>
    <string name="custom_url_scheme">{config['packageName']}</string>
</resources>
'''
        self.files['android/app/src/main/res/values/strings.xml'] = strings_xml

        # ============================================
        # colors.xml
        # ============================================
        colors_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="colorPrimary">{config.get('themeColor', '#3880ff')}</color>
    <color name="colorPrimaryDark">{config.get('themeColor', '#3880ff')}</color>
    <color name="colorAccent">{config.get('themeColor', '#3880ff')}</color>
    <color name="backgroundColor">{config.get('backgroundColor', '#ffffff')}</color>
    <color name="statusBarColor">{config.get('statusBarColor', config.get('themeColor', '#3880ff'))}</color>
</resources>
'''
        self.files['android/app/src/main/res/values/colors.xml'] = colors_xml

        # ============================================
        # styles.xml
        # ============================================
        styles_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <!-- Base application theme -->
    <style name="AppTheme" parent="Theme.AppCompat.Light.DarkActionBar">
        <item name="colorPrimary">@color/colorPrimary</item>
        <item name="colorPrimaryDark">@color/colorPrimaryDark</item>
        <item name="colorAccent">@color/colorAccent</item>
        <item name="android:windowBackground">@color/backgroundColor</item>
    </style>

    <style name="AppTheme.NoActionBar" parent="Theme.AppCompat.Light.NoActionBar">
        <item name="colorPrimary">@color/colorPrimary</item>
        <item name="colorPrimaryDark">@color/colorPrimaryDark</item>
        <item name="colorAccent">@color/colorAccent</item>
        <item name="android:windowBackground">@color/backgroundColor</item>
        <item name="android:statusBarColor">@color/statusBarColor</item>
        <item name="android:windowLightStatusBar">false</item>
    </style>

    <!-- Splash Screen Theme -->
    <style name="AppTheme.NoActionBarLaunch" parent="Theme.SplashScreen">
        <item name="android:windowBackground">@color/backgroundColor</item>
        <item name="android:statusBarColor">@color/statusBarColor</item>
    </style>
</resources>
'''
        self.files['android/app/src/main/res/values/styles.xml'] = styles_xml

        # ============================================
        # build.gradle (app level)
        # ============================================
        firebase_plugin = ''
        firebase_deps = ''
        if firebase.get('enabled'):
            firebase_plugin = "apply plugin: 'com.google.gms.google-services'"
            firebase_deps = '''
    // Firebase
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-analytics'
    implementation 'com.google.firebase:firebase-messaging'
'''

        admob_deps = ''
        if admob.get('enabled'):
            admob_deps = '''
    // AdMob
    implementation 'com.google.android.gms:play-services-ads:22.6.0'
'''

        app_build_gradle = f'''apply plugin: 'com.android.application'
{firebase_plugin}

android {{
    namespace "{config['packageName']}"
    compileSdkVersion rootProject.ext.compileSdkVersion
    
    defaultConfig {{
        applicationId "{config['packageName']}"
        minSdkVersion rootProject.ext.minSdkVersion
        targetSdkVersion rootProject.ext.targetSdkVersion
        versionCode {config.get('versionCode', 1)}
        versionName "{config.get('version', '1.0.0')}"
        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }}
    
    buildTypes {{
        release {{
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
        }}
    }}
    
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
}}

repositories {{
    flatDir {{
        dirs '../capacitor-cordova-android-plugins/src/main/libs', 'libs'
    }}
}}

dependencies {{
    implementation fileTree(include: ['*.jar'], dir: 'libs')
    implementation "androidx.appcompat:appcompat:$androidxAppCompatVersion"
    implementation "androidx.coordinatorlayout:coordinatorlayout:$androidxCoordinatorLayoutVersion"
    implementation "androidx.core:core-splashscreen:$coreSplashScreenVersion"
    implementation project(':capacitor-android')
    testImplementation "junit:junit:$junitVersion"
    androidTestImplementation "androidx.test.ext:junit:$androidxJunitVersion"
    androidTestImplementation "androidx.test.espresso:espresso-core:$androidxEspressoCoreVersion"
    implementation project(':capacitor-cordova-android-plugins')
{admob_deps}{firebase_deps}
}}

apply from: 'capacitor.build.gradle'
'''
        self.files['android/app/build.gradle'] = app_build_gradle

        # ============================================
        # build.gradle (project level)
        # ============================================
        firebase_classpath = ''
        if firebase.get('enabled'):
            firebase_classpath = "        classpath 'com.google.gms:google-services:4.4.0'"

        project_build_gradle = f'''// Top-level build file where you can add configuration options common to all sub-projects/modules.

buildscript {{
    repositories {{
        google()
        mavenCentral()
    }}
    dependencies {{
        classpath 'com.android.tools.build:gradle:8.2.1'
{firebase_classpath}
    }}
}}

apply from: "variables.gradle"

allprojects {{
    repositories {{
        google()
        mavenCentral()
    }}
}}

task clean(type: Delete) {{
    delete rootProject.buildDir
}}
'''
        self.files['android/build.gradle'] = project_build_gradle

        # ============================================
        # variables.gradle
        # ============================================
        variables_gradle = '''ext {
    minSdkVersion = 22
    compileSdkVersion = 34
    targetSdkVersion = 34
    androidxAppCompatVersion = '1.6.1'
    androidxCoordinatorLayoutVersion = '1.2.0'
    coreSplashScreenVersion = '1.0.1'
    androidxJunitVersion = '1.1.5'
    junitVersion = '4.13.2'
    androidxEspressoCoreVersion = '3.5.1'
}
'''
        self.files['android/variables.gradle'] = variables_gradle

        # ============================================
        # settings.gradle
        # ============================================
        settings_gradle = f'''include ':app'
include ':capacitor-android'
project(':capacitor-android').projectDir = new File('../node_modules/@capacitor/android/capacitor')
include ':capacitor-cordova-android-plugins'
project(':capacitor-cordova-android-plugins').projectDir = new File('../node_modules/@capacitor/android/capacitor-cordova-android-plugins')
'''
        self.files['android/settings.gradle'] = settings_gradle

        # ============================================
        # gradle.properties
        # ============================================
        gradle_properties = '''# Project-wide Gradle settings.
org.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.enableJetifier=true
android.nonTransitiveRClass=true
'''
        self.files['android/gradle.properties'] = gradle_properties

        # ============================================
        # MainActivity.java
        # ============================================
        main_activity = f'''package {config['packageName']};

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {{
    @Override
    public void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
    }}
}}
'''
        self.files[f'android/app/src/main/java/{package_path}/MainActivity.java'] = main_activity

        # ============================================
        # file_paths.xml
        # ============================================
        file_paths_xml = '''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <external-path name="my_images" path="." />
    <cache-path name="cache" path="." />
    <files-path name="files" path="." />
</paths>
'''
        self.files['android/app/src/main/res/xml/file_paths.xml'] = file_paths_xml

        # ============================================
        # capacitor.build.gradle
        # ============================================
        capacitor_build_gradle = '''// DO NOT EDIT THIS FILE! IT IS GENERATED EACH TIME "capacitor update android" IS RUN
'''
        self.files['android/app/capacitor.build.gradle'] = capacitor_build_gradle

        # ============================================
        # proguard-rules.pro
        # ============================================
        proguard_rules = '''# Add project specific ProGuard rules here.

# Capacitor
-keep class com.getcapacitor.** { *; }
-keep @com.getcapacitor.annotation.CapacitorPlugin public class * { *; }

# AdMob
-keep class com.google.android.gms.ads.** { *; }

# Firebase
-keep class com.google.firebase.** { *; }
'''
        self.files['android/app/proguard-rules.pro'] = proguard_rules

    def _generate_ios_files(self):
        """Generate iOS-specific files"""
        config = self.config
        admob = config.get('admob', {})
        firebase = config.get('firebase', {})
        google_auth = config.get('googleAuth', {})

        # ============================================
        # Info.plist
        # ============================================
        admob_plist = ''
        if admob.get('enabled') and admob.get('ios', {}).get('appId'):
            admob_plist = f'''
    <key>GADApplicationIdentifier</key>
    <string>{admob['ios']['appId']}</string>
    <key>GADIsAdManagerApp</key>
    <true/>
    <key>SKAdNetworkItems</key>
    <array>
        <dict>
            <key>SKAdNetworkIdentifier</key>
            <string>cstr6suwn9.skadnetwork</string>
        </dict>
        <dict>
            <key>SKAdNetworkIdentifier</key>
            <string>4fzdc2evr5.skadnetwork</string>
        </dict>
        <dict>
            <key>SKAdNetworkIdentifier</key>
            <string>2fnua5tdw4.skadnetwork</string>
        </dict>
    </array>'''

        google_auth_plist = ''
        if google_auth.get('enabled') and google_auth.get('iosUrlScheme'):
            google_auth_plist = f'''
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLName</key>
            <string>google</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>{google_auth['iosUrlScheme']}</string>
            </array>
        </dict>
    </array>
    <key>GIDClientID</key>
    <string>{google_auth.get('iosClientId', '')}</string>'''

        camera_plist = ''
        if config.get('plugins', {}).get('camera'):
            camera_plist = '''
    <key>NSCameraUsageDescription</key>
    <string>This app needs access to the camera to take photos.</string>
    <key>NSPhotoLibraryUsageDescription</key>
    <string>This app needs access to the photo library to select photos.</string>
    <key>NSPhotoLibraryAddUsageDescription</key>
    <string>This app needs access to save photos to your library.</string>'''

        location_plist = ''
        if config.get('plugins', {}).get('geolocation'):
            location_plist = '''
    <key>NSLocationWhenInUseUsageDescription</key>
    <string>This app needs access to your location.</string>
    <key>NSLocationAlwaysUsageDescription</key>
    <string>This app needs access to your location.</string>'''

        info_plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>{config['appName']}</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoD
  <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{config['appName']}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{config.get('version', '1.0.0')}</string>
    <key>CFBundleVersion</key>
    <string>{config.get('versionCode', 1)}</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UILaunchStoryboardName</key>
    <string>LaunchScreen</string>
    <key>UIMainStoryboardFile</key>
    <string>Main</string>
    <key>UIRequiredDeviceCapabilities</key>
    <array>
        <string>armv7</string>
    </array>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
    </array>
    <key>UISupportedInterfaceOrientations~ipad</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationPortraitUpsideDown</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
    <key>UIViewControllerBasedStatusBarAppearance</key>
    <true/>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>{admob_plist}{google_auth_plist}{camera_plist}{location_plist}
</dict>
</plist>
'''
        self.files['ios/App/App/Info.plist'] = info_plist

        # ============================================
        # AppDelegate.swift
        # ============================================
        firebase_import = ''
        firebase_config = ''
        if firebase.get('enabled'):
            firebase_import = 'import FirebaseCore'
            firebase_config = '        FirebaseApp.configure()'

        google_auth_import = ''
        google_auth_config = ''
        if google_auth.get('enabled'):
            google_auth_import = 'import GoogleSignIn'
            google_auth_config = '''
    
    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        return GIDSignIn.sharedInstance.handle(url)
    }'''

        app_delegate = f'''import UIKit
import Capacitor
{firebase_import}
{google_auth_import}

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {{

    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {{
{firebase_config}
        return true
    }}

    func applicationWillResignActive(_ application: UIApplication) {{
    }}

    func applicationDidEnterBackground(_ application: UIApplication) {{
    }}

    func applicationWillEnterForeground(_ application: UIApplication) {{
    }}

    func applicationDidBecomeActive(_ application: UIApplication) {{
    }}

    func applicationWillTerminate(_ application: UIApplication) {{
    }}

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {{
        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }}

    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {{
        return ApplicationDelegateProxy.shared.application(application, continue: userActivity, restorationHandler: restorationHandler)
    }}
{google_auth_config}
}}
'''
        self.files['ios/App/App/AppDelegate.swift'] = app_delegate

        # ============================================
        # Podfile
        # ============================================
        firebase_pods = ''
        if firebase.get('enabled'):
            firebase_pods = '''
  # Firebase
  pod 'FirebaseCore'
  pod 'FirebaseMessaging'
  pod 'FirebaseAnalytics'
'''

        google_auth_pods = ''
        if google_auth.get('enabled'):
            google_auth_pods = '''
  # Google Sign-In
  pod 'GoogleSignIn'
'''

        admob_pods = ''
        if admob.get('enabled'):
            admob_pods = '''
  # Google Mobile Ads (AdMob)
  pod 'Google-Mobile-Ads-SDK'
'''

        podfile = f'''require_relative '../../node_modules/@capacitor/ios/scripts/pods_helpers'

platform :ios, '13.0'
use_frameworks!

# workaround to avoid Xcode caching of Pods that requires
# temporary clearing of FRAMEWORKS_SEARCH_PATHS
install! 'cocoapods', :disable_input_output_paths => true

def capacitor_pods
  pod 'Capacitor', :path => '../../node_modules/@capacitor/ios'
  pod 'CapacitorCordova', :path => '../../node_modules/@capacitor/ios'
end

target 'App' do
  capacitor_pods
  # Add your Pods here
{firebase_pods}{google_auth_pods}{admob_pods}
end

post_install do |installer|
  assertDeploymentTarget(installer)
  
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '13.0'
    end
  end
end
'''
        self.files['ios/App/Podfile'] = podfile

        # ============================================
        # ViewController.swift (Main)
        # ============================================
        view_controller = f'''import UIKit
import Capacitor

class ViewController: CAPBridgeViewController {{
    
    override func viewDidLoad() {{
        super.viewDidLoad()
        // Additional setup after loading the view
    }}
    
    override var preferredStatusBarStyle: UIStatusBarStyle {{
        return .lightContent
    }}
    
    override var prefersStatusBarHidden: Bool {{
        return false
    }}
}}
'''
        self.files['ios/App/App/ViewController.swift'] = view_controller

    def _generate_readme(self):
        """Generate comprehensive README.md"""
        config = self.config
        admob = config.get('admob', {})
        firebase = config.get('firebase', {})
        google_auth = config.get('googleAuth', {})
        plugins = config.get('plugins', {})

        # Build plugins table
        plugins_table = ''
        plugin_list = [
            ('Browser', plugins.get('browser'), '@capacitor/browser'),
            ('Camera', plugins.get('camera'), '@capacitor/camera'),
            ('Geolocation', plugins.get('geolocation'), '@capacitor/geolocation'),
            ('Share', plugins.get('share'), '@capacitor/share'),
            ('Status Bar', plugins.get('statusBar'), '@capacitor/status-bar'),
            ('Splash Screen', plugins.get('splashScreen'), '@capacitor/splash-screen'),
            ('Keyboard', plugins.get('keyboard'), '@capacitor/keyboard'),
            ('Network', plugins.get('network'), '@capacitor/network'),
            ('Storage', plugins.get('storage'), '@capacitor/preferences'),
            ('Push Notifications', plugins.get('pushNotifications'), '@capacitor/push-notifications'),
            ('Haptics', plugins.get('haptics'), '@capacitor/haptics'),
            ('Device', plugins.get('device'), '@capacitor/device'),
            ('App', plugins.get('app'), '@capacitor/app'),
        ]

        for name, enabled, package in plugin_list:
            status = '✅ Enabled' if enabled else '❌ Disabled'
            plugins_table += f'| {name} | `{package}` | {status} |\n'

        # AdMob section
        admob_section = ''
        if admob.get('enabled'):
            admob_android = admob.get('android', {})
            admob_ios = admob.get('ios', {})
            admob_section = f'''
## 💰 AdMob Configuration

AdMob is **enabled** in this project.

### Android Ad Unit IDs

| Ad Type | Ad Unit ID |
|---------|------------|
| App ID | `{admob_android.get('appId', 'Not configured')}` |
| Banner | `{admob_android.get('bannerId', 'Not configured')}` |
| Interstitial | `{admob_android.get('interstitialId', 'Not configured')}` |
| Rewarded | `{admob_android.get('rewardedId', 'Not configured')}` |

### iOS Ad Unit IDs

| Ad Type | Ad Unit ID |
|---------|------------|
| App ID | `{admob_ios.get('appId', 'Not configured')}` |
| Banner | `{admob_ios.get('bannerId', 'Not configured')}` |
| Interstitial | `{admob_ios.get('interstitialId', 'Not configured')}` |
| Rewarded | `{admob_ios.get('rewardedId', 'Not configured')}` |

### Where AdMob IDs are Configured

- **Android**: `android/app/src/main/AndroidManifest.xml`
- **iOS**: `ios/App/App/Info.plist`
- **JavaScript**: `www/js/app.js` and `www/js/admob-config.js`

### Using Ads in Your App

```javascript
// Show banner ad
window.WrapifyAI.showBannerAd();

// Hide banner ad
window.WrapifyAI.hideBannerAd();

// Show interstitial ad
await window.WrapifyAI.showInterstitialAd();

// Show rewarded ad
await window.WrapifyAI.showRewardedAd();
// Request interstitial ad
window.parent.postMessage({{ type: 'SHOW_INTERSTITIAL' }}, '*');

// Request rewarded ad
window.parent.postMessage({{ type: 'SHOW_REWARDED' }}, '*');

// Hide banner
window.parent.postMessage({{ type: 'HIDE_BANNER' }}, '*');

// Show banner
window.parent.postMessage({{ type: 'SHOW_BANNER' }}, '*');
    # Firebase section
    firebase_section = ''
    if firebase.get('enabled'):
        firebase_section = f'''

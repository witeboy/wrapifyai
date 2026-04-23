from http.server import BaseHTTPRequestHandler
import json
import base64
import zipfile
import io
from datetime import datetime


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
        self._generate_app_js()
        self._generate_admob_service()
        self._generate_firebase_service()
        self._generate_android_files()
        self._generate_ios_files()
        self._generate_readme()

        return self._create_zip()

    def _create_zip(self):
        """Create ZIP file from self.files dict"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filepath, content in self.files.items():
                zf.writestr(filepath, content)
        return zip_buffer.getvalue()

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

        if admob.get('enabled'):
            dependencies['@capacitor-community/admob'] = self.PLUGIN_VERSIONS['@capacitor-community/admob']

        if firebase.get('enabled'):
            dependencies['@capacitor-firebase/app'] = self.PLUGIN_VERSIONS['@capacitor-firebase/app']
            if firebase.get('messaging'):
                dependencies['@capacitor-firebase/messaging'] = self.PLUGIN_VERSIONS['@capacitor-firebase/messaging']
            if firebase.get('authentication'):
                dependencies['@capacitor-firebase/authentication'] = self.PLUGIN_VERSIONS['@capacitor-firebase/authentication']

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
        plugins = config.get('plugins', {})

        plugins_config = {}

        if plugins.get('splashScreen'):
            plugins_config['SplashScreen'] = {
                'launchShowDuration': 2000,
                'backgroundColor': config.get('backgroundColor', '#ffffff'),
                'showSpinner': False,
                'androidScaleType': 'CENTER_CROP',
            }

        if plugins.get('statusBar'):
            plugins_config['StatusBar'] = {
                'style': config.get('statusBarStyle', 'dark'),
                'backgroundColor': config.get('statusBarColor', config.get('themeColor', '#3880ff')),
            }

        if plugins.get('keyboard'):
            plugins_config['Keyboard'] = {
                'resize': 'body',
                'resizeOnFullScreen': True,
            }

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
            border-top-color: {config

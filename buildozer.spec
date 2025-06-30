[app]
title = Passenger
package.name = carwash
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# (list) Application requirements
requirements = python3,kivy,plyer

# (str) Custom source folders for requirements
# (Separate multiple paths with commas)
# requirements.source =

# (list) Permissions
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# (str) Android entry point, default is ok
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, default is 'import android' (crashes without it)
#android.theme = '@android:style/Theme.NoTitleBar'

# (str) Package the .apk to be signed with a debug key
#android.debug = 1

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Pattern to whitelist for the whole project
# whitelist = *

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (str) Supported architectures
# android.arch = armeabi-v7a, arm64-v8a, x86, x86_64

# (str) Minimum API your APK will support
android.minapi = 21

# (str) Target API your APK will support
android.api = 33

# (str) Android NDK version to use
# android.ndk = 23b

# (str) Android NDK API to use
# android.ndk_api = 21

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (bool) Hide the statusbar
# android.hide_statusbar = 1

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
# orientation = portrait

# (bool) Android logcat filters to use
# android.logcat_filters = *:S python:D

# (str) Android entry point, default is ok
# android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, default is 'import android' (crashes without it)
# android.theme = '@android:style/Theme.NoTitleBar'

# (str) Package the .apk to be signed with a debug key
# android.debug = 1

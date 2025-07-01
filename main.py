from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy_garden.mapview import MapView, MapMarker
import requests
import threading
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.utils import platform
# type: ignore
# برای دریافت لوکیشن فعلی
try:
    from plyer import gps
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False

# تنظیمات سرور
SERVER_URL = "https://carwash-d5ot.onrender.com/send_location"
API_TOKEN = "my_secret_token"

class MainScreen(BoxLayout):
    def __init__(self, screen_manager, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=10, **kwargs)
        self.screen_manager = screen_manager

        # عنوان برنامه
        title_label = Label(
            text='CARWASH',
            size_hint_y=None, 
            height=60,
            font_size='20sp',
            bold=True
        )
        self.add_widget(title_label)

        # ورودی شناسه کاربر
        self.user_id_input = TextInput(
            hint_text='Enter your ID',
            size_hint_y=None, 
            height=50,
            multiline=False
        )
        self.add_widget(self.user_id_input)
        
        # نمایش لوکیشن انتخاب شده
        self.location_label = Label(
            text='No location selected',
            size_hint_y=None, 
            height=40,
            color=(0.7, 0.7, 0.7, 1)
        )
        self.add_widget(self.location_label)

        # دکمه دریافت لوکیشن فعلی

        # دکمه انتخاب لوکیشن
        self.select_location_btn = Button(
            text='Select location on the map',
            size_hint_y=None, 
            height=50,
            background_color=(0.2, 0.6, 1, 1)
        )
        self.select_location_btn.bind(on_press=self.select_location)  # type: ignore
        self.add_widget(self.select_location_btn)

        # دکمه ارسال
        self.send_btn = Button(
            text='Send location to server',
            size_hint_y=None, 
            height=50, 
            disabled=True,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.send_btn.bind(on_press=self.send_location)  # type: ignore
        self.add_widget(self.send_btn)

        # نمایش وضعیت
        self.status_label = Label(
            text='',
            size_hint_y=None, 
            height=40,
            color=(0.3, 0.3, 0.3, 1)
        )
        self.add_widget(self.status_label)

        self.selected_latlon = None

    def get_current_location(self, instance):
        if not GPS_AVAILABLE:
            self.status_label.text = "GPS not available. Please select location manually."
            return
        


        try:
            gps.configure(on_location=self.on_location) # type: ignore
            gps.start() # type: ignore
        except Exception as e:
            self.status_label.text = f"GPS error: {str(e)}"


    def on_location(self, **kwargs):
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        
        if lat and lon:
            self.set_location(lat, lon)
            self.status_label.text = "Current location received!"
            gps.stop() # type: ignore
        else:
            self.status_label.text = "Could not get current location"
        

    def select_location(self, instance):
        if not self.user_id_input.text.strip():
            self.status_label.text = "Please enter your ID first"
            return
        self.screen_manager.transition = SlideTransition(direction='left')
        self.screen_manager.current = 'map'

    def set_location(self, lat, lon):
        self.selected_latlon = (lat, lon)
        self.location_label.text = f'Selected location: {lat:.5f}, {lon:.5f}'
        self.location_label.color = (0.2, 0.8, 0.2, 1)
        self.send_btn.disabled = False
        self.status_label.text = "Location selected. You can now send it."

    def send_location(self, instance):
        user_id = self.user_id_input.text.strip()
        if not user_id or not self.selected_latlon:
            self.status_label.text = "Please enter your ID and location"
            return
        
        # غیرفعال کردن دکمه در حین ارسال
        self.send_btn.disabled = True
        self.send_btn.text = "Sending..."
        self.status_label.text = "Sending location..."
        
        # ارسال در thread جداگانه
        threading.Thread(target=self._send_location_thread, args=(user_id,)).start()

    def _send_location_thread(self, user_id):
        try:
            if self.selected_latlon is None:
                # Use Clock.schedule_once to safely update UI from thread
                Clock.schedule_once(lambda dt: self._update_status_error("No location selected"))
                return
            lat, lon = self.selected_latlon
            data = {
                "user_id": user_id,
                "lat": lat,
                "lon": lon,
                "token": API_TOKEN
            }
            
            resp = requests.post(SERVER_URL, json=data, timeout=30)
            
            # بازگشت به thread اصلی برای به‌روزرسانی UI
            Clock.schedule_once(lambda dt: self._update_status(resp))
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self._update_status_error(str(e)))

    def _update_status(self, response):
        if response.status_code == 200 and response.json().get('status') == 'ok':
            self.status_label.text = "✅ Location sent successfully!"
            self.status_label.color = (0.2, 0.8, 0.2, 1)
        else:
            error_msg = response.json().get('message', 'Unknown error') if response.status_code != 200 else 'Error sending'
            self.status_label.text = f"❌ Error: {error_msg}"
            self.status_label.color = (0.8, 0.2, 0.2, 1)
        
        self.send_btn.disabled = False
        self.send_btn.text = "Send location to server"

    def _update_status_error(self, error_msg):
        self.status_label.text = f"❌ Error: {error_msg}"
        self.status_label.color = (0.8, 0.2, 0.2, 1)
        self.send_btn.disabled = False
        self.send_btn.text = "Send location to server"



class MapScreen(Screen):
    def __init__(self, main_screen, **kwargs):
        super().__init__(**kwargs)
        self.main_screen = main_screen

        layout = BoxLayout(orientation='vertical')

        # استفاده از FloatLayout برای قرار دادن دکمه روی نقشه
        map_container = FloatLayout(size_hint=(1, 1))

        self.mapview = MapView(
            zoom=15,
            lat=35.6892,
            lon=51.3890,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.marker = None
        self.selected_latlon = None
        self.mapview.bind(on_touch_down=self.on_map_touch)  # type: ignore
        map_container.add_widget(self.mapview)

        # دکمه "Find Me" روی نقشه (گوشه پایین راست)
        self.find_me_btn = Button(
            text='📍',
            size_hint=(None, None),
            size=(48, 48),
            pos_hint={'right': 0.98, 'y': 0.02},
            background_color=(0.2, 0.6, 1, 1)
        )
        self.find_me_btn.bind(on_press=self.center_on_current_location)  # type: ignore
        map_container.add_widget(self.find_me_btn)
# دکمه برگشت بالای نقشه
        self.back_btn = Button(
            text='Back',
            size_hint=(None, None),
            size=(80, 40),
            pos_hint={'x': 0.02, 'top': 0.98},
            background_color=(1, 0.5, 0.2, 1)
        )
        self.back_btn.bind(on_press=self.go_back)  # type: ignore
        map_container.add_widget(self.back_btn)

        layout.add_widget(map_container)

        # دکمه تأیید زیر نقشه
        self.confirm_btn = Button(
            text='Confirm Location',
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.8, 0.2, 1),
            disabled=True
        )
        self.confirm_btn.bind(on_press=self.confirm_location)  # type: ignore
        layout.add_widget(self.confirm_btn)

        self.add_widget(layout)

    def on_map_touch(self, instance, touch):
        if not self.mapview.collide_point(*touch.pos):
            return False
        # فقط لمس تک انگشتی و بدون حرکت زیاد
        if len(touch.device.touch_ids) > 1:
            return False
        if touch.is_double_tap:
            return False
        if abs(touch.dx) > 5 or abs(touch.dy) > 5:
            return False
        if touch.is_mouse_scrolling:
            return False
        # فقط tap ساده
        map_x = touch.x - self.mapview.x
        map_y = touch.y - self.mapview.y
        lat, lon = self.mapview.get_latlon_at(map_x, map_y)
        if self.marker:
            self.mapview.remove_marker(self.marker)
        self.marker = MapMarker(lat=lat, lon=lon)
        self.mapview.add_marker(self.marker)
        self.selected_latlon = (lat, lon)
        self.confirm_btn.disabled = False
        return True
        
    def confirm_location(self, instance):
        if self.selected_latlon:
            lat, lon = self.selected_latlon
            self.main_screen.set_location(lat, lon)
        self.parent.transition = SlideTransition(direction='right')
        self.parent.current = 'main'

    def center_on_current_location(self, instance):
        if GPS_AVAILABLE:
            try:
                gps.configure(on_location=self._center_on_location)  # type: ignore
                gps.start()  # type: ignore
            except Exception as e:
                self.show_status("GPS کار نمی‌کند: " + str(e))
                threading.Thread(target=self._get_ip_location).start()
        else:
            self.show_status("GPS در دسترس نیست. از موقعیت IP استفاده می‌شود.")
            threading.Thread(target=self._get_ip_location).start()

    def show_status(self, msg):
        from kivy.uix.popup import Popup
        popup = Popup(title='وضعیت', content=Label(text=msg), size_hint=(0.8, 0.3))
        popup.open()

    def _center_on_location(self, **kwargs):
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        if lat and lon:
            Clock.schedule_once(lambda dt: self._center_map(lat, lon))
            gps.stop()  # type: ignore

    def _get_ip_location(self):
        try:
            response = requests.get('http://ip-api.com/json/', timeout=10)
            data = response.json()
            if data.get('status') == 'success':
                lat = data.get('lat')
                lon = data.get('lon')
                Clock.schedule_once(lambda dt: self._center_map(lat, lon))
        except Exception:
            pass

    def _center_map(self, lat, lon):
        if lat is not None and lon is not None and self.mapview is not None:
            self.mapview.center_on(lat, lon)  # type: ignore
            # اضافه کردن مارکر روی لوکیشن فعلی
            if self.marker:
                self.mapview.remove_marker(self.marker)
            self.marker = MapMarker(lat=lat, lon=lon)
            self.mapview.add_marker(self.marker)
            self.selected_latlon = (lat, lon)
            self.confirm_btn.disabled = False

    def go_back(self, instance):
        self.parent.transition = SlideTransition(direction='right')
        self.parent.current = 'main'

class MainScreenWrapper(Screen):
    def __init__(self, screen_manager, **kwargs):
        super().__init__(**kwargs)
        self.main_screen = MainScreen(screen_manager)
        self.add_widget(self.main_screen)

class PassengerApp(App):
    if platform == 'android':
        from android.permissions import request_permissions, Permission # type: ignore
        request_permissions([Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_FINE_LOCATION])
        
    def build(self):
        self.screen_manager = ScreenManager()
        
        # صفحه اصلی
        self.main_screen_wrapper = MainScreenWrapper(self.screen_manager, name='main')
        self.main_screen_wrapper.ids = {'main_screen': self.main_screen_wrapper.main_screen}
        
        # صفحه نقشه
        self.map_screen = MapScreen(self.main_screen_wrapper.main_screen, name='map')
        
        self.screen_manager.add_widget(self.main_screen_wrapper)
        self.screen_manager.add_widget(self.map_screen)
        
        return self.screen_manager

if __name__ == '__main__':
    PassengerApp().run()

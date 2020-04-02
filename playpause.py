import os
import kivy
import sys
import socket_client
from pynput.keyboard import Key, Controller
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput  import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView

class ConnectPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 2

        if os.path.isfile("saved_details.txt"):
            with open("saved_details.txt","r") as f:
                d = f.read().split(",")
                prev_ip = d[0]
                prev_port = d[1]
                prev_name = d[2]
                prev_session_id = d[3]
        else:
            prev_ip = ''
            prev_port=''
            prev_name=''
            prev_session_id=''


        self.add_widget(Label(text="IP:"))
        self.ip = TextInput(text=prev_ip, multiline=False)
        self.add_widget(self.ip)

        self.add_widget(Label(text="Port:"))
        self.port = TextInput(text=prev_port, multiline=False)
        self.add_widget(self.port)

        self.add_widget(Label(text="Name:"))
        self.name = TextInput(text=prev_name, multiline=False)
        self.add_widget(self.name)

        self.add_widget(Label(text="Session Id:"))
        self.session_id = TextInput(text=prev_session_id, multiline=False)
        self.add_widget(self.session_id)

        self.join = Button(text="Join")
        self.join.bind(on_press=self.join_button)
        self.add_widget(Label())
        self.add_widget(self.join)

    def join_button(self, instance):
        ip = self.ip.text
        port = self.port.text
        name = self.name.text
        session_id = self.session_id.text
        with open("saved_details.txt", "w") as f:
            f.write(f"{ip},{port},{name},{session_id}")
        info = f"Attempting to join {ip}:{port} as {name}"
        playpause_app.info_page.update_info(info)
        playpause_app.screen_manager.current = 'Info'
        Clock.schedule_once(self.connect, 1)

    def connect(self, _):
        port = int(self.port.text)
        ip = self.ip.text
        name = self.name.text
        session_id = self.session_id.text

        if not socket_client.connect(ip, port, name, session_id, show_error):
            return

        playpause_app.create_session_page()
        playpause_app.screen_manager.current = "Session"

class InfoPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 1
        self.message = Label(halign="center", valign="middle", font_size=30)
        self.message.bind(width=self.update_text_width)

        self.add_widget(self.message)

    def update_info(self, message):
        self.message.text = message

    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)

class SessionPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 2
        self.bind(size=self.adjust_fields)

        self.history = ScrollableLabel(height=Window.size[1]*0.9, size_hint_y=None)
        self.add_widget(self.history)

        self.new_message = TextInput(width=Window.size[0]*0.8, size_hint_x=None)
        self.send = Button(text="Send")
        self.send.bind(on_press=self.send_message)

        bot_row = GridLayout(cols=2)
        bot_row.add_widget(self.new_message)
        bot_row.add_widget(self.send)
        self.add_widget(bot_row)

        Window.bind(on_key_down=self.on_key_down)
        Clock.schedule_once(self.focus_text_input, 1)

        socket_client.start_listening(self.incoming_message, show_error)

    def send_message(self, _):
        message = self.new_message.text
        self.new_message.text = ''

        if message:
            self.history.update_chat_history(f"[color=dd2020]{playpause_app.connect_page.name.text}[/color] > {message}")
            socket_client.send(message)
            if message == 'play' or message == 'pause':
                print("Triggering play/pause...")
                keyboard.press(Key.media_play_pause)
                keyboard.release(Key.media_play_pause)

        Clock.schedule_once(self.focus_text_input, 0.1)

    def incoming_message(self, username, message):
        self.history.update_chat_history(f'[color=20dd20]{username}[/color] > {message}')
        if message == 'play' or message == 'pause':
            print("Triggering play/pause...")
            keyboard.press(Key.media_play_pause)
            keyboard.release(Key.media_play_pause)

    def adjust_fields(self, *_):
        new_height = Window.size[1] - 50 if Window.size[1] * 0.1 < 50 else Window.size[1] * 0.9
        self.history.height = new_height

        new_width = Window.size[0] - 160 if Window.size[0] * 0.1 < 160 else Window.size[0] * 0.8
        self.new_message.width = new_width

        Clock.schedule_once(self.history.update_chat_history_layout)

    def focus_text_input(self, _):
        self.new_message.focus = True
    
    def on_key_down(self, instance, keyboard, keycode, text, modifiers):
        if text == '\r':
            self.send_message(None)

class ScrollableLabel(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = GridLayout(cols=1, size_hint_y=None)
        self.add_widget(self.layout)

        self.chat_history = Label(size_hint_y=None, markup=True)
        self.scroll_to_point = Label()

        self.layout.add_widget(self.chat_history)
        self.layout.add_widget(self.scroll_to_point)

    def update_chat_history(self, message):
        self.chat_history.text += "\n" + message
        self.update_chat_history_layout()

        self.scroll_to(self.scroll_to_point)

    def update_chat_history_layout(self, _=None):
        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

class PlayPauseApp(App):
    def build(self):
        self.screen_manager = ScreenManager()

        # Connect Page
        self.connect_page = ConnectPage()
        screen = Screen(name="Connect")
        screen.add_widget(self.connect_page)
        self.screen_manager.add_widget(screen)

        # Info Page
        self.info_page = InfoPage()
        screen = Screen(name="Info")
        screen.add_widget(self.info_page)
        self.screen_manager.add_widget(screen)

        return self.screen_manager

    def create_session_page(self):
        self.session_page = SessionPage()
        screen = Screen(name="Session")
        screen.add_widget(self.session_page)
        self.screen_manager.add_widget(screen)

def show_error(message):
    playpause_app.info_page.update_info(message)
    playpause_app.screen_manager.current = "Info"
    Clock.schedule_once(sys.exit, 5)

if __name__ == "__main__":
    keyboard = Controller()
    playpause_app = PlayPauseApp()
    playpause_app.run()
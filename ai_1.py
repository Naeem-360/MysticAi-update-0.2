import sys
import random
import pyttsx3
import speech_recognition as sr
import pywhatkit
import datetime
import wikipedia
from datetime import date
import webbrowser
import os
import shutil
import subprocess
import psutil
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import requests
from bs4 import BeautifulSoup
import noisereduce as nr
import pyautogui
import time
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from fuzzywuzzy import process
import openai
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QTextEdit, QLineEdit
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen
import re

load_dotenv()
api_key = os.getenv("GITHUB_TOKEN") # Get you gpt-4o-mini api key form github marketplace
if not api_key:
    print("Error: API key not found. Please check your .env file.")
else:
    print("API key loaded successfully.")

client = openai.OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key,
)

engine = pyttsx3.init(driverName="sapi5")
engine.setProperty("rate", 190)
engine.setProperty("volume", 1.0)
current_mode = "text"
is_speaking = False 

FILLER_WORDS = {"please", "now", "just", "can", "you", "do", "me", "some", "extra", "word", "it", "hey", "quickly"}

commands_dict = {
    "chrome": ["chrome", "chrom", "crome", "googl", "google", "browser", "web", "internet", "chorme", "chromi"],
    "notepad": ["notepad", "note", "notepd", "editor", "text", "txt", "notbook", "notepade", "writer"],
    "calculator": ["calculator", "calc", "calcu", "cal", "math", "calculate", "calcultor", "calclator"],
    "youtube": ["youtube", "yt", "utub", "you tube", "youtub", "video", "yotube", "youtobe", "utube"],
    "screenshot": ["screenshot", "ss", "screen shot", "snap", "capture", "screen", "pic", "shot", "screensht"],
    "shutdown": ["shutdown", "shut down", "exit", "quit", "power off", "turn off", "close", "shut", "off", "stop"],
    "time": ["time", "clock", "what time", "current time", "now", "tim", "hour", "tyme"],
    "play": ["play", "start", "run", "listen", "music", "song", "pla", "pley"],
    "volume up": ["volume up", "increase volume", "louder", "up volume", "raise volume", "vol up", "more volume"],
    "volume down": ["volume down", "decrease volume", "lower", "down volume", "reduce volume", "vol down", "less volume"],
    "google": ["google", "search", "find", "look up", "googl", "serch", "googal", "lookup"],
    "chat": ["chat", "talk", "speak", "discuss", "converse", "chit chat", "tell me", "say"],
    "explain": ["explain", "tell me about", "describe", "info", "what is", "explan", "details"],
    "open": ["open", "launch", "start", "run", "go to", "ope", "opn"],
    "close": ["close", "shut", "terminate", "end", "stop", "clos", "exit"],
    "date": ["date", "today", "current date", "day", "what date", "dat"],
}

def preprocess_command(command):
    command = command.lower().strip()
    words = [word for word in command.split() if word not in FILLER_WORDS]
    return " ".join(words)

def get_best_match(user_input):
    cleaned_input = preprocess_command(user_input)
    if not cleaned_input:
        return None
    for command, aliases in commands_dict.items():
        if cleaned_input == command or cleaned_input in aliases:
            return command
    best_match, score = process.extractOne(cleaned_input, commands_dict.keys())
    if score > 60:
        return best_match
    return None

def talk(text, gui=None):
    global is_speaking
    print("Assistant:", text)
    if gui:
        gui.update_output(text)
    if current_mode == "voice" and text.strip():
        is_speaking = True
        engine.say(text)
        engine.runAndWait()
        is_speaking = False

def stop_talking():
    global is_speaking
    if is_speaking:
        engine.stop()
        is_speaking = False
        print("Speech stopped.")

class VoiceThread(QThread):
    voice_result = pyqtSignal(str)

    def run(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as mic:
                print("Listening...")
                recognizer.adjust_for_ambient_noise(mic, duration=0.2)
                audio = recognizer.listen(mic, timeout=5, phrase_time_limit=5)
                text = recognizer.recognize_google(audio).lower()
                print(f"You (voice): {text}")
                self.voice_result.emit(text)
        except Exception as e:
            print(f"Voice Error: {e}")
            self.voice_result.emit("")


    
class HoloGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.voice_thread = None
        self.animation_radius = 50
        self.animation_step = 2
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)

    def initUI(self):
        self.setWindowTitle("Mysticai gui")
        self.setGeometry(200, 200, 800, 600)
        self.setStyleSheet("background-color: #0a0a0a; border: 1px solid blue;")
        
        layout = QVBoxLayout()
        self.title = QLabel("MysticAI", self)
        self.title.setFont(QFont("Arial", 30))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("color: white; text-shadow: 0 0 5px blue;")
        layout.addWidget(self.title)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 0.7); border: 2px solid blue;")
        self.output.setFont(QFont("Arial", 16))
        self.output.setMinimumHeight(400)
        layout.addWidget(self.output)

        self.input_field = QLineEdit(self)
        self.input_field.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 0.7); border: 2px solid blue;")
        self.input_field.setFont(QFont("Arial", 14))
        self.input_field.returnPressed.connect(self.process_input)
        layout.addWidget(self.input_field)
        button_layout = QVBoxLayout()

        self.toggle_btn = QPushButton("🎙️", self)
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.setStyleSheet("background-color: transparent; border: 2px solid blue; color: white; font-size: 20px;")
        self.toggle_btn.clicked.connect(self.toggle_mode)
        button_layout.addWidget(self.toggle_btn, alignment=Qt.AlignCenter)

        self.stop_btn = QPushButton("⏹️", self)
        self.stop_btn.setFixedSize(40, 40)
        self.stop_btn.setStyleSheet("background-color: transparent; border: 2px solid blue; color: white; font-size: 20px;")
        self.stop_btn.clicked.connect(stop_talking)
        button_layout.addWidget(self.stop_btn, alignment=Qt.AlignCenter)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.flicker_timer = QTimer(self)
        self.flicker_timer.timeout.connect(self.flicker_effect)
        self.flicker_timer.start(500)
        self.update_output(get_greeting())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(0, 0, 255, 100), 2)
        painter.setPen(pen)
        center_x = self.width() // 2
        center_y = self.height() // 2 - 50
        painter.drawEllipse(QRect(center_x - self.animation_radius, center_y - self.animation_radius,
                                  self.animation_radius * 2, self.animation_radius * 2))
        outer_pen = QPen(QColor(0, 0, 255, 50), 1)
        painter.setPen(outer_pen)
        painter.drawEllipse(QRect(center_x - self.animation_radius - 10, center_y - self.animation_radius - 10,
                                  (self.animation_radius + 10) * 2, (self.animation_radius + 10) * 2))

    def update_animation(self):
        self.animation_radius += self.animation_step
        if self.animation_radius >= 70 or self.animation_radius <= 50:
            self.animation_step = -self.animation_step
        self.update()

    def flicker_effect(self):
        current_style = self.title.styleSheet()
        if "opacity: 0.8" in current_style:
            self.title.setStyleSheet("color: white; text-shadow: 0 0 5px blue; opacity: 1;")
        else:
            self.title.setStyleSheet("color: white; text-shadow: 0 0 5px blue; opacity: 0.8;")

    def update_output(self, text):
        self.output.append(text)

    def toggle_mode(self):
        global current_mode
        if current_mode == "text":
            current_mode = "voice"
            self.update_output("Switched to voice mode. Listening...")
            talk("Voice mode activated. Say 'switch to text' to change back.", self)
            self.start_voice_input()
        else:
            current_mode = "text"
            self.update_output("Switched to text mode. Type your command.")
            talk("Text mode activated. Type 'switch to voice' to change back.", self)
            self.input_field.setFocus()

    def start_voice_input(self):
        if current_mode == "voice":
            self.voice_thread = VoiceThread(self)
            self.voice_thread.voice_result.connect(self.process_voice_input)
            self.voice_thread.start()

    def process_voice_input(self, text):
        if text:
            self.update_output(f"You (voice): {text}")
            self.process_command(text)
        else:
            talk("I didn’t hear anything. Please try again.", self)
        if current_mode == "voice":
            self.start_voice_input()

    def process_input(self):
        if current_mode == "text":
            command = self.input_field.text().lower().strip()
            self.update_output(f"You: {command}")
            self.input_field.clear()
            self.process_command(command)

    def process_command(self, command):
        if not command:
            return

        try:
            cleaned_command = preprocess_command(command)
            print(f"Debug - Original Command: {command}")
            print(f"Debug - Cleaned Command: {cleaned_command}")

            if command == "switch to voice":
                self.toggle_mode()
                return
            elif command == "switch to text":
                self.toggle_mode()
                return
            elif command == "quit":
                talk("Shutting down. Have a nice day, sir!", self)
                QApplication.quit()
                return

            if control_pc(cleaned_command):
                return
            
            if manage_files_folders(cleaned_command, self):
                return
            
            if "messenger" in cleaned_command:
                open_messenger_in_chrome()
                return
            if "facebook" in cleaned_command and "account" not in cleaned_command:
                open_facebook_in_chrome()
                return
            if "linkedin" in cleaned_command and "account" not in cleaned_command:
                open_linkedin_in_chrome()
                return
            if "github" in cleaned_command and "account" not in cleaned_command:
                open_github_in_chrome()
                return

            if "github" in cleaned_command and "account" in cleaned_command:
                url = "Your GitHub account link here" #👈
                webbrowser.open(url)
                talk("Here is your GitHub account", self)
                return
            elif "facebook" in cleaned_command and "account" in cleaned_command:
                url1 = "Your Facebook Link here" #👈
                webbrowser.open(url1)
                talk("Here's your Facebook account", self)
                return
            elif "linkedin" in cleaned_command and "account" in cleaned_command:
                url2 = "Your LinkedIn account here" #👈
                webbrowser.open(url2)
                talk("Here is your LinkedIn account", self)
                return

            best_match = get_best_match(cleaned_command)
            if best_match:
                print(f"Debug - Best Match: {best_match}")

            if "chat" in command or "talk to jarvis" in command:
                user_prompt = command.replace("chat", "").replace("talk to jarvis", "").strip()
                if not user_prompt:
                    talk("What would you like to talk about?", self)
                    return
                answer = chat_with_gpt(user_prompt)
                talk(answer, self)

            elif "play" in command:
                song = command.replace("play", "", 1).strip()
                if not song:
                    talk("What song would you like to play?", self)
                    return
                print(f"Debug - Attempting to play song: {song}")
                talk("Playing " + song, self)
                try:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
                except Exception as e:
                    talk(f"Failed to play '{song}': {str(e)}. Check your internet or browser.", self)

            elif "hit the song" in command:
                talk("Playing the song", self)
                try:
                    pywhatkit.playonyt("https://youtu.be/y-MtHQ-msFk?si=8pA8NEJtwUhAhv1G")
                except Exception as e:
                    talk(f"Failed to play the song: {str(e)}", self)

            elif "hit the funny" in command or "funny one" in command:
                talk("Playing the song", self)
                try:
                    pywhatkit.playonyt("https://youtu.be/Jyeracn7S9I?si=fSggMt9uN83HcqXN")
                except Exception as e:
                    talk(f"Failed to play the funny song: {str(e)}", self)

            elif "hit the hindi" in command or "hindi song" in command:
                talk("Playing the song", self)
                try:
                    pywhatkit.playonyt("https://youtu.be/eK5gPcFjQps?si=HXpSxqGU7sA5Hsk4")
                except Exception as e:
                    talk(f"Failed to play the Hindi song: {str(e)}", self)

            
            elif "hit the phonk" in command:
                talk("Playing the song", self)
                try:
                    pywhatkit.playonyt("https://youtu.be/ZU3Tj82gya8?si=jqS5BrLZg9mjmNBw")
                except Exception as e:
                    talk(f"Failed to play the phonk song: {str(e)}", self)

            elif "time" in command:
                if "time in" in command:
                    location = command.replace("time in", "").strip()
                    get_time_in_location(location)
                else:
                    get_time_in_location("Bangladesh")

            elif "screenshot" in command or "take screenshot" in command:
                take_screenshot()

            elif "new tab" in command or "another code" in command:
                open_vs_code_new_tab()

            elif "date" in command:
                current_date = date.today()
                talk(str(current_date), self)

            elif "close" in command or "terminate" in command:
                app = command.replace("close", "").replace("terminate", "").strip()
                close_application(app)

            
            elif "who" in command:
                anything = command.replace("how", "").replace("who", "").replace("what", "").strip()
                try:
                    info = wikipedia.summary(anything, sentences=3)
                    talk(info, self)
                except Exception as e:
                    talk("Sorry, I couldn't fetch that information.", self)

            elif "hi" in command or "how are you" in command:
                talk("I am fine! How can I help you sir?", self)

            elif "explain" in command:
                topic = command.replace("explain", "", 1).strip()
                if not topic:
                    talk("Please specify a topic to explain.", self)
                    return
                print(f"Debug - Fetching explanation for: {topic}")
                try:
                    info = wikipedia.summary(topic, sentences=5)
                    talk(info, self)
                except Exception as e:
                    talk(f"Failed to explain '{topic}': {str(e)}. Check your internet or try another topic.", self)

            elif "increase volume" in command or "volume up" in command:
                change_volume(increase=True)

            elif "decrease volume" in command or "volume down" in command:
                change_volume(increase=False)

            elif "google" in cleaned_command or "search" in cleaned_command:
                quest = cleaned_command.replace("google", "").replace("search", "").strip()
                if not quest:
                    talk("What would you like to search for?", self)
                    return
                talk(f"Searching {quest}", self)
                search_google(quest)

            elif "open voicemod" in command or "voicemod" in command:
                talk("Opening Voicemod", self)
                subprocess.Popen(r"Application path here (if you have this application)") #👈
            
            elif "open cursor" in command:
                talk("Opening Cursor", self)
                subprocess.Popen(r"Application path here (if you have this application)") #👈
            
            elif "open file explorer" in command or "open explorer" in command or "open this pc" in command:
                talk("Opening File Explorer", self)
                os.startfile("explorer")

            elif "telegram" in cleaned_command:
                talk("Opening Telegram", self)
                subprocess.Popen(r"Application path here (if you have this application)") #👈

            elif "chrome" in cleaned_command:
                talk("Opening Chrome", self)
                subprocess.Popen(r"Application path here (if you have this application)") #👈

            elif "word" in command or "wordpad" in command:
                talk("Opening WordPad", self)
                os.startfile("write")

            elif "open settings" in command or "pc settings" in command:
                talk("Opening Windows Settings", self)
                subprocess.Popen("start ms-settings:", shell=True)

            elif "dp settings" in command:
                talk("Opening Display Settings", self)
                subprocess.Popen("start ms-settings:display", shell=True)

            elif "cmd" in command:
                talk("Opening CMD", self)
                subprocess.Popen("cmd", shell=True)

            elif "open cap" in command or "run cap" in command or "launch cap" in command:
                talk("Opening Capcut", self)
                subprocess.Popen(r"Application path here (if you have this application)") #👈

            elif "store" in command or "microsoft store" in command or "ms store" in command:
                talk("Opening Microsoft Store", self)
                subprocess.Popen("start ms-windows-store:", shell=True)

            elif "open steam" in command or "steam" in command:
                talk("Opening Steam", self)
                subprocess.Popen(r"Application path here (if you have this application)") #👈

            elif "calculator" in command:
                talk("Opening Calculator", self)
                subprocess.Popen("calc", shell=True)
            
            elif "open" in cleaned_command:
                app = cleaned_command.replace("open", "").strip()
                if app:
                    talk(f"I don’t know how to open {app}. Try a specific app name!", self)
            
            elif command.lower() == "help":
                show_help()

            else:
                try:
                    response = chat_with_gpt(command)
                    talk(response, self)
                except:
                    talk("I don’t understand that. Try rephrasing it or say 'help' for a list of commands!", self)

        except Exception as e:
            talk(f"Critical error processing command '{command}': {str(e)}. Please report this!", self)
            print(f"Crash Debug - Exception: {str(e)}")

def get_greeting():
    hour = int(time.strftime("%H"))
    if hour < 12:
        return "Good Morning Sir!"
    elif hour < 15:
        return "It's Noon Sir! You should rest"
    elif hour < 17:
        return "Good Afternoon Sir!"
    elif hour < 19:
        return "Good Evening Sir!"
    elif hour > 21:
        return "It's late night sir! You should sleep"
    else:
        return "It's Night sir!"

def open_linkedin_in_chrome():
    try:
        chrome_path = r"Your Chrome path here" #👈
        url = "https://bd.linkedin.com/"
        subprocess.Popen([chrome_path, "--new-window", url])
        talk("Opening LinkedIn in Chrome", gui)
    except Exception as e:
        talk(f"Failed to open LinkedIn: {str(e)}", gui)

def open_github_in_chrome():
    try:
        chrome_path = r"Your Chrome path here" #👈
        url = "https://github.com/"
        subprocess.Popen([chrome_path, "--new-window", url])
        talk("Opening GitHub in Chrome", gui)
    except Exception as e:
        talk(f"Failed to open GitHub: {str(e)}", gui)

def open_messenger_in_chrome():
    try:
        chrome_path = r"Your Chrome path here" #👈
        url = "https://www.messenger.com"
        subprocess.Popen([chrome_path, "--new-window", url])
        talk("Opening Messenger in Chrome", gui)
    except Exception as e:
        talk(f"Failed to open Messenger: {str(e)}", gui)

def open_facebook_in_chrome():
    try:
        chrome_path = r"Your Chrome path here" #👈
        url = "https://www.facebook.com/"
        subprocess.Popen([chrome_path, "--new-window", url])
        talk("Opening Facebook in Chrome", gui)
    except Exception as e:
        talk(f"Failed to open Facebook: {str(e)}", gui)

def manage_files_folders(command, gui):
    try:
        if "create folder" in command or "make folder" in command:
            folder_name = command.replace("create folder", "").replace("make folder", "").strip()
            if not folder_name:
                talk("Please specify a folder name.", gui)
                return True
            os.makedirs(folder_name, exist_ok=True)
            talk(f"Folder '{folder_name}' created successfully.", gui)
            return True

        elif "create file" in command or "make file" in command:
            file_info = command.replace("create file", "").replace("make file", "").strip()
            if not file_info:
                talk("Please specify a file name.", gui)
                return True
            parts = file_info.split(" with content ")
            file_name = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            with open(file_name, "w") as f:
                f.write(content)
            talk(f"File '{file_name}' created{' with content' if content else ''}.", gui)
            return True

        elif "delete folder" in command or "remove folder" in command:
            folder_name = command.replace("delete folder", "").replace("remove folder", "").strip()
            if not folder_name:
                talk("Please specify a folder name to delete.", gui)
                return True
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name)
                talk(f"Folder '{folder_name}' deleted successfully.", gui)
            else:
                talk(f"Folder '{folder_name}' does not exist.", gui)
            return True

        elif "delete file" in command or "remove file" in command:
            file_name = command.replace("delete file", "").replace("remove file", "").strip()
            if not file_name:
                talk("Please specify a file name to delete.", gui)
                return True
            if os.path.exists(file_name):
                os.remove(file_name)
                talk(f"File '{file_name}' deleted successfully.", gui)
            else:
                talk(f"File '{file_name}' does not exist.", gui)
            return True

        elif "write to file" in command or "add to file" in command:
            parts = command.replace("write to file", "").replace("add to file", "").strip().split(" content ")
            if len(parts) < 2:
                talk("Please specify a file name and content.", gui)
                return True
            file_name = parts[0].strip()
            content = parts[1].strip()
            if not os.path.exists(file_name):
                talk(f"File '{file_name}' does not exist. Creating it now.", gui)
            with open(file_name, "a") as f:
                f.write(content + "\n")
            talk(f"Content added to '{file_name}'.", gui)
            return True

        elif "remove from file" in command or "delete from file" in command:
            parts = command.replace("remove from file", "").replace("delete from file", "").strip().split(" content ")
            if len(parts) < 2:
                talk("Please specify a file name and content to remove.", gui)
                return True
            file_name = parts[0].strip()
            content_to_remove = parts[1].strip()
            if not os.path.exists(file_name):
                talk(f"File '{file_name}' does not exist.", gui)
                return True
            with open(file_name, "r") as f:
                lines = f.readlines()
            with open(file_name, "w") as f:
                removed = False
                for line in lines:
                    if content_to_remove not in line:
                        f.write(line)
                    else:
                        removed = True
            talk(f"{'Content removed from' if removed else 'Content not found in'} '{file_name}'.", gui)
            return True

        return False

    except Exception as e:
        talk(f"An error occurred: {str(e)}", gui)
        return True

def get_time_in_location(location="Bangladesh"):
    geolocator = Nominatim(user_agent="geoapi")
    try:
        location_data = geolocator.geocode(location)
        if not location_data:
            talk("Sorry, I couldn't find that location.", gui)
            return
        lat, lon = location_data.latitude, location_data.longitude
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=lon, lat=lat)
        if timezone_str is None:
            talk("Sorry, I couldn't determine the timezone.", gui)
            return
        timezone = pytz.timezone(timezone_str)
        local_time = datetime.datetime.now(timezone).strftime("%I:%M %p")
        talk(f"The current time in {location} is {local_time}", gui)
    except Exception as e:
        talk(f"An error occurred: {e}", gui)

def change_volume(increase=True):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)
    current_volume = volume.GetMasterVolumeLevelScalar()
    step = 0.1
    if increase:
        new_volume = min(current_volume + step, 1.0)
    else:
        new_volume = max(current_volume - step, 0.0)
    volume.SetMasterVolumeLevelScalar(new_volume, None)
    talk(f"Volume set to {int(new_volume * 100)} percent", gui)

def open_vs_code_new_tab():
    vscode_path = r"E:\VS Code\Microsoft VS Code\Code.exe"
    subprocess.Popen([vscode_path, "--new-window"])
    talk("Opening a new tab in VS Code", gui)

def control_pc(command):
    if "shutdown" in command:
        talk("Shutting down your PC.", gui)
        os.system("shutdown /s /t 5")
        return True
    elif "restart" in command:
        talk("Restarting your PC.", gui)
        os.system("shutdown /r /t 5")
        return True
    elif "open notepad" in command:
        talk("Opening Notepad", gui)
        os.system("notepad")
        return True
    return False

def take_screenshot():
    screenshot_folder = os.path.join(os.getcwd(), "Screenshots")
    os.makedirs(screenshot_folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_path = os.path.join(screenshot_folder, f"screenshot_{timestamp}.png")
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)
        talk("Screenshot taken and saved successfully", gui)
    except Exception as e:
        talk(f"Error taking screenshot: {e}", gui)

def search_google(query):
    url = f"https://www.google.com/search?q={query}"
    try:
        webbrowser.open(url)
        talk(f"Here are the results for {query}", gui)
    except Exception as e:
        talk(f"Failed to open Google search: {str(e)}", gui)

def close_application(app_name):
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if app_name.lower() in process.info['name'].lower():
            talk(f"Closing {process.info['name']}", gui)
            os.kill(process.info['pid'], 9)
            return
    talk(f"No running application found with name {app_name}", gui)

def show_help():
    help_text = [
        "Here’s a list of commands I can understand:",
        "1. 'switch to voice' - Switch to voice input mode.",
        "2. 'switch to text' - Switch to text input mode.",
        "3. 'quit' - Exit the assistant.",
        "4. 'time' - Show current time in Bangladesh (or 'time in [location]').",
        "5. 'google [query]' - Search Google.",
        "6. 'play [song name]' - Play a song on YouTube.",
        "7. 'screenshot' - Take and save a screenshot.",
        "8. 'volume up' - Increase system volume.",
        "9. 'volume down' - Decrease system volume.",
        "10. 'explain [topic]' - Get a detailed explanation from Wikipedia.",
        "11. 'chat [topic]' - Talk to me about anything!",
        "12. 'open chrome' - Open Google Chrome.",
        "13. 'shutdown' - Shut down your PC.",
        "14. 'open my github account' - Open your GitHub account.",
        "15. 'create folder [name]' - Create a folder.",
        "16. 'delete file [name]' - Delete a file.",
        "17. 'help' - Show this help menu."
    ]
    for line in help_text:
        talk(line, gui)

def chat_with_gpt(prompt):
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            model="gpt-4o-mini",
            temperature=0.6,
            max_tokens=300,
            top_p=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, I couldn't process that request: {e}"

gui = None

def main():
    app = QApplication(sys.argv)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 10, 10))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    app.setPalette(palette)

    global gui
    gui = HoloGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

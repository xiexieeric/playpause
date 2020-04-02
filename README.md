# playpause
PlayPause is a cross-platform app that allows users to synchronize media playback on multiple computers. When multiple computers join the same online session, they can issue play/pause commands to other computers in the session, making it easy to watch shows together. I was motivated to create this app after having a poor experience with Netflix Party, which is not only limited to Netflix on the browser, but also had server issues that made it unusable sometimes. 

## How it's made
The server uses websockets connections to relay messages to clients in real time. When a client connects, it either must provide a session ID or the server will grant it a new one. Clients that connect via the same session ID are able to send messages amongst each other. 

The client is a GUI application made with Kivy. Aside from making connections to the server and enabling the chat functionality, the application leverages Pynput to simulate pressing the play/pause media key. 

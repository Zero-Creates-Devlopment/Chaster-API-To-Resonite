
Resonite X Chaster Timer
========================

A cyber-styled desktop app for tracking your active Chaster locks. It shows remaining lock time, keyholder information, and lets you add time remotely through a local API.

The app is packaged as a Windows executable, so users do not need Python or any dependencies installed.

--------------------------------
Features
--------------------------------
- Cyber-terminal styled GUI
- Shows remaining lock time and updates it every second
- Handles hidden timers gracefully
- Displays keyholder username
- Saves your login and lock ID in a config file
- Restores saved settings automatically on future runs
- Exposes a local API to add time to a lock
- Provides a local /time endpoint for external use
- Fully self-contained .exe — no Python install required

--------------------------------
Requirements
--------------------------------
- Windows 10 or higher
- The lock must be visible to see the remaining time
- Nothing else is required — the .exe is portable

--------------------------------
First Time Setup
--------------------------------
1. Run Resonite X Chaster Timer.exe
2. Click "Login With Chaster"
3. Confirm the browser login flow
4. If prompted, allow local network access if you want easier local integration
5. If the browser flow does not provide your user ID automatically, enter it manually
6. Click "Fetch Locks"
7. Select your lock from the dropdown
8. Click "Save Lock"
9. Enter the amount of time you want to add in seconds, then click "Add Time"

- The app creates its config folder and .env file automatically on first run.
- The config file is stored in your user AppData folder at:
  %APPDATA%\ResoniteXChasterTimer\.env
- On subsequent runs, your saved user ID and lock ID are restored automatically.

--------------------------------
Local API Usage
--------------------------------
GET remaining time:
http://localhost:5000/time

Example response:
5d 12h 03m 21s

If the timer is hidden, the response is:
hidden

POST add time to a lock:
http://localhost:5000/add-time

--------------------------------
Resonite Folder
--------------------------------
````resrec:///U-1hZTrMJ7lke/R-CFBD243741B5D4C5F630613B9BC59D2A1322E9A24D113A245E60A6C5E9A732A1````

--------------------------------
Notes
--------------------------------
- The .env file can be edited manually if needed
- Firewall may ask to allow the app to use port 5000 for the local API
- Hidden timers show as "TIMER HIDDEN" in the GUI and "hidden" via API
- The lock must be visible to see the remaining time

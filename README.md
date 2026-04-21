# There is a major error in the backend check back here for updates


Resonite X Chaster Timer
==============================

A cyber-styled desktop app for tracking your active Chaster locks. 
This app shows remaining lock time, keyholder information, and lets 
you add time remotely via a local API.  

It’s fully packaged as a .exe — users do NOT need Python or any dependencies. 
The .exe automatically creates a .env file on first run.  

--------------------------------
Features
--------------------------------
- Cyber-terminal styled GUI
- Shows remaining lock time, updates every second
- Handles hidden timers gracefully
- Displays keyholder username
- Auto-saves Login and lock ID in .env
- Auto-restores settings on reopen
- POST endpoint to add time to a lock
- Local /time API for external use
- Fully self-contained .exe — no Python install required

--------------------------------
Requirements
--------------------------------
- Windows 10 or higher
- Lock must be VISIBLE to see the remaining time
- Nothing else — the .exe is fully portable

--------------------------------
First Time Setup
--------------------------------
1. Run Resonite X Chaster Timer.exe
2. Click "Login With Chaster"
3. Click "yes"
4. Then the page will ask to access your local network (this is not required but will make it easyer)
5. if you choose not to you will need to enter the user id manually
6. Click "Fetch Locks"
7. Select your lock from the dropdown
8. Click "Save Lock"
9. Choose the time You want To add in seconds in the field then add that time to save (this will actually add the time so sorry)

- The .env file is created automatically in the same folder as the .exe
- On subsequent runs, your token and lock are restored automatically

--------------------------------
Local API Usage
--------------------------------
GET Remaining Time:
http://localhost:5000/time
Example response:
5d 12h 03m 21s
or if the timer is hidden:
hidden

POST Add Time to Lock:
http://localhost:5000/add-time

--------------------------------
Resonite Folder
--------------------------------
````resrec:///U-1hZTrMJ7lke/R-CFBD243741B5D4C5F630613B9BC59D2A1322E9A24D113A245E60A6C5E9A732A1````

--------------------------------
Notes
--------------------------------
- .env can be manually edited if needed
- Firewall may ask to allow the app to use port 5000 (for the local API)
- Hidden timers show as "TIMER HIDDEN" in the GUI and "hidden" via API
- Lock must be visible to see remaining time

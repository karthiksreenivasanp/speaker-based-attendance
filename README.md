# Voice Attendance System

A full-stack, real-time Voice Attendance System built using Python, FastAPI, React (Vite), and SpeechBrain (ECAPA-TDNN). This system allows you to enroll students through their voice and automatically mark their attendance using speaker verification.

![Voice Attendance System](frontend-app/public/vite.svg)

## Features

- **Speaker Verification:** Uses ECAPA-TDNN models from SpeechBrain to extract embeddings from a student's voice and compare it to known signatures.
- **Microphone Integration:** Real-time recording on the browser and sending to the API.
- **Robust Database:** SQLAlchemy with a SQLite backend to store student features and attendance logs.
- **RESTful API:** FastAPI powers the backend services for simple and fast integrations.
- **Frontend Dashboard:** React+Vite frontend for enrollment, verification, and viewing logs.
- **Network Exposing:** Features Ngrok configuration to share your local backend securely via internet for remote connections.

---

## 🚀 Setup on a New System

### Prerequisites

You will need the following installed:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js (LTS version)](https://nodejs.org/) (for the frontend React App)
- [Git](https://git-scm.com/downloads)

---

### 1. Clone the Repository

Clone the project to your local machine:
```bash
git clone https://github.com/sreelakshmits225/speaker_verification_attendence.git
cd speaker_verification_attendence
```

### 2. Backend Setup (FastAPI & SpeechBrain)

1. **Create and Activate a Virtual Environment:**
   Run the following commands in the root of the project:
   ```bash
   # Create a virtual environment named "env"
   python -m venv env

   # Activate the virtual environment
   # On Windows:
   env\Scripts\activate
   # On Mac/Linux:
   source env/bin/activate
   ```

2. **Install Python Dependencies:**
   With the virtual environment activated, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Initialization:**
   The application uses a SQLite database. It will be generated dynamically on first run in the root directory under the name `voice_attendance.db`. If you need to reset your database at any time, you can run:
   ```bash
   python reset_database.py
   ```

> [!IMPORTANT]
> The very first time you verify/enroll a speaker, SpeechBrain will automatically download the large pre-trained `spkrec-ecapa-voxceleb` model and cache it locally in `pretrained_models/`. This might take a few minutes depending on your internet connection.

### 3. Frontend Setup (React/Vite)

1. Open a **new terminal window** and navigate to the frontend application:
   ```bash
   cd frontend-app
   ```

2. Install Node.js packages:
   ```bash
   npm install
   ```

---

## 🏃 Running the Application

### The Easy Way (Windows ONLY)
If you are on Windows, simply double click the `start_app.bat` script located in the root directory. It runs both the Python API (FastAPI) and the React Frontend simultaneously.
It will print the URLs you need to access both the Backend and the app on your Browser or Phone.

### The Manual Way (Mac/Linux/Windows)

If you don't want to use the batch script, run the layers separately.

**1. Start the API Server:**
In the root directory, with the virtual environment activated:
```bash
# Run uvicorn server on all interfaces (0.0.0.0) so your phone can reach it
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API should now be running at: `http://localhost:8000`

**2. Start the Frontend:**
In the `frontend-app` directory:
```bash
npm run dev -- --host
```
The Frontend should now be running at: `http://localhost:5173`

---

## 🌍 Remote Access (Sharing to other devices)

If you want others over the internet to connect to your app, you can use `ngrok`.
A script is provided in the root `share_remote.bat` which will start ngrok and create a public URL.

**Usage:**
1. You must have a free [Ngrok account](https://ngrok.com/).
2. Unzip or add `ngrok.exe` in the root of the project (if it isn't set up globally).
3. Connect your authtoken in a terminal: `ngrok config add-authtoken <YOUR_TOKEN>`
4. Run the sharing script:
   ```bash
   share_remote.bat
   ```

This spins up paths that expose standard traffic securely. You'll need to update the base URL in your frontend's `src/api.js` to whatever HTTPS URL Ngrok generated.

## Folder Structure

```
├── app/                  # FastAPI Application Core
│   ├── api/              # API Endpoints (enrollment, verification)
│   ├── ml_engine/        # SpeechBrain & Embedding extraction logic
│   ├── db/               # Database management
│   └── models.py         # SQLAlchemy Models
├── frontend-app/         # VITE React application source
├── dataset/              # Downloaded student datasets (git ignored)
├── pretrained_models/    # Cached SpeechBrain models (git ignored)
├── reset_database.py     # Script to clear local databases
├── start_app.bat         # Single click script to run the Full Stack Application
└── requirements.txt      # Python dependencies
```

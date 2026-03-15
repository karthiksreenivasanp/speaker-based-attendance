# Speaker Based Attendance System

A fully cloud-hosted, real-time Voice Biometric Attendance System built using Python, FastAPI, React (Vite), Firebase Firestore, and SpeechBrain (ECAPA-TDNN). This system allows students to enroll their voice signatures and automatically mark verifiable attendance based on speaker recognition and GPS geofencing.

## ✨ Features

- **Speaker Verification:** Uses ECAPA-TDNN models from SpeechBrain to extract embeddings from a student's voice and compare it to known signatures.
- **Serverless Cloud Database:** Fully integrated with Firebase Firestore for real-time syncing of students, classes, and attendance logs.
- **Cloud Deployment Ready:** Includes Docker configuration for deploying the AI Backend on Hugging Face Spaces and GitHub Actions workflow for hosting the frontend on GitHub Pages.
- **Geofenced Attendance:** Uses GPS to verify the student is within the classroom radius before permitting them to mark attendance.
- **RESTful API:** FastAPI powers the robust backend services.
- **Frontend Dashboard:** A responsive, modern React GUI for enrollment, verification, mentor selection, and viewing logs.

---

## 🚀 Live Demo

- **Frontend App:** [Hosted on GitHub Pages](https://karthiksreenivasanp.github.io/speaker-based-attendance/)
- **Backend API:** [Hosted on Hugging Face Spaces](https://huggingface.co/spaces/karthiksreenivasanp/speaker-attendance-backend)

---

## 💻 Local Development Setup

If you wish to run the project locally instead of using the live deployments:

### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/)
- Firebase Credentials JSON file (place inside the root folder or supply via `FIREBASE_CREDENTIALS` environment variable)

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/karthiksreenivasanp/speaker-based-attendance.git
cd speaker-based-attendance

# Create and activate a virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install Python Dependencies
pip install -r requirements.txt

# Start the FastAPI Server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Note: The first time you run a voice inference, it will download necessary SpeechBrain AI models into the `pretrained_models/` directory.*

### 2. Frontend Setup

```bash
# In a new terminal, navigate to the frontend directory
cd frontend-app

# Install Node dependencies
npm install

# Start the React development server
npm run dev -- --host
```

---

## 📁 Project Structure

```
├── app/                  # FastAPI Application Core
│   ├── api/              # API Endpoints (enrollment, verification, auth)
│   ├── ml_engine/        # SpeechBrain & Embedding extraction logic
│   └── db/               # Firebase Database connections
├── frontend-app/         # VITE React application source
├── pretrained_models/    # Cached SpeechBrain models (Git LFS)
├── fine_tuned_model/     # Optional custom-trained models (Git LFS)
├── Dockerfile            # Hugging Face deployment container
├── requirements.txt      # Python dependencies
└── .github/workflows/    # CI/CD pipelines
```

---

## 🤖 Tech Stack

- **AI/ML:** PyTorch, SpeechBrain, Librosa, Noisereduce
- **Backend:** Python, FastAPI, Firebase Firestore (NoSQL)
- **Frontend:** React, HTML5 Audio API, Geolocation API, Tailwind Concepts
- **Deployment:** Docker, Hugging Face Spaces, GitHub Pages, GitHub Actions

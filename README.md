# Lyftr AI

**A lightweight AI chatbot with conversation memory, response caching, and automatic API fallback.**

Lyftr AI is a full-stack chatbot built to explore how modern AI applications work beyond simply sending a prompt to an LLM. It uses Google's Gemini API to generate responses and includes features such as conversation history, caching for repeated questions, and fallback handling when an API provider is unavailable.

The application has a React frontend and a FastAPI backend, with the backend containerized using Docker and deployed separately from the frontend.

## Live Demo

- **Live Application:** https://lyftrai-chatbot.netlify.app
- **Backend API:** https://lyftr-ai-backend-kwno.onrender.com
- **Health Check:** https://lyftr-ai-backend-kwno.onrender.com/health
- **GitHub Repository:** https://github.com/shagun25408/lyftrAI-assignment

## Features

- **AI-powered conversations:** Generates responses using Google's Gemini API through LiteLLM.
- **Conversation memory:** Maintains conversation history within a session so follow-up questions have context.
- **Response caching:** Stores responses to avoid unnecessary API calls when the same question is repeated in the same context.
- **Automatic API fallback:** Attempts another configured API key when a provider request fails.
- **Failure handling:** Handles provider errors and returns appropriate responses instead of leaving requests unresolved.
- **Session history:** Stores conversation messages using SQLite.
- **REST API:** Provides a FastAPI backend with interactive API documentation.
- **Docker support:** Packages the backend for consistent deployment.
- **Cloud deployment:** Frontend and backend are deployed independently.

## Tech Stack

| Area | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| AI Integration | Google Gemini, LiteLLM |
| Database | SQLite |
| Containerization | Docker |
| Frontend Hosting | Netlify |
| Backend Hosting | Render |
| Version Control | Git, GitHub |

## Project Architecture

The application follows a simple frontend-backend architecture.

1. The user sends a message through the React frontend.
2. The frontend sends the request to the FastAPI backend.
3. The backend checks whether a matching response is available in the cache.
4. If there is no cache hit, the backend sends the conversation context to Gemini.
5. If a configured API key fails, the backend attempts another available key.
6. The response is returned to the frontend and the conversation is stored in the database.

```text
                 User
                  |
                  v
          React + Vite Frontend
                  |
                  v
             FastAPI Backend
                  |
          +-------+-------+
          |               |
          v               v
     Cache Check      Session History
          |
     Cache Miss
          |
          v
       LiteLLM
          |
          v
      Google Gemini
          |
     API Fallback
          |
          v
      AI Response
          |
          v
       Frontend
```

## Project Structure

```text
lyftrAI-assignment/
│
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   └── services/
│   │       └── llm_service.py
│   ├── tests/
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       └── lib/
│           └── api.ts
│
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

*The structure above highlights the main application files; additional frontend and backend modules are omitted for readability.*

## ⚙️ Getting Started

Follow these steps to run Lyftr AI locally.

### 1. Clone the repository

```bash
git clone https://github.com/shagun25408/lyftrAI-assignment.git
cd lyftrAI-assignment
```

### 2. Configure the backend

Navigate to the backend directory:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv venv
```

On Windows:

```powershell
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file using the provided `.env.example` as a reference. Configure the required environment variables:

```env
LLM_API_KEYS=your_gemini_api_key
LLM_MODEL=gemini/gemini-3.5-flash-lite
DATABASE_URL=sqlite:///./app.db
ALLOWED_ORIGINS=http://localhost:3000
CACHE_ENABLED=true
ENABLE_FAILURE_SIMULATION=false
```

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### 3. Configure the frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed by Vite in your terminal.

## Environment Variables

### Backend

| Variable | Description |
|---|---|
| `LLM_API_KEYS` | Comma-separated Gemini API keys used by the backend |
| `LLM_MODEL` | LLM model identifier |
| `DATABASE_URL` | Database connection string |
| `ALLOWED_ORIGINS` | Frontend origins allowed by CORS |
| `CACHE_ENABLED` | Enables or disables response caching |
| `ENABLE_FAILURE_SIMULATION` | Enables controlled failure simulation for testing |

### Frontend

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the backend API |

**Important:** Keep API keys in environment variables. Never commit your `.env` files or expose API credentials in frontend code.

## Testing

The backend includes automated tests for API behavior, provider fallback, error handling, and related application logic.

Run the backend tests from the backend directory:

```bash
pytest
```

The frontend production build can be checked using:

```bash
npm run build
```

Failure simulation is intended for testing and should remain disabled in production.

##  Deployment

Lyftr AI is deployed using two separate services:

- **Frontend:** Hosted on [Netlify](https://www.netlify.com/).
- **Backend:** Containerized using Docker and hosted on [Render](https://render.com/).

The frontend communicates with the deployed backend through the `VITE_API_BASE_URL` environment variable.

The backend uses environment variables configured in the Render dashboard for API credentials and application settings.

##  Future Improvements

Some areas I would like to explore further:

- Support for additional LLM providers.
- Persistent response caching across backend restarts.
- Improved conversation management and session controls.
- Better monitoring and analytics for API usage.
- More comprehensive automated frontend testing.

## Author

**Shagun**

B.Tech Computer Science Engineering | DevOps & Cloud

- [GitHub](https://github.com/shagun25408)

---

*Built as a hands-on project to understand the engineering behind AI-powered applications, from API integration and backend development to caching, reliability, and cloud deployment.*
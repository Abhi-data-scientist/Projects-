# REGEX CAFE

REGEX CAFE is a FastAPI-based cafe seat-booking app. Users can register, book seats through text or voice, view bookings, and cancel bookings. Booking and cancellation updates are sent through Twilio WhatsApp.

## Features

- Email/password user registration and login
- Mandatory WhatsApp number during registration
- Live seat availability
- Seat booking and cancellation
- Text and microphone chat
- Voice-to-text with Faster-Whisper
- Text-to-speech replies with Piper
- Per-user chat history in a local JSON file
- WhatsApp booking/cancellation notifications using Twilio

## Tech stack

- FastAPI
- MySQL
- Faster-Whisper
- Piper TTS
- Twilio WhatsApp API
- Redis (optional)

## Project flow

1. User creates an account with email, password, and WhatsApp number.
2. User logs in and sends a text or voice message.
3. Voice messages are converted into text.
4. The app helps the user book, view, or cancel a seat.
5. Booking records are stored in MySQL.
6. Chat messages are stored in `data/chat_history.json`.
7. Twilio sends a WhatsApp notification after booking or cancellation.

## Setup

### 1. Create and activate virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Create MySQL database

```sql
CREATE DATABASE voice_sql_assistant;
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
```

Update these values in `.env`:

```env
MYSQL_PASSWORD=your_mysql_password
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
ENABLE_TTS=true
```

For Twilio Sandbox, join the sandbox from the WhatsApp number that will receive test messages. Phone numbers must use international format, for example `+919876543210`.

### 4. Add Piper model

Place these two files in the `models/` folder:

- `en_US-lessac-medium.onnx`
- `en_US-lessac-medium.onnx.json`

### 5. Run the app

```powershell
python -m uvicorn main:app --reload
```

Open: http://127.0.0.1:8000

## Chat history

Chat history is saved locally at:

```
data/chat_history.json
```

Each message contains the user ID, a secure session fingerprint, role, message content, and timestamp. The raw login token is not stored in the file.

## Main API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Current user |
| POST | `/chat` | Send text or voice chat |
| POST | `/chat/reset` | Reset booking flow |
| GET | `/seats` | View live seats |
| GET | `/bookings/my` | View own bookings |
| POST | `/bookings/{booking_id}/cancel` | Cancel booking |
| GET | `/health` | Check app health |

## Important folders

```
api/        API routes
core/       configuration and database setup
services/   booking, auth, voice, session, and WhatsApp services
static/     browser UI
models/     Piper voice model files
audio/      generated voice replies
data/       local chat history
logs/       application logs
```

## Notes

- MySQL is required for users, seats, bookings, and login sessions.
- Redis is optional; the app works when Redis is disabled.
- WhatsApp notifications do not block a successful booking or cancellation if Twilio is unavailable.
- Do not commit your `.env` file or Twilio credentials.

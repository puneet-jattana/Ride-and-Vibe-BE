# Ride and Vibe Backend

This is the backend server for the Ride and Vibe application, built with Flask.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- On macOS/Linux:
```bash
source venv/bin/activate
```
- On Windows:
```bash
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (optional):
Create a `.env` file in the root directory with the following variables:
```
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
JWT_SECRET_KEY=your-jwt-secret-key
```

5. Run the application:
```bash
python app.py
```

The server will start running on `http://localhost:5000`

## API Endpoints

- `GET /`: Welcome message
- `GET /health`: Health check endpoint

## Project Structure

- `app.py`: Main application file
- `config.py`: Configuration settings
- `requirements.txt`: Project dependencies 
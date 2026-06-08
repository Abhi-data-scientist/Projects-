# Amazon Research Agent 🔍

An AI-powered product research system that searches Amazon products, filters results, ranks products using a custom scoring algorithm, and displays them through a modern Streamlit dashboard.

## Features

* Amazon Product Search using Rainforest API
* FastAPI Backend
* Streamlit Frontend
* Product Scoring & Ranking
* Price Filtering
* CSV Export
* Interactive Dashboard
* REST API Architecture

## Project Structure

```text
AMAZON-RESEARCH-AGENT/
│
├── FastApi/
│   ├── .env
│   ├── fetching.py
│   ├── main.py
│   ├── pydantic_model.py
│   └── scoring.py
│
├── venv/
│
├── frontend.py
├── requirements.txt
└── README.md
```

## Tech Stack

### Backend

* FastAPI
* Pydantic
* Requests

### Frontend

* Streamlit
* Pandas

### API

* Rainforest API

## Installation

### Clone Repository

```bash
git clone https://github.com/Abhi-data-scientist/amazon-research-agent.git

cd amazon-research-agent
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file inside the `FastApi` folder:

```env
RAINFOREST_API_KEY=YOUR_API_KEY
```

## Run Backend

```bash
cd FastApi

uvicorn main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

## Run Frontend

Open a new terminal:

```bash
streamlit run frontend.py
```

Frontend URL:

```text
http://localhost:8501
```

## API Example

POST `/search`

```json
{
  "keyword": "wireless mouse",
  "min_price": 10,
  "max_price": 100,
  "num_results": 10
}
```

## Scoring Logic

Products are ranked based on:

* Product Rating
* Number of Reviews
* Amazon Choice Badge
* Sponsored Product Penalty

Higher score = Better product quality.

## Future Improvements

* Google Sheets Integration
* AI Product Insights
* Product Trend Analysis
* Multi-Marketplace Support
* LLM-based Product Recommendations

## Author

Abhishek

GitHub:
https://github.com/Abhi-data-scientist

Data Science | Machine Learning | FastAPI | AI Automation

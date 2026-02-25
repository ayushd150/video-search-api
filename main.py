from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI(title="Sentiment API")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

class CommentRequest(BaseModel):
    comment: str

class CommentResponse(BaseModel):
    sentiment: str
    rating: int

schema = {
    "name": "sentiment_response",
    "schema": {
        "type": "object",
        "properties": {
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral"]
            },
            "rating": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5
            }
        },
        "required": ["sentiment", "rating"],
        "additionalProperties": False
    }
}

@app.post("/comment", response_model=CommentResponse)
def analyze_comment(data: CommentRequest):

    if not data.comment.strip():
        raise HTTPException(status_code=400, detail="Empty comment")

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Classify sentiment strictly."},
                {"role": "user", "content": data.comment}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": schema
            },
        )

        return response.choices[0].message.parsed

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
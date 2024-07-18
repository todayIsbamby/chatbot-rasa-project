import asyncio
import datetime
import pymysql
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

class Question(BaseModel):
    message: str

@app.post("/question")
async def answer_question(question: Question):
    # Logging received question
    print(f"Received question: {question}")

    # Capture the time when the question is sent to Rasa
    rasa_request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # Save the question to the database before sending it to Rasa
    save_question_to_db(question.message, rasa_request_time)
    await asyncio.sleep(1)  # Delay for 1 second

    # Replace with your Rasa endpoint URL
    rasa_endpoint = "http://localhost:5005/webhooks/rest/webhook"

    try:
        # Send request to Rasa API
        async with httpx.AsyncClient() as client:
            response = await client.post(rasa_endpoint, json={"message": question.message})
            response.raise_for_status()
            output = response.json()
            print(output)
            # Capture the time when the response is received from Rasa
            rasa_response_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            # Check if the response from Rasa is not empty
            if not output or "text" not in output[0]:
                return {"message": "คำถามไม่ตรงกับคำตอบที่มีอยู่ โปรดลองอีกครั้ง"}

            # Get the "text" value from Rasa's response
            text_value = output[0]["text"]

            # Retrieve the answer from the database
            answer = get_answer_from_db(text_value)

            if answer==None:
                # If not found in the database, save the Rasa response directly
                save_answer_to_db(text_value, rasa_response_time)
                return {"message": text_value}

            # If an answer is found in the database, return it
            data = {"message": answer}

            # Save the answer to the database with the response time from Rasa
            save_answer_to_db(data["message"], rasa_response_time)

            return data

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (e.g., 4xx, 5xx)
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    except Exception as e:
        # Handle unexpected exceptions
        raise HTTPException(status_code=500, detail="Internal server error")

def save_question_to_db(question_message, request_time):
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='myadmin',
            db='sys',
        )
        cur = conn.cursor()

        # Insert the question message into the tb_history_chat table
        cur.execute("""
            INSERT INTO tb_history_chat (chat_id, message, message_type, time_sent)
            VALUES (%s, %s, %s, %s)
        """, (1, question_message, 1, request_time))

        conn.commit()
        cur.close()
        conn.close()

    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {e}")

def save_answer_to_db(answer_message, response_time):
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='myadmin',
            db='sys',
        )
        cur = conn.cursor()

        # Insert the answer message into the tb_history_chat table
        cur.execute("""
            INSERT INTO tb_history_chat (chat_id, message, message_type, time_sent)
            VALUES (%s, %s, %s, %s)
        """, (1, answer_message, 0, response_time))

        conn.commit()
        cur.close()
        conn.close()

    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {e}")

def get_answer_from_db(code):
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='myadmin',
            db='sys',
        )
        cur = conn.cursor()

        # Retrieve the answer from the database
        cur.execute("""
            SELECT answer
            FROM prompt
            WHERE code = %s
        """, (code,))
        output = cur.fetchone()

        cur.close()
        conn.close()

        return output[0] if output else None

    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=80)

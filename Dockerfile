FROM python:3.11-slim

WORKDIR /main

COPY . /main

RUN pip install -r requirements.txt

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run frontend.py --server.address=0.0.0.0 --server.port=8501"]

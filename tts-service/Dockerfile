FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/models && python3 -c "\
import urllib.request, shutil;\
voice='en_US-lessac-medium';\
base='https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/';\
urllib.request.urlretrieve(base+voice+'.onnx', '/app/models/'+voice+'.onnx');\
urllib.request.urlretrieve(base+voice+'.onnx.json', '/app/models/'+voice+'.onnx.json');\
shutil.move('/app/models/'+voice+'.onnx.json', '/app/models/'+voice+'.json')"

COPY ./app ./app

EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]

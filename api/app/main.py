from fastapi import FastAPI

app = FastAPI(
    title="Cloud Intelligence Platform",
    description="Control plane for AWS discovery, CMDB sync, and drift detection",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
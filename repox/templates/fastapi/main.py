from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "ok", "repo": "{{repo_name}}", "author": "{{author}}"}

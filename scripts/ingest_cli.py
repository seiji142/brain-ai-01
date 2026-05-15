import typer, json
from pathlib import Path
from ai_architect.pipelines.ingest import ingest_episode

app = typer.Typer()

@app.command()
def main(file: str):
    p = Path(file)
    data = json.loads(p.read_text(encoding="utf-8"))
    res = ingest_episode(data)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    app()

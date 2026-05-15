import typer, json
from typing import Optional
from ai_architect.pipelines.evaluate import evaluate_query

app = typer.Typer()

@app.command()
def main(query: str, project: Optional[str] = None, top_k: int = 5, collection: str = "semantic"):
    res = evaluate_query(query=query, project=project, top_k=top_k, collection=collection)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    app()

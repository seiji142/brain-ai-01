import typer, json
from typing import Optional
from ai_architect.core.retrieval import retrieve

app = typer.Typer()

@app.command()
def main(query: str, top_k: int = 5, project: Optional[str] = None, collection: str = "semantic",
         tags: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
    tag_list = tags.split(",") if tags else None
    res = retrieve(query=query, top_k=top_k, project=project, tags=tag_list,
                   date_from=date_from, date_to=date_to, collection=collection)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    app()

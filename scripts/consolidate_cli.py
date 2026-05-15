import typer, json
from typing import Optional
from ai_architect.pipelines.consolidate import consolidate_project

app = typer.Typer()

@app.command()
def main(project: Optional[str] = None):
    res = consolidate_project(project)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    app()

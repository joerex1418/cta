from rich.theme import Theme
from rich.style import Style
from rich.console import Console

console = Console(
    theme=Theme({
        "json.brace": Style(bold=True),
        "json.key": Style(color="cyan"),
        "json.str": Style(color="bright_magenta"),
        "json.number": Style(color="yellow", bold=True),
        "json.bool_true": Style(color="bright_green", italic=True),
        "json.bool_false": Style(color="bright_red", italic=True),
        "json.null": Style(dim=True, italic=True)
    })
)

def ppjson(data):
    try:
        console.print_json(data=data.json())
    except:
        console.print_json(data=data)
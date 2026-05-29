import requests


def decode_secret_message(url: str) -> None:
    doc_id = url.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/document/d/e/{doc_id}/pub"

    response = requests.get(export_url)
    response.raise_for_status()
    lines = response.text.splitlines()

    grid = {}
    max_x = 0
    max_y = 0

    for line in lines:
        parts = line.split("\t")
        if len(parts)!=3:
            continue
        char,x_str, y_str = parts
        try:
            x,y = int(x_str.strip()), int(y_str.strip())
        except ValueError:
            continue

        grid[(x,y)] = char
        max_x = max(max_x,x)
        max_y = max(max_y,y)

        for y in range(max_y+1):
            row = ""
            for x in range(max_x+1):
                row+=grid.get((x,y),"")
            print(row)



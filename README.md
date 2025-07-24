# clocpot (count lines of code, plot over time)

## Install dependencies
```
brew install git
brew install cloc
brew install uv
uv pip install -r pyproject.toml
```

## Plot all lines of code in the main branch
```sh
uv run main.py /path/to/repo -b main
```

## Plot all lines of code and lines by language in the main branch
```sh
uv run main.py /path/to/repo -b main --all
```

## Example output
![image](./example_output.png)


<!-- ## init (don't run these, I just have them here so I don't forget) -->
<!-- ```sh -->
<!-- uv init -->
<!-- uv add matplotlib -->
<!-- uv pip install -->
<!-- ``` -->

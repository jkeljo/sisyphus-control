==========================
Setting up dev environment
==========================

This repo uses Poetry to manage its dependencies, and pre-commit for pre-commit hooks.

1. `pip install poetry` to add it to your Python installation if you don't have it already
3. `poetry install` to set up a venv with all needed dependencies
4. `poetry run pytest` (for example) to run tests
5. `poetry shell` to get a shell inside the poetry-created venv

For testing with a live table, use `poetry shell` and then `python -m shell` to send commands to the table. If you're messing around with the socket code at all, also send commands to the table from your Sisyphus app and verify that shell.py shows the state changes occurring.

For testing with Home Assistant:
1. Bump the version in `pyproject.toml`
2. Run `poetry build -f wheel` to create a new package in the `dist` folder
3. `scp` that wheel (it will be named something like `sisyphus_control-2.2.2-py3-none-any.whl`) to your Home Assistant server
4. `ssh` into your Home Assistant server and run `PYTHONUSERBASE=/config/deps pip3 install --user --no-cache-dir --prefix= --no-dependencies <path to wheel>
`, substituting the path to the wheel file you uploaded previously. You can delete the wheel when you're done.
5. In the Home Assistant repo, edit the `sisyphus` component's `manifest.json` to specify the new version number
6. `scp` all the files in the `sisyphus` component to `config/custom_components/sisyphus` on your Home Assistant server
7. Restart Home Assistant

When you're done, you can delete anything sisyphus related from the `config/deps` folder and restart HA again.
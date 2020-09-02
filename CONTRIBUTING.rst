==========================
Setting up dev environment
==========================

A Visual Studio Code workspace is provided in the repo. Run ``dev_setup.sh`` to create and populate the ``virtualenv``, then open
the repo in VS Code.

For testing with a live table, use shell.py to send commands to the table. If you're messing around with the socket code at all, also send commands to the table from your Sisyphus app and verify that shell.py shows the state changes occurring.

For testing with Home Assistant:
1. Bump the version in `setup.py`
2. Run `python -m setup bdist_wheel` to create a new package in the `dist` folder
3. `scp` that wheel (it will be named something like `sisyphus_control-2.2.2-py3-none-any.whl`) to your Home Assistant server
4. `ssh` into your Home Assistant server and run `PYTHONUSERBASE=/config/deps pip3 install --user --no-cache-dir --prefix= --no-dependencies <path to wheel>
`, substituting the path to the wheel file you uploaded previously. You can delete the wheel when you're done.
5. In the Home Assistant repo, edit the `sisyphus` component's `manifest.json` to specify the new version number
6. `scp` all the files in the `sisyphus` component to `config/custom_components/sisyphus` on your Home Assistant server
7. Restart Home Assistant

When you're done, you can delete anything sisyphus related from the `config/deps` folder and restart HA again.
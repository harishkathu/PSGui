# Power Supply GUI

GUI to control PS2000 Power supply and serial relay module

## Known Limitations

1) **Timer accuracy for toggle**: All toggle timers are OS dependant for their accuracy. Though all toggles have a resolution of 1ms, but in real-world this will not be the case. Toggle timers might toggle later based on the system resource. If the toggle interval is very short <30ms the toggle might happen later (or in somecases only once per interval).

## Build and Generate

Generate Layout.py

```shell
pyuic5 -o layout.py ./Layout.ui
```

Generate resource_rc.py

```shell
pyrcc5 -o resources_rc.py ./resources.qrc
```

Build to exe

```shell
# remember to generate latest layout.py and rsources_rc.py
pyinstaller --clear ps_gui.spec
```

## Help

Harish Kathalingam

Mail: <kathalingam.harish@continental-corporation.com>

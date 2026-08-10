# Physical Cursor Control on Windows

## When the User Wants Real Mouse Control

If the user says "control my cursor", "click on Edge", "move my mouse", or "type in the address bar" — they want **physical desktop mouse control**, not web element interaction.

### Method: ctypes (no pip install needed)

```python
import ctypes

# Get screen dimensions
screen_w = ctypes.windll.user32.GetSystemMetrics(0)
screen_h = ctypes.windll.user32.GetSystemMetrics(1)

# Move cursor to position (x, y)
ctypes.windll.user32.SetCursorPos(x, y)

# Left click
ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP

# Right click
ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
ctypes.windll.user32.mouse_event(10, 0, 0, 0, 0) # MOUSEEVENTF_RIGHTUP
```

### Limitations
- Cannot interact with elevated (admin) windows from non-elevated process
- UAC prompts cannot be automated without admin rights
- Some apps block synthetic input
- Screen coordinates depend on DPI scaling: `ctypes.windll.shcore.GetScaleFactorForDevice(0)` returns percentage (100, 125, 150...)

### Alternative: pyautogui (if installed)
```python
import pyautogui
pyautogui.moveTo(x, y)
pyautogui.click()
pyautogui.typewrite('hello world', interval=0.05)
pyautogui.press('enter')
```

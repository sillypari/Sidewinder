from rich.text import Text
from sidewinder.ui.components import LogoWidget

try:
    widget = LogoWidget()
    text_content = widget.render()
    t = Text.from_markup(text_content)
    print("Logo parsed successfully!")
except Exception as e:
    print("Logo error:", type(e), e)

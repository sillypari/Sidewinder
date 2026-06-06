import pytest
from textual.app import App
from textual.widgets import Input, OptionList, Checkbox, Static
from sidewinder.ui.screens import CommandPaletteScreen, ScanOptionsScreen, ScanScreen, ThemeSelectScreen
from sidewinder.ui.theme_loader import register_themes
from sidewinder.core.config import SidewinderConfig


class MockApp(App):
    CSS_PATH = "../sidewinder/ui/colors.tcss"
    
    def __init__(self, screen_class):
        super().__init__()
        self.screen_class = screen_class
        self.settings = SidewinderConfig.load()
        register_themes(self, self.settings)

    def on_mount(self) -> None:
        self.push_screen(self.screen_class())


@pytest.mark.asyncio
async def test_command_palette_navigation():
    app = MockApp(CommandPaletteScreen)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Get option list and input
        olist = app.screen.query_one(OptionList)
        inp = app.screen.query_one(Input)

        # Initially, the first option should be highlighted (0)
        assert olist.highlighted == 0

        # Press down key to move highlight to 1
        await pilot.press("down")
        assert olist.highlighted == 1

        # Press up key to move highlight to 0
        await pilot.press("up")
        assert olist.highlighted == 0

        # Filter the options by writing in the input
        await pilot.click(Input)
        await pilot.press(*list("help"))
        await pilot.pause()

        # The options should be filtered, and first filtered item should be highlighted (0)
        assert olist.option_count > 0
        assert olist.highlighted == 0

        # Pressing enter should trigger submit / action_submit
        await pilot.press("enter")
        await pilot.pause()
        
        # Verify CommandPaletteScreen is dismissed (the current active screen is now HelpScreen)
        assert app.screen.__class__.__name__ == "HelpScreen"


@pytest.mark.asyncio
async def test_scan_options_submission():
    app = MockApp(ScanOptionsScreen)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Get channels input
        inp = app.screen.query_one(Input)
        assert inp.id == "channels-input"

        # Pressing Enter while channels input is active should trigger start_scan and push ScanScreen
        await pilot.click(Input)
        await pilot.press("enter")
        await pilot.pause()

        # Verify ScanScreen is pushed
        assert app.screen.__class__.__name__ == "ScanScreen"


@pytest.mark.asyncio
async def test_theme_live_preview():
    app = MockApp(ThemeSelectScreen)
    async with app.run_test() as pilot:
        await pilot.pause()

        olist = app.screen.query_one(OptionList)
        assert olist.highlighted is not None
        
        # Find index of "cyberpunk"
        cyberpunk_idx = None
        for i, opt in enumerate(olist._options):
            if opt.id == "cyberpunk":
                cyberpunk_idx = i
                break
        
        assert cyberpunk_idx is not None, "cyberpunk theme not found in list"

        # Check initial style of theme list background
        theme_list = app.screen.query_one("#theme-list")
        initial_bg = theme_list.styles.background
        print("Initial theme list background:", initial_bg)

        # Navigate to cyberpunk in the option list
        olist.highlighted = cyberpunk_idx
        await pilot.pause()

        # Check that the app theme has changed to cyberpunk
        assert app.theme == "cyberpunk"
        
        # Check computed background after change
        new_bg = theme_list.styles.background
        print("Cyberpunk theme list background:", new_bg)
        
        # Background should have updated since cyberpunk's panel color is different from midnight's
        assert new_bg != initial_bg

        # Press enter to select and confirm
        await pilot.press("enter")
        await pilot.pause()

        # Check that settings.theme was saved
        assert app.settings.theme == "cyberpunk"

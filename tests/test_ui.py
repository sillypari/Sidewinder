import pytest
from textual.app import App
from textual.widgets import Input, OptionList, Checkbox, Static
from sidewinder.ui.screens import CommandPaletteScreen, ScanOptionsScreen, ScanScreen, ThemeSelectScreen
from sidewinder.ui.theme_loader import register_themes
from sidewinder.core.config import SidewinderConfig
from sidewinder.core.session import Session


class MockApp(App):
    CSS_PATH = "../sidewinder/ui/colors.tcss"
    
    def __init__(self, screen_class):
        super().__init__()
        self.screen_class = screen_class
        # Use a default config and mock save to prevent mutating the real config.json
        self.settings = SidewinderConfig()
        self.settings.save = lambda *args, **kwargs: None
        self.session = Session()
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
        
        # Determine current theme and pick a different target theme
        initial_theme = app.theme
        target_theme = "cyberpunk" if initial_theme != "cyberpunk" else "midnight"
        
        # Find index of target theme
        target_idx = None
        for i, opt in enumerate(olist._options):
            if opt.id == target_theme:
                target_idx = i
                break
        
        assert target_idx is not None, f"{target_theme} theme not found in list"

        # Check initial style of theme list background
        theme_list = app.screen.query_one("#theme-list")
        initial_bg = theme_list.styles.background
        print(f"Initial theme ({initial_theme}) list background:", initial_bg)

        # Navigate to target theme in the option list
        olist.highlighted = target_idx
        await pilot.pause()

        # Check that the app theme has changed to target theme
        assert app.theme == target_theme
        
        # Check computed background after change
        new_bg = theme_list.styles.background
        print(f"New theme ({target_theme}) list background:", new_bg)
        
        # Background should have updated
        assert new_bg != initial_bg

        # Press enter to select and confirm
        await pilot.press("enter")
        await pilot.pause()

        # Check that settings.theme was saved
        assert app.settings.theme == target_theme


@pytest.mark.asyncio
async def test_responsive_sidebar_collapse():
    app = MockApp(ScanScreen)
    async with app.run_test() as pilot:
        # Resize to > 120 width
        await pilot.resize_terminal(130, 40)
        await pilot.pause()
        
        # Verify sidebar and separator are displayed
        sidebar = app.screen.query_one("#right-sidebar")
        sep = app.screen.query_one("#sidebar-sep")
        assert sidebar.display is True
        assert sep.display is True
        
        # Resize to < 120 width
        await pilot.resize_terminal(100, 40)
        await pilot.pause()
        
        # Verify sidebar and separator are hidden
        assert sidebar.display is False
        assert sep.display is False


@pytest.mark.asyncio
async def test_session_status_screen():
    from sidewinder.ui.screens import SessionStatusScreen
    from sidewinder.core.session import Network
    app = MockApp(SessionStatusScreen)
    # Configure the session
    app.session.selected_target = Network(
        bssid="11:22:33:44:55:66",
        channel=1,
        signal=-40,
        privacy="WPA2",
        cipher="CCMP",
        auth="PSK",
        essid="TestTarget"
    )
    app.session.captures = ["/tmp/cap1.cap", "/tmp/cap2.cap"]
    
    async with app.run_test() as pilot:
        await pilot.pause()
        
        # Verify the details are rendered
        details = app.screen.query_one("#status-details", Static)
        text = str(details.render())
        assert "TestTarget" in text
        assert "2 captures" in text
        assert "11:22:33:44:55:66" in text
        
        # Go back
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_session_list_screen(tmp_path):
    from unittest.mock import patch
    from sidewinder.ui.screens import SessionListScreen
    from sidewinder.core.session import Session, Network
    
    # Create some mock session files in a temp directory
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    
    s1 = Session()
    s1.id = "11111111-2222-3333-4444-555555555555"
    s1.selected_target = Network(
        bssid="AA:BB:CC:DD:EE:FF",
        channel=6,
        signal=-50,
        privacy="WPA2",
        cipher="CCMP",
        auth="PSK",
        essid="TestNetwork1"
    )
    # Save the session inside the patched context to ensure all directories align
    def mock_expand(path):
        import os
        path_str = str(path)
        if path_str.startswith("~/.sidewinder"):
            res = path_str.replace("~/.sidewinder", str(tmp_path).replace("\\", "/"))
            return os.path.abspath(res)
        return os.path.abspath(os.path.expanduser(path_str))
        
    with patch("sidewinder.core.config.expand_user_path", side_effect=mock_expand):
        s1.save(str(sessions_dir / f"{s1.id}.json"))
        
        app = MockApp(SessionListScreen)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            # Check table contents
            from textual.widgets import DataTable
            table = app.screen.query_one("#sessions-table", DataTable)
            assert table.row_count == 1
            
            # Focus table to receive key events
            table.focus()
            await pilot.pause()
            
            # Navigate and load session
            await pilot.press("enter")
            await pilot.pause()
            
            # Verify the session is loaded in the app
            assert app.session.id == s1.id
            assert app.session.selected_target.essid == "TestNetwork1"


@pytest.mark.asyncio
async def test_session_list_screen_delete(tmp_path):
    from unittest.mock import patch
    from sidewinder.ui.screens import SessionListScreen
    from sidewinder.core.session import Session
    import os
    
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    
    s1 = Session()
    s1.id = "22222222-3333-4444-5555-666666666666"
    
    def mock_expand(path):
        path_str = str(path)
        if path_str.startswith("~/.sidewinder"):
            res = path_str.replace("~/.sidewinder", str(tmp_path).replace("\\", "/"))
            return os.path.abspath(res)
        return os.path.abspath(os.path.expanduser(path_str))
        
    with patch("sidewinder.core.config.expand_user_path", side_effect=mock_expand):
        s1.save(str(sessions_dir / f"{s1.id}.json"))
        
        app = MockApp(SessionListScreen)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            from textual.widgets import DataTable
            table = app.screen.query_one("#sessions-table", DataTable)
            assert table.row_count == 1
            
            # Focus table
            table.focus()
            await pilot.pause()
            
            # Delete the session
            await pilot.press("d")
            await pilot.pause()
            
            # Verify the row is gone and file is deleted
            assert table.row_count == 0
            assert not os.path.exists(str(sessions_dir / f"{s1.id}.json"))




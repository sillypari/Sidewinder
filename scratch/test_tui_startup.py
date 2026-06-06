import pytest
import asyncio
from sidewinder.ui.app import SidewinderApp
from sidewinder.ui.components import BottomNavBar

async def test_startup():
    app = SidewinderApp(dev_mode=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        
        # Verify BottomNavBar is mounted
        nav_bar = app.screen.query_one(BottomNavBar)
        print("BottomNavBar widget found in active screen:", nav_bar)
        
        # Verify it renders successfully
        rendered_text = nav_bar.render()
        print("BottomNavBar render output:", repr(rendered_text))
        assert rendered_text != ""
        
        print("TUI startup test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_startup())
